"""大世界的裝備（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.4）：換上、開戰用穿戴的、回收價、
傭兵的系統裝備、影子的裝備。"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.equipment import ItemDef
from trpg.content.item_budget import affix_points, base_bonus_points, item_budget
from trpg.content.item_gen import downscale_item, generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.battle import prepare_battle
from trpg.world.economy import gear_price
from trpg.world.economy_actions import EquipAction, ItemEquippedEvent, ItemSoldEvent, SellAction
from trpg.world.errors import WorldActionError
from trpg.world.gear import mercenary_equipment, shadow_equipment
from trpg.world.shadows import shadow_snapshot, shadow_spawn
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SHOP = "shop_liu"


def _item(library: ContentLibrary, slot: str, rarity: str = "rare", level: int = 3) -> ItemDef:
    return generate_item(library, Rng(7), slot, rarity, level, weapon_class="focus")  # type: ignore[arg-type]


def _min_points(library: ContentLibrary, affix_id: str) -> Fraction:
    affix = library.affixes[affix_id]
    rules = library.item_gen
    assert rules is not None
    return affix_points(rules, affix, None if affix.value is None else affix.value.min)


def _act(library: ContentLibrary, char: CharacterState, action: object) -> CharacterState:
    return world_step(library, make_world(), char, action, NOON).char  # type: ignore[arg-type]


def test_equip_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    body = _item(library, "body")
    char = make_char(gear=(body,))
    result = world_step(library, make_world(), char, EquipAction(item=body.id), NOON)
    assert result.char.equipment["body"] == body
    assert result.char.gear == ()
    event = next(e for e in result.events if isinstance(e, ItemEquippedEvent))
    assert event.slot == "body" and event.removed == ()
    # 換第二件：第一件回背包
    other = generate_item(library, Rng(8), "body", "uncommon", 2)
    again = _act(
        library, result.char.model_copy(update={"gear": (other,)}), EquipAction(item=other.id)
    )
    assert again.equipment["body"] == other
    assert again.gear == (body,)


def test_equip_only_at_service(library: ContentLibrary, make_char: MakeChar) -> None:
    body = _item(library, "body")
    char = make_char(gear=(body,), location="ferry_steps")
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        world_step(library, make_world(), char, EquipAction(item=body.id), NOON)
    with pytest.raises(WorldActionError, match="沒有這件"):
        world_step(library, make_world(), make_char(), EquipAction(item=body.id), NOON)


def test_main_hand_same_class(library: ContentLibrary, make_char: MakeChar) -> None:
    sword = generate_item(library, Rng(3), "weapon", "rare", 2, weapon_class="melee")
    with pytest.raises(WorldActionError, match="同一大類"):
        _act(library, make_char(gear=(sword,)), EquipAction(item=sword.id))
    staff = _item(library, "weapon")
    char = _act(library, make_char(gear=(staff,)), EquipAction(item=staff.id))
    assert char.equipment["main_hand"] == staff
    assert char.hero.weapon == staff.weapon
    assert [g.id for g in char.gear] == [f"base_{make_char().hero.weapon}"]  # 原本的武器收進背包


def _weapon(library: ContentLibrary, weapon_class: str, *, two_handed: bool) -> ItemDef:
    for s in range(3000):
        item = generate_item(library, Rng(s), "weapon", "common", 2, weapon_class=weapon_class)  # type: ignore[arg-type]
        found = library.weapons.get(item.weapon or "")
        if found is not None and found.two_handed == two_handed and not found.paired:
            return item
    raise AssertionError(weapon_class)


def test_two_handed_needs_room_for_the_offhand(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """5D-R1：已穿副手時換雙手武器，換下主手＋副手兩件、換上一件，背包要多 1 格；滿了就拒絕。"""
    weapon_class = library.weapons[make_char().hero.weapon].weapon_class
    one_handed = _weapon(library, weapon_class, two_handed=False)
    two_handed = _weapon(library, weapon_class, two_handed=True)
    shield = next(
        i
        for s in range(300)
        if (i := generate_item(library, Rng(s), "offhand", "common", 2)).slot_type == "offhand"
    )
    worn = _act(library, make_char(gear=(one_handed,)), EquipAction(item=one_handed.id))
    worn = _act(library, worn.model_copy(update={"gear": (shield,)}), EquipAction(item=shield.id))
    assert worn.equipment["off_hand"] == shield
    rules = library.world_economy.rules
    assert rules is not None
    # 粗料一格 20 個：29 格粗料＋1 件雙手武器＝30 格滿
    full = worn.model_copy(
        update={"gear": (two_handed,), "bag": {"item_coarse_material": 20 * (rules.bag_slots - 1)}}
    )
    with pytest.raises(WorldActionError, match="背包放不下"):
        world_step(library, make_world(), full, EquipAction(item=two_handed.id), NOON)
    # 騰出 1 格就換得上：副手與原本的主手都收進背包，``removed`` 依放進的順序
    roomy = full.model_copy(update={"bag": {"item_coarse_material": 20 * (rules.bag_slots - 2)}})
    result = world_step(library, make_world(), roomy, EquipAction(item=two_handed.id), NOON)
    assert "off_hand" not in result.char.equipment
    assert result.char.equipment["main_hand"] == two_handed
    assert result.char.gear == (shield, one_handed)
    event = next(e for e in result.events if isinstance(e, ItemEquippedEvent))
    assert event.removed == (shield.name_zh, one_handed.name_zh)


def test_battle_uses_worn_gear(library: ContentLibrary, make_char: MakeChar) -> None:
    body = _item(library, "body")
    char = _act(library, make_char(gear=(body,)), EquipAction(item=body.id))
    char = char.model_copy(
        update={"location": "ferry_steps", "pending_encounter": make_encounter("ferry_steps")}
    )
    hero = prepare_battle(library, char).setup.units[0]
    worn = {e.slot: e.item for e in hero.equipment.items}
    assert worn["body"].affixes == body.affixes


def test_sell_gear(library: ContentLibrary, make_char: MakeChar) -> None:
    rare = _item(library, "ring", "rare", 3)
    epic = _item(library, "neck", "epic", 2)
    char = make_char(gear=(rare, epic))
    result = world_step(library, make_world(), char, SellAction(shop=SHOP, item=rare.id), NOON)
    sold = next(e for e in result.events if isinstance(e, ItemSoldEvent))
    assert sold.gold_gained == 3 * 8  # 物品等級 × 稀有 8（20.1）
    assert result.char.gold == 24 and result.char.gear == (epic,)
    after = _act(library, result.char, SellAction(shop=SHOP, item=epic.id))
    assert after.gold == 24 + 2 * 12
    with pytest.raises(WorldActionError, match="一次賣一件"):
        _act(library, make_char(gear=(rare,)), SellAction(shop=SHOP, item=rare.id, count=2))


def test_starting_gear_not_sellable(library: ContentLibrary, make_char: MakeChar) -> None:
    staff = _item(library, "weapon")
    char = _act(library, make_char(gear=(staff,)), EquipAction(item=staff.id))
    assert gear_price(library, char.gear[0]) is None  # 初始武器沒有物品等級：不收（代決 5D2-8）
    legend = _item(library, "ring").model_copy(update={"id": "item_x", "rarity": "legendary"})
    assert gear_price(library, legend) is None
    with pytest.raises(WorldActionError, match="不能賣"):
        _act(library, make_char(gear=(legend,)), SellAction(shop=SHOP, item=legend.id))


def test_mercenary_system_gear(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(
        mercenaries=PARTY,
        location="ferry_steps",
        pending_encounter=make_encounter("ferry_steps"),
    )
    prepared = prepare_battle(library, char)
    merc = prepared.setup.units[1]
    worn = {e.slot: e.item for e in merc.equipment.items}
    assert set(worn) >= {"head", "body", "hands", "feet", "neck", "ring_1", "ring_2"}
    assert all(
        worn[s].rarity == "rare" and worn[s].item_level == char.level for s in ("body", "neck")
    )
    other = make_char(
        "bob",
        mercenaries=PARTY,
        location="ferry_steps",
        pending_encounter=make_encounter("ferry_steps", seed=5),
    )
    again = {e.slot: e.item for e in prepare_battle(library, other).setup.units[1].equipment.items}
    assert again == worn  # 每個人看到的同一名傭兵裝備都一樣（#87）
    base = next(b.hero for b in library.builds.builds if b.id == "build_tank")
    assert mercenary_equipment(library, "merc_tiebi", base, 3)["body"].item_level == 3


def test_shadow_gear_capped(library: ContentLibrary, make_char: MakeChar) -> None:
    low = _item(library, "body", "rare", 2)
    high = _item(library, "neck", "rare", 5)
    char = make_char(equipment={"body": low, "neck": high})
    snapshot = shadow_snapshot(char, NOON)
    assert snapshot.equipment == {"body": low, "neck": high}
    # 5D-2b（#87，玩法 PM 2026-11-03 代決）：超過招募者等級的壓到招募者等級後照穿
    worn = shadow_equipment(library, snapshot.equipment, 3)
    assert set(worn) == {"body", "neck"}
    assert worn["body"] == low  # 沒超過的原樣
    assert worn["neck"].item_level == 3 and worn["neck"].id == high.id
    assert [r.affix for r in worn["neck"].affixes] == [r.affix for r in high.affixes]
    spawn, _ = shadow_spawn(library, snapshot.model_copy(update={"level": 5}), 3)
    assert {e.slot for e in spawn.equipment.items} == {"body", "neck"}


def test_downscale_item_follows_item_level_budget(library: ContentLibrary) -> None:
    """詞條數值照物品等級規則縮（8.22.1）：不超過原本的數值、放進新等級的詞條預算；同等級以下不變。"""
    rules = library.item_gen
    assert rules is not None
    for slot_type in ("weapon", "body", "neck", "ring"):
        for rarity in ("common", "uncommon", "rare", "epic"):
            item = _item(library, slot_type, rarity, 8)
            assert downscale_item(library, item, 8) == item
            assert downscale_item(library, item, 9) == item
            low = downscale_item(library, item, 2)
            assert low.item_level == 2
            assert low.base_bonus_permille <= item.base_bonus_permille
            old_by_id = {r.affix: r for r in item.affixes}
            kept = [r.affix for r in item.affixes if r.affix in {n.affix for n in low.affixes}]
            assert [r.affix for r in low.affixes] == kept  # 只拿掉、不換、不改順序
            for new in low.affixes:
                old = old_by_id[new.affix]
                if old.value is not None and new.value is not None:
                    assert abs(new.value) <= abs(old.value)
            dropped = [r.affix for r in item.affixes if r.affix not in kept]
            assert all(library.affixes[a].value is None or _is_fixed(library, a) for a in dropped)
            budget = item_budget(rules, low, library.affixes)
            assert budget is not None
            floor = base_bonus_points(rules, low.base_bonus_permille) + sum(
                (_min_points(library, r.affix) for r in low.affixes), Fraction(0)
            )
            assert budget.points <= max(Fraction(budget.budget), floor)
            if any(_is_fixed(library, r.affix) for r in low.affixes):
                assert budget.points <= budget.budget  # 還留著固定詞條＝已經放得進


def _is_fixed(library: ContentLibrary, affix_id: str) -> bool:
    affix = library.affixes[affix_id]
    if affix.value is None:
        return True
    rules = library.item_gen
    assert rules is not None
    return affix_points(rules, affix, affix.value.min) == affix_points(
        rules, affix, affix.value.max
    )


def test_downscale_drops_highest_fixed_affix_until_it_fits(library: ContentLibrary) -> None:
    """#87（5D-4 玩法 PM 代決）：縮到下限仍超出新預算 → 從點數最高的固定點數詞條開始拿掉。"""
    rules = library.item_gen
    assert rules is not None
    found = 0
    for seed in range(40):
        item = generate_item(library, Rng(seed), "weapon", "epic", 10, weapon_class="focus")
        low = downscale_item(library, item, 1)
        if len(low.affixes) == len(item.affixes):
            continue
        found += 1
        dropped = [r.affix for r in item.affixes if r.affix not in {n.affix for n in low.affixes}]
        kept_fixed = [r.affix for r in low.affixes if _is_fixed(library, r.affix)]
        top_dropped = min(_min_points(library, a) for a in dropped)
        assert all(_min_points(library, a) <= top_dropped for a in kept_fixed)
        budget = item_budget(rules, low, library.affixes)
        assert budget is not None
        if kept_fixed:
            assert budget.points <= budget.budget
        # 拿掉的都是固定點數詞條（範圍詞條只縮數值）
        assert all(_is_fixed(library, a) for a in dropped)
    assert found > 0
