"""E6-a2：招牌物品的 70% 下限改成「放得下就放」（08 8.30 第 2 點的解讀，玩法 PM 定）。

- 招牌以外的部分放得下就放，不要求湊到 70%；一條都放不下時，整件只有招牌。
- 預算檢查對招牌物品不再檢查下限（上限照舊是整件的 100%）。

用 E6-a1 的測試內容庫（標了招牌、開關打開）。現有詞條的點數大多能湊到 70%，所以把下限調成 100%，
讓「放得下但湊不到下限」的情況一定出現。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.content.test_signature_gen_e6a1 import SLOTS, TERRAIN, signature_library
from trpg.content.equipment import AffixRoll, ItemDef, item_problems
from trpg.content.item_budget import (
    affix_budget,
    affix_points,
    item_budget_problems,
    signature_points,
)
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng


@pytest.fixture(scope="module")
def strict() -> ContentLibrary:
    """下限 100%：只有剛好填滿才「湊得到」。"""
    return signature_library(min_fill_permille=1000)


def _rest(lib: ContentLibrary, item: ItemDef) -> tuple[Fraction, Fraction]:
    """（招牌以外的點數, 剩下的預算）。"""
    rules = lib.item_gen
    assert rules is not None and item.item_level is not None
    budget = affix_budget(rules, item.item_level, item.slot_type)
    rest = sum(
        (
            affix_points(rules, lib.affixes[r.affix], r.value, budget=budget)
            for r in item.affixes
            if lib.affixes[r.affix].signature is None
        ),
        Fraction(0),
    )
    return rest, budget - signature_points(rules, budget)


def _problems(lib: ContentLibrary, item: ItemDef) -> list[str]:
    rules = lib.item_gen
    assert rules is not None
    return item_problems(
        item, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands
    ) + item_budget_problems(rules, item, lib.affixes)


def test_fits_are_kept_even_below_the_floor(strict: ContentLibrary) -> None:
    """湊不到下限（這裡是 100%）時，放得下的照樣放進去，物品照樣通過檢查。"""
    under = 0
    for slot in SLOTS:
        for level in range(1, 11):
            for seed in range(4):
                item = generate_item(strict, Rng(seed), slot, "rare", level)
                assert _problems(strict, item) == [], (slot, level, seed)
                rest, room = _rest(strict, item)
                assert rest <= room
                if 0 < rest < room:
                    under += 1
                    assert len(item.affixes) >= 2  # 招牌＋放得下的詞條
    assert under >= 20


def test_signature_alone_only_when_nothing_fits(strict: ContentLibrary) -> None:
    """一條都放不下時才只有招牌：1～4 級稀有靴子剩 1.6～2.8 點，腳的候選最便宜要 3 點。"""
    rules = strict.item_gen
    assert rules is not None
    for level in range(1, 5):
        for seed in range(6):
            item = generate_item(strict, Rng(seed), "feet", "rare", level)
            assert [r.affix for r in item.affixes] == [TERRAIN], (level, seed)
    # 5 級：剩 3.2 點，放得下 3 點的詞條（只有 3.2 的 94%，照樣放）
    for seed in range(6):
        item = generate_item(strict, Rng(seed), "feet", "rare", 5)
        rest, room = _rest(strict, item)
        assert room == Fraction(16, 5)
        assert 0 < rest < room
        assert item.affixes[-1].affix == TERRAIN


def test_budget_check_has_no_floor_for_signature_items() -> None:
    """預算檢查：招牌物品不檢查下限，只檢查不超過整件預算。"""
    lib = signature_library()
    rules = lib.item_gen
    assert rules is not None
    budget = affix_budget(rules, 5, "weapon")  # 24：招牌 14.4、剩 9.6、70% 是 6.72
    base = generate_item(lib, Rng(0), "weapon", "rare", 5)
    sig = next(r for r in base.affixes if lib.affixes[r.affix].signature is not None)

    def with_str(value: int) -> ItemDef:
        stat = AffixRoll(affix="affix_attr_str", value=value)
        return base.model_copy(update={"affixes": (stat, sig)})

    points = affix_points(rules, lib.affixes["affix_attr_str"], 20, budget=budget)
    assert points * 1000 < (budget - signature_points(rules, budget)) * rules.min_fill_permille
    assert item_budget_problems(rules, with_str(20), lib.affixes) == []  # 6 點 < 6.72，照樣通過
    over = item_budget_problems(rules, with_str(40), lib.affixes)  # 14.4 ＋ 12 > 24
    assert any("超過預算" in p for p in over)
