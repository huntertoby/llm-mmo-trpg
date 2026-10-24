"""Phase 3-55：技能卡寫出具體屬性（使用者：「什麼吃 str 什麼吃魔法」）。

- 武器技的算法句：有持有者寫實際屬性與「目前 +N」，沒有持有者列由武器資料產生的例子；
- 親和效果（若手持某武器時）寫明那把武器看的屬性；
- 「目前 +N」＝實戰（引擎傷害的屬性加成）；
- 法術技寫具體屬性（含組合主題的雙屬性）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from trpg.content.battle import weapon_attr_examples_zh
from trpg.content.skills import ConditionSpec, SkillDef, condition_text
from trpg.engine.events import DamageDealt
from trpg.engine.rules.statuses import effective_attribute
from trpg.narrative.skills import CardOwner, effect_summary, skill_card
from trpg.shared.bonus_text import plain_text
from trpg.shared.types import Attribute

SINGLE = {"type": "single", "range": 1}


def _weapon_skill(
    second: str | None = None, effects: list[dict[str, Any]] | None = None, **over: Any
) -> SkillDef:
    base = make_skill(SID, SINGLE, effects or [{"type": "damage"}], category="weapon", attr="str")
    data = {**base.model_dump(mode="json"), **over}
    if second is not None:
        data["secondary_scaling_attr"] = second
    return SkillDef.model_validate(data)


def test_examples_come_from_weapon_data_and_group_by_attribute() -> None:
    lib = library()
    text = weapon_attr_examples_zh(lib.weapons.values(), "melee", max_groups=99)
    for weapon in lib.weapons.values():
        if weapon.weapon_class == "melee" and not weapon.summon_only:
            assert weapon.scaling_names_zh() in text
    ranged = weapon_attr_examples_zh(lib.weapons.values(), "ranged")
    assert "魔導劍" not in ranged and "敏捷" in ranged


def test_card_without_owner_lists_examples_not_a_generic_phrase() -> None:
    lib = library()
    card = skill_card(lib, _weapon_skill())
    assert card.formula_lines[0].startswith("傷害算法：武器骰＋武器屬性 × 0.3")
    assert "目前" not in card.formula_lines[0]
    assert "武器屬性看手上的武器" in card.formula_lines[1]
    assert "力量" in card.formula_lines[1]
    both = skill_card(lib, _weapon_skill("int"))
    assert "武器屬性與智力（取平均）" in both.formula_lines[0]


@pytest.mark.parametrize(
    ("weapon_id", "second", "expect"),
    [
        ("one_handed_sword", None, "力量"),
        ("dagger", None, "敏捷／力量（取較高）"),
        ("arcane_blade", None, "力量／智力（取平均）"),
        ("one_handed_sword", "int", "力量與智力（取平均）"),
    ],
)
def test_card_with_owner_names_the_real_attributes(
    weapon_id: str, second: str | None, expect: str
) -> None:
    lib = library()
    weapon = lib.weapons[weapon_id]
    card = skill_card(
        lib, _weapon_skill(second), owner=CardOwner(weapon=weapon, attr_get=lambda a: 14)
    )
    (line,) = card.formula_lines
    assert expect in line and "目前 +" in line and "武器屬性" not in line


def _with_wielding(skill: SkillDef, weapon_id: str) -> str:
    spec = skill.effects[0].model_copy(
        update={"condition": ConditionSpec(type="wielding_weapon", weapon=weapon_id)}
    )
    return effect_summary(library(), skill, spec)


def test_affinity_effect_line_names_the_attribute_of_that_weapon() -> None:
    skill = _weapon_skill()
    assert "若手持魔導劍時，這把武器吃力量／智力（取平均）" in _with_wielding(skill, "arcane_blade")
    assert "這把武器吃敏捷／感知（取平均）" in _with_wielding(skill, "whip")
    both = _with_wielding(_weapon_skill("wil"), "arcane_blade")
    assert "力量／智力（取平均）與意志（取平均）" in both


def test_wielding_condition_without_a_weapon_never_shows_the_code() -> None:
    assert "wielding_weapon" not in condition_text(ConditionSpec(type="wielding_weapon"))


@pytest.mark.parametrize(
    ("weapon_id", "second", "attrs"),
    [
        ("one_handed_sword", None, {"str": 15}),
        ("dagger", None, {"str": 9, "dex": 17}),
        ("arcane_blade", "wil", {"str": 12, "int": 21, "wil": 8}),
        ("whip", None, {"dex": 14, "wis": 20}),
    ],
)
def test_card_current_bonus_equals_combat(
    weapon_id: str, second: str | None, attrs: dict[str, int]
) -> None:
    """卡片（含主角的屬性）寫的「目前 +N」＝實戰傷害事件的屬性加成。"""
    skill = _weapon_skill(second)
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    unit = state.units[U1]
    unit.weapon = library().weapons[weapon_id]
    for name, value in attrs.items():
        unit.attributes[Attribute(name)] = value
    card = skill_card(
        library(),
        skill,
        owner=CardOwner(
            weapon=unit.weapon, attr_get=lambda a: effective_attribute(state.ruleset, unit, a)
        ),
    )
    line = plain_text(card.formula_lines[0])
    shown = int(line.split("目前 +")[1].split("）")[0].split("｜")[0])
    result = cast(hit_with(state), target_id=U2)
    (dealt,) = [e for e in of(result, DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == shown


def test_contest_text_follows_the_owner_weapon() -> None:
    """擊倒的對抗屬性：有持有者寫那把武器實際的屬性（和引擎 ``contest_attr`` 同一個來源）。"""
    lib = library()
    skill = _weapon_skill(effects=[{"type": "damage"}, {"type": "knock_prone"}])
    dagger = lib.weapons["dagger"]
    plain = skill_card(lib, skill)
    held = skill_card(lib, skill, owner=CardOwner(weapon=dagger, attr_get=lambda a: 10))
    assert "擊倒（力量對抗）" in plain.effects[1]
    assert "擊倒（敏捷／力量（取較高）對抗）" in held.effects[1]
    both = skill_card(
        lib, _weapon_skill("int", effects=[{"type": "knock_prone"}]), owner=CardOwner(weapon=dagger)
    )
    assert both.effects[0].count("取平均") == 1


SPELLS = [
    s.id
    for s in sorted(library().skills.values(), key=lambda s: s.id)
    if s.category == "spell" and any(e.type == "damage" for e in s.effects)
]


@pytest.mark.parametrize("skill_id", SPELLS[::5])
def test_spell_cards_name_their_attribute(skill_id: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    line = skill_card(lib, skill).formula_lines[0]
    assert skill.scaling_attr.display_name in line
    if skill.secondary_scaling_attr is not None:
        assert f"{skill.secondary_scaling_attr.display_name}（取平均）" in line
