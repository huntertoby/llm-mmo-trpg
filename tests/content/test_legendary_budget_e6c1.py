"""E6-c1 第 1 項：稀有度表的傳說與傳說的預算檢查（08 8.27、8.30 第 6、7 點）。

傳說＝2 條詞條（類別同史詩）＋ 1 個獨特效果；獨特效果照招牌計價（詞條預算的 60%），不佔那 2 條；
只出在主手、副手、身體、腳、項鍊。沒有物品等級的測試傳說（``items.yaml``）照舊不檢查。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import library
from trpg.content.equipment import AffixRoll, ItemDef
from trpg.content.item_budget import (
    ItemGenRules,
    affix_budget,
    affix_points,
    item_budget_problems,
    item_points,
    legendary_unique,
    signature_points,
)
from trpg.content.library import ContentLibrary

RULE = "affix_rule_fire_mends"


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return library()


def _rules(lib: ContentLibrary) -> ItemGenRules:
    assert lib.item_gen is not None
    return lib.item_gen


def _neck(*rolls: AffixRoll, level: int | None = 10, slot: str = "neck") -> ItemDef:
    return ItemDef(
        id="item_test_legend",
        name_zh="測試傳說",
        slot_type=slot,  # type: ignore[arg-type]
        rarity="legendary",
        legendary=True,
        item_level=level,
        affixes=rolls,
    )


GOOD = (
    AffixRoll(affix="affix_kw_burn_duration"),
    AffixRoll(affix="affix_attr_str", value=10),
    AffixRoll(affix=RULE),
)


def test_rarity_table_has_legendary_like_epic(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    legendary = rules.rarity("legendary")
    epic = rules.rarity("epic")
    assert (legendary.min_affixes, legendary.max_affixes) == (2, 2)
    assert legendary.categories == epic.categories
    assert legendary.required
    assert rules.legendary_slots == ("weapon", "offhand", "body", "feet", "neck")
    for slot in ("head", "hands", "ring"):
        assert not rules.legendary_slot(slot)


def test_unique_candidates(lib: ContentLibrary) -> None:
    assert legendary_unique(lib.affixes[RULE])
    assert not legendary_unique(lib.affixes["affix_attr_str"])
    assert not legendary_unique(lib.affixes["affix_kw_burn_duration"])
    tagged = lib.affixes["affix_act_grapple"].model_copy(update={"signature": "action"})
    assert legendary_unique(tagged)


def test_unique_effect_priced_at_60_percent_and_passes(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    item = _neck(*GOOD)
    budget = affix_budget(rules, 10, "neck")
    unique = affix_points(rules, lib.affixes[RULE], None, budget=budget, legendary=True)
    assert unique == signature_points(rules, budget) == Fraction(budget * 600, 1000)
    # 非傳說或不知道預算時照類別點數
    assert affix_points(rules, lib.affixes[RULE], None, budget=budget) == 40
    assert affix_points(rules, lib.affixes[RULE], None, legendary=True) == 40
    assert item_points(rules, item, lib.affixes) == 8 + 3 + unique
    assert item_budget_problems(rules, item, lib.affixes) == []


def test_unique_does_not_count_towards_two_affixes(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    three = _neck(
        AffixRoll(affix="affix_kw_burn_duration"),
        AffixRoll(affix="affix_attr_str", value=10),
        AffixRoll(affix="affix_attr_dex", value=10),
        AffixRoll(affix=RULE),
    )
    problems = item_budget_problems(rules, three, lib.affixes)
    assert any("傳說最多 2 條詞條（有 3 條）" in p for p in problems), problems


def test_legendary_needs_exactly_one_unique(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    none = _neck(*GOOD[:2])
    assert any("獨特效果" in p for p in item_budget_problems(rules, none, lib.affixes))
    two = _neck(*GOOD, AffixRoll(affix="affix_rule_move_any_object"))
    assert any("有 2 個" in p for p in item_budget_problems(rules, two, lib.affixes))


def test_legendary_over_budget_is_reported(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    item = _neck(
        AffixRoll(affix="affix_kw_burn_duration"),
        AffixRoll(affix="affix_attr_str", value=40),
        AffixRoll(affix=RULE),
    )
    assert any("超過預算" in p for p in item_budget_problems(rules, item, lib.affixes))


def test_legendary_has_no_lower_bound(lib: ContentLibrary) -> None:
    """獨特效果比照招牌：只檢查上限（08 8.30 第 2 點的解讀）。"""
    item = _neck(AffixRoll(affix="affix_attr_str", value=10), AffixRoll(affix=RULE))
    assert item_budget_problems(_rules(lib), item, lib.affixes) == []


@pytest.mark.parametrize("slot", ["head", "hands", "ring"])
def test_legendary_slot_problem(lib: ContentLibrary, slot: str) -> None:
    item = _neck(AffixRoll(affix=RULE), level=10, slot=slot)
    problems = item_budget_problems(_rules(lib), item, lib.affixes)
    assert any("傳說不能出在" in p for p in problems), problems


def test_test_legendaries_without_level_are_not_checked(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    for item_id in ("item_g3b_legend_ember", "item_g3b_legend_titan", "item_g3b_legend_wake"):
        item = lib.items[item_id]
        assert item.item_level is None
        assert item_budget_problems(rules, item, lib.affixes) == []
        assert item_points(rules, item, lib.affixes) == 40  # 照舊：類別點數
