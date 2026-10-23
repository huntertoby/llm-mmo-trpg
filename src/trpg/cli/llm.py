"""``trpg llm ping``（檢查本機模型）與 ``trpg llm propose``（Phase 4-L5：提議小測試）。"""

from __future__ import annotations

import json
import time
from collections import Counter
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
from trpg.llm.errors import LLM_START_HINT
from trpg.llm.propose import ProposalOutcome, ProposalStats, propose_skill
from trpg.shared.rng import Rng
from trpg.skillgen.proposal import (
    CLOSED_SKELETONS,
    PROPOSAL_KINDS,
    ProposalContext,
    proposal_from_skill,
)
from trpg.skillgen.proposal_fallback import FallbackError, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest

__all__ = ["PROPOSE_RARITIES", "ProposeArgs", "cmd_llm_ping", "cmd_llm_propose", "propose_requests"]

PROPOSE_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")
"""沒有指定稀有度時輪替的稀有度（傳說要源力代價等提議模型沒有的欄位，只在指定時使用）。"""
MOCK_EMPTY = "{}"
"""Mock 找不到合適的手寫技能時回傳的空提議（會一路失敗、走退回）。"""


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


def _open_skeletons(library: ContentLibrary, rarity: SkillRarity) -> list[str]:
    return sorted(
        s.id
        for s in library.skeletons.values()
        if s.enabled
        and s.id not in CLOSED_SKELETONS
        and any(k in PROPOSAL_KINDS for k in s.kinds)
        and rarity_rank(s.min_rarity) <= rarity_rank(rarity)
    )


def propose_requests(
    library: ContentLibrary, args: ProposeArgs
) -> list[tuple[ProposalRequest, int]]:
    """``count`` 個題目與各自的種子：沒指定的稀有度、骨架、關鍵字依 ``seed`` 確定性輪替
    （稀有度依序輪流；骨架半數不指定；關鍵字 0 或 1 個）。"""
    keywords = library.keywords.ids()
    unknown = [k for k in args.keywords if k not in keywords]
    if unknown:
        raise ValueError(f"未知的關鍵字：{'、'.join(unknown)}（可用：{'、'.join(keywords)}）")
    out: list[tuple[ProposalRequest, int]] = []
    for index in range(args.count):
        rng = Rng(args.seed).fork(f"llm.propose.{index}")
        rarity = args.rarity or PROPOSE_RARITIES[(args.seed + index) % len(PROPOSE_RARITIES)]
        skeleton = args.skeleton
        if skeleton is None and rng.chance_permille(500):
            skeleton = rng.choice(_open_skeletons(library, rarity))
        picked = args.keywords
        if not picked and rng.chance_permille(500):
            picked = (rng.choice(keywords),)
        request = ProposalRequest(args.tier, rarity, skeleton=skeleton, keywords=picked)
        out.append((request, rng.next_u32()))
    return out


def _mock_client(
    library: ContentLibrary, request: ProposalRequest, seed: int, attempts: int
) -> MockLLMClient:
    """回傳 ``proposal_from_skill`` 產生的提議（同階級、稀有度、種類與骨架的手寫技能，依種子
    挑一個；不看關鍵字）；沒有合適的技能時回傳空提議（走退回）。"""
    kind = wanted_kind(library, request)
    texts: list[str] = []
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if (
            skill.tier != request.tier
            or skill.rarity != request.rarity
            or skill.kind != kind
            or (request.skeleton is not None and skill.skeleton != request.skeleton)
        ):
            continue
        try:
            proposal = proposal_from_skill(skill, library)
        except ValueError:
            continue
        texts.append(json.dumps(proposal, ensure_ascii=False, sort_keys=True))
    text = Rng(seed).fork("llm.propose.mock").choice(texts) if texts else MOCK_EMPTY
    return MockLLMClient([text] * attempts)


def _describe(request: ProposalRequest) -> str:
    keywords = "、".join(request.keywords) or "無關鍵字"
    return f"{request.rarity}／{request.skeleton or '不限骨架'}／{keywords}"


def _attempt_codes(codes: tuple[str, ...]) -> str:
    """一次嘗試的錯誤代碼（重複的合併為 ``代碼×次數``；沒有錯誤為「通過」）。"""
    counts = Counter(codes)
    return "、".join(f"{c}×{counts[c]}" if counts[c] > 1 else c for c in counts) or "通過"


def _outcome_line(index: int, request: ProposalRequest, outcome: ProposalOutcome) -> str:
    codes = "；".join(_attempt_codes(c) for c in outcome.codes) or "—"
    return (
        f"{index:>3}. {_describe(request)}｜{outcome.source}｜嘗試 {outcome.attempts}｜"
        f"{codes}｜{outcome.seconds:.2f} 秒｜{outcome.skill.name_zh}"
    )


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
            print(_outcome_line(index, request, outcome), file=out)
    finally:
        if real is not None:
            real.close()
    print("", file=out)
    for line in stats.summary_lines():
        print(line, file=out)
    return 0
