"""物品基礎份額（3K-2c，08 8.22）：同部位底材都拿整池，雙手另加副手池。"""

from __future__ import annotations

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
    for kind in ("robe", "coat", "leather", "mail", "plate"):  # 同等級總預算相同（08 8.12）
        body = _item("body", level, kind=kind)
        assert item_base_points(_RULES, body, weapons) == _POOLS["body"][index]


@pytest.mark.parametrize(
    ("weapon", "expected"),
    [
        ("one_handed_sword", 18),
        ("dagger", 18),
        ("axe", 18),  # 單手：主手池
        ("greatsword", 24),  # 雙手：主手池 18 ＋ 副手池 6（佔掉副手，08 8.11）
        ("dual_dagger", 24),  # 成對：同上
    ],
)
def test_one_handed_get_the_weapon_pool_two_handed_add_the_offhand_pool(
    weapon: str, expected: int
) -> None:
    item = _item("weapon", 1, weapon=weapon)
    assert item_base_points(_RULES, item, _LIB.weapons) == expected


def test_missing_level_uses_fallback_level() -> None:
    sword = _item("weapon", None, weapon="one_handed_sword")
    assert item_base_points(_RULES, sword, _LIB.weapons) == _POOLS["weapon"][0]
