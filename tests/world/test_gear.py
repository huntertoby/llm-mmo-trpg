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
            for old, new in zip(item.affixes, low.affixes, strict=True):
                assert old.affix == new.affix
                if old.value is not None and new.value is not None:
                    assert abs(new.value) <= abs(old.value)
            budget = item_budget(rules, low, library.affixes)
            assert budget is not None
            floor = base_bonus_points(rules, low.base_bonus_permille) + sum(
                (_min_points(library, r.affix) for r in low.affixes), Fraction(0)
            )
            assert budget.points <= max(Fraction(budget.budget), floor)
