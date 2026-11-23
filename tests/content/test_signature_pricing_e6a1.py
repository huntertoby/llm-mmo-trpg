"""E6-a1：招牌詞條 60% 定價與 70% 下限（08 8.27、8.30 第 2、11 點，8.22.1 第 6 點）。"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

from tests.engine.helpers import library
from trpg.content.equipment import ItemDef
from trpg.content.item_budget import (
    ItemGenRules,
    affix_budget,
    affix_points,
    item_budget_problems,
    item_points,
    signature_points,
)
from trpg.content.library import ContentLibrary

SIG = "affix_act_grapple"


def tagged_library() -> ContentLibrary:
    """把 ``affix_act_grapple`` 標成新動作招牌的內容庫（現有內容沒有標招牌的詞條）。"""
    lib = library()
    affix = lib.affixes[SIG].model_copy(update={"signature": "action"})
    return dataclasses.replace(lib, affixes={**lib.affixes, SIG: affix})


def _rules(lib: ContentLibrary) -> ItemGenRules:
    assert lib.item_gen is not None
    return lib.item_gen


def _item(rolls: list[tuple[str, int | None]], level: int = 5) -> ItemDef:
    return ItemDef.model_validate(
        {
            "id": "item_t_sig",
            "name_zh": "測試",
            "slot_type": "weapon",
            "weapon": "one_handed_sword",
            "rarity": "rare",
            "item_level": level,
            "affixes": [{"affix": a, "value": v} for a, v in rolls],
        }
    )


def _fill(problems: list[str]) -> list[str]:
    return [p for p in problems if "預算" in p]


def test_signature_permille_is_600() -> None:
    assert _rules(library()).signature_permille == 600


def test_signature_points_are_60_percent_without_rounding() -> None:
    lib = tagged_library()
    rules = _rules(lib)
    budget = affix_budget(rules, 1, "weapon")
    assert budget == 12
    assert signature_points(rules, budget) == Fraction(36, 5)  # 7.2，不捨去
    affix = lib.affixes[SIG]
    assert affix_points(rules, affix, None, budget=budget) == Fraction(36, 5)
    for level in range(1, 11):
        b = affix_budget(rules, level, "weapon")
        assert affix_points(rules, affix, None, budget=b) == Fraction(b * 600, 1000)


def test_signature_without_item_budget_keeps_category_points() -> None:
    lib = tagged_library()
    rules = _rules(lib)
    assert affix_points(rules, lib.affixes[SIG], None) == rules.category_points["action"]


def test_item_points_price_the_signature_by_the_item_budget() -> None:
    lib = tagged_library()
    rules = _rules(lib)
    item = _item([("affix_attr_str", 30), (SIG, None)])
    assert item_points(rules, item, lib.affixes) == Fraction(72, 5) + 9  # 24 × 60% ＋ 力量 30


def test_lower_bound_only_counts_the_rest() -> None:
    lib = tagged_library()
    rules = _rules(lib)
    # 5 級主手：預算 24、招牌 14.4、剩 9.6、下限 6.72
    ok = _item([("affix_attr_str", 30), (SIG, None)])  # 9 ≥ 6.72
    assert _fill(item_budget_problems(rules, ok, lib.affixes)) == []
    low = _item([("affix_attr_str", 20), (SIG, None)])  # 6 < 6.72
    assert any("招牌以外" in p for p in item_budget_problems(rules, low, lib.affixes))
    over = _item([("affix_attr_str", 40), (SIG, None)])  # 14.4 ＋ 12 > 24
    assert any("超過預算" in p for p in item_budget_problems(rules, over, lib.affixes))


def test_signature_alone_passes_the_lower_bound() -> None:
    lib = tagged_library()
    rules = _rules(lib)
    for level in (1, 5, 10):
        alone = _item([(SIG, None)], level=level)
        assert _fill(item_budget_problems(rules, alone, lib.affixes)) == []


def test_untagged_library_prices_unchanged() -> None:
    lib = library()
    rules = _rules(lib)
    item = _item([("affix_attr_str", 30), (SIG, None)])
    assert item_points(rules, item, lib.affixes) == 9 + rules.category_points["action"]
