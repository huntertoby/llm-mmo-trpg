"""6S-2b：升級候選退回路徑的缺口——任何合法出題都至少產生一個保底技能。

退回（:func:`~trpg.skillgen.proposal_fallback.fallback_skill`）只看題目的階級、稀有度、種類、
骨架、關鍵字與種子（核心原語、輪替選單種子、主題不影響退回），所以「階級 × 出題稀有度 × 種類 ×
關鍵字」窮舉、種子抽樣，就涵蓋升級候選出題（:func:`~trpg.skillgen.proposal_topic.make_topic`）的
所有退回情況。合法出題＝ :func:`select_subset` 得出選單，且選單帶得到題目關鍵字（與 ``make_topic``
相同的條件）。
"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import fallback_skill
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError, select_subset
from trpg.skillgen.proposal_topic import TOPIC_RARITIES, TopicRequest, make_topic
from trpg.skillgen.proposal_topup import keywords_reachable
from trpg.skillgen.validate import validate_skill

TIERS = (1, 2, 3)
KINDS = (None, "reaction")


def _composable(library: ContentLibrary) -> list[str]:
    table = library.keywords.by_id()
    return [k for k in library.keywords.ids() if table[k].composable]


def _legal(library: ContentLibrary, request: ProposalRequest) -> bool:
    try:
        subset = select_subset(library, request)
    except SubsetError:
        return False
    return keywords_reachable(library, subset)


def _check(library: ContentLibrary, request: ProposalRequest, seed: int) -> str:
    ctx = ProposalContext(request.tier, request.rarity)
    skill, source = fallback_skill(library, request, ctx, seed=seed)
    assert validate_skill(skill, library) == []
    assert skill.tier == request.tier and skill.rarity == request.rarity
    assert skill.kind == (request.kind or "active")
    return source


# ---------------------------------------------------------------------------
# 回歸：6S-2 報告待決 6 的那一題（mock 升級候選第 43 題）
# ---------------------------------------------------------------------------

REGRESSION = ProposalRequest(
    2,
    "rare",
    kind="reaction",
    keywords=("high_ground",),
    core_primitive="heal",
    menu_seed=457164577,
)
REGRESSION_SEED = 3514268949


def test_reaction_heal_high_ground_rare_tier2_falls_back(library: ContentLibrary) -> None:
    """反應技＋高地（階級 2 稀有）：組合器做不出帶高地的反應技、技能池沒有階級 2 的反應技，
    原本工坊也沒填反應時機而丟 FallbackError；現在由工坊做出反應技。"""
    ctx = ProposalContext(2, "rare")
    skill, source = fallback_skill(library, REGRESSION, ctx, seed=REGRESSION_SEED)
    assert source == "workshop"
    assert skill.kind == "reaction" and skill.skeleton == "reaction"
    assert skill.reaction is not None
    assert validate_skill(skill, library) == []
    again, _ = fallback_skill(library, REGRESSION, ctx, seed=REGRESSION_SEED)
    assert again == skill  # 確定性


@pytest.mark.parametrize("keyword", ["wet", "high_ground", "summon"])
def test_reaction_keywords_the_composer_cannot_carry(library: ContentLibrary, keyword: str) -> None:
    """修補前所有階級的稀有／史詩反應技配這三個關鍵字都會丟 FallbackError（掃描 18 組）。"""
    request = ProposalRequest(3, "epic", kind="reaction", keywords=(keyword,))
    assert _legal(library, request)
    assert _check(library, request, seed=0) == "workshop"


# ---------------------------------------------------------------------------
# 窮舉（slow）
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("rarity", TOPIC_RARITIES)
@pytest.mark.parametrize("tier", TIERS)
def test_every_legal_topic_has_a_fallback(
    library: ContentLibrary, tier: int, rarity: SkillRarity, kind: str | None
) -> None:
    """每個合法的（階級, 稀有度, 種類, 無關鍵字或一個可交給 LLM 的關鍵字）× 種子 0、1 都有保底。"""
    checked = 0
    for keywords in [(), *((k,) for k in _composable(library))]:
        request = ProposalRequest(tier, rarity, kind=kind, keywords=keywords)
        if not _legal(library, request):
            continue
        for seed in (0, 1):
            _check(library, request, seed)
            checked += 1
    if kind is None or rarity != "common":  # 反應技最低稀有；其餘每組都至少有沒關鍵字的題
        assert checked > 0


@pytest.mark.slow
def test_sampled_make_topic_outputs_have_a_fallback(library: ContentLibrary) -> None:
    """照升級候選的出題方式依種子抽樣（含反應技題與帶關鍵字的題），每題都有保底。"""
    keywords = _composable(library)
    made = 0
    for seed in range(60):
        picked = (keywords[seed % len(keywords)],) if seed % 2 else ()
        topic = make_topic(
            library,
            TopicRequest(
                tier=TIERS[seed % 3],
                keywords=picked,
                seed=seed,
                uses={},
                reaction_permille=500,
            ),
        )
        if topic is None:
            continue
        request, ctx, item_seed = topic
        skill, _ = fallback_skill(library, request, ctx, seed=item_seed)
        assert validate_skill(skill, library) == []
        made += 1
    assert made >= 40
