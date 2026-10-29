"""``trpg llm ping``（檢查本機模型）與 ``trpg llm propose``（Phase 4-L5：提議小測試）。"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import httpx

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity, rarity_rank
from trpg.llm import (
    ChatMessage,
    LLMClient,
    LLMConfigError,
    LLMError,
    MockLLMClient,
    OpenAICompatClient,
    load_llm_config,
)
from trpg.llm.candidate_source import mock_client_for, mock_naming_client
from trpg.llm.errors import LLM_START_HINT
from trpg.llm.naming import apply_naming, name_skill, template_text
from trpg.llm.propose import ProposalOutcome, ProposalStats, propose_skill
from trpg.shared.rng import Rng
from trpg.skillgen.proposal import (
    CLOSED_SKELETONS,
    PROPOSAL_KINDS,
    ProposalContext,
)
from trpg.skillgen.proposal_fallback import FallbackError, fallback_skill
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError, select_subset

__all__ = ["PROPOSE_RARITIES", "ProposeArgs", "cmd_llm_ping", "cmd_llm_propose", "propose_requests"]

PROPOSE_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")
"""沒有指定稀有度時輪替的稀有度（傳說要源力代價等提議模型沒有的欄位，只在指定時使用）。"""
ROTATION_TRIES = 12
"""輪替出的題目不可行時，最多換幾組（依種子確定性）；都不可行就用第一組。"""


def cmd_llm_ping(
    out: TextIO,
    err: TextIO,
    *,
    config_path: Path | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    try:
        config = load_llm_config(config_path)
    except LLMConfigError as exc:
        print(f"錯誤：{exc}", file=err)
        return 1
    client = OpenAICompatClient(config, transport=transport)
    messages = [ChatMessage(role="user", content="請只回覆「好」。")]
    start = time.perf_counter()
    try:
        reply = client.complete(messages)
    except LLMError as exc:
        print(f"錯誤：{exc}", file=err)
        if LLM_START_HINT not in str(exc):
            print(LLM_START_HINT, file=err)
        return 1
    finally:
        client.close()
    elapsed = time.perf_counter() - start
    print(f"模型：{config.model}（{config.base_url}）", file=out)
    print(f"回應時間：{elapsed:.2f} 秒", file=out)
    print(f"回應：{reply.strip()[:80]}", file=out)
    return 0


# ---------------------------------------------------------------------------
# trpg llm propose
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProposeArgs:
    """``trpg llm propose`` 的參數；``None`` 的欄位依 ``seed`` 輪替。"""

    count: int = 1
    seed: int = 0
    tier: int = 1
    rarity: SkillRarity | None = None
    skeleton: str | None = None
    keywords: tuple[str, ...] = ()
    mock: bool = False
    naming: bool = False
    """通過驗證的 LLM 技能再請模型命名與寫敘事（4-L7；Mock 用 ``mock_naming_client``）。
    關閉時名稱與敘事都用組合式名稱與模板敘事（4-L8b）。"""


def _open_skeletons(library: ContentLibrary, rarity: SkillRarity) -> list[str]:
    return sorted(
        s.id
        for s in library.skeletons.values()
        if s.enabled
        and s.id not in CLOSED_SKELETONS
        and any(k in PROPOSAL_KINDS for k in s.kinds)
        and rarity_rank(s.min_rarity) <= rarity_rank(rarity)
    )


def _feasible(library: ContentLibrary, request: ProposalRequest, seed: int) -> bool:
    """題目可行：``select_subset`` 不丟 ``SubsetError``，且三層退回至少一層做得出技能。"""
    try:
        select_subset(library, request)
        fallback_skill(library, request, ProposalContext(request.tier, request.rarity), seed=seed)
    except (SubsetError, FallbackError):
        return False
    return True


def _rotated_request(
    library: ContentLibrary, args: ProposeArgs, keywords: Sequence[str], index: int, attempt: int
) -> tuple[ProposalRequest, int]:
    """第 ``index`` 題的第 ``attempt`` 組輪替（第 0 組與 4-L5 的輸出相同）。"""
    label = f"llm.propose.{index}" if attempt == 0 else f"llm.propose.{index}.{attempt}"
    rng = Rng(args.seed).fork(label)
    rarity = args.rarity or PROPOSE_RARITIES[(args.seed + index + attempt) % len(PROPOSE_RARITIES)]
    skeleton = args.skeleton
    if skeleton is None and rng.chance_permille(500):
        skeleton = rng.choice(_open_skeletons(library, rarity))
    picked = args.keywords
    if not picked and rng.chance_permille(500):
        picked = (rng.choice(keywords),)
    return ProposalRequest(args.tier, rarity, skeleton=skeleton, keywords=picked), rng.next_u32()


def propose_requests(
    library: ContentLibrary, args: ProposeArgs
) -> list[tuple[ProposalRequest, int]]:
    """``count`` 個題目與各自的種子：沒指定的稀有度、骨架、關鍵字依 ``seed`` 確定性輪替
    （稀有度依序輪流；骨架半數不指定；關鍵字 0 或 1 個）。輪替出的題目先檢查可行
    （:func:`_feasible`），不可行就依種子換下一組（最多 :data:`ROTATION_TRIES` 組）；
    稀有度、骨架、關鍵字都由參數指定的題目照跑。"""
    keywords = library.keywords.ids()
    unknown = [k for k in args.keywords if k not in keywords]
    if unknown:
        raise ValueError(f"未知的關鍵字：{'、'.join(unknown)}（可用：{'、'.join(keywords)}）")
    explicit = args.rarity is not None and args.skeleton is not None and bool(args.keywords)
    out: list[tuple[ProposalRequest, int]] = []
    for index in range(args.count):
        first = _rotated_request(library, args, keywords, index, 0)
        chosen = first
        if not explicit:
            for attempt in range(ROTATION_TRIES):
                candidate = (
                    first
                    if attempt == 0
                    else _rotated_request(library, args, keywords, index, attempt)
                )
                if _feasible(library, *candidate):
                    chosen = candidate
                    break
        out.append(chosen)
    return out


def _mock_client(
    library: ContentLibrary, request: ProposalRequest, seed: int, attempts: int
) -> MockLLMClient:
    """見 :func:`trpg.llm.candidate_source.mock_client_for`（Phase 4-L6 起也看題目的關鍵字與核心
    原語，因為驗證器會要求提議帶到它們）。"""
    return mock_client_for(library, request, seed, attempts)


def _describe(request: ProposalRequest) -> str:
    keywords = "、".join(request.keywords) or "無關鍵字"
    return f"{request.rarity}／{request.skeleton or '不限骨架'}／{keywords}"


def _attempt_codes(codes: tuple[str, ...]) -> str:
    """一次嘗試的錯誤代碼（重複的合併為 ``代碼×次數``；沒有錯誤為「通過」）。"""
    counts = Counter(codes)
    return "、".join(f"{c}×{counts[c]}" if counts[c] > 1 else c for c in counts) or "通過"


def _outcome_line(
    index: int, request: ProposalRequest, outcome: ProposalOutcome, name: str, note: str = ""
) -> str:
    codes = "；".join(_attempt_codes(c) for c in outcome.codes) or "—"
    return (
        f"{index:>3}. {_describe(request)}｜{outcome.source}｜嘗試 {outcome.attempts}｜"
        f"{codes}｜{outcome.seconds:.2f} 秒｜{name}{note}"
    )


@dataclass(slots=True)
class _Naming:
    """命名步驟的結果統計（只有 ``--naming`` 時使用）。"""

    generated: int = 0
    fallback: int = 0
    calls: int = 0

    def line(self) -> str:
        total = self.generated + self.fallback
        return (
            f"命名：{total} 個，生成 {self.generated}，組合式名稱 {self.fallback}，"
            f"呼叫 {self.calls} 次"
        )


def _name_outcome(
    library: ContentLibrary,
    args: ProposeArgs,
    outcome: ProposalOutcome,
    seed: int,
    client: LLMClient | None,
    *,
    taken: set[str],
    attempts: int,
    naming: _Naming,
) -> tuple[str, str]:
    """通過驗證的 LLM 技能的最終名稱與備註。命名關閉時（4-L8b）換成組合式名稱與模板敘事；
    只處理 ``llm`` 來源（退回的技能本來就是組合式名稱與模板敘事）。"""
    skill = outcome.skill
    if outcome.source != "llm":
        return skill.name_zh, ""
    if not args.naming:
        plain = template_text(library, skill, taken)
        taken.add(plain.name_zh)
        return plain.name_zh, ""
    used = mock_naming_client(library, skill, seed) if client is None else client
    result = name_skill(used, library, skill, taken=taken, max_attempts=attempts)
    taken.add(result.text.name_zh)
    named = apply_naming(skill, result.text)
    naming.calls += result.attempts
    if result.source == "llm":
        naming.generated += 1
    else:
        naming.fallback += 1
    return named.name_zh, f"（命名 {result.source}，{result.attempts} 次）"


def cmd_llm_propose(
    library: ContentLibrary,
    args: ProposeArgs,
    out: TextIO,
    err: TextIO,
    *,
    config_path: Path | None = None,
    client: LLMClient | None = None,
) -> int:
    """跑 ``args.count`` 個題目，每個一行結果，最後印 :class:`ProposalStats` 摘要。"""
    try:
        config = load_llm_config(config_path)
    except LLMConfigError as exc:
        print(f"錯誤：{exc}", file=err)
        return 1
    try:
        requests = propose_requests(library, args)
    except ValueError as exc:
        print(f"錯誤：{exc}", file=err)
        return 1
    real = None if args.mock or client is not None else OpenAICompatClient(config)
    label = "Mock（proposal_from_skill）" if args.mock else f"{config.model}（{config.base_url}）"
    print(f"模型：{label}；每題最多 {config.max_retries} 次", file=out)
    stats = ProposalStats(alert_permille=config.fallback_alert_permille)
    naming = _Naming()
    taken: set[str] = set()
    try:
        for index, (request, seed) in enumerate(requests, start=1):
            used = client or real or _mock_client(library, request, seed, config.max_retries)
            ctx = ProposalContext(request.tier, request.rarity)
            try:
                outcome = propose_skill(
                    used,
                    library,
                    request,
                    ctx,
                    seed=seed,
                    max_attempts=config.max_retries,
                    clock=(lambda: 0.0) if args.mock else time.perf_counter,
                )
            except (FallbackError, ValueError) as exc:
                print(f"{index:>3}. {_describe(request)}｜失敗：{exc}", file=out)
                continue
            stats.add(outcome)
            name_client = client or real
            name, note = _name_outcome(
                library,
                args,
                outcome,
                seed,
                None if args.mock else name_client,
                taken=taken,
                attempts=config.max_retries,
                naming=naming,
            )
            print(_outcome_line(index, request, outcome, name, note), file=out)
    finally:
        if real is not None:
            real.close()
    print("", file=out)
    for line in stats.summary_lines():
        print(line, file=out)
    if args.naming:
        print(naming.line(), file=out)
    return 0
