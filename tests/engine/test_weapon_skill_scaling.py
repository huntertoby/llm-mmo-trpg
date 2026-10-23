"""Phase 3H-6：武器技的命中、傷害、對抗、專精一律看手上武器的屬性（玩法決定 #45）。

技能自己的 ``scaling_attr`` 對武器技不生效（只當顯示提示）；雙屬性武器照 ``attr_mode`` 取較高／
取平均；法術技不受影響。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from trpg.content.skills import SkillDef
from trpg.engine import UseSkill, preview
from trpg.engine.events import AttackRolled, DamageDealt, ManeuverRolled, StatusSaveRolled
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skills.scaling import (
    mastery_active,
    skill_scale_attr,
    skill_scaling_attr,
    skill_scaling_value,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute

SINGLE = {"type": "single", "range": 1}
STRIKE = {"type": "damage"}


def _weapon_skill(
    effects: list[dict[str, Any]] | None = None, attr: str = "int", **over: Any
) -> SkillDef:
    """武器技；``attr`` 是技能自己的（顯示提示）縮放屬性，故意設成和武器無關的值。"""
    base = make_skill(SID, SINGLE, effects or [STRIKE], category="weapon", attr=attr)
    return SkillDef.model_validate({**base.model_dump(mode="json"), **over})


def _state(skill: SkillDef, weapon_id: str, attrs: dict[str, int]) -> BattleState:
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    unit = state.units[U1]
    unit.weapon = library().weapons[weapon_id]
    for name, value in attrs.items():
        unit.attributes[Attribute(name)] = value
    return state


def _value(skill: SkillDef, weapon_id: str, attrs: dict[str, int]) -> int:
    state = _state(skill, weapon_id, attrs)
    return skill_scaling_value(state.ruleset, state.units[U1], skill)


# 武器 × 屬性：技能自己的屬性是智力，施放者智力再高也不加
TABLE = [
    # (武器, 屬性, 期望值)
    ("one_handed_sword", {"str": 12, "dex": 9, "int": 30}, 12),  # 力量單屬性
    ("one_handed_sword", {"str": 12, "dex": 20, "int": 30}, 12),  # 敏捷再高也不算
    ("bow", {"str": 20, "dex": 11, "int": 30}, 11),  # 敏捷單屬性
    ("dagger", {"str": 10, "dex": 14, "int": 30}, 14),  # 敏捷／力量取較高
    ("dagger", {"str": 16, "dex": 14, "int": 30}, 16),
    ("hammer", {"str": 10, "con": 15, "int": 30}, 12),  # 體質／力量取平均（15 + 10) // 2
    ("hammer", {"str": 11, "con": 15, "int": 30}, 13),
    ("fire_staff", {"str": 10, "int": 17}, 17),  # 法杖看智力
]


@pytest.mark.parametrize(("weapon_id", "attrs", "expected"), TABLE)
def test_a_weapon_skill_reads_the_wielded_weapon_attribute(
    weapon_id: str, attrs: dict[str, int], expected: int
) -> None:
    assert _value(_weapon_skill(), weapon_id, attrs) == expected


def test_the_skill_own_scaling_attr_does_not_matter_for_a_weapon_skill() -> None:
    attrs = {"str": 13, "int": 25, "wil": 25}
    values = {a: _value(_weapon_skill(attr=a), "one_handed_sword", attrs) for a in ("int", "wil")}
    assert set(values.values()) == {13}
    # 技能自己的第二屬性也不生效
    dual = _weapon_skill(rarity="epic", secondary_scaling_attr="wil")
    assert _value(dual, "one_handed_sword", attrs) == 13


def test_a_spell_skill_still_reads_its_own_attribute() -> None:
    spell = make_skill(
        SID, SINGLE, [{"type": "damage", "dice": "1d4", "element": "fire"}], category="spell"
    )
    state = battle(spell, [(4, 3)], caster=(3, 3))  # 法師拿法器
    state.units[U1].attributes[Attribute.STR] = 30
    state.units[U1].attributes[Attribute.INT] = 12
    assert skill_scaling_value(state.ruleset, state.units[U1], spell) == 12


def test_effective_attributes_with_status_bonuses_count() -> None:
    skill = _weapon_skill()
    state = _state(skill, "one_handed_sword", {"str": 10})
    from trpg.engine.state import StatusInstance  # noqa: PLC0415

    state.units[U1].statuses = [StatusInstance("empowered", 2, U1)]  # 六屬性各 +2
    unit = state.units[U1]
    assert skill_scaling_value(state.ruleset, unit, skill) == effective_attribute(
        state.ruleset, unit, Attribute.STR
    )


def test_contest_attribute_and_damage_log_attribute_follow_the_weapon() -> None:
    skill = _weapon_skill()
    sword = _state(skill, "one_handed_sword", {}).units[U1]
    hammer = _state(skill, "hammer", {}).units[U1]
    assert skill_scaling_attr(sword, skill) is Attribute.STR
    assert skill_scale_attr(sword, skill) is Attribute.STR
    assert skill_scale_attr(hammer, skill) is None  # 雙屬性：紀錄顯示「屬性」
    spell = make_skill(SID, SINGLE, [{"type": "damage", "dice": "1d4", "element": "fire"}])
    assert skill_scaling_attr(sword, spell) is Attribute.INT


def _amount(weapon_id: str, attrs: dict[str, int]) -> int:
    state = hit_with(_state(_weapon_skill(), weapon_id, attrs))
    result = cast(state, target_id=U2)
    return next(e.amount for e in of(result, DamageDealt) if e.cause == "attack")


def test_a_high_intelligence_adds_no_damage_to_a_strength_weapon_skill() -> None:
    low = _amount("one_handed_sword", {"str": 10, "int": 10})
    assert _amount("one_handed_sword", {"str": 10, "int": 40}) == low
    assert _amount("one_handed_sword", {"str": 40, "int": 10}) > low


def test_hit_uses_the_weapon_attack_value_and_not_the_skill_attribute() -> None:
    rolled = []
    for intel in (10, 40):
        result = cast(
            hit_with(_state(_weapon_skill(), "one_handed_sword", {"int": intel})), target_id=U2
        )
        rolled.append(next(e.attack_value for e in of(result, AttackRolled) if e.skill_id == SID))
    assert rolled[0] == rolled[1]


def test_status_save_and_knock_prone_contests_use_the_weapon_attribute() -> None:
    effects: list[dict[str, Any]] = [
        STRIKE,
        {"type": "apply_status", "status": "slow", "duration": 2},
    ]
    saves = []
    for intel in (10, 40):
        state = _state(_weapon_skill(effects), "one_handed_sword", {"str": 13, "int": intel})
        save = of(cast(hit_with(state), target_id=U2), StatusSaveRolled)[0]
        saves.append((save.attack_attr, save.attack_value))
    assert saves[0] == saves[1] == (Attribute.STR, 13)
    prone: list[dict[str, Any]] = [STRIKE, {"type": "knock_prone"}]
    mods = []
    for intel in (10, 40):
        state = _state(_weapon_skill(prone), "one_handed_sword", {"str": 13, "int": intel})
        mods.append(of(cast(hit_with(state), target_id=U2), ManeuverRolled)[0].modifier)
    assert mods[0] == mods[1]


def test_preview_status_chance_follows_the_weapon() -> None:
    effects: list[dict[str, Any]] = [
        STRIKE,
        {"type": "apply_status", "status": "slow", "duration": 2},
    ]
    chances = []
    for intel in (10, 40):
        state = _state(_weapon_skill(effects), "one_handed_sword", {"int": intel})
        view = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
        chances.append(view.targets[0].status_chances[0].apply_chance)
    assert chances[0] == chances[1]


def test_mastery_for_a_weapon_skill_looks_at_the_weapon_attribute() -> None:
    skill = _weapon_skill(rarity="epic", mastery="range", shape={"type": "single", "range": 2})
    # 力量武器：力量是最高屬性 → 專精生效，即使技能自己的屬性（智力）不是最高
    state = _state(skill, "one_handed_sword", {"str": 16, "int": 10})
    assert mastery_active(state.units[U1], skill)
    # 力量不是最高屬性 → 不生效，即使技能自己的屬性（智力）是最高
    state = _state(skill, "one_handed_sword", {"str": 10, "int": 18})
    assert not mastery_active(state.units[U1], skill)
    # 雙屬性取平均：兩個都要是最高（平均不低於最高）才生效
    state = _state(skill, "hammer", {"str": 14, "con": 14})
    assert mastery_active(state.units[U1], skill)
    state = _state(skill, "hammer", {"str": 10, "con": 16})
    assert not mastery_active(state.units[U1], skill)
    # 雙屬性取較高：任一個是最高即可
    state = _state(skill, "dagger", {"str": 10, "dex": 16})
    assert mastery_active(state.units[U1], skill)


def test_the_card_bonus_equals_the_engine_value() -> None:
    """卡片的「目前 +N」和引擎實際值用同一個算法（3-41c 的保證延伸到武器技）。"""
    lib = library()
    skill = _weapon_skill()
    for weapon_id, attrs in (("one_handed_sword", {"str": 13, "int": 25}), ("hammer", {"str": 9})):
        state = _state(skill, weapon_id, attrs)
        unit = state.units[U1]
        engine = skill_scaling_value(state.ruleset, unit, skill)
        weapon = lib.weapons[weapon_id]

        def get(a: Attribute, state: BattleState = state, unit: UnitState = unit) -> int:
            return effective_attribute(state.ruleset, unit, a)

        assert skill.scaling_value(get, weapon) == engine
        lines = skill.formula_lines_zh(lib.ruleset.core, weapon, get)
        assert lines
        assert weapon.scaling_names_zh() in lines[0]
        assert "目前" in lines[0]


def test_the_card_names_the_weapon_attribute_or_the_generic_text() -> None:
    lib = library()
    skill = _weapon_skill()
    (generic,) = skill.formula_lines_zh(lib.ruleset.core)
    assert "武器的屬性" in generic
    (named,) = skill.formula_lines_zh(lib.ruleset.core, lib.weapons["one_handed_sword"])
    assert "力量" in named and "智力" not in named
