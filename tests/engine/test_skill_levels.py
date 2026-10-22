"""Phase 3-26a：技能等級的引擎結算（2／4 級效果加成、5 級小特性、單位資料、重播）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    library,
    make_map,
    make_skill,
    make_state,
    spawn,
    template,
)
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of, script_rolls
from trpg.content.skill_growth import SkillGrowthRules
from trpg.engine import state_from_json, state_to_json
from trpg.engine.events import DamageDealt, Healed, ShieldGained
from trpg.engine.modifiers import acting_skill
from trpg.engine.skill_levels import level_multiplier, level_trait
from trpg.engine.state import BattleState
from trpg.shared.types import Team

_HEAL = [{"type": "heal", "dice": "2d6", "affects": "allies"}]
_SHIELD = [{"type": "shield", "dice": "2d6", "affects": "allies"}]
_FIRE = [{"type": "damage", "dice": "2d6", "element": "fire", "affects": "enemies"}]


def _leveled(state: BattleState, level: int) -> BattleState:
    s = state.clone()
    s.units[U1].skill_levels = {SID: level} if level > 1 else {}  # type: ignore[index]
    return s


def _damage(level: int, monkeypatch: pytest.MonkeyPatch) -> DamageDealt:
    skill = make_skill(SID, {"type": "single", "range": 5}, _FIRE)
    state = _leveled(battle(skill, foes=[(5, 3)]), level)
    with monkeypatch.context() as scripted:
        script_rolls(scripted, [10, 6, 6])  # 命中 d20，再 2d6
        (dealt,) = of(cast(state, target_id=U2), DamageDealt)
    return dealt


def test_the_growth_table_comes_from_content() -> None:
    growth = library().ruleset.skill_growth
    assert growth == SkillGrowthRules()  # 預設值與 content/skill_growth.yaml 相同
    assert [growth.multiplier_permille(n) for n in range(1, 6)] == [1000, 1100, 1100, 1200, 1200]
    assert growth.points_per_level == 2 and growth.upgrade_cost == 1 and growth.max_level == 5


def test_damage_levels_two_and_four_add_ten_percent_each(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _damage(1, monkeypatch)
    two = _damage(2, monkeypatch)
    three = _damage(3, monkeypatch)
    four = _damage(4, monkeypatch)
    assert two.multiplier_permille == base.multiplier_permille * 1100 // 1000
    assert three.amount == two.amount  # 3 級先只計等級
    assert four.multiplier_permille == base.multiplier_permille * 1200 // 1000
    assert base.amount < two.amount < four.amount
    # 無條件捨去的整數結算：2d6=12 ＋ 縮放，倍率 1100 → amount ＝ raw × 1.1 向下取整
    raw = base.amount
    assert two.amount == raw * 1100 // 1000
    assert four.amount == raw * 1200 // 1000


@pytest.mark.parametrize(("kind", "effects"), [("heal", _HEAL), ("shield", _SHIELD)])
def test_heal_and_shield_scale_too(
    kind: str, effects: list[dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def amount(level: int) -> int:
        skill = make_skill(SID, {"type": "single", "range": 4}, effects)
        state = _leveled(battle(skill, foes=[(6, 6)], allies=[(3, 4)]), level)
        with monkeypatch.context() as scripted:
            script_rolls(scripted, [6, 6])
            result = cast(state, target_id="unit_0002")
        event = of(result, Healed)[0] if kind == "heal" else of(result, ShieldGained)[0]
        return event.amount

    base = amount(1)
    # 治療以「已受傷」為前提；沒受傷時 Healed.amount 會被夾成 0，所以只比較護盾
    if kind == "shield":
        assert amount(2) == base * 1100 // 1000
        assert amount(4) == base * 1200 // 1000
    else:
        assert base == 0  # 目標滿血：治療量為 0（等級效果在受傷時才看得到，見下個測試）


def test_heal_multiplier_applies_to_a_wounded_ally(monkeypatch: pytest.MonkeyPatch) -> None:
    def healed(level: int) -> int:
        skill = make_skill(SID, {"type": "single", "range": 4}, _HEAL)
        state = _leveled(battle(skill, foes=[(6, 6)], allies=[(3, 4)]), level)
        wounded = state.clone()
        wounded.units["unit_0002"].hp = 1  # type: ignore[index]
        with monkeypatch.context() as scripted:
            script_rolls(scripted, [6, 6])
            return of(cast(wounded, target_id="unit_0002"), Healed)[0].amount

    base = healed(1)
    assert healed(2) > base and healed(4) > healed(2)
    assert healed(3) == healed(2) and healed(5) == healed(4)


def test_only_active_skills_get_the_effect_bonus() -> None:
    rules = library().ruleset
    skill = make_skill(SID, {"type": "single", "range": 4}, _FIRE)
    state = _leveled(battle(skill, foes=[(5, 3)]), 4)
    unit = state.units[U1]  # type: ignore[index]
    assert level_multiplier(rules, unit, skill) == 1200
    passive = skill.model_copy(update={"kind": "passive"})
    assert level_multiplier(rules, unit, passive) == 1000


def test_level_five_trait_picks_area_when_the_shape_can_grow() -> None:
    rules = library().ruleset
    cone = make_skill(SID, {"type": "cone", "size": 3}, _FIRE)
    assert level_trait(rules, cone) == "area"
    state = _leveled(battle(cone, foes=[(5, 3)]), 5)
    shaped = acting_skill(state, state.units[U1], SID)  # type: ignore[arg-type]
    assert shaped.shape.size == 4 and cone.shape.size == 3
    four = _leveled(state, 4)
    assert acting_skill(four, four.units[U1], SID).shape.size == 3  # type: ignore[arg-type]


def test_level_five_area_trait_is_capped_by_the_shape_maximum() -> None:
    rules = library().ruleset
    top = rules.shape_def("cone").params["size"].max
    maxed = make_skill(SID, {"type": "cone", "size": top}, _FIRE)
    assert level_trait(rules, maxed) is None  # 範圍已達上限、也沒有冷卻 → 沒有小特性
    state = _leveled(battle(maxed, foes=[(5, 3)]), 5)
    assert acting_skill(state, state.units[U1], SID).shape.size == top  # type: ignore[arg-type]
    with_cooldown = make_skill(SID, {"type": "cone", "size": top}, _FIRE, cost={"cooldown": 3})
    assert level_trait(rules, with_cooldown) == "cooldown"  # 範圍滿了就改減冷卻


def test_level_five_trait_falls_back_to_cooldown_minus_one() -> None:
    rules = library().ruleset
    single = make_skill(SID, {"type": "single", "range": 4}, _FIRE, cost={"cooldown": 3})
    assert level_trait(rules, single) == "cooldown"
    state = _leveled(battle(single, foes=[(5, 3)]), 5)
    assert acting_skill(state, state.units[U1], SID).cost.cooldown == 2  # type: ignore[arg-type]
    # 冷卻 1 減了就沒有冷卻，不做；沒有冷卻也不做
    for cost in ({"cooldown": 1}, {"mana": 0}):
        plain = make_skill(SID, {"type": "single", "range": 4}, _FIRE, cost=cost)
        assert level_trait(rules, plain) is None


def test_the_reduced_cooldown_is_what_the_cast_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    single = make_skill(SID, {"type": "single", "range": 5}, _FIRE, cost={"cooldown": 3})
    state = _leveled(battle(single, foes=[(5, 3)]), 5)
    script_rolls(monkeypatch, [10, 3, 3])
    assert cast(state, target_id=U2).state.units[U1].cooldowns[SID] == 2  # type: ignore[index]


def test_skill_levels_survive_a_json_round_trip_and_clone() -> None:
    skill = make_skill(SID, {"type": "single", "range": 4}, _FIRE)
    state = _leveled(battle(skill, foes=[(5, 3)]), 4)
    again = state_from_json(state_to_json(state))
    assert again.units[U1].skill_levels == {SID: 4}  # type: ignore[index]
    assert again == state
    assert state.clone().units[U1].skill_levels == {SID: 4}  # type: ignore[index]


def test_a_template_with_skill_levels_builds_a_leveled_unit() -> None:
    skill = make_skill(SID, {"type": "single", "range": 4}, _FIRE)
    m = make_map("000\n000", ally=[(0, 0)], enemy=[(2, 1)])
    tmpl = caster_template([skill], skill_levels={SID: 3})
    foe = spawn(Team.ENEMY, (2, 1), template("bandit"))
    state = make_state(m, [spawn(Team.ALLY, (0, 0), tmpl), foe], skills=[skill])
    assert state.units[U1].skill_levels == {SID: 3}  # type: ignore[index]


def test_template_rejects_levels_for_unequipped_skills() -> None:
    with pytest.raises(ValidationError, match="裝備中"):
        template("hero_mage", skills=["skill_fireball"], skill_levels={"skill_other": 2})
    with pytest.raises(ValidationError, match="技能等級必須"):
        template("hero_mage", skills=["skill_fireball"], skill_levels={"skill_fireball": 1})
