"""BAL-2c：形態幅度（``enter_form.magnitude_permille``）。

只放大形態對自己有利的部分（同完整姿態的幅度，3W-5b）；代價（負值、弱點）與維持費不放大。
引擎、預算器、卡片都用 :func:`trpg.content.forms.scaled_form_def`（經 ``Ruleset.scaled_form``），
行為一致：卡片數字＝實戰。
"""

from __future__ import annotations

from fractions import Fraction

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
from tests.engine.skill_helpers import FLAT7, U1, of
from trpg.content.forms import scaled_form_def
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, resolve
from trpg.engine.events import FormUpkeepPaid, ShieldGained
from trpg.engine.rules.forms import form_defense_permille, form_move_delta, form_taken_permille
from trpg.engine.state import state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.narrative.skills import skill_card
from trpg.shared.types import Element, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

FORM_SKILLS = (
    "skill_form_bear",
    "skill_form_cat",
    "skill_form_demon",
    "skill_form_dragon",
    "skill_form_elemental",
    "skill_form_giant",
    "skill_form_roc",
    "skill_form_shadow",
    "skill_form_treant",
    "skill_form_werewolf",
)


def _with_magnitude(skill_id: str, magnitude: int) -> SkillDef:
    skill = library().skills[skill_id]
    effect = skill.effects[0].model_copy(update={"magnitude_permille": magnitude})
    return skill.model_copy(update={"effects": (effect,)})


def _renamed(skill: SkillDef) -> SkillDef:
    """放進戰鬥用：換 ID（測試技能不能和內建技能同 ID）。"""
    return skill.model_copy(update={"id": f"{skill.id}_m"})


def _structural(skill: SkillDef) -> list[str]:
    """驗證器的違規（預算比例除外：1 階 ×120% 以上本來就超出預算窗）。"""
    return [v.rule for v in validate_skill(skill, library()) if not v.rule.startswith("budget.")]


def _scene(skill: SkillDef) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(5, 3)])
    owner = caster_template([skill], base="hero_fighter", max_hp=200, stamina=40)
    state = make_state(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=99))],
        skills=[skill],
    )
    state = give_turn(state, U1)
    state.units[U1].stamina = 40
    state.units[U1].mana = 40
    return state


def test_magnitude_1000_is_the_unchanged_form() -> None:
    rules = library().ruleset
    for form in rules.forms.forms:
        assert scaled_form_def(form, 1000) is form
        assert rules.scaled_form(form.id, 1000) is form


def test_only_the_favourable_parts_grow() -> None:
    rules = library().ruleset
    bear = rules.scaled_form("bear", 1500)
    assert bear.effects.max_hp_permille == 225 and bear.effects.defense_permille == 150
    assert bear.effects.move == -1  # 代價不放大
    assert bear.entry.shield_max_hp_permille == 150
    roc = rules.scaled_form("roc", 2000)
    assert roc.effects.max_hp_permille == -100 and roc.effects.flat_height == 2
    assert roc.entry.next_attack_hit == 4
    shadow = rules.scaled_form("shadow", 1500)
    taken = {m.element: m.permille for m in shadow.effects.damage_taken}
    assert taken == {Element.PHYSICAL: 700, Element.HOLY: 1500}  # 減傷放大、弱點不變
    treant = rules.scaled_form("treant", 1500)
    assert treant.effects.heal_permille == 300 and treant.effects.move == -2
    assert [m.permille for m in treant.effects.damage_taken] == [1500]
    werewolf = rules.scaled_form("werewolf", 1500)
    assert werewolf.effects.defense_permille == -100 and werewolf.effects.move == 1
    assert werewolf.entry.heal_max_hp_permille == 150
    elemental = rules.scaled_form("elemental", 1500)
    assert elemental.natural_weapon.damage_permille == 150
    assert elemental.natural_weapon.dice == rules.form_def("elemental").natural_weapon.dice
    giant = rules.scaled_form("giant", 1200)
    assert giant.entry.collision_permille == 600 and giant.effects.move == -1
    assert rules.scaled_form("cat", 1500).entry.next_attack_crit == 3
    assert rules.scaled_form("shadow", 2000).entry.conceal == 1  # 回合數不放大


def test_the_skill_with_a_magnitude_is_legal_and_its_points_grow() -> None:
    lib = library()
    base = skill_budget(lib.skills["skill_form_bear"], lib)
    for magnitude in (1000, 1200, 2000):
        skill = _with_magnitude("skill_form_bear", magnitude)
        assert _structural(skill) == []
        assert skill_budget(skill, lib).total == base.total * Fraction(magnitude, 1000)


def test_a_magnitude_below_1000_is_refused() -> None:
    skill = library().skills["skill_form_bear"]
    with pytest.raises(ValueError, match="magnitude_permille"):
        effect = skill.effects[0].model_copy(update={"magnitude_permille": 900})
        SkillDef.model_validate({**skill.model_dump(), "effects": [effect.model_dump()]})


def test_bear_in_battle_matches_the_card() -> None:
    """熊 ×150%：最大 HP、防禦、護盾＝卡片寫的數字；移動 −1 與維持費不變。"""
    skill = _renamed(_with_magnitude("skill_form_bear", 1500))
    lib = library()
    card = "".join(skill_card(lib, skill).effects)
    assert "幅度強化 ×150%" in card
    assert "最大 HP +22.5%" in card and "防禦 +15%" in card and "移動 −1" in card
    assert "護盾＝最大 HP 的 15%" in card
    assert f"−{lib.ruleset.forms.upkeep_stamina} 耐力" in card
    state = _scene(skill)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id))
    unit = result.state.units[U1]
    assert unit.form is not None and unit.form.magnitude_permille == 1500
    assert unit.max_hp == 200 + 200 * 225 // 1000
    assert form_defense_permille(result.state.ruleset, unit) == 150
    assert form_move_delta(result.state.ruleset, unit) == -1
    (shield,) = of(result, ShieldGained)
    assert shield.amount == unit.max_hp * 150 // 1000
    view = project_for(result.state, Team.ALLY).units
    hud = next(u for u in view if u.id == U1).form
    assert hud is not None and "防禦 +15%" in hud.effects_zh
    # 維持費照形態種類固定（#67）
    step = resolve(result.state, EndTurn(unit_id=U1))
    paid = list(of(step, FormUpkeepPaid))
    while step.state.active_unit != U1:
        step = resolve(step.state, EndTurn(unit_id=step.state.active_unit))  # type: ignore[arg-type]
        paid += of(step, FormUpkeepPaid)
    assert [e.amount for e in paid] == [lib.ruleset.forms.upkeep_stamina]


def test_shadow_resist_in_battle_matches_the_card() -> None:
    skill = _renamed(_with_magnitude("skill_form_shadow", 1500))
    card = "".join(skill_card(library(), skill).effects)
    assert "受物理傷害 −30%" in card and "受神聖傷害 +50%" in card
    result = resolve(_scene(skill), UseSkill(unit_id=U1, skill_id=skill.id))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    assert form_taken_permille(rules, unit, Element.PHYSICAL) == 700
    assert form_taken_permille(rules, unit, Element.HOLY) == 1500


def test_elemental_burst_is_scaled_like_the_card_says() -> None:
    skill = _with_magnitude("skill_form_elemental", 1200)
    card = "".join(skill_card(library(), skill).effects)
    assert "×120%" in card and "天生武器傷害 +12%" in card


@pytest.mark.parametrize("skill_id", FORM_SKILLS)
def test_every_form_card_uses_the_scaled_numbers(skill_id: str) -> None:
    lib = library()
    skill = _with_magnitude(skill_id, 2000)
    form = lib.ruleset.scaled_form(skill.form_id or "", 2000)
    assert _structural(skill) == []
    card = "".join(skill_card(lib, skill).effects)
    assert "幅度強化 ×200%" in card
    if form.effects.max_hp_permille > 0:
        assert f"最大 HP +{form.effects.max_hp_permille / 10:g}%" in card


def test_state_round_trip_keeps_the_magnitude_and_old_states_default() -> None:
    skill = _renamed(_with_magnitude("skill_form_bear", 1300))
    state = resolve(_scene(skill), UseSkill(unit_id=U1, skill_id=skill.id)).state
    text = state_to_json(state)
    back = state_from_json(text)
    form = back.units[U1].form
    assert form is not None and form.magnitude_permille == 1300
    old = text.replace('"magnitude_permille":1300,', "").replace(',"magnitude_permille":1300', "")
    assert '"magnitude_permille":1300' not in old
    legacy = state_from_json(old).units[U1].form
    assert legacy is not None and legacy.magnitude_permille == 1000
