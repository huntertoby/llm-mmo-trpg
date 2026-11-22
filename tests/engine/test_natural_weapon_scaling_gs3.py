"""GS-3（#173，06 6.30 野性連擊）：縮放屬性的「天生武器」選項
（``scaling_source: natural_weapon``）。

- 命中與傷害（含對抗）都用目前形態天生武器的屬性；天生武器有兩個屬性時照 08 8.11 取較高；
- 只有技能條件是「在形態中」、不是武器技的技能可以用。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import UseSkill, resolve
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.engine.skills.scaling import skill_scaling_attr, skill_scaling_value
from trpg.engine.state import BattleState
from trpg.shared.types import Attribute, Team

SID = "skill_t_natural"


def natural_skill(**overrides: Any) -> SkillDef:
    data: dict[str, Any] = {
        "id": SID,
        "name_zh": "測試天生武器",
        "tier": 3,
        "rarity": "rare",
        "skeleton": "strike",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": 1,
        "scaling_attr": "str",
        "scaling_source": "natural_weapon",
        "shape": {"type": "single", "range": 1},
        "effects": [{"type": "damage", "dice": "1d4", "element": "physical"}],
        "condition": {"type": "in_form"},
        "cost": {"mana": 0},
    }
    data.update(overrides)
    return SkillDef.model_validate(data)


def _set(state: BattleState, **values: int) -> None:
    attrs = state.units[U1].attributes
    for key in list(attrs):
        name = str(getattr(key, "value", key))
        if name in values:
            attrs[key] = values[name]


def scene(skill: SkillDef, form: str | None, **attrs: int) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    forms = ["skill_form_bear", "skill_form_cat"]
    owner = caster_template([skill, *forms], base="hero_fighter", stamina=400)
    spawns = [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=9990))]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    unit = state.units[U1]
    unit.ap, unit.stamina, unit.mana = 8, 400, 400
    _set(state, **attrs)
    if form is not None:
        state = resolve(state, UseSkill(unit_id=U1, skill_id=f"skill_form_{form}")).state
        state.units[U1].ap = 8
    return state


def test_a_bear_uses_the_higher_of_strength_and_constitution() -> None:
    skill = natural_skill()
    rules = library().ruleset
    low_str = scene(skill, "bear", str=20, con=90, dex=10)
    assert skill_scaling_value(rules, low_str.units[U1], skill) == 90  # 熊爪：力量／體質取較高
    assert skill_scaling_attr(low_str.units[U1], skill) == Attribute.STR  # 對抗看天生武器的主屬性
    high_str = scene(skill, "bear", str=80, con=30, dex=10)
    assert skill_scaling_value(rules, high_str.units[U1], skill) == 80


def test_a_cat_uses_dexterity_even_though_the_skill_says_strength() -> None:
    skill = natural_skill()
    state = scene(skill, "cat", str=90, con=90, dex=40)
    assert skill_scaling_value(library().ruleset, state.units[U1], skill) == 40
    assert skill_scaling_attr(state.units[U1], skill) == Attribute.DEX


def test_hit_and_damage_both_use_the_natural_weapon(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    plain = natural_skill(scaling_source=None)
    results = {}
    for name, skill in (("natural", natural_skill()), ("plain", plain)):
        state = scene(skill, "cat", str=20, con=20, dex=90)
        results[name] = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    rolled = {k: of(r, AttackRolled)[0].attack_value for k, r in results.items()}
    dealt = {k: of(r, DamageDealt)[0].amount for k, r in results.items()}
    assert rolled["natural"] - rolled["plain"] == 90 - 20  # 命中：敏捷 90 取代力量 20
    assert dealt["natural"] > dealt["plain"]  # 傷害的屬性加成也換成敏捷


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"condition": None}, "在形態中"),
        ({"condition": {"type": "wielding_weapon", "weapon": "sword"}}, "在形態中"),
        ({"secondary_scaling_attr": "con"}, "secondary_scaling_attr"),
        (
            {"category": "weapon", "weapon_req": "melee", "effects": [{"type": "damage"}]},
            "武器技",
        ),
    ],
)
def test_only_in_form_non_weapon_skills_can_use_the_natural_weapon(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        natural_skill(**overrides)


def test_omitting_the_option_keeps_the_serialized_skill_unchanged() -> None:
    assert "scaling_source" not in natural_skill(scaling_source=None).model_dump()
