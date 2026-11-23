"""E6-c2 第 3 項：傳說的賣價（08 8.30 第 11 點，平衡待查第 41 條初值：係數 20；仍不能分解）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.equipment import ItemDef
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.crafting_actions import SalvageAction
from trpg.world.economy import gear_price
from trpg.world.economy_actions import ItemSoldEvent, SellAction
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SHOP = "shop_liu"
SMITHY = "smithy_mist_ferry"


def _legendary(library: ContentLibrary, level: int) -> ItemDef:
    assert library.item_gen is not None
    lib = dataclasses.replace(
        library, item_gen=library.item_gen.model_copy(update={"legendary_enabled": True})
    )
    item = generate_item(lib, Rng(3), "neck", "legendary", level)
    assert item.rarity == "legendary" and item.item_level == level
    return item


def test_legendary_sell_coef(library: ContentLibrary) -> None:
    rules = library.world_loot
    assert rules is not None
    assert rules.sell_rarity_coef["legendary"] == 20
    assert rules.sell_price("legendary", 7) == 140
    assert gear_price(library, _legendary(library, 5)) == 100


def test_sell_a_legendary(library: ContentLibrary, make_char: MakeChar) -> None:
    item = _legendary(library, 4)
    char = make_char(gear=(item,))
    result = world_step(library, make_world(), char, SellAction(shop=SHOP, item=item.id), NOON)
    sold = next(e for e in result.events if isinstance(e, ItemSoldEvent))
    assert sold.gold_gained == 4 * 20
    assert result.char.gold == char.gold + 80 and result.char.gear == ()


def test_legendary_still_cannot_be_salvaged(library: ContentLibrary, make_char: MakeChar) -> None:
    """8.14「傳說不能分解」不變（``crafting.yaml`` 的 ``salvage`` 沒有傳說）。"""
    item = _legendary(library, 4)
    char = make_char(gear=(item,))
    with pytest.raises(WorldActionError):
        world_step(library, make_world(), char, SalvageAction(station=SMITHY, item=item.id), NOON)
