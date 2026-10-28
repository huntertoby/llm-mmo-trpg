"""Phase 3K-1：武器元素詞條接上 3I-6 的元素優先順序（08 8.21.2.4 #52、06 6.10 補充二 A′）。

表格測試（``test_attack_element.py``）只驗純函式；這裡驗「裝上詞條後實戰元素正確」：卡片（傷害參數、
有效元素）與實際結算的 ``DamageDealt`` 一致，法杖本身的元素不被覆寫，普通物品的基礎加成也真的生效。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.test_gear import _item
from trpg.content.equipment import ItemDef, Loadout, loadout_problems
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import Attack, BattleState, UseSkill, resolve, start_battle
from trpg.engine import modifiers as mods
from trpg.engine.attack_element import (
    attack_element_sources,
    effective_attack_element,
    weapon_affix_element,
)
from trpg.engine.events import DamageDealt
from trpg.engine.gear import build_gear, gear_defense_permille
from trpg.engine.gear_summon import inherit_attack_gear
from trpg.engine.gear_view import gear_totals
from trpg.engine.setup import UnitSpawn
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.targeting import damage_parameters
from trpg.engine.state import StatusInstance
from trpg.shared.types import Element, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
type Rolls = Sequence[tuple[str, int | None]]


def _hero(slots: Mapping[str, Rolls], *, weapon: str = "one_handed_sword") -> UnitSpawn:
    s = spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter", skills=("skill_cleave",)), weapon)
    order = list(SLOT_TYPE_OF)
    items = tuple(
        _item(slot, slots[slot], weapon=weapon if slot == "main_hand" else None)
        for slot in sorted(slots, key=order.index)
    )
    return s.model_copy(update={"equipment": Loadout(items=items)})


def _state(hero: UnitSpawn) -> BattleState:
    m = make_map("00", ally=[(0, 0)], enemy=[(1, 0)])
    foe = spawn(Team.ENEMY, (1, 0), no_reactions("bandit", max_hp=200))
    return give_turn(start_battle(make_setup(m, [hero, foe]), 0), U1)


def _attack_element(state: BattleState) -> Element:
    result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    dealt = [e for e in result.events if isinstance(e, DamageDealt) and e.cause == "attack"]
    assert dealt
    return dealt[0].element


def _skill_element(state: BattleState) -> Element:
    cleave = library().skills["skill_cleave"]
    card = damage_parameters(state, state.units[U1], cleave, cleave.effects[0]).element
    cast = resolve(
        with_rolls(state, [(20, 15), (8, 4), (8, 4)]),
        UseSkill(unit_id=U1, skill_id="skill_cleave", direction="east"),
    )
    dealt = [e for e in cast.events if isinstance(e, DamageDealt)]
    assert dealt
    assert all(e.element is card for e in dealt)  # 卡片與實戰一致
    return card


@pytest.mark.parametrize(
    "element",
    [Element.FIRE, Element.ICE, Element.LIGHTNING, Element.POISON, Element.HOLY, Element.SHADOW],
)
def test_weapon_element_changes_basic_attack_and_weapon_skill(element: Element) -> None:
    state = _state(_hero({"main_hand": [(f"affix_weapon_{element.value}", None)]}))
    unit = state.units[U1]
    assert weapon_affix_element(unit) is element
    assert attack_element_sources(state.ruleset, unit).weapon_affix is element
    assert _attack_element(state) is element
    fresh = _state(_hero({"main_hand": [(f"affix_weapon_{element.value}", None)]}))
    assert _skill_element(fresh) is element


def test_without_the_affix_the_attack_stays_physical() -> None:
    state = _state(_hero({"main_hand": [("affix_attr_str", 1)]}))
    assert weapon_affix_element(state.units[U1]) is None
    assert _attack_element(state) is Element.PHYSICAL


def test_basic_attack_affix_beats_weapon_element_only_on_basic_attacks() -> None:
    rolls: Rolls = [("affix_attack_holy", None), ("affix_weapon_fire", None)]
    assert _attack_element(_state(_hero({"main_hand": rolls}))) is Element.HOLY
    assert _skill_element(_state(_hero({"main_hand": rolls}))) is Element.FIRE


def test_enchant_beats_weapon_element() -> None:
    state = _state(_hero({"main_hand": [("affix_weapon_fire", None)]}))
    state.units[U1].statuses.append(StatusInstance("infused_holy", 3))
    assert _attack_element(state) is Element.HOLY


def test_weapon_element_off_the_main_hand_is_ignored() -> None:
    """武器元素詞條只看主手（資料上只能掛主手；這裡硬塞到戒指，確認引擎也只讀主手）。"""
    hero = _hero({"ring_1": [("affix_weapon_fire", None)]})
    state = _state(_hero({}))
    state.units[U1].gear = build_gear(hero.equipment, library().ruleset.equipment)
    assert weapon_affix_element(state.units[U1]) is None
    assert _attack_element(state) is Element.PHYSICAL


def test_staff_element_is_not_overwritten_by_the_weapon_element_affix() -> None:
    """法杖不能掛（穿戴驗證擋住）；就算硬塞進去，法杖本身的元素也只有附魔能覆寫（06 6.10 A′）。"""
    hero = _hero({"main_hand": [("affix_weapon_ice", None)]}, weapon="fire_staff")
    problems = loadout_problems(hero.equipment, hero.weapon, library().ruleset.equipment)
    assert any("不能掛武器元素詞條" in p for p in problems)
    state = _state(spawn(Team.ALLY, (0, 0), no_reactions("hero_mage"), "fire_staff"))
    unit = state.units[U1]
    unit.gear = build_gear(hero.equipment, library().ruleset.equipment)
    assert weapon_affix_element(unit) is Element.ICE
    assert effective_attack_element(state.ruleset, unit, is_basic=True) is Element.FIRE
    assert _attack_element(state) is Element.FIRE


def test_a_summon_does_not_inherit_the_weapon_element() -> None:
    hero = _hero(
        {"main_hand": [("affix_weapon_fire", None), ("affix_summon_inherit_attack", None)]}
    )
    state = _state(hero)
    inherited = inherit_attack_gear(state.units[U1], state.units[U2].gear)
    assert all(a.affix.id != "affix_weapon_fire" for a in inherited.affixes)


def test_two_weapon_element_affixes_on_one_item_are_rejected() -> None:
    hero = _hero({"main_hand": [("affix_weapon_fire", None), ("affix_weapon_ice", None)]})
    problems = loadout_problems(hero.equipment, hero.weapon, library().ruleset.equipment)
    assert any("武器元素詞條同一件最多 1 條" in p for p in problems)


# ---------------------------------------------------------------------------
# 普通物品的基礎加成（08 8.22.1 第 5 點）：武器傷害、防具防禦，真的生效
# ---------------------------------------------------------------------------


def _with_base(hero: UnitSpawn, slot: str, permille: int) -> UnitSpawn:
    items = []
    for entry in hero.equipment.items:
        item: ItemDef = entry.item
        if entry.slot == slot:
            item = item.model_copy(update={"base_bonus_permille": permille, "affixes": ()})
            items.append(entry.model_copy(update={"item": item, "affixes": ()}))
        else:
            items.append(entry)
    return hero.model_copy(update={"equipment": Loadout(items=tuple(items))})


def test_common_base_bonus_adds_weapon_damage_and_armor_defense() -> None:
    hero = _hero({"main_hand": [], "body": []})
    hero = _with_base(_with_base(hero, "main_hand", 60), "body", 40)
    state = _state(hero)
    unit, foe = state.units[U1], state.units[U2]
    assert mods.damage_permille(state, unit, mods.ATTACK, Subject(foe, foe.xy)) == 1060
    assert gear_defense_permille(unit) == 40
    lines = gear_totals(unit, damage_cap=500, move_cap=2)
    assert any(s.endswith("：基礎加成") for line in lines for s in line.sources_zh)
