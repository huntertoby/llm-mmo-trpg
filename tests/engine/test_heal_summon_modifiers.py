"""兩種新修正（Phase 3-24b1，``docs/design/08-裝備.md`` 8.21.4.2）：治療量與召喚物數值。

- ``heal_permille``：你的治療量 ±‰（技能的治療與聖光雙效的治療）。
- ``summon_hp_permille``／``summon_attack_dice``：你召喚的召喚物最大 HP +‰、攻擊傷害骰 +1 顆。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from trpg.content.skills import ModifierChange, SkillDef
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.events import Healed, UnitSummoned
from trpg.shared.types import Pos, Team, UnitId

HEAL = "skill_t_heal"
SUMMON = "skill_t_summon"
HERO = (3, 3)
ALLY = (4, 3)


def modifier(skill_id: str, change: dict[str, Any], applies_to: dict[str, Any]) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": "修正",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": [{"applies_to": applies_to, "change": change}],
        }
    )


def heal_arena(
    effects: list[dict[str, Any]],
    mods: list[SkillDef],
    *,
    shape: dict[str, Any] | None = None,
    tags: tuple[str, ...] = (),
) -> BattleState:
    """U1（施放者）與受傷的友方 U2（HP 5/200）。"""
    skill = make_skill(HEAL, shape or {"type": "single", "range": 3}, effects)
    skill = skill.model_copy(update={"tags": tags})
    m = make_map(FLAT7, ally=[HERO, ALLY], enemy=[(6, 6)])
    spawns = [
        spawn(Team.ALLY, HERO, caster_template([skill, *mods], base="hero_mage")),
        spawn(Team.ALLY, ALLY, no_reactions("hero_archer", max_hp=200)),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=999)),
    ]
    state = make_state(m, spawns, skills=[skill, *mods])
    state = give_turn(state, U1)
    state.units[U2].hp = 5
    return state


def healed_amount(state: BattleState) -> int:
    result = resolve(state, UseSkill(unit_id=U1, skill_id=HEAL, target_id=U2))
    [event] = [e for e in of(result, Healed) if e.target_id == U2]
    return event.amount


PLAIN_HEAL = [{"type": "heal", "dice": "3d6", "affects": "allies"}]


def mod(change: dict[str, Any], **applies: Any) -> SkillDef:
    return modifier("skill_t_mod_a", change, applies or {"all_skills": True})


# ---------------------------------------------------------------------------
# 治療量
# ---------------------------------------------------------------------------


def test_heal_permille_scales_a_skill_heal_and_leaves_the_roll_alone() -> None:
    base = healed_amount(heal_arena(PLAIN_HEAL, []))
    doubled = healed_amount(heal_arena(PLAIN_HEAL, [mod({"heal_permille": 1000})]))
    halved = healed_amount(heal_arena(PLAIN_HEAL, [mod({"heal_permille": -500})]))
    boosted = healed_amount(heal_arena(PLAIN_HEAL, [mod({"heal_permille": 150})]))
    assert base > 0  # 同一個種子：骰值相同，只有倍率不同
    assert doubled in (2 * base, 2 * base + 1)
    assert halved in (base // 2, base // 2 + 1)
    assert base < boosted <= base * 115 // 100 + 1


def test_heal_permille_rules_add_up() -> None:
    base = healed_amount(heal_arena(PLAIN_HEAL, []))
    two = healed_amount(
        heal_arena(
            PLAIN_HEAL,
            [
                mod({"heal_permille": 500}),
                modifier("skill_t_mod_b", {"heal_permille": 500}, {"all_skills": True}),
            ],
        )
    )
    assert two in (2 * base, 2 * base + 1)


def test_heal_permille_only_applies_to_matching_skills() -> None:
    base = healed_amount(heal_arena(PLAIN_HEAL, []))
    fire = mod({"heal_permille": 1000}, skill_tags=["fire"])
    assert healed_amount(heal_arena(PLAIN_HEAL, [fire])) == base  # 測試技能沒有 fire 標籤
    healer = mod({"heal_permille": 1000}, skill_tags=["heal"])
    tagged = healed_amount(heal_arena(PLAIN_HEAL, [healer], tags=("heal",)))
    assert tagged in (2 * base, 2 * base + 1)


def test_heal_permille_also_scales_the_split_heal_of_a_holy_burst() -> None:
    split = [
        {
            "type": "damage",
            "dice": "3d6",
            "element": "holy",
            "affects": "all",
            "split_heal": True,
        }
    ]
    shape = {"type": "ring", "radius": 1}
    plain = heal_arena(split, [], shape=shape)
    boosted = heal_arena(split, [mod({"heal_permille": 1000})], shape=shape)
    results = []
    for state in (plain, boosted):
        result = resolve(state, UseSkill(unit_id=U1, skill_id=HEAL))
        results.append(sum(e.amount for e in of(result, Healed) if e.target_id == U2))
    assert results[0] > 0 and results[1] in (2 * results[0], 2 * results[0] + 1)


def test_heal_permille_never_goes_below_zero_and_validates_its_range() -> None:
    with pytest.raises(ValidationError):
        ModifierChange.model_validate({"heal_permille": 0})
    with pytest.raises(ValidationError):
        ModifierChange.model_validate({"heal_permille": -501})
    assert ModifierChange.model_validate({"heal_permille": -500}).kind == "heal_permille"


# ---------------------------------------------------------------------------
# 召喚物數值
# ---------------------------------------------------------------------------


def summon_arena(mods: list[SkillDef], *, tags: tuple[str, ...] = ()) -> BattleState:
    skill = make_skill(
        SUMMON,
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": "summon_skeleton_warrior", "duration": 2}],
    ).model_copy(update={"tags": tags})
    m = make_map(FLAT7, ally=[(0, 3)], enemy=[(6, 6)])
    spawns = [
        spawn(Team.ALLY, (0, 3), caster_template([skill, *mods])),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=200)),
    ]
    return give_turn(make_state(m, spawns, skills=[skill, *mods]), U1)


def summoned(state: BattleState) -> Any:
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SUMMON, target_pos=Pos(x=2, y=3)))
    [event] = of(result, UnitSummoned)
    return result.state.units[UnitId(event.unit_id)]


def test_summon_hp_permille_raises_the_summons_max_hp_and_fills_it() -> None:
    base = summoned(summon_arena([]))
    boosted = summoned(summon_arena([mod({"summon_hp_permille": 200})]))
    assert base.max_hp == 20 and base.hp == 20
    assert boosted.max_hp == 24 and boosted.hp == 24  # +20%


def test_summon_hp_permille_rules_add_up() -> None:
    both = summoned(
        summon_arena(
            [
                mod({"summon_hp_permille": 200}),
                modifier("skill_t_mod_b", {"summon_hp_permille": 300}, {"all_skills": True}),
            ]
        )
    )
    assert both.max_hp == 30  # +50%


def test_summon_attack_dice_adds_one_die_to_the_summons_weapon_only() -> None:
    plain = summoned(summon_arena([]))
    boosted = summoned(summon_arena([mod({"summon_attack_dice": 1})]))
    assert plain.weapon.dice.count == 1 and boosted.weapon.dice.count == 2
    assert boosted.weapon.dice.sides == plain.weapon.dice.sides
    assert boosted.weapon.id == plain.weapon.id  # 武器資料表本身沒有被改


def test_summon_modifiers_follow_their_applies_to() -> None:
    other = summoned(summon_arena([mod({"summon_hp_permille": 500}, skill_tags=["fire"])]))
    assert other.max_hp == 20
    tagged = summoned(
        summon_arena([mod({"summon_hp_permille": 500}, skill_tags=["summon"])], tags=("summon",))
    )
    assert tagged.max_hp == 30


def test_summon_modifiers_validate_their_range() -> None:
    for bad in ({"summon_hp_permille": 0}, {"summon_hp_permille": 1001}, {"summon_attack_dice": 2}):
        with pytest.raises(ValidationError):
            ModifierChange.model_validate(bad)
