"""SK-3 的新觸發與重擲接進出題（SK-3b 第 3 項，玩法交接 4.1.30 第 5 點）。

- 組合器：「你造的關鍵字被利用時」被動（``composer.exploit``）、重擲反應技（``composer.reroll``）
  都只走獨立串流；機率設 0 時結果和改前逐字相同（主串流沒動）。
- LLM：反應事件清單多重擲的兩個時機；觸發清單本來就有新觸發（照 ``skill_triggers.yaml`` 全部列）。
- 反應骨架的核心收重擲；重擲的預算隨階級長（固定 5 點時階級 1 也只到 60%）。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library, sk3b_streams
from trpg.content.skills import REROLL_EVENTS, SKILL_REACTION_EVENTS, SkillDef
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal.builder import LLM_REACTION_EVENTS, reaction_events
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

SEEDS = range(12)


def test_with_the_streams_on_the_composer_makes_exploit_passives() -> None:
    lib = sk3b_streams(library(), 1000)
    made = [
        compose_random_skill(s, tier=1, rarity="epic", skeleton="passive", library=lib)
        for s in SEEDS
    ]
    exploit = [
        m for m in made if m.trigger is not None and m.trigger.event == "on_keyword_exploited"
    ]
    assert len(exploit) >= len(made) // 2
    for skill in exploit:
        assert validate_skill(skill, lib) == []
        assert skill.trigger is not None and skill.trigger.target == "self"


@pytest.mark.parametrize("rarity", ["rare", "epic"])
def test_with_the_streams_on_the_composer_makes_reroll_reactions(rarity: Any) -> None:
    lib = sk3b_streams(library(), 1000)
    made = [
        compose_random_skill(s, tier=t, rarity=rarity, skeleton="reaction", library=lib)
        for s in SEEDS
        for t in (1, 2, 3)
    ]
    rerolls = [m for m in made if [e.type for e in m.effects] == ["reroll"]]
    assert len(rerolls) == len(made)
    assert {m.reaction.event for m in rerolls if m.reaction is not None} == set(REROLL_EVENTS)
    for skill in rerolls:
        assert validate_skill(skill, lib) == []
        assert skill.shape.type == "self"


def test_a_weapon_reaction_is_never_a_reroll() -> None:
    lib = sk3b_streams(library(), 1000)
    for seed in SEEDS:
        skill = compose_random_skill(
            seed, tier=1, rarity="rare", skeleton="reaction", category="weapon", library=lib
        )
        assert "reroll" not in [e.type for e in skill.effects]


@pytest.mark.parametrize("skeleton", ["passive", "reaction"])
def test_with_the_streams_off_nothing_new_is_made(skeleton: str) -> None:
    lib = sk3b_streams(library(), 0)
    for seed in range(40):
        skill = compose_random_skill(seed, tier=1, rarity="epic", skeleton=skeleton, library=lib)
        assert skill.trigger is None or skill.trigger.event != "on_keyword_exploited"
        assert "reroll" not in [e.type for e in skill.effects]


def test_the_streams_do_not_move_the_main_stream() -> None:
    """沒抽中新串流的種子：和機率 0 的結果逐字相同。"""
    on, off = library(), sk3b_streams(library(), 0)
    for skeleton in ("passive", "reaction"):
        for seed in range(40):
            a = compose_random_skill(seed, tier=1, rarity="epic", skeleton=skeleton, library=on)
            new = (a.trigger is not None and a.trigger.event == "on_keyword_exploited") or (
                "reroll" in [e.type for e in a.effects]
            )
            if not new:
                b = compose_random_skill(
                    seed, tier=1, rarity="epic", skeleton=skeleton, library=off
                )
                assert a == b, (skeleton, seed)


def test_the_llm_reaction_menu_lists_the_reroll_timings() -> None:
    assert (*SKILL_REACTION_EVENTS, *REROLL_EVENTS) == LLM_REACTION_EVENTS
    ids = [e for e, _ in reaction_events(library())]
    assert ids[-2:] == list(REROLL_EVENTS)


def test_the_llm_trigger_menu_has_the_new_trigger() -> None:
    triggers = {t.id: t for t in library().ruleset.skill_triggers.triggers}
    assert "on_keyword_exploited" in triggers
    assert "符文" in triggers["on_keyword_exploited"].llm_hint


def test_the_reaction_skeleton_takes_reroll_as_core() -> None:
    assert "reroll" in library().skeletons["reaction"].core.primitives


def _reroll(tier: int, cost: dict[str, Any]) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": "skill_t_reroll",
            "name_zh": "測試重擲",
            "tier": tier,
            "rarity": "rare",
            "kind": "reaction",
            "skeleton": "reaction",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "dex",
            "shape": {"type": "self"},
            "effects": [{"type": "reroll"}],
            "reaction": {"event": "enemy_hit_roll"},
            "cost": cost,
        }
    )


@pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
def test_the_reroll_budget_grows_with_the_tier(tier: int) -> None:
    lib = library()
    report = skill_budget(_reroll(tier, {"mana": 0}), lib)
    expected = (
        lib.ruleset.core.tier_budget[tier]
        * Fraction(lib.budget.reaction_coefficient_permille, 1000)
        * Fraction(lib.budget.reroll_budget_permille, 1000)
    )
    assert report.effects[0].points == expected
    assert validate_skill(_reroll(tier, {"mana": 2}), lib) == []
