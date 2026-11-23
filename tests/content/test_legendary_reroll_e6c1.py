"""E6-c1 第 5 項：傳說的獨特效果不能重抽（08 8.27「可打造不可重抽」）；另外 2 條照一般規則。

配套：縮等級（影子借用）與必帶詞條也不會拿掉獨特效果，計價照 60%。"""

from __future__ import annotations

import pytest

from tests.content.test_legendary_gen_e6c1 import SLOTS, legendary_library
from trpg.content.equipment import ItemDef, item_problems
from trpg.content.item_budget import item_budget_problems, legendary_unique
from trpg.content.item_gen import (
    affix_choices,
    downscale_item,
    generate_item,
    pick_affix,
    replace_affix,
    with_affix,
)
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return legendary_library()


def _items(lib: ContentLibrary, level: int = 10) -> list[ItemDef]:
    return [
        generate_item(lib, Rng(seed), slot, "legendary", level)
        for slot in SLOTS
        for seed in range(4)
    ]


def _problems(lib: ContentLibrary, item: ItemDef) -> list[str]:
    assert lib.item_gen is not None
    return item_problems(
        item, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands
    ) + item_budget_problems(lib.item_gen, item, lib.affixes)


def test_unique_effect_has_no_choices(lib: ContentLibrary) -> None:
    for item in _items(lib):
        last = len(item.affixes) - 1
        assert legendary_unique(lib.affixes[item.affixes[last].affix])
        assert affix_choices(lib, item, last) == []


def test_other_affixes_reroll_normally(lib: ContentLibrary) -> None:
    rerolled = 0
    for i, item in enumerate(_items(lib)):
        for index in range(len(item.affixes) - 1):
            options = affix_choices(lib, item, index)
            assert all(not legendary_unique(a) for a, _ in options)
            if not options:
                continue
            affix, value = pick_affix(lib, item, options, Rng(i))
            new = replace_affix(item, index, affix, value)
            assert _problems(lib, new) == [], (new.affixes, _problems(lib, new))
            assert new.affixes[-1] == item.affixes[-1]
            rerolled += 1
    assert rerolled > 0


def test_downscale_drops_unique_effect_last(lib: ContentLibrary) -> None:
    """比照招牌（E6-a1 `_drop_fixed`）：獨特效果最後才拿；拿掉它時其他固定點數詞條都已經拿完。"""
    kept_unique = 0
    for item in _items(lib):
        unique = item.affixes[-1].affix
        small = downscale_item(lib, item, 1)
        ids = [r.affix for r in small.affixes]
        if unique in ids:
            kept_unique += 1
            continue
        for affix_id in ids:
            affix = lib.affixes[affix_id]
            assert affix.value is not None and affix.value.min != affix.value.max, ids
    assert kept_unique > 0


def test_with_affix_keeps_unique_effect(lib: ContentLibrary) -> None:
    for item in _items(lib):
        new = with_affix(lib, item, "affix_max_hp")
        assert item.affixes[-1].affix in [r.affix for r in new.affixes]
