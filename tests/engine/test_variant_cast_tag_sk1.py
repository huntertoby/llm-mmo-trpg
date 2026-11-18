"""SK-1（06 6.38 第 7 點，#166）：戰場變奏讀「本回合施放過帶某標籤的技能」（``caster_cast_tag``）。

條件成立與不成立、不看目標點（合法動作只列那一個型態）、走位估值不加分、卡片字、LLM schema 與
工坊選單都有這一支。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import U1
from trpg.content.skills import VARIANT_CONDITIONS, SkillDef, VariantWhen
from trpg.engine import BattleState
from trpg.engine.ai.variant import variant_move_bonus
from trpg.engine.variants import chosen_variant, possible_variants, variant_holds
from trpg.narrative.skills import variant_condition_text
from trpg.shared.types import Team
from trpg.skillgen.validate import validate_skill

FLAT = "\n".join(["0000000"] * 7)


def _skill() -> SkillDef:
    base = library().skills["skill_fire_bolt"]
    data: dict[str, Any] = base.model_dump(mode="json", exclude_none=True)
    data.update(
        id="skill_t_sk1_followup_bolt",
        rarity="epic",
        variants=[
            {
                "id": "after_fire",
                "name_zh": "趁火",
                "when": {"caster_cast_tag": "fire"},
                "shape": {"type": "line", "size": 3},
            }
        ],
    )
    return SkillDef.model_validate(data)


def _state(tags: tuple[str, ...]) -> BattleState:
    skill = _skill()
    m = make_map(FLAT, ally=[(3, 3)], enemy=[(3, 1)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([skill.id], base="hero_mage")),
        spawn(Team.ENEMY, (3, 1), no_reactions("bandit", max_hp=200)),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    state.units[U1].turn_cast_tags = tags
    return state


def test_when_accepts_exactly_the_new_branch() -> None:
    assert "caster_cast_tag" in VARIANT_CONDITIONS
    when = VariantWhen(caster_cast_tag="fire")
    assert when.kind == "caster_cast_tag"
    assert not when.target_dependent
    with pytest.raises(ValueError, match="恰好填一種"):
        VariantWhen(caster_cast_tag="fire", caster_high_ground=True)


def test_holds_only_after_a_matching_cast_this_turn() -> None:
    skill = _skill()
    on, off = _state(("spell", "fire")), _state(("spell", "ice"))
    when = skill.variants[0].when
    assert variant_holds(on, on.units[U1], when, None)
    assert not variant_holds(off, off.units[U1], when, (3, 1))
    found = chosen_variant(on, on.units[U1], on.ruleset.skill_def(skill.id), (3, 1))
    assert found is not None and found.id == "after_fire"
    assert chosen_variant(off, off.units[U1], off.ruleset.skill_def(skill.id), (3, 1)) is None
    # 不看目標點：成立時只剩這一個型態，不成立時只剩基礎型態
    assert possible_variants(on, on.units[U1], on.ruleset.skill_def(skill.id)) == ("after_fire",)
    assert possible_variants(off, off.units[U1], off.ruleset.skill_def(skill.id)) == (None,)


def test_moving_never_scores_for_an_order_condition() -> None:
    state = _state(())
    assert variant_move_bonus(state, state.units[U1], (2, 3), 5) == 0


def test_card_text_names_the_tag_in_chinese() -> None:
    text = variant_condition_text(library(), VariantWhen(caster_cast_tag="fire"))
    assert text.startswith("本回合已施放過帶「")
    assert "fire" not in text


def test_the_condition_itself_passes_validation() -> None:
    """驗證器不擋這個條件（預算由一般規則管，這裡只看條件與引用）。"""
    problems = validate_skill(_skill(), library())
    assert [p.rule for p in problems if "when" in p.message or "caster_cast_tag" in p.message] == []
