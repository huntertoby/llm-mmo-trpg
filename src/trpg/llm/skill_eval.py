"""完整技能生成的真模型評估（Phase 4-L9；``docs/phases/Phase4計畫.md`` 4-L9 列與 3C 節 4～6 點）。

三組題目，全部由種子確定性產生（不依賴模型的回答，所以可以平行請求）：

- **升級候選**（:func:`upgrade_items`）：照一輪實際出題的方式——
  :func:`~trpg.skillgen.proposal_topic.make_topic`（稀有度依權重、核心原語依 run 內配額、輪替選單、
  主題詞與反應題機率取自 ``roguelite.yaml``），角色階級 1～3 輪替，半數題目帶一個關鍵字。
  run 內配額用「前面題目抽到的核心原語」累積（每 10 題重設一次，模擬一輪）。合格的技能再請模型
  命名（和實際一輪相同，``make_proposer(naming=client)``）。
- **強制測試**（:func:`forced_items`）：每個開放的核心原語各 ``per`` 題，題目把它設為
  ``core_primitive``。
- **自由測試**（:func:`free_items`）：不指定核心原語、不帶關鍵字，只用輪替選單；統計每個原語出現在
  選單、被選中的次數，並以隨機組合器（:func:`composer_baseline`）的分布對照。

:func:`run_items` 用 ``ThreadPoolExecutor`` 平行呼叫 :func:`~trpg.llm.propose.propose_skill`
（每題一個 client；真模型用 :class:`UsageTransport` 記下每次呼叫的 token 用量、HTTP 狀態與
JSON schema 寫法）。
報表（Markdown 與 CSV）只放摘要與每題明細，不存 prompt。**評估只量測，不改任何設定、hint、權重或
schema**；調整建議由 PM 決定。腳本入口 ``scripts/eval_llm_skills.py``（預設用 Mock）。
"""

from __future__ import annotations

import csv
import io
import json
import statistics
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import httpx

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.client import ChatMessage, LLMClient
from trpg.llm.config import LLMConfig
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.propose import ProposalOutcome, ProposalStats, propose_skill
from trpg.llm.response import clean_response, drop_false_flags
from trpg.shared.rng import Rng
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_fallback import FallbackError
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    SubsetError,
    legal_core_primitives,
    select_subset,
)
from trpg.skillgen.proposal_topic import TOPIC_RARITIES, TopicRequest, make_topic

__all__ = [
    "CallUsage",
    "EvalItem",
    "ItemClient",
    "ItemResult",
    "RecordingClient",
    "Suite",
    "UsageTransport",
    "composer_baseline",
    "csv_text",
    "errors_csv_text",
    "forced_items",
    "forced_table",
    "free_items",
    "free_table",
    "open_core_primitives",
    "percentile",
    "run_items",
    "suite_summary",
    "upgrade_items",
]

type Suite = Literal["upgrade", "forced", "free"]
EVAL_TIERS = (1, 2, 3)
"""評估輪替的角色階級。"""
RUN_LENGTH = 10
"""升級候選的 run 內配額每幾題重設一次（約一輪的 LLM 題數）。"""
KEYWORD_PERMILLE = 500
"""升級候選帶一個關鍵字的機率（‰）。"""
KEYWORD_TRIES = 12
LOW_SHARE_DIVISOR = 3
"""自由測試：選中率低於平均的 1/3 就列出。"""


# ---------------------------------------------------------------------------
# 題目
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvalItem:
    """一個評估題目。"""

    suite: Suite
    index: int
    request: ProposalRequest
    ctx: ProposalContext
    seed: int


def _composable_keywords(library: ContentLibrary) -> list[str]:
    table = library.keywords.by_id()
    return [k for k in library.keywords.ids() if table[k].composable]


def _upgrade_topic(
    library: ContentLibrary, index: int, seed: int, uses: Mapping[str, int]
) -> tuple[ProposalRequest, ProposalContext, int] | None:
    rng = Rng(seed).fork(f"eval.upgrade.{index}")
    tier = EVAL_TIERS[index % len(EVAL_TIERS)]
    settings = library.roguelite.candidates
    keywords = _composable_keywords(library)
    want_keyword = rng.chance_permille(KEYWORD_PERMILLE)
    for attempt in range(KEYWORD_TRIES + 1):
        picked = (rng.choice(keywords),) if want_keyword and attempt < KEYWORD_TRIES else ()
        made = make_topic(
            library,
            TopicRequest(
                tier=tier,
                keywords=picked,
                seed=rng.next_u32(),
                uses=uses,
                theme_permille=settings.llm_theme_permille,
                reaction_permille=settings.llm_reaction_permille,
            ),
        )
        if made is not None:
            return made
    return None


def upgrade_items(library: ContentLibrary, count: int, *, seed: int = 0) -> list[EvalItem]:
    """照一輪實際出題的方式產生 ``count`` 題升級候選（見模組說明）。"""
    items: list[EvalItem] = []
    uses: dict[str, int] = {}
    index = 0
    while len(items) < count and index < count * 4:
        if index % RUN_LENGTH == 0:
            uses = {}
        made = _upgrade_topic(library, index, seed, uses)
        index += 1
        if made is None:
            continue
        request, ctx, item_seed = made
        if request.core_primitive is not None:
            uses[request.core_primitive] = uses.get(request.core_primitive, 0) + 1
        items.append(EvalItem("upgrade", len(items), request, ctx, item_seed))
    return items


def open_core_primitives(library: ContentLibrary) -> list[str]:
    """開放的核心原語：角色階級 1～3 × 出題稀有度 × 主動／反應，任一組合可當核心的原語
    （扣掉 ``llm_topic.core_exclude``），依原語表順序。"""
    found: set[str] = set()
    for tier, rarity, kind in _combos():
        try:
            found.update(legal_core_primitives(library, ProposalRequest(tier, rarity, kind=kind)))
        except SubsetError:
            continue
    return [p.id for p in library.ruleset.primitives.primitives if p.id in found]


def _combos() -> list[tuple[int, Any, str | None]]:
    return [(t, r, k) for t in EVAL_TIERS for r in TOPIC_RARITIES for k in (None, "reaction")]


def _feasible(library: ContentLibrary, request: ProposalRequest) -> bool:
    try:
        select_subset(library, request)
    except SubsetError:
        return False
    return True


def forced_items(
    library: ContentLibrary,
    *,
    per: int = 3,
    seed: int = 0,
    only: Sequence[str] | None = None,
) -> list[EvalItem]:
    """每個開放的核心原語各 ``per`` 題：題目指定它為核心，階級／稀有度／種類在可行的組合中
    由種子輪替。``only`` 限定原語（測試用）。"""
    items: list[EvalItem] = []
    primitives = list(only) if only is not None else open_core_primitives(library)
    for primitive in primitives:
        rng = Rng(seed).fork(f"eval.forced.{primitive}")
        combos = [
            c
            for c in _combos()
            if _feasible(library, ProposalRequest(c[0], c[1], kind=c[2], core_primitive=primitive))
        ]
        if not combos:
            continue
        order = rng.shuffled(combos)
        for j in range(per):
            tier, rarity, kind = order[j % len(order)]
            request = ProposalRequest(
                tier, rarity, kind=kind, core_primitive=primitive, menu_seed=rng.next_u32()
            )
            if not _feasible(library, request):
                request = replace(request, menu_seed=None)
            ctx = ProposalContext(tier, rarity)
            items.append(EvalItem("forced", len(items), request, ctx, rng.next_u32()))
    return items


def free_items(library: ContentLibrary, count: int, *, seed: int = 0) -> list[EvalItem]:
    """不指定核心原語、不帶關鍵字的題目（輪替選單照常），階級 1～3 輪替。"""
    items: list[EvalItem] = []
    settings = library.roguelite.candidates
    index = 0
    while len(items) < count and index < count * 4:
        rng = Rng(seed).fork(f"eval.free.{index}")
        tier = EVAL_TIERS[index % len(EVAL_TIERS)]
        index += 1
        made = make_topic(
            library,
            TopicRequest(
                tier=tier,
                keywords=(),
                seed=rng.next_u32(),
                uses={},
                reaction_permille=settings.llm_reaction_permille,
            ),
        )
        if made is None:
            continue
        request, ctx, item_seed = made
        request = replace(request, core_primitive=None)
        if _feasible(library, request):
            items.append(EvalItem("free", len(items), request, ctx, item_seed))
    return items


# ---------------------------------------------------------------------------
# 呼叫紀錄
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CallUsage:
    """一次 ``/chat/completions`` 呼叫：HTTP 狀態、schema 寫法、token 用量、結束原因。"""

    status: int
    mode: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""


def _request_mode(request: httpx.Request) -> str:
    try:
        body = json.loads(request.content or b"{}")
    except ValueError:
        return "unknown"
    if "response_format" in body:
        return "response_format"
    if "guided_json" in body:
        return "guided_json"
    return "none"


def _usage_of(status: int, mode: str, response: httpx.Response) -> CallUsage:
    try:
        payload = response.json()
    except ValueError:
        return CallUsage(status, mode)
    usage = payload.get("usage") or {} if isinstance(payload, dict) else {}
    choices = payload.get("choices") if isinstance(payload, dict) else None
    finish = ""
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        finish = str(choices[0].get("finish_reason") or "")
    return CallUsage(
        status,
        mode,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        finish,
    )


class UsageTransport(httpx.BaseTransport):
    """包住真正的 transport，記下每次 ``chat/completions`` 呼叫的 :class:`CallUsage`。"""

    def __init__(self, inner: httpx.BaseTransport | None = None) -> None:
        self.inner = inner if inner is not None else httpx.HTTPTransport()
        self.calls: list[CallUsage] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        if request.url.path.endswith("/chat/completions"):
            response.read()
            self.calls.append(_usage_of(response.status_code, _request_mode(request), response))
        return response

    def close(self) -> None:
        self.inner.close()


@dataclass(slots=True)
class ItemClient:
    """一題用的 client 與它的呼叫紀錄（Mock 時紀錄為空）。"""

    client: LLMClient
    calls: list[CallUsage] = field(default_factory=list)
    close: Callable[[], None] = lambda: None


class RecordingClient:
    """包住 client，記下每次回應的原始文字（事後重新驗證以取得錯誤訊息；不存 prompt）。"""

    def __init__(self, inner: LLMClient) -> None:
        self.inner = inner
        self.raws: list[str] = []

    def complete(
        self, messages: Sequence[ChatMessage], *, json_schema: Mapping[str, Any] | None = None
    ) -> str:
        raw = self.inner.complete(messages, json_schema=json_schema)
        self.raws.append(raw)
        return raw


type ClientFactory = Callable[[EvalItem], ItemClient]
type NamingFactory = Callable[[EvalItem, SkillDef, ItemClient], ItemClient]
"""（題目，合格的技能，提議用的 client）→ 命名用的 client（真模型時沿用同一個）。"""


def real_client_factory(config: LLMConfig) -> ClientFactory:
    """真模型：每題一個 :class:`~trpg.llm.client.OpenAICompatClient`，以
    :class:`UsageTransport` 記錄。"""
    from trpg.llm.client import OpenAICompatClient  # noqa: PLC0415 - 只在真模型時建立

    def make(_item: EvalItem) -> ItemClient:
        transport = UsageTransport()
        client = OpenAICompatClient(config, transport=transport)
        return ItemClient(client, transport.calls, client.close)

    return make


# ---------------------------------------------------------------------------
# 執行
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ItemResult:
    """一題的結果（報表用；耗時不進任何確定性狀態）。"""

    item: EvalItem
    outcome: ProposalOutcome | None
    error: str | None = None
    calls: list[CallUsage] = field(default_factory=list)
    """提議迴圈的呼叫（不含命名）。"""
    name_calls: list[CallUsage] = field(default_factory=list)
    est_tokens: int = 0
    schema_chars: int = 0
    menu: tuple[str, ...] = ()
    chosen: tuple[str, ...] = ()
    name: str = ""
    concept: str = ""
    name_source: str = ""
    name_attempts: int = 0
    name_seconds: float = 0.0
    errors: list[tuple[int, str, str, str]] = field(default_factory=list)
    """（第幾次嘗試, 代碼, 路徑, 訊息）：回給 LLM 的錯誤（由原始回應重新驗證取得）。"""

    @property
    def seconds(self) -> float:
        return (self.outcome.seconds if self.outcome else 0.0) + self.name_seconds

    @property
    def ok(self) -> bool:
        return self.outcome is not None and self.outcome.source == "llm"


def _skill_primitives(skill: SkillDef) -> tuple[str, ...]:
    return tuple(sorted({e.type for e in skill.effects}))


def _prompt_facts(library: ContentLibrary, item: EvalItem, result: ItemResult) -> None:
    try:
        prompt = build_proposal_prompt(library, item.request)
    except (SubsetError, ValueError):
        return
    result.est_tokens = prompt.tokens
    result.schema_chars = prompt.schema_chars
    result.menu = tuple(sorted(prompt.subset.primitives))


def _error_details(
    library: ContentLibrary, item: EvalItem, raws: Sequence[str]
) -> list[tuple[int, str, str, str]]:
    """重新驗證每份原始回應（與 ``propose_skill`` 相同的上下文），取出回給 LLM 的錯誤。"""
    if not raws:
        return []
    try:
        models = build_proposal_prompt(library, item.request).models
    except (SubsetError, ValueError):
        return []
    req = item.request
    ctx = replace(
        item.ctx,
        keywords=req.keywords,
        core_primitive=req.core_primitive,
        weapon_class=req.weapon_class,
    )
    out: list[tuple[int, str, str, str]] = []
    for number, raw in enumerate(raws, start=1):
        text = drop_false_flags(clean_response(raw))
        result = evaluate_with_repair(text, models, library, ctx, seed=item.seed).result
        out += [(number, e.code, e.path, e.message) for e in result.errors]
    return out


def _name(
    library: ContentLibrary,
    item: EvalItem,
    *,
    skill: SkillDef,
    client: ItemClient,
    naming: NamingFactory,
    result: ItemResult,
    taken: _TakenNames | None = None,
) -> None:
    from trpg.llm.naming import name_skill  # noqa: PLC0415 - 只有升級候選命名

    used = naming(item, skill, client)
    start = time.perf_counter()
    names = set() if taken is None else taken.snapshot()
    outcome = name_skill(used.client, library, skill, taken=names)
    if taken is not None:
        taken.add(outcome.text.name_zh)
    result.name_seconds = time.perf_counter() - start
    result.name = outcome.text.name_zh
    result.concept = outcome.text.concept
    result.name_source = outcome.source
    result.name_attempts = outcome.attempts


class _TakenNames:
    """平行評估共用的已取名稱（執行緒安全）。"""

    def __init__(self) -> None:
        self._names: set[str] = set()
        self._lock = threading.Lock()

    def snapshot(self) -> set[str]:
        with self._lock:
            return set(self._names)

    def add(self, name: str) -> None:
        with self._lock:
            self._names.add(name)


def run_item(
    library: ContentLibrary,
    item: EvalItem,
    clients: ClientFactory,
    *,
    max_attempts: int,
    naming: NamingFactory | None = None,
    taken: _TakenNames | None = None,
) -> ItemResult:
    """跑一題：提議迴圈（失敗時退回），合格且有 ``naming`` 時再命名（``taken``：這次評估已取過
    的名稱，帶進命名 prompt 的 taken_names，4-L10a C3）。"""
    client = clients(item)
    result = ItemResult(item, None)
    _prompt_facts(library, item, result)
    recorder = RecordingClient(client.client)
    try:
        outcome = propose_skill(
            recorder,
            library,
            item.request,
            item.ctx,
            seed=item.seed,
            max_attempts=max_attempts,
        )
    except (FallbackError, ValueError) as exc:
        result.error = str(exc)
        result.calls = list(client.calls)
        client.close()
        return result
    result.calls = list(client.calls)
    result.errors = _error_details(library, item, recorder.raws)
    result.outcome = outcome
    result.name = outcome.skill.name_zh
    if outcome.source == "llm":
        result.chosen = _skill_primitives(outcome.skill)
        if naming is not None:
            _name(
                library,
                item,
                skill=outcome.skill,
                client=client,
                naming=naming,
                result=result,
                taken=taken,
            )
            result.name_calls = list(client.calls[len(result.calls) :])
    client.close()
    return result


def run_items(
    library: ContentLibrary,
    items: Sequence[EvalItem],
    clients: ClientFactory,
    *,
    max_attempts: int,
    workers: int = 8,
    naming: NamingFactory | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[ItemResult]:
    """平行跑全部題目（最多 ``workers`` 個同時請求），結果依題目順序回傳。"""
    done = 0
    taken = _TakenNames()

    def one(item: EvalItem) -> ItemResult:
        nonlocal done
        result = run_item(
            library, item, clients, max_attempts=max_attempts, naming=naming, taken=taken
        )
        done += 1
        if progress is not None:
            progress(done, len(items))
        return result

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, items))


# ---------------------------------------------------------------------------
# 統計與報表
# ---------------------------------------------------------------------------


def percentile(values: Sequence[float], pct: int) -> float:
    """最近秩百分位數（``pct`` 0～100）；空序列回傳 0。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, -(-pct * len(ordered) // 100))
    return ordered[min(rank, len(ordered)) - 1]


def _pct(part: int, total: int) -> str:
    return f"{part * 100 / total:.1f}%" if total else "—"


def _outcomes(results: Iterable[ItemResult]) -> list[ProposalOutcome]:
    return [r.outcome for r in results if r.outcome is not None]


def _code_rows(results: Sequence[ItemResult]) -> list[tuple[str, int, int, float]]:
    """各錯誤代碼：（代碼，出現次數，出現的題數，這些題目的平均嘗試次數）。"""
    hits: Counter[str] = Counter()
    items: dict[str, list[int]] = {}
    for result in results:
        if result.outcome is None:
            continue
        seen: set[str] = set()
        for record in result.outcome.records:
            hits.update(record.codes)
            seen.update(record.codes)
        for code in seen:
            items.setdefault(code, []).append(result.outcome.attempts)
    return [
        (code, hits[code], len(items[code]), statistics.fmean(items[code]))
        for code in sorted(hits, key=lambda c: (-hits[c], c))
    ]


def _token_lines(results: Sequence[ItemResult]) -> list[str]:
    calls = [c for r in results for c in r.calls if c.status == httpx.codes.OK]
    if not calls:
        return ["- token 用量：（Mock，無資料）"]
    prompt = [c.prompt_tokens for c in calls]
    completion = [c.completion_tokens for c in calls]
    statuses = Counter(c.status for c in (c for r in results for c in r.calls))
    modes = Counter(c.mode for r in results for c in r.calls if c.status == httpx.codes.OK)
    firsts = [(r.est_tokens, r.calls[0].prompt_tokens) for r in results if r.calls]
    ratio = [real / est for est, real in firsts if est and real]
    lines = [
        f"- 呼叫 {len(calls)} 次；prompt token 平均 {statistics.fmean(prompt):.0f}、"
        f"最大 {max(prompt)}；輸出 token 平均 {statistics.fmean(completion):.0f}、"
        f"最大 {max(completion)}",
        "- HTTP 狀態：" + "、".join(f"{k} ×{v}" for k, v in sorted(statuses.items())),
        "- 被接受的 schema 寫法：" + "、".join(f"{k} ×{v}" for k, v in sorted(modes.items())),
        "- 結束原因："
        + "、".join(
            f"{k or '（空）'} ×{v}" for k, v in Counter(c.finish_reason for c in calls).items()
        ),
    ]
    if ratio:
        lines.append(
            "- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）："
            f"平均 {statistics.fmean(ratio):.2f}"
            f"、最小 {min(ratio):.2f}、最大 {max(ratio):.2f}"
        )
    return lines


def suite_summary(results: Sequence[ItemResult], *, alert_permille: int = 200) -> list[str]:
    """一組題目的 Markdown 摘要（條列＋錯誤代碼表）。"""
    stats = ProposalStats.of(_outcomes(results), alert_permille=alert_permille)
    retry_pass = stats.sources["llm"] - stats.first_pass
    seconds = [r.seconds for r in results if r.outcome is not None]
    attempt_seconds = [s.seconds for r in results if r.outcome for s in r.outcome.records]
    errors = [r for r in results if r.error]
    lines = [
        f"- 題目 {len(results)}（失敗丟例外 {len(errors)}）",
        f"- 一次通過 {stats.first_pass}（{_pct(stats.first_pass, stats.total)}）；"
        f"重試後通過 {retry_pass}（累計 {_pct(stats.sources['llm'], stats.total)}）；"
        f"退回 {stats.fallbacks}（{_pct(stats.fallbacks, stats.total)}）"
        + ("　**⚠ 超過 20% 提醒線**" if stats.alert else ""),
        "- 退回來源："
        + ("、".join(f"{k} {v}" for k, v in stats.sources.items() if k != "llm") or "無"),
        f"- 平均嘗試 {stats.mean_attempts:.2f}",
        f"- 每題耗時（含命名）：平均 {statistics.fmean(seconds) if seconds else 0:.1f} 秒、"
        f"p50 {percentile(seconds, 50):.1f}、p90 {percentile(seconds, 90):.1f}、"
        f"最大 {max(seconds, default=0):.1f}",
        f"- 每次呼叫耗時：p50 {percentile(attempt_seconds, 50):.1f}、"
        f"p90 {percentile(attempt_seconds, 90):.1f} 秒",
        "- 引擎修補：" + ("、".join(f"{k} {v}" for k, v in stats.repaired.most_common()) or "無"),
        *_token_lines(results),
    ]
    named = [r for r in results if r.name_source]
    if named:
        sources = Counter(r.name_source for r in named)
        lines.append(
            f"- 命名：{len(named)} 個，"
            + "、".join(f"{k} {v}" for k, v in sources.items())
            + f"；平均呼叫 {statistics.fmean(r.name_attempts for r in named):.2f} 次、"
            f"平均 {statistics.fmean(r.name_seconds for r in named):.1f} 秒"
        )
    rows = _code_rows(results)
    if rows:
        lines += ["", "| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |", "|---|---:|---:|---:|"]
        lines += [f"| `{c}` | {n} | {k} | {m:.2f} |" for c, n, k, m in rows]
    return lines


def forced_table(library: ContentLibrary, results: Sequence[ItemResult]) -> list[str]:
    """強制測試：每個核心原語的一次通過／重試通過／退回與錯誤代碼。"""
    by: dict[str, list[ItemResult]] = {}
    for result in results:
        by.setdefault(result.item.request.core_primitive or "?", []).append(result)
    lines = [
        "| 原語 | 中文 | 題數 | 一次通過 | 重試通過 | 退回 | 錯誤代碼 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for primitive, group in by.items():
        outs = _outcomes(group)
        first = sum(1 for o in outs if o.source == "llm" and o.attempts == 1)
        retry = sum(1 for o in outs if o.source == "llm" and o.attempts > 1)
        codes = Counter(c for o in outs for rec in o.records for c in rec.codes)
        lines.append(
            f"| `{primitive}` | {plain_name(primitive, library)} | {len(group)} | "
            f"{first} | {retry} | "
            f"{len(group) - first - retry} | "
            + ("、".join(f"`{c}`×{n}" for c, n in codes.most_common()) or "—")
            + " |"
        )
    return lines


def composer_baseline(library: ContentLibrary, count: int, *, seed: int = 0) -> Counter[str]:
    """隨機組合器的原語分布（每個技能每種原語算 1）：階級 1～3、出題稀有度輪替。"""
    from trpg.shared.errors import TrpgError  # noqa: PLC0415
    from trpg.skillgen.random_composer import compose_with_stats  # noqa: PLC0415

    counts: Counter[str] = Counter()
    for index in range(count):
        tier = EVAL_TIERS[index % len(EVAL_TIERS)]
        rarity = TOPIC_RARITIES[(index // len(EVAL_TIERS)) % len(TOPIC_RARITIES)]
        try:
            skill = compose_with_stats(
                seed + index, tier=tier, rarity=rarity, library=library
            ).skill
        except TrpgError:
            continue
        counts.update(_skill_primitives(skill))
    return counts


@dataclass(frozen=True, slots=True)
class FreeRow:
    primitive: str
    menu: int
    chosen: int
    composer: int

    @property
    def rate(self) -> float:
        return self.chosen / self.menu if self.menu else 0.0


def free_rows(results: Sequence[ItemResult], baseline: Counter[str]) -> list[FreeRow]:
    menu: Counter[str] = Counter(p for r in results for p in r.menu)
    chosen: Counter[str] = Counter(p for r in results for p in r.chosen)
    names = sorted(set(menu) | set(chosen) | set(baseline))
    return [FreeRow(p, menu[p], chosen[p], baseline[p]) for p in names]


def free_table(
    library: ContentLibrary, results: Sequence[ItemResult], baseline: Counter[str]
) -> list[str]:
    """自由測試：每個原語的選單次數、被選次數、選中率、被選占比與組合器占比；標出 0 次或偏低的。"""
    rows = free_rows(results, baseline)
    picked_total = sum(r.chosen for r in rows) or 1
    base_total = sum(r.composer for r in rows) or 1
    rates = [r.rate for r in rows if r.menu]
    mean_rate = statistics.fmean(rates) if rates else 0.0
    lines = [
        f"平均選中率 {mean_rate:.1%}；低於 {mean_rate / LOW_SHARE_DIVISOR:.1%}"
        "（平均的 1/3）或 0 次標 ⚠。",
        "",
        "| 原語 | 中文 | 選單次數 | 被選次數 | 選中率 | 被選占比 | 組合器占比 | 標記 |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda r: (-r.menu, r.primitive)):
        low = row.menu > 0 and (row.chosen == 0 or row.rate < mean_rate / LOW_SHARE_DIVISOR)
        mark = "⚠" if low else ("（不在選單）" if row.menu == 0 else "")
        lines.append(
            f"| `{row.primitive}` | {plain_name(row.primitive, library)} | "
            f"{row.menu} | {row.chosen} | "
            f"{row.rate:.1%} | {row.chosen / picked_total:.1%} | {row.composer / base_total:.1%} | "
            f"{mark} |"
        )
    return lines


def describe(library: ContentLibrary, skill: SkillDef) -> str:
    """技能的結構描述（主題一致性抽樣用）：骨架／形狀／效果（狀態、元素、地表）。"""
    effects = []
    for effect in skill.effects:
        extra = [
            plain_name(str(v), library)
            for v in (effect.status, effect.element, effect.surface, effect.object)
            if v is not None
        ]
        text = plain_name(effect.type, library)
        effects.append(text + (f"（{'、'.join(extra)}）" if extra else ""))
    return (
        f"{plain_name(skill.skeleton, library)}／{plain_name(skill.shape.type, library)}／"
        + "＋".join(effects)
    )


CSV_HEAD = [
    "suite",
    "index",
    "tier",
    "rarity",
    "kind",
    "skeleton",
    "keywords",
    "core_primitive",
    "theme",
    "source",
    "attempts",
    "codes",
    "repaired",
    "seconds",
    "name_seconds",
    "calls",
    "prompt_tokens",
    "completion_tokens",
    "first_prompt_tokens",
    "est_tokens",
    "schema_chars",
    "http_statuses",
    "modes",
    "menu_primitives",
    "chosen_primitives",
    "skill_name",
    "name_source",
    "name_attempts",
    "error",
]


def _csv_row(result: ItemResult) -> list[object]:
    req = result.item.request
    out = result.outcome
    calls = result.calls
    return [
        result.item.suite,
        result.item.index,
        req.tier,
        req.rarity,
        req.kind or "",
        req.skeleton or "",
        "|".join(req.keywords),
        req.core_primitive or "",
        req.theme or "",
        out.source if out else "error",
        out.attempts if out else 0,
        ";".join("|".join(c) or "ok" for c in out.codes) if out else "",
        "|".join(c for r in out.records for c in r.repaired) if out else "",
        f"{out.seconds:.2f}" if out else "",
        f"{result.name_seconds:.2f}",
        len(calls),
        sum(c.prompt_tokens for c in calls),
        sum(c.completion_tokens for c in calls),
        calls[0].prompt_tokens if calls else 0,
        result.est_tokens,
        result.schema_chars,
        "|".join(str(c.status) for c in calls),
        "|".join(dict.fromkeys(c.mode for c in calls)),
        "|".join(result.menu),
        "|".join(result.chosen),
        result.name,
        result.name_source,
        result.name_attempts,
        result.error or "",
    ]


def csv_text(results: Sequence[ItemResult]) -> str:
    """每題一列的明細 CSV（不含 prompt）。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEAD)
    for result in results:
        writer.writerow(_csv_row(result))
    return buffer.getvalue()


def errors_csv_text(results: Sequence[ItemResult], *, limit: int = 300) -> str:
    """每條回給 LLM 的錯誤一列：suite、題號、核心原語、第幾次、代碼、路徑、訊息
    （截斷 ``limit`` 字）。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["suite", "index", "core_primitive", "attempt", "code", "path", "message"])
    for result in results:
        core = result.item.request.core_primitive or ""
        for number, code, path, message in result.errors:
            row = [result.item.suite, result.item.index, core, number, code, path, message[:limit]]
            writer.writerow(row)
    return buffer.getvalue()
