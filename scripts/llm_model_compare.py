"""本機 LLM 模型比較（Phase LB-1）：用 4-L5 那組 20 題（``trpg llm propose -n 20``，seed 0）
量一個模型的速度與品質，輸出 JSON 原始資料。

用法::

    uv run python scripts/llm_model_compare.py --model qwen3.6-35b-a3b
    uv run python scripts/llm_model_compare.py --model <gemma id> --reasoning-effort none

- 設定照 ``config/llm.toml``（＋環境變數）；``--model``／``--reasoning-effort`` 只透過環境變數
  ``TRPG_LLM_MODEL``／``TRPG_LLM_REASONING_EFFORT`` 覆寫這一次執行，不改任何設定檔。
- 先跑 1 題暖機（另一個種子的題目、只試 1 次，不計入結果），把載入模型的時間排除在外。
- 每題 ＝ 技能提議（重試迴圈，最多 ``max_retries`` 次）＋ 通過時的命名（``name_skill``，
  與遊戲相同）。
- 一次只送一個請求；不平行。
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from trpg.cli.llm import ProposeArgs, propose_requests
from trpg.content.library import ContentLibrary, load_library
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.naming import name_skill
from trpg.llm.propose import ProposalOutcome, propose_skill
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import FallbackError
from trpg.skillgen.proposal_subset import ProposalRequest

DEFAULT_OUT_DIR = Path("docs/phases/LB-1資料")
WARMUP_SEED = 999
HTTP_OK = 200
"""暖機題目的輪替種子（和正式的 seed 0 題目不同）。"""

FORMAT_CODES = frozenset(
    {
        "json_invalid",
        "json_type",
        "missing",
        "extra_forbidden",
        "literal_error",
        "union_tag_invalid",
        "union_tag_not_found",
        "value_error",
        "string_type",
        "int_type",
        "int_parsing",
        "list_type",
        "dict_type",
        "model_type",
        "bool_type",
        "enum",
        "too_short",
        "too_long",
        "greater_than_equal",
        "less_than_equal",
        "string_too_short",
        "string_too_long",
    }
)
"""pydantic 層的錯誤代碼（格式錯）；其餘（``budget.*``、``keyword.*``…）算引擎合法性檢查。"""


@dataclass(slots=True)
class CallLog:
    """一次 HTTP 呼叫：哪一步、耗時、狀態、結束原因、token 數。"""

    step: str
    seconds: float
    status: int | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    error: str | None = None


@dataclass(slots=True)
class RecordingTransport(httpx.BaseTransport):
    """包住 ``httpx.HTTPTransport``，記下每次呼叫的耗時與 ``usage``（不改請求與回應）。"""

    inner: httpx.BaseTransport = field(default_factory=httpx.HTTPTransport)
    step: str = "propose"
    calls: list[CallLog] = field(default_factory=list)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        start = time.perf_counter()
        try:
            response = self.inner.handle_request(request)
            response.read()
        except httpx.HTTPError as exc:
            self.calls.append(CallLog(self.step, time.perf_counter() - start, error=repr(exc)))
            raise
        log = CallLog(self.step, time.perf_counter() - start, status=response.status_code)
        _fill_usage(log, response.content)
        self.calls.append(log)
        return response

    def close(self) -> None:
        self.inner.close()


def _fill_usage(log: CallLog, content: bytes) -> None:
    try:
        payload = json.loads(content)
    except ValueError:
        return
    if not isinstance(payload, dict):
        return
    choices = payload.get("choices") or [{}]
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        log.finish_reason = choices[0].get("finish_reason")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return
    log.prompt_tokens = usage.get("prompt_tokens")
    log.completion_tokens = usage.get("completion_tokens")
    details = usage.get("completion_tokens_details")
    if isinstance(details, dict):
        log.reasoning_tokens = details.get("reasoning_tokens")


def _describe(request: ProposalRequest) -> str:
    keywords = "、".join(request.keywords) or "無關鍵字"
    return f"{request.tier} 階／{request.rarity}／{request.skeleton or '不限骨架'}／{keywords}"


def _run_one(
    library: ContentLibrary,
    client: OpenAICompatClient,
    transport: RecordingTransport,
    request: ProposalRequest,
    seed: int,
    *,
    attempts: int,
    taken: set[str],
) -> dict[str, Any]:
    """一題：提議（＋通過時命名），回傳這題的原始紀錄。"""
    transport.calls = []
    transport.step = "propose"
    start = time.perf_counter()
    row: dict[str, Any] = {"request": _describe(request), "seed": seed}
    try:
        outcome: ProposalOutcome = propose_skill(
            client,
            library,
            request,
            ProposalContext(request.tier, request.rarity),
            seed=seed,
            max_attempts=attempts,
            clock=time.perf_counter,
        )
    except (FallbackError, ValueError) as exc:
        row.update(source="failed", error=str(exc), seconds=time.perf_counter() - start)
        row["calls"] = [_call_dict(c) for c in transport.calls]
        return row
    propose_seconds = time.perf_counter() - start
    row.update(
        source=outcome.source,
        attempts=outcome.attempts,
        codes=[list(c) for c in outcome.codes],
        repaired=[list(r.repaired) for r in outcome.records],
        reason=outcome.reason,
        first_pass=outcome.source == "llm" and outcome.attempts == 1,
        propose_seconds=round(propose_seconds, 3),
    )
    skill = outcome.skill
    naming_seconds = 0.0
    if outcome.source == "llm":
        transport.step = "naming"
        name_start = time.perf_counter()
        named = name_skill(client, library, skill, taken=taken, max_attempts=attempts)
        naming_seconds = time.perf_counter() - name_start
        taken.add(named.text.name_zh)
        row.update(
            naming_source=named.source,
            naming_attempts=named.attempts,
            naming_codes=list(named.codes),
            name_zh=named.text.name_zh,
            concept=named.text.concept,
            cast_flavor=named.text.cast_flavor,
        )
    else:
        row.update(
            name_zh=skill.name_zh,
            concept=skill.narrative.concept,
            cast_flavor=skill.narrative.cast_flavor,
        )
    row["skill_kind"] = skill.kind
    row["effects"] = [e.type for e in skill.effects]
    row["naming_seconds"] = round(naming_seconds, 3)
    row["seconds"] = round(propose_seconds + naming_seconds, 3)
    row["calls"] = [_call_dict(c) for c in transport.calls]
    return row


def _call_dict(call: CallLog) -> dict[str, Any]:
    data = {k: getattr(call, k) for k in CallLog.__slots__}
    data["seconds"] = round(call.seconds, 3)
    return {k: v for k, v in data.items() if v is not None}


def _failure_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """所有嘗試的錯誤代碼，分成 LLM 呼叫層、格式（pydantic）、引擎合法性三類。"""
    groups: dict[str, Counter[str]] = {"llm": Counter(), "format": Counter(), "engine": Counter()}
    for row in rows:
        for attempt in row.get("codes", []):
            for code in attempt:
                if code.startswith("llm."):
                    groups["llm"][code] += 1
                elif code in FORMAT_CODES:
                    groups["format"][code] += 1
                else:
                    groups["engine"][code] += 1
    return {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))) for k, v in groups.items()}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """一個模型的摘要：每題秒數、一次通過率、退回率、失敗類型。"""
    done = [r for r in rows if r["source"] != "failed"]
    seconds = [r["seconds"] for r in done]
    calls = [c for r in rows for c in r.get("calls", [])]
    tokens = [c for c in calls if c.get("completion_tokens") and c.get("status") == HTTP_OK]
    count = len(done)
    first = sum(1 for r in done if r["first_pass"])
    fallback = sum(1 for r in done if r["source"] != "llm")
    naming_llm = sum(1 for r in done if r.get("naming_source") == "llm")
    naming_total = sum(1 for r in done if r["source"] == "llm")
    return {
        "questions": len(rows),
        "completed": count,
        "first_pass": first,
        "first_pass_permille": first * 1000 // count if count else 0,
        "fallback": fallback,
        "fallback_permille": fallback * 1000 // count if count else 0,
        "sources": dict(Counter(r["source"] for r in rows)),
        "mean_attempts": round(sum(r["attempts"] for r in done) / count, 2) if count else 0,
        "seconds_median": round(statistics.median(seconds), 2) if seconds else None,
        "seconds_max": round(max(seconds), 2) if seconds else None,
        "seconds_mean": round(statistics.fmean(seconds), 2) if seconds else None,
        "propose_seconds_median": (
            round(statistics.median(r["propose_seconds"] for r in done), 2) if done else None
        ),
        "call_seconds_median": (
            round(statistics.median(c["seconds"] for c in calls), 2) if calls else None
        ),
        "calls": len(calls),
        "completion_tokens_per_second": (
            round(
                sum(c["completion_tokens"] for c in tokens) / sum(c["seconds"] for c in tokens), 1
            )
            if tokens
            else None
        ),
        "reasoning_tokens": sum(c.get("reasoning_tokens") or 0 for c in calls),
        "naming_llm": naming_llm,
        "naming_total": naming_total,
        "failures": _failure_counts(rows),
    }


def _server_info(base_url: str, model: str) -> dict[str, Any]:
    """LM Studio 的模型資訊（``/api/v0/models``）；拿不到就空。"""
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        payload = httpx.get(f"{root}/api/v0/models", timeout=10).json()
    except (httpx.HTTPError, ValueError):
        return {}
    for item in payload.get("data", []):
        if item.get("id") == model:
            keys = ("arch", "quantization", "compatibility_type", "loaded_context_length", "state")
            return {k: item.get(k) for k in keys}
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--model", required=True, help="LM Studio 的 model id")
    parser.add_argument("--reasoning-effort", default=None, help="例如 none（Gemma）")
    parser.add_argument("-n", "--count", type=int, default=20, help="題數（預設 20）")
    parser.add_argument("--seed", type=int, default=0, help="題目輪替種子（預設 0＝4-L5）")
    parser.add_argument("--out", type=Path, default=None, help="JSON 輸出路徑")
    parser.add_argument("--no-warmup", action="store_true")
    args = parser.parse_args(argv)

    os.environ["TRPG_LLM_MODEL"] = args.model
    if args.reasoning_effort is not None:
        os.environ["TRPG_LLM_REASONING_EFFORT"] = args.reasoning_effort
    config = load_llm_config()
    library = load_library()
    requests = propose_requests(library, ProposeArgs(count=args.count, seed=args.seed))
    transport = RecordingTransport()
    client = OpenAICompatClient(config, transport=transport)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    result: dict[str, Any] = {
        "model": config.model,
        "base_url": config.base_url,
        "reasoning_effort": config.reasoning_effort,
        "enable_thinking": config.enable_thinking,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_s": config.timeout_s,
        "max_retries": config.max_retries,
        "seed": args.seed,
        "started_utc": started,
    }
    try:
        if not args.no_warmup:
            warm_request, warm_seed = propose_requests(
                library, ProposeArgs(count=1, seed=WARMUP_SEED)
            )[0]
            warm = _run_one(
                library, client, transport, warm_request, warm_seed, attempts=1, taken=set()
            )
            result["warmup"] = {k: warm.get(k) for k in ("request", "source", "seconds", "calls")}
            print(f"暖機：{warm.get('seconds', 0):.1f} 秒（{warm['source']}）", flush=True)
        rows: list[dict[str, Any]] = []
        taken: set[str] = set()
        for index, (request, seed) in enumerate(requests, start=1):
            row = _run_one(
                library,
                client,
                transport,
                request,
                seed,
                attempts=config.max_retries,
                taken=taken,
            )
            row["index"] = index
            rows.append(row)
            print(
                f"{index:>3}. {row['request']}｜{row['source']}｜嘗試 {row.get('attempts', 0)}｜"
                f"{row['seconds']:.1f} 秒｜{row.get('name_zh', row.get('error', ''))}",
                flush=True,
            )
    finally:
        client.close()
    result["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    result["server"] = _server_info(config.base_url, config.model)
    result["summary"] = summarize(rows)
    result["rows"] = rows
    out = args.out or DEFAULT_OUT_DIR / f"{args.model.replace('/', '_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    print(
        f"中位數 {summary['seconds_median']} 秒、最慢 {summary['seconds_max']} 秒、"
        f"一次通過 {summary['first_pass']}/{summary['completed']}、"
        f"退回 {summary['fallback']}/{summary['completed']} → {out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
