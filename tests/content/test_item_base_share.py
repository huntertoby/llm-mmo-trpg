"""物品基礎份額（Phase 3K-2c，08 8.22 的「基礎：詞條」比例）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from trpg.content.equipment import ItemDef
from trpg.content.item_budget import (
    ItemGenRules,
    affix_budget,
    base_pool,
    item_base_points,
    slot_budget,
)
from trpg.content.library import load_library
from trpg.content.slots import SLOT_TYPES, SlotType

_LIB = load_library()
_RULES: ItemGenRules = _LIB.item_gen  # type: ignore[assignment]

# 等級 1／5／10 的基礎份額池（全身預算 100／200／350 × 部位比例 × 基礎比例）
_POOLS: dict[SlotType, tuple[int, int, int]] = {
    "weapon": (18, 36, 63),
    "body": (12, 24, 42),
    "offhand": (6, 12, 21),
    "head": (4, 8, 14),
    "hands": (4, 8, 14),
    "feet": (4, 8, 14),
    "neck": (0, 0, 0),
    "ring": (0, 0, 0),
}
_LEVELS = [(0, 1), (1, 5), (2, 10)]


@pytest.mark.parametrize("slot", SLOT_TYPES)
@pytest.mark.parametrize(("index", "level"), _LEVELS)
def test_base_pool_table(slot: SlotType, index: int, level: int) -> None:
    assert base_pool(_RULES, level, slot) == _POOLS[slot][index]
    total = affix_budget(_RULES, level, slot) + base_pool(_RULES, level, slot)
    assert total == slot_budget(_RULES, level, slot)


def _item(slot: SlotType, level: int | None, **extra: object) -> ItemDef:
    base: dict[str, object] = {
        "id": f"t_{slot}",
        "name_zh": "測試",
        "slot_type": slot,
        "item_level": level,
        "rarity": "common",
    }
    return ItemDef.model_validate(base | extra)


@pytest.mark.parametrize(("index", "level"), _LEVELS)
def test_item_base_share_by_slot(index: int, level: int) -> None:
    weapons = _LIB.weapons
    sword = _item("weapon", level, weapon="one_handed_sword")
    assert item_base_points(_RULES, sword, weapons) == _POOLS["weapon"][index]
    flat_slots: tuple[SlotType, ...] = ("offhand", "head", "hands", "feet")
    for slot in flat_slots:
        assert item_base_points(_RULES, _item(slot, level), weapons) == _POOLS[slot][index]
    empty_slots: tuple[SlotType, ...] = ("neck", "ring")
    for slot in empty_slots:
        assert item_base_points(_RULES, _item(slot, level), weapons) == 0
    for kind, defense in (("robe", 1), ("coat", 2), ("leather", 3), ("mail", 5), ("plate", 7)):
        body = _item("body", level, kind=kind)
        expected = Fraction(_POOLS["body"][index] * defense, 3)
        assert item_base_points(_RULES, body, weapons) == expected


def test_weapon_share_follows_dice_average_times_strikes() -> None:
    weapons = _LIB.weapons
    ref = Fraction(9, 2)  # 1d8 平均
    dagger = _item("weapon", 1, weapon="dagger")  # 1d4：2.5
    assert item_base_points(_RULES, dagger, weapons) == 18 * Fraction(5, 2) / ref
    great = _item("weapon", 1, weapon="greatsword")  # 2d6：7
    assert item_base_points(_RULES, great, weapons) == 18 * Fraction(7) / ref
    dual = weapons["dual_dagger"]
    assert dual.strikes == 2 and dual.dice.sides == 4 and dual.dice.count == 1
    pair = _item("weapon", 1, weapon="dual_dagger")  # 兩次打擊：2 × 2.5
    assert item_base_points(_RULES, pair, weapons) == 18 * Fraction(5) / ref


def test_missing_level_uses_fallback_level() -> None:
    sword = _item("weapon", None, weapon="one_handed_sword")
    assert item_base_points(_RULES, sword, _LIB.weapons) == _POOLS["weapon"][0]
