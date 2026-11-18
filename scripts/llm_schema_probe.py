"""LB-2：查 LM Studio 什麼時候對技能提議的 JSON schema 回 400。

對 4-L5 那 20 題（＋暖機題）的 schema，各送一個 ``max_tokens`` 很小的請求，記下 HTTP 狀態與回應
本文（不解析內容）。可選 ``oneOf`` 原樣或改 ``anyOf``、``response_format`` 或 ``guided_json``。

用法::

    uv run python scripts/llm_schema_probe.py --model <id> --reasoning-effort none [--keep-oneof]

一次只送一個請求；不平行。結果印成一行一題，``--out`` 另存 JSON。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from trpg.cli.llm import ProposeArgs, propose_requests
from trpg.content.library import load_library
from trpg.llm import load_llm_config
from trpg.llm.client import rewrite_oneof_as_anyof
from trpg.llm.prompts.proposal import build_proposal_prompt

WARMUP_SEED = 999


def probe(
    url: str, body: dict[str, Any], timeout: float
) -> tuple[int | None, str, float, str | None]:
    start = time.perf_counter()
    try:
        response = httpx.post(url, json=body, timeout=timeout)
    except httpx.HTTPError as exc:
        return None, repr(exc), time.perf_counter() - start, None
    finish = None
    try:
        payload = response.json()
        finish = payload["choices"][0].get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError):
        pass
    return response.status_code, response.text[:600], time.perf_counter() - start, finish


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--keep-oneof", action="store_true", help="不把 oneOf 改成 anyOf")
    parser.add_argument(
        "--mode", default="response_format", choices=["response_format", "guided_json"]
    )
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--only", type=int, nargs="*", default=None, help="只測這幾題（0＝暖機）")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    config = load_llm_config()
    library = load_library()
    items = [(0, *propose_requests(library, ProposeArgs(count=1, seed=WARMUP_SEED))[0])]
    items += [
        (i, r, s) for i, (r, s) in enumerate(propose_requests(library, ProposeArgs(20, 0)), 1)
    ]
    url = config.base_url.rstrip("/") + "/chat/completions"
    rows: list[dict[str, Any]] = []
    for index, request, _seed in items:
        if args.only is not None and index not in args.only:
            continue
        prompt = build_proposal_prompt(library, request)
        schema = (
            prompt.json_schema if args.keep_oneof else rewrite_oneof_as_anyof(prompt.json_schema)
        )
        body: dict[str, Any] = {
            "model": args.model,
            "messages": prompt.messages,
            "temperature": 0.0,
            "max_tokens": args.max_tokens,
        }
        if args.reasoning_effort:
            body["reasoning_effort"] = args.reasoning_effort
        if args.mode == "response_format":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema, "strict": True},
            }
        else:
            body["guided_json"] = schema
        status, text, seconds, finish = probe(url, body, config.timeout_s)
        row = {
            "index": index,
            "status": status,
            "seconds": round(seconds, 2),
            "finish_reason": finish,
            "schema_chars": len(json.dumps(schema, ensure_ascii=False)),
            "body": text if status != 200 else text[:200],  # noqa: PLR2004
        }
        rows.append(row)
        print(
            f"{index:>2}｜HTTP {status}｜{seconds:.1f} 秒｜{finish}｜{row['schema_chars']}｜"
            f"{text[:160]!r}",
            flush=True,
        )
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
