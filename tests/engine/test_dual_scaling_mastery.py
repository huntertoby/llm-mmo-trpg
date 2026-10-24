"""Phase 2H-2：雙屬性縮放（各 50%，取平均）與專精加成（最高屬性時施放距離／狀態持續 +1）。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from tests.skillgen.helpers import lib, violations
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import UseSkill, legal_actions, preview, resolve
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    Healed,
    ManeuverRolled,
    StatusApplied,
    StatusSaveRolled,
)
from trpg.engine.skills.scaling import mastery_active, skill_scaling_value
from trpg.engine.state import StatusInstance
from trpg.shared.types import Attribute, Pos

SINGLE = {"type": "single", "range": 5}
SPELL = {"type": "damage", "dice": "1d4", "element": "fire"}


def _skill(
    shape: dict[str, Any] = SINGLE,
    effects: list[dict[str, Any]] | None = None,
    *,
    rarity: str = "epic",
    **over: Any,
) -> SkillDef:
    base = make_skill(SID, shape, effects or [SPELL])
    return SkillDef.model_validate({**base.model_dump(mode="json"), "rarity": rarity, **over})


def _state(
    skill: SkillDef, attrs: dict[str, int], foes: Any = ((5, 3),), at: tuple[int, int] = (3, 3)
) -> Any:
    state = battle(skill, list(foes), caster=at)
    for name, value in attrs.items():
        state.units[U1].attributes[Attribute(name)] = value
    return state


def _amount(skill: SkillDef, attrs: dict[str, int]) -> int:
    result = cast(hit_with(_state(skill, attrs)), target_id=U2)
    return next(e.amount for e in of(result, DamageDealt) if e.cause == "attack")


DUAL: dict[str, Any] = {"scaling_attr": "str", "secondary_scaling_attr": "int"}

# ---------------------------------------------------------------------------
# 4.1 雙屬性縮放
# ---------------------------------------------------------------------------


def test_scaling_value_is_the_floored_average_of_the_two_effective_attributes() -> None:
    dual = _skill(**DUAL)
    state = _state(dual, {"str": 15, "int": 10})
    rules = state.ruleset
    assert skill_scaling_value(rules, state.units[U1], dual) == 12  # (15 + 10) // 2，奇數捨去
    state.units[U1].attributes[Attribute.STR] = 16
    assert skill_scaling_value(rules, state.units[U1], dual) == 13
    assert skill_scaling_value(rules, state.units[U1], _skill(scaling_attr="str")) == 16


def test_scaling_value_uses_effective_attributes_including_status_bonuses() -> None:
    dual = _skill(**DUAL)
    state = _state(dual, {"str": 10, "int": 11})
    state.units[U1].statuses = [StatusInstance("empowered", 2, U1)]  # 六屬性各 +2
    assert skill_scaling_value(state.ruleset, state.units[U1], dual) == (12 + 13) // 2


def test_spell_damage_uses_the_average() -> None:
    as_wis = _skill(scaling_attr="wis")  # wis 12 = (8 + 16) / 2
    as_int = _skill(scaling_attr="int")
    attrs = {"str": 8, "int": 16, "wis": 12}
    assert _amount(_skill(**DUAL), attrs) == _amount(as_wis, attrs)
    assert _amount(_skill(**DUAL), attrs) != _amount(as_int, attrs)


def test_spell_hit_uses_the_average() -> None:
    result = cast(hit_with(_state(_skill(**DUAL), {"str": 8, "int": 16})), target_id=U2)
    rolled = next(e for e in of(result, AttackRolled) if e.skill_id == SID)
    assert rolled.attack_value == 12


def test_heal_scaling_uses_the_average() -> None:
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    amounts = []
    for kwargs in ({"scaling_attr": "wis"}, DUAL):
        skill = _skill({"type": "self"}, [heal], **kwargs)
        state = _state(skill, {"str": 8, "int": 16, "wis": 12})
        state.units[U1].hp = 5
        result = resolve(hit_with(state), UseSkill(unit_id=U1, skill_id=SID))
        amounts.append(of(result, Healed)[0].amount)
    assert amounts[0] == amounts[1]


def test_status_save_uses_the_average() -> None:
    effects = [{"type": "apply_status", "status": "slow", "duration": 2}]
    dual = _skill(effects=effects, **DUAL)
    result = cast(hit_with(_state(dual, {"str": 8, "int": 16})), target_id=U2)
    save = of(result, StatusSaveRolled)[0]
    assert (save.attack_attr, save.attack_value) == (Attribute.STR, 12)


def _flat_defender(state: Any) -> None:
    for attr in Attribute:
        state.units[U2].attributes[attr] = 12


def test_knock_prone_contest_uses_the_average_for_the_attacker() -> None:
    effects: list[dict[str, Any]] = [SPELL, {"type": "knock_prone"}]
    modifiers = []
    for kwargs in ({"scaling_attr": "wis"}, DUAL):
        state = _state(_skill(effects=effects, **kwargs), {"str": 8, "int": 16, "wis": 12})
        _flat_defender(state)
        result = cast(hit_with(state), target_id=U2)
        modifiers.append(of(result, ManeuverRolled)[0].modifier)
    assert modifiers[0] == modifiers[1]


def test_preview_uses_the_average() -> None:
    effects = [{"type": "apply_status", "status": "slow", "duration": 2}]
    chances = []
    for kwargs in ({"scaling_attr": "wis"}, DUAL):
        state = _state(_skill(effects=effects, **kwargs), {"str": 8, "int": 16, "wis": 12})
        _flat_defender(state)
        view = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
        chances.append(view.targets[0].status_chances[0].apply_chance)
    assert chances[0] == chances[1]


def test_a_dual_skill_must_not_repeat_the_primary_attribute() -> None:
    with pytest.raises(ValidationError, match="不可和 scaling_attr 相同"):
        _skill(scaling_attr="int", secondary_scaling_attr="int")


def test_dual_scaling_needs_rare_or_better() -> None:
    """3I-3（#46）：雙屬性縮放的最低稀有度由史詩降為稀有。"""
    rules = lib().ruleset
    assert rules.core.dual_scaling_min_rarity == "rare"
    for rarity, ok in (("common", False), ("rare", True), ("epic", True), ("legendary", True)):
        # 傳說必須花源力並含改寫規則型原語（Phase 3C-4a），這裡補上讓它只差雙屬性這一項
        legendary: dict[str, Any] = (
            {
                "cost": {"source": 1, "cooldown": 2},
                "effects": [SPELL, {"type": "grant_ap", "amount": 1, "affects": "self"}],
            }
            if rarity == "legendary"
            else {}
        )
        problems = skill_problems(
            _skill(rarity=rarity, **DUAL, **legendary),
            rules.shapes.by_id(),
            rules.primitives.by_id(),
            status_ids={s.id for s in rules.statuses.statuses},
            object_ids={o.id for o in rules.objects.objects},
            conditions=rules.conditions.by_id(),
            dual_min_rarity=rules.core.dual_scaling_min_rarity,
        )
        assert (problems == []) is ok, (rarity, problems)


def test_the_validator_rejects_a_dual_skill_below_rare() -> None:
    assert "reference" in {v.rule for v in violations(_skill(rarity="common", **DUAL))}
    assert "reference" not in {v.rule for v in violations(_skill(rarity="rare", **DUAL))}


# ---------------------------------------------------------------------------
# 4.2 專精加成
# ---------------------------------------------------------------------------


def test_mastery_is_active_when_the_scaling_attribute_is_the_highest_including_ties() -> None:
    skill = _skill(mastery="range", scaling_attr="int")
    unit = _state(skill, {}).units[U1]  # hero_mage：int 16 為最高
    assert mastery_active(unit, skill)
    unit.attributes[Attribute.STR] = 16  # 並列
    assert mastery_active(unit, skill)
    unit.attributes[Attribute.STR] = 17
    assert not mastery_active(unit, skill)
    assert not mastery_active(unit, _skill(scaling_attr="int"))  # 沒有 mastery


def test_mastery_uses_base_attributes_not_status_bonuses() -> None:
    skill = _skill(mastery="range", scaling_attr="wis")
    unit = _state(skill, {}).units[U1]  # int 16 > wis 12
    unit.statuses = [StatusInstance("empowered", 2, U1)]  # 全屬性 +2 也不改變最高屬性
    assert not mastery_active(unit, skill)


def _targets(state: Any) -> set[str]:
    return {a.target_id for a in legal_actions(state) if isinstance(a, UseSkill) and a.target_id}


def test_range_mastery_makes_a_target_one_tile_farther_legal() -> None:
    far = ((6, 3),)  # 施放者 (0,3)，距離 6 超出射程 5；射程 +1 後合法
    plain = _skill(scaling_attr="int")
    mastered = _skill(mastery="range", scaling_attr="int")
    assert U2 not in _targets(_state(plain, {}, far, (0, 3)))
    assert U2 in _targets(_state(mastered, {}, far, (0, 3)))
    assert U2 not in _targets(_state(mastered, {"str": 20}, far, (0, 3)))  # 非最高屬性：不生效


def test_range_mastery_extends_the_cast_distance_but_not_the_area_size() -> None:
    area = _skill({"type": "square3", "range": 3}, [SPELL], mastery="range", scaling_attr="int")
    state = _state(area, {}, ((6, 6),), (0, 3))
    centers = {
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_pos
    }
    assert (4, 3) in centers and (5, 3) not in centers  # 原本最遠 (3,3)；專精 +1 → (4,3)
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=4, y=3))
    assert len(preview(state, action).affected_tiles) == 9  # 3×3 不變


def test_duration_mastery_adds_one_turn_to_the_applied_status() -> None:
    effects = [{"type": "apply_status", "status": "feared", "duration": 2}]
    got = []
    for mastery, str_ in ((None, 8), ("duration", 8), ("duration", 20)):
        skill = _skill(effects=effects, scaling_attr="int", mastery=mastery)
        state = _state(skill, {"str": str_})
        _flat_defender(state)
        result = cast(hit_with(state, [(20, 20)]), target_id=U2)
        got.append([e.duration for e in of(result, StatusApplied) if e.target_id == U2])
    assert got == [[2], [3], [2]]  # 沒專精 2；專精生效 3；力量比智力高 → 不生效 2


def test_duration_mastery_does_not_change_the_self_status_cost() -> None:
    effects: list[dict[str, Any]] = [
        SPELL,
        {"type": "apply_status", "status": "slow", "duration": 2},
    ]
    skill = _skill(
        effects=effects,
        scaling_attr="int",
        mastery="duration",
        cost={"mana": 0, "self_status": {"status": "vulnerable", "duration": 2}},
    )
    result = cast(hit_with(_state(skill, {}), [(20, 20)]), target_id=U2)
    status = result.state.units[U1].get_status("vulnerable")
    assert status is not None and status.remaining == 2


def test_preview_shows_the_mastered_status_duration() -> None:
    effects = [{"type": "apply_status", "status": "feared", "duration": 2}]
    skill = _skill(effects=effects, scaling_attr="int", mastery="duration")
    state = _state(skill, {})
    view = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    applied = [e for e in view.max_events if isinstance(e, StatusApplied) and e.target_id == U2]
    assert applied and applied[0].duration == 3


def test_invalid_mastery_combinations_are_rejected() -> None:
    shield = [{"type": "shield", "dice": "1d4", "affects": "self"}]
    with pytest.raises(ValidationError, match=r"shape\.range"):
        _skill({"type": "self"}, shield, mastery="range")
    with pytest.raises(ValidationError, match="apply_status"):
        _skill(mastery="duration")  # 只有傷害
    with pytest.raises(ValidationError, match="不享專精"):
        _skill(mastery="range", **DUAL)
