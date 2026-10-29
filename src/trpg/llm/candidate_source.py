"""候選產生器的 LLM 來源（Phase 4-L6）：把 :func:`~trpg.llm.propose.propose_skill` 接成
:data:`~trpg.skillgen.proposal_topic.LlmProposer`。

- :func:`make_proposer`：真模型（或任何 :class:`~trpg.llm.client.LLMClient`）。每個題目呼叫
  :func:`propose_skill`（最多 ``max_attempts`` 次）；提議器不使用退回的技能——退回由候選產生器的
  來源順序（組合器 → 技能池）處理，所以只回報 ``llm`` 來源的技能。
- :func:`mock_proposer`：不需網路與金鑰的 Mock（CI 與 ``--llm-mock``）。對每個題目從內容庫挑一個同
  階級、稀有度、種類、帶題目關鍵字且用到指定核心原語的手寫技能，轉成提議（``proposal_from_skill``）；
  挑不到時回傳空提議（走重試與退回）。確定性：依題目種子挑選。

LLM 只提議：技能的數值一律來自預算器（``propose_skill`` 內）。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, rarity_rank
from trpg.content.world import load_world_style
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.naming import DEFAULT_NAMING_ATTEMPTS, apply_naming, name_skill
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.propose import DEFAULT_MAX_ATTEMPTS, ProposalOutcome, propose_skill
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal import ProposalContext, proposal_from_skill
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_fallback import FallbackError, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError
from trpg.skillgen.proposal_topic import LlmAttempt, LlmProposer

__all__ = [
    "MOCK_EMPTY",
    "NamingClient",
    "ProposerStats",
    "make_proposer",
    "mock_client_for",
    "mock_naming_client",
    "mock_proposer",
    "name_attempt",
]

MOCK_TRIES = 30
"""Mock 每個放寬階段最多檢查幾份提議。"""
MOCK_EMPTY = "{}"
"""Mock 找不到合適的手寫技能時回傳的空提議（會一路失敗、走退回）。"""


class ProposerStats(Protocol):
    """提議器的統計掛鉤（可省略）：每個題目結束時收到 :class:`ProposalOutcome`。"""

    def add(self, outcome: ProposalOutcome) -> None: ...


def _attempt_of(outcome: ProposalOutcome) -> LlmAttempt:
    codes = tuple(dict.fromkeys(c for record in outcome.records for c in record.codes))
    if outcome.source == "llm":
        return LlmAttempt(outcome.skill, outcome.attempts, codes)
    return LlmAttempt(None, outcome.attempts, codes, outcome.reason)


type NamingClient = LLMClient | Callable[[SkillDef, int], LLMClient]
"""命名用的 client：固定的 client（同一個本機模型），或依（技能，種子）建立的函式（Mock 用）。"""


def _theme_name(request: ProposalRequest) -> str | None:
    if request.theme is None:
        return None
    world = load_world_style()
    return next((t.name_zh for t in world.themes if t.id == request.theme), None)


def name_attempt(
    attempt: LlmAttempt,
    naming: NamingClient,
    library: ContentLibrary,
    request: ProposalRequest,
    *,
    seed: int,
    taken: set[str],
    max_attempts: int,
) -> LlmAttempt:
    """結構合格的 LLM 技能再請模型命名與寫敘事（4-L7）：只換文字，失敗用組合式名稱。"""
    skill = attempt.skill
    if skill is None:
        return attempt
    used = naming if isinstance(naming, LLMClient) else naming(skill, seed)
    result = name_skill(
        used, library, skill, taken=taken, theme=_theme_name(request), max_attempts=max_attempts
    )
    taken.add(result.text.name_zh)
    return replace(
        attempt,
        skill=apply_naming(skill, result.text),
        name_source=result.source,
        name_attempts=result.attempts,
        name_codes=result.codes,
    )


def make_proposer(
    client: LLMClient | Callable[[ProposalRequest, int], LLMClient],
    library: ContentLibrary,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    stats: ProposerStats | None = None,
    naming: NamingClient | None = None,
) -> LlmProposer:
    """真模型的提議器。``client`` 可以是固定的 client，或依（題目，種子）建立 client 的函式
    （Mock 用）。題目沒有可用結構、退回也失敗等都算失敗（``LlmAttempt.skill`` 為 ``None``）。

    ``naming``（4-L7）：給了就在結構合格後請它為技能命名與寫敘事（``name_skill``，最多
    ``max_attempts`` 次，失敗用組合式名稱）；``None`` ＝ 沿用提議裡的名稱與敘事（不多呼叫一次）。
    已用過的名稱記在提議器內，同一個提議器產生的技能不會重名。"""
    taken: set[str] = set()

    def propose(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
        used = client if isinstance(client, LLMClient) else client(request, seed)
        try:
            outcome = propose_skill(
                used, library, request, ctx, seed=seed, max_attempts=max_attempts
            )
        except (FallbackError, ValueError) as exc:
            return LlmAttempt(None, 0, (), str(exc))
        if stats is not None:
            stats.add(outcome)
        attempt = _attempt_of(outcome)
        if naming is None:
            return attempt
        return name_attempt(
            attempt, naming, library, request, seed=seed, taken=taken, max_attempts=max_attempts
        )

    return propose


# 命名用的 Mock 詞庫（全形中文）：「<詞首><骨架>之<詞尾>」，由種子挑選，不需網路與金鑰。
_MOCK_HEADS = ("碎光", "殘響", "裂隙", "浮影", "晶輝", "沉霧", "曦痕", "遠嵐")
_MOCK_TAILS = ("低語", "餘燼", "回聲", "迴旋", "誓約", "斷章")


def mock_naming_client(library: ContentLibrary, skill: SkillDef, seed: int) -> MockLLMClient:
    """合格的命名回應（確定性：依種子挑詞）。名稱與既有技能重複時，命名步驟會重試後改用組合式名稱。"""
    rng = Rng(seed).fork("llm.naming.mock")
    skeleton = plain_name(skill.skeleton, library)
    name = f"{rng.choice(_MOCK_HEADS)}{rng.choice(_MOCK_TAILS)}"
    text = {
        "name_zh": name,
        "concept": f"源晶碎片的頻率凝成{skeleton}。",
        "cast_flavor": f"碎界的低鳴應聲而起，{name}隨你而動。",
    }
    return MockLLMClient([json.dumps(text, ensure_ascii=False)] * DEFAULT_NAMING_ATTEMPTS)


def _mock_texts(
    library: ContentLibrary, request: ProposalRequest, *, core: bool, tier: bool
) -> list[str]:
    """符合題目的手寫技能的提議文字；``core``／``tier`` 為假時放寬該條件。"""
    kind = wanted_kind(library, request)
    rank = rarity_rank(request.rarity)
    texts: list[str] = []
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if (
            skill.kind != kind
            or (tier and skill.tier != request.tier)
            or (tier and skill.rarity != request.rarity)
            or (not tier and rarity_rank(skill.rarity) > rank)
            or (request.skeleton is not None and skill.skeleton != request.skeleton)
            or (
                core
                and request.core_primitive is not None
                and all(e.type != request.core_primitive for e in skill.effects)
            )
            or (request.keywords and not skill_has_keywords(skill, request.keywords, library))
        ):
            continue
        try:
            proposal = proposal_from_skill(skill, library)
        except ValueError:
            continue
        texts.append(json.dumps(proposal, ensure_ascii=False, sort_keys=True))
    return texts


def _passes(library: ContentLibrary, request: ProposalRequest, text: str, seed: int) -> bool:
    """Mock 事先檢查：這份提議在題目的 schema 子集與驗證器下是否合格（扮演「答對的模型」）。"""
    prompt = build_proposal_prompt(library, request)
    ctx = ProposalContext(
        request.tier,
        request.rarity,
        keywords=request.keywords,
        core_primitive=request.core_primitive,
    )
    return evaluate_with_repair(text, prompt.models, library, ctx, seed=seed).result.ok


def mock_client_for(
    library: ContentLibrary, request: ProposalRequest, seed: int, attempts: int
) -> MockLLMClient:
    """回傳 ``proposal_from_skill`` 產生的提議：同種類（與骨架）、帶題目關鍵字的手寫技能，依種子
    洗牌後取第一個 **在這個題目下合格** 的（Mock 扮演答對的模型）。依序放寬：階級與稀有度相同且用到
    指定核心原語 → 不看核心原語 → 不看階級（稀有度不高於題目）；都找不到合格的就回傳第一個候選
    （讓驗證器擋下，測重試與退回），連候選都沒有回傳空提議。"""
    rng = Rng(seed).fork("llm.propose.mock")
    first: str | None = None
    for core, tier in ((True, True), (False, True), (False, False)):
        for text in rng.shuffled(_mock_texts(library, request, core=core, tier=tier))[:MOCK_TRIES]:
            first = first or text
            try:
                ok = _passes(library, request, text, seed)
            except SubsetError:
                return MockLLMClient([MOCK_EMPTY] * attempts)
            if ok:
                return MockLLMClient([text] * attempts)
    return MockLLMClient([first or MOCK_EMPTY] * attempts)


def mock_proposer(
    library: ContentLibrary,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    stats: ProposerStats | None = None,
    naming: bool = False,
) -> LlmProposer:
    """Mock 提議器（見模組說明）；不需網路與金鑰。``naming`` 為真時結構合格後用 Mock 命名
    （:func:`mock_naming_client`）。"""
    return make_proposer(
        lambda request, seed: mock_client_for(library, request, seed, max_attempts),
        library,
        max_attempts=max_attempts,
        stats=stats,
        naming=(lambda skill, seed: mock_naming_client(library, skill, seed)) if naming else None,
    )
