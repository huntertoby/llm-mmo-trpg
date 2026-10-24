"""魔劍士方案 A＋魔導劍（Phase 3I-3；`docs/phases/Phase3I計畫.md`；06 6.10、08 8.11，#46）。

- 魔導劍：單手近戰、1d8、力量／智力取平均、沒有特性；普攻吃平均。
- 武器技可帶一個心智第二屬性：命中、傷害、控制抵抗用「武器的縮放值」與「心智屬性值」的平均
  （無條件捨去）；對抗判定的攻方值也用平均（3I-3b），守方仍比武器的主屬性。
- 行為一致測試：每把武器 × 屬性組合 × 第二屬性，實際跑普攻與武器技，``damage_dealt`` 的骰外加成
  等於卡片的「目前 +N」。
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with, of
from tests.engine.test_weapons_24a1 import U1, U2, armed, dice, hit, kinds, state_of, weapon
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, preview
from trpg.engine.events import AttackRolled, DamageDealt, ManeuverRolled, StatusSaveRolled
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skills.scaling import skill_scale_attr, skill_scaling_attr, skill_scaling_value
from trpg.engine.state import UnitState
from trpg.narrative.skills import contest_label
from trpg.roguelite.start import start_weapons
from trpg.shared.bonus_text import plain_text
from trpg.shared.types import Attribute, Team

A = Attribute
_CURRENT = re.compile(r"目前 \+(\d+)")


def _current(line: str) -> int:
    found = _CURRENT.search(plain_text(line))
    assert found is not None, line
    return int(found.group(1))


def _getter(state: BattleState, unit: UnitState) -> Any:
    return lambda a: effective_attribute(state.ruleset, unit, a)


# ---------------------------------------------------------------------------
# 魔導劍的資料
# ---------------------------------------------------------------------------


def test_the_arcane_blade_is_a_single_hand_melee_weapon_without_traits() -> None:
    blade = library().weapons["arcane_blade"]
    assert (blade.weapon_class, blade.range, blade.two_handed, blade.paired) == (
        "melee",
        1,
        False,
        False,
    )
    assert (str(blade.dice), blade.flat, blade.element.value) == ("1d8", 0, "physical")
    assert (blade.scaling_attr, blade.secondary_scaling_attr, blade.attr_mode) == (
        A.STR,
        A.INT,
        "mean",
    )
    # 沒有特性（小特性待定）：沒有反擊、收割、纏繞、破甲、震退……的任何特性行
    assert blade.trait_lines_zh() == ()
    assert blade.look is not None
    assert (blade.look.kind, blade.look.form, blade.look.material) == ("sword", "arcane", "steel")
    assert blade.look.element is None


def test_the_arcane_blade_appears_in_the_start_weapons() -> None:

    assert "arcane_blade" in start_weapons(library())


# ---------------------------------------------------------------------------
# 縮放值：武器技的第二屬性取平均
# ---------------------------------------------------------------------------


def _weapon_skill(second: str | None = None, **over: Any) -> SkillDef:
    base = make_skill(SID, {"type": "single", "range": 2}, [{"type": "damage"}], category="weapon")
    data = {**base.model_dump(mode="json"), "weapon_req": "melee", "rarity": "rare", **over}
    if second is not None:
        data["secondary_scaling_attr"] = second
    return SkillDef.model_validate(data)


def _state(skill: SkillDef, weapon_id: str, attrs: dict[str, int]) -> BattleState:
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    unit = state.units[U1]
    unit.weapon = library().weapons[weapon_id]
    for name, value in attrs.items():
        unit.attributes[Attribute(name)] = value
    return state


# (武器, 第二屬性, 屬性, 期望縮放值)
VALUE_TABLE: list[tuple[str, str | None, dict[str, int], int]] = [
    ("one_handed_sword", None, {"str": 12, "int": 30}, 12),  # 沒有第二屬性：智力不算
    ("one_handed_sword", "int", {"str": 12, "int": 20}, 16),  # 魔劍斬：力量 12、智力 20 → 16
    ("one_handed_sword", "int", {"str": 13, "int": 20}, 16),  # 無條件捨去 (13 + 20) // 2
    ("one_handed_sword", "wis", {"str": 10, "int": 40, "wis": 16}, 13),  # 感知，智力不算
    ("one_handed_sword", "wil", {"str": 18, "wil": 10}, 14),
    ("arcane_blade", None, {"str": 12, "int": 20}, 16),  # 魔導劍本身：(12 + 20) // 2
    ("arcane_blade", "int", {"str": 12, "int": 20}, 18),  # 武器值 16 再和智力 20 平均
    ("arcane_blade", "wis", {"str": 12, "int": 20, "wis": 8}, 12),  # (16 + 8) // 2
    ("scythe", "int", {"wil": 16, "str": 11, "int": 21}, 17),  # (13 + 21) // 2
    ("dagger", "wil", {"dex": 14, "str": 16, "wil": 6}, 11),  # 匕首取較高 16，(16 + 6) // 2
    ("hammer", "int", {"con": 18, "str": 11, "int": 10}, 14),  # 錘取較高 18，(18 + 10) // 2
    ("whip", "wis", {"dex": 15, "wis": 10}, 11),  # 鞭 (15 + 10) // 2 ＝ 12，再和感知 10 → 11
]


@pytest.mark.parametrize(("weapon_id", "second", "attrs", "expected"), VALUE_TABLE)
def test_a_weapon_skill_averages_the_weapon_value_with_the_mind_attribute(
    weapon_id: str, second: str | None, attrs: dict[str, int], expected: int
) -> None:
    skill = _weapon_skill(second)
    state = _state(skill, weapon_id, attrs)
    assert skill_scaling_value(state.ruleset, state.units[U1], skill) == expected


def test_contest_attribute_stays_the_weapon_primary_and_the_log_shows_a_blend() -> None:
    skill = _weapon_skill("int")
    sword = _state(skill, "one_handed_sword", {}).units[U1]
    assert skill_scaling_attr(sword, skill) is A.STR  # 對抗只用武器的主屬性
    assert skill_scale_attr(sword, skill) is None  # 雙屬性：紀錄顯示「屬性」
    single = _weapon_skill()
    assert skill_scale_attr(sword, single) is A.STR


def test_the_hit_roll_uses_the_averaged_value() -> None:
    values = []
    for second in (None, "int"):
        skill = _weapon_skill(second)
        state = hit_with(_state(skill, "one_handed_sword", {"str": 10, "int": 30}))
        result = cast(state, target_id=U2)
        values.append(next(e.attack_value for e in of(result, AttackRolled) if e.skill_id == SID))
    assert values[1] - values[0] == 10  # (10 + 30) // 2 ＝ 20，比單屬性的 10 多 10


def test_the_builtin_arcane_blade_skill_is_a_melee_weapon_skill_with_intelligence() -> None:
    lib = library()
    skill = lib.skills["skill_arcane_blade"].model_copy(update={"id": SID})
    assert skill.category == "weapon" and skill.weapon_req == "melee"
    assert skill.secondary_scaling_attr is A.INT
    state = _state(skill, "arcane_blade", {"str": 12, "int": 20})
    assert skill_scaling_value(state.ruleset, state.units[U1], skill) == 18


# ---------------------------------------------------------------------------
# 行為一致：普攻與武器技的骰外加成＝卡片「目前 +N」
# ---------------------------------------------------------------------------

ATTACK_TABLE: list[tuple[str, dict[str, int]]] = [
    ("arcane_blade", {"str": 12, "int": 20}),  # 平均 16
    ("arcane_blade", {"str": 21, "int": 10}),  # 平均 15（無條件捨去）
    ("arcane_blade", {"str": 10, "int": 10}),
    ("one_handed_sword", {"str": 14, "int": 30}),  # 對照：單屬性，智力不算
]


@pytest.mark.parametrize(("weapon_id", "attrs"), ATTACK_TABLE)
def test_basic_attack_matches_the_card_current_bonus(
    weapon_id: str, attrs: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = state_of(
        [
            armed(Team.ALLY, (2, 2), weapon(weapon_id), attributes=attrs),
            armed(Team.ENEMY, (3, 2), weapon("one_handed_sword"), base="bandit", resist={}),
        ]
    )
    unit = state.units[U1]
    now = _current(unit.weapon.attack_formula_zh(state.ruleset.core, _getter(state, unit)))
    (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == now
    if dealt.scaled_permille % 1000 == 0:
        assert dealt.amount == sum(dealt.rolls) + now


SKILL_TABLE: list[tuple[str, str | None, dict[str, int]]] = [
    ("one_handed_sword", "int", {"str": 12, "int": 20}),
    ("one_handed_sword", "wis", {"str": 15, "int": 40, "wis": 9}),
    ("one_handed_sword", "wil", {"str": 8, "wil": 17}),
    ("arcane_blade", None, {"str": 12, "int": 20}),
    ("arcane_blade", "int", {"str": 12, "int": 20}),
    ("arcane_blade", "wil", {"str": 19, "int": 11, "wil": 6}),
    ("scythe", "int", {"wil": 16, "str": 11, "int": 21}),
    ("dagger", "wis", {"dex": 14, "str": 16, "wis": 7}),
    ("whip", "int", {"dex": 15, "wis": 10, "int": 25}),
]


@pytest.mark.parametrize(("weapon_id", "second", "attrs"), SKILL_TABLE)
def test_weapon_skill_damage_matches_the_card_current_bonus(
    weapon_id: str, second: str | None, attrs: dict[str, int]
) -> None:
    skill = _weapon_skill(second)
    state = _state(skill, weapon_id, attrs)
    unit = state.units[U1]
    lines = skill.formula_lines_zh(state.ruleset.core, unit.weapon, _getter(state, unit))
    damage_line = next(line for line in lines if "目前" in line)
    assert unit.weapon.scaling_names_zh() in damage_line
    if second is not None:  # 卡片寫出第二屬性與取平均
        assert f"{Attribute(second).display_name}（取平均）" in damage_line
    result = cast(hit_with(state), target_id=U2)
    (dealt,) = [e for e in of(result, DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == _current(damage_line)
    assert skill.scaling_value(_getter(state, unit), unit.weapon) == skill_scaling_value(
        state.ruleset, unit, skill
    )


# ---------------------------------------------------------------------------
# 3I-3b：對抗判定也用平均（實際擲骰＝預覽機率＝卡片）
# ---------------------------------------------------------------------------

CONTEST_TABLE: list[tuple[str, str | None, dict[str, int]]] = [
    ("one_handed_sword", "int", {"str": 12, "int": 30}),  # 平均 21，主屬性只有 12
    ("one_handed_sword", None, {"str": 12, "int": 30}),  # 對照：單屬性不變
    ("arcane_blade", "int", {"str": 12, "int": 20}),
    ("hammer", "wis", {"con": 18, "str": 11, "wis": 6}),
]


@pytest.mark.parametrize(("weapon_id", "second", "attrs"), CONTEST_TABLE)
def test_knock_prone_contest_uses_the_averaged_value(
    weapon_id: str, second: str | None, attrs: dict[str, int]
) -> None:
    skill = _weapon_skill(second, effects=[{"type": "damage"}, {"type": "knock_prone"}])
    state = hit_with(_state(skill, weapon_id, attrs))
    unit, target = state.units[U1], state.units[U2]
    value = skill_scaling_value(state.ruleset, unit, skill)
    attr = skill_scaling_attr(unit, skill)
    expected = state.ruleset.hit_table.modifier(
        value, max(1, effective_attribute(state.ruleset, target, attr))
    )
    (rolled,) = of(cast(state, target_id=U2), ManeuverRolled)
    assert rolled.modifier == expected
    if second is None:  # 單屬性技能的對抗行為不變：就是武器縮放值
        assert value == unit.weapon.scaling_value(_getter(state, unit))


def test_status_save_and_preview_use_the_averaged_value() -> None:
    effects: list[dict[str, Any]] = [{"type": "damage"}, {"type": "apply_status", "status": "slow"}]
    chances = {}
    for second in (None, "int"):
        skill = _weapon_skill(second, effects=effects)
        state = hit_with(_state(skill, "one_handed_sword", {"str": 12, "int": 30}))
        view = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
        chances[second] = view.targets[0].status_chances[0].apply_chance
        save = of(cast(state, target_id=U2), StatusSaveRolled)[0]
        assert save.attack_value == skill_scaling_value(state.ruleset, state.units[U1], skill)
    assert chances["int"] >= chances[None]  # 平均 21 不會比力量 12 更難


def test_contest_label_says_average_only_for_dual_skills() -> None:
    lib = library()
    assert contest_label(_weapon_skill("int"), lib) == "力量／智力（取平均）"
    assert contest_label(_weapon_skill(), lib) == "力量"
    spell = make_skill(SID, {"type": "single", "range": 2}, [{"type": "knock_prone"}])
    assert "取平均" not in contest_label(spell, lib)
