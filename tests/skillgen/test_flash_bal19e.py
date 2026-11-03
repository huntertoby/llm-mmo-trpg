"""BAL-19e（玩法決定 #110「閃現的反應、姿態變化模板各補到約 10 種」，06 6.34.4）：

- 姿態：附帶護身（``self_rider``：護盾、治療、冷卻 −1、回魔、淨化）、沉勢（``stance_enter_heavy``：
  進入代價 +1、本體提高一級）。變身姿態不出（BAL-2c／10c）。
- 反應：附帶護身（護盾、冷卻 −1），「觸發範圍 +1／+2」用在反應的單體射程。
行為一致：預算比例在窗內、分數不低於變化前、驗證通過。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.flash_templates import FlashTemplate
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_category import template_kinds
from trpg.skillgen.flash_derive import apply_variation, at_role_tier
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.flash_trade import MINOR_OPS
from trpg.skillgen.validate import validate_skill

STANCE_RIDERS = ("stance_ward", "stance_mend", "stance_refocus", "stance_channel", "stance_cleanse")
REACTION_RIDERS = ("reaction_ward", "reaction_refocus")


def _variation(template_id: str) -> Variation:
    template = library().flash.minor_template(template_id)
    assert template is not None
    return Variation(source="minor", template=template_id, category=template.category)


def _at(skill_id: str, tier: int) -> SkillDef:
    return at_role_tier(library(), library().skills[skill_id], tier)


def _sound(before: SkillDef, after: SkillDef | None) -> SkillDef:
    lib = library()
    assert after is not None
    assert validate_skill(after, lib) == []
    report = skill_budget(after, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio
    assert budget_power(after, lib) >= budget_power(before, lib)
    return after


def _applicable(kind: str) -> list[FlashTemplate]:
    table = library().flash
    return [t for t in table.minor if kind in template_kinds(table, t) and t.op in MINOR_OPS]


@pytest.mark.parametrize("kind", ["stance", "reaction"])
def test_about_ten_minor_templates_for_reactions_and_stances(kind: str) -> None:
    assert len(_applicable(kind)) >= 10


@pytest.mark.parametrize(
    ("skill_id", "template_id"),
    [("skill_st_dawn_vigil", t) for t in STANCE_RIDERS]
    + [("skill_fury_stance", t) for t in STANCE_RIDERS if t != "stance_channel"],
)
def test_stance_riders_add_one_self_effect_on_entry(skill_id: str, template_id: str) -> None:
    lib = library()
    stance = _at(skill_id, 2)
    got = _sound(
        stance, apply_variation(lib, stance, _variation(template_id), bonus=40, rng=Rng(3))
    )
    template = lib.flash.minor_template(template_id)
    assert template is not None and template.rider is not None
    assert len(got.effects) == 2
    assert got.effects[0].status is not None  # 姿態本體仍在第一個
    assert got.effects[1].type == template.rider.type and got.effects[1].affects == "self"


def test_riders_skip_forms_and_stances_that_already_have_a_rider() -> None:
    lib = library()
    form = _at("skill_form_bear", 2)
    assert apply_variation(lib, form, _variation("stance_ward"), bonus=40, rng=Rng(3)) is None
    stance = _at("skill_fury_stance", 2)
    warded = apply_variation(lib, stance, _variation("stance_ward"), bonus=40, rng=Rng(3))
    assert warded is not None
    assert apply_variation(lib, warded, _variation("stance_mend"), bonus=80, rng=Rng(3)) is None


@pytest.mark.parametrize("skill_id", ["skill_fury_stance", "skill_st_umbral_pact"])
def test_enter_heavy_raises_the_entry_cost_and_the_stance(skill_id: str) -> None:
    lib = library()
    stance = _at(skill_id, 2)
    got = _sound(
        stance, apply_variation(lib, stance, _variation("stance_enter_heavy"), bonus=40, rng=Rng(3))
    )
    assert got.cost.mana + got.cost.stamina == stance.cost.mana + stance.cost.stamina + 1
    assert got.stance_upkeep == stance.stance_upkeep  # 維持費不動（#67）
    assert got.effects[0] != stance.effects[0]  # 姿態本體提高一級（幅度或階梯）
    form = _at("skill_form_bear", 2)
    assert (
        apply_variation(lib, form, _variation("stance_enter_heavy"), bonus=40, rng=Rng(3)) is None
    )


@pytest.mark.parametrize("template_id", REACTION_RIDERS)
def test_reaction_riders_add_a_self_effect_and_retune_the_main_one(template_id: str) -> None:
    lib = library()
    riposte = _at("skill_riposte", 1)
    got = _sound(
        riposte, apply_variation(lib, riposte, _variation(template_id), bonus=40, rng=Rng(3))
    )
    assert got.effects[0].type == "damage"
    assert got.effects[1].affects == "self" and len(got.effects) == 2
    # 擋攻擊（intercept）與已經有附帶效果的反應不出
    for skill_id in ("skill_stand_firm", "skill_rx_shadow_grasp"):
        skill = _at(skill_id, 1)
        assert apply_variation(lib, skill, _variation(template_id), bonus=40, rng=Rng(3)) is None


def test_trigger_range_reaches_further_for_single_target_reactions() -> None:
    lib = library()
    counter = _at("skill_counterspell", 1)
    assert counter.shape.range == 6
    got = _sound(
        counter, apply_variation(lib, counter, _variation("trigger_range"), bonus=40, rng=Rng(3))
    )
    assert got.shape.type == "single" and got.shape.range == 7
    riposte = _at("skill_riposte", 1)  # 武器射程：不適用
    assert apply_variation(lib, riposte, _variation("trigger_range"), bonus=40, rng=Rng(3)) is None
