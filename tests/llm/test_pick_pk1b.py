"""PK-1b：挑選模式的 LLM 一步——卡片的 ``fit``、避開濫用詞、候選池空時不退回手上已有的技能。"""

from __future__ import annotations

from functools import cache

from trpg.content.library import ContentLibrary, load_library
from trpg.content.player_pool import player_skills
from trpg.content.skills import skill_elements
from trpg.llm.client import MockLLMClient
from trpg.llm.pick import candidate_card, fit_notes, mock_pick_client, pick_skill
from trpg.llm.prompts.pick import AVOID_WORDS, PICK_PROMPT_VERSION
from trpg.shared.types import Element
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import fits_request, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.skill_pick import PickSlate, pick_slate

REQUEST = ProposalRequest(1, "rare", skeleton="rune")
KEYWORD = ProposalRequest(1, "rare", keywords=("fury",))
SEED = 4


@cache
def _lib() -> ContentLibrary:
    return load_library()


def _ice_player() -> PickPlayer:
    skill = next(
        s
        for s in sorted(player_skills(_lib()).values(), key=lambda s: s.id)
        if skill_elements(s) == {Element.ICE} and s.tier == 1
    )
    return PickPlayer(held_skills=(skill,))


def test_prompt_version_and_avoid_words() -> None:
    assert PICK_PROMPT_VERSION == "skill-pick/2"
    assert {"頻率", "餘燼", "烙印", "殘餘"} <= set(AVOID_WORDS)
    lib = _lib()
    ctx = ProposalContext(REQUEST.tier, REQUEST.rarity)
    slate = pick_slate(lib, REQUEST, ctx, seed=SEED)
    client = mock_pick_client(lib, slate, SEED)
    pick_skill(client, lib, REQUEST, ctx, seed=SEED, slate=slate)
    system = client.calls[0][0]["content"]
    assert all(word in system for word in AVOID_WORDS)


def test_cards_say_how_a_candidate_fits_the_player() -> None:
    lib = _lib()
    player = _ice_player()
    ctx = ProposalContext(REQUEST.tier, REQUEST.rarity)
    slate = pick_slate(lib, REQUEST, ctx, seed=SEED, player=player)
    ice = next(c for c in slate.ranked if Element.ICE in skill_elements(c.skill))
    notes = fit_notes(lib, ice.skill, player)
    assert any(player.held_skills[0].name_zh in n and "同元素" in n for n in notes)
    card = candidate_card(lib, ice.skill, 0, fit=notes)
    assert card["fit"] == notes
    assert "fit" not in candidate_card(lib, ice.skill, 0)  # 沒有關係就不寫
    assert fit_notes(lib, ice.skill, None) == []
    client = mock_pick_client(lib, slate, SEED)
    pick_skill(client, lib, REQUEST, ctx, seed=SEED, slate=slate, player=player)
    assert "同元素" in client.calls[0][1]["content"]


def test_empty_slate_never_hands_back_a_held_skill() -> None:
    lib = _lib()
    kind = wanted_kind(lib, KEYWORD)
    fitting = tuple(
        s
        for s in sorted(player_skills(lib).values(), key=lambda s: s.id)
        if s.tier == 1 and s.rarity == "rare" and fits_request(s, KEYWORD, kind, lib)
    )
    assert fitting
    player = PickPlayer(held_skills=fitting)
    ctx = ProposalContext(KEYWORD.tier, KEYWORD.rarity, keywords=KEYWORD.keywords)
    for seed in (0, 1, 2):
        outcome = pick_skill(
            MockLLMClient([]),
            lib,
            KEYWORD,
            ctx,
            seed=seed,
            player=player,
            slate=PickSlate((), 0, 60),
        )
        assert outcome.reason == "pick.empty"
        assert outcome.skill.id not in {s.id for s in fitting}
