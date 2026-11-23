"""E6-c1 第 6 項（開關）與產生器產傳說（08 8.27、8.30 第 6、7、10、11 點）。

``legendary_enabled`` 預設關；關著時抽到傳說照舊從 ``items.yaml`` 挑。打開時：傳說＝2 條詞條＋獨特
效果（60%），頭、手、戒指降成史詩，沒有獨特效果的候選也降成史詩。"""

from __future__ import annotations

import dataclasses

import pytest

from tests.content.test_signature_gen_e6a1 import signature_library
from tests.engine.helpers import library
from trpg.content.equipment import ItemDef, item_problems
from trpg.content.item_budget import (
    ItemGenRules,
    affix_budget,
    affix_points,
    item_budget_problems,
    legendary_unique,
    signature_points,
)
from trpg.content.item_gen import ItemGenError, generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng

SLOTS = ("weapon", "offhand", "body", "feet", "neck")
RULES = ("affix_rule_bleeding_wake", "affix_rule_fire_mends", "affix_rule_move_any_object")


def legendary_library(base: ContentLibrary | None = None, **update: object) -> ContentLibrary:
    lib = base or library()
    assert lib.item_gen is not None
    rules = lib.item_gen.model_copy(update={"legendary_enabled": True, **update})
    return dataclasses.replace(lib, item_gen=rules)


def _rules(lib: ContentLibrary) -> ItemGenRules:
    assert lib.item_gen is not None
    return lib.item_gen


def _gen(
    lib: ContentLibrary, seed: int, slot: str, level: int, rarity: str = "legendary"
) -> ItemDef:
    return generate_item(lib, Rng(seed), slot, rarity, level)  # type: ignore[arg-type]


def _check(lib: ContentLibrary, item: ItemDef) -> None:
    problems = item_problems(
        item, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands
    ) + item_budget_problems(_rules(lib), item, lib.affixes)
    assert problems == [], (item.id, problems)


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return legendary_library()


def test_switch_defaults_off() -> None:
    assert _rules(library()).legendary_enabled is False


def test_switch_off_keeps_picking_test_legendaries() -> None:
    lib = library()
    neck = _gen(lib, 1, "neck", 3)
    assert neck.id in lib.items and neck.legendary
    assert _gen(lib, 1, "ring", 3).rarity == "epic"


@pytest.mark.parametrize("slot", SLOTS)
def test_legendary_is_two_affixes_plus_unique_at_60_percent(lib: ContentLibrary, slot: str) -> None:
    rules = _rules(lib)
    for level in range(1, 11):
        for seed in range(5):
            item = _gen(lib, seed, slot, level)
            assert item.rarity == "legendary" and item.legendary
            assert item.item_level == level
            defs = [lib.affixes[r.affix] for r in item.affixes]
            assert legendary_unique(defs[-1]), item.affixes  # 獨特效果放最後
            assert not any(legendary_unique(d) for d in defs[:-1])
            assert len(defs) - 1 <= 2
            budget = affix_budget(rules, level, item.slot_type)
            unique = affix_points(
                rules, defs[-1], item.affixes[-1].value, budget=budget, legendary=True
            )
            assert unique == signature_points(rules, budget)
            _check(lib, item)


def test_high_level_legendary_has_build_affix_and_two_affixes(lib: ContentLibrary) -> None:
    for seed in range(10):
        item = _gen(lib, seed, "main_hand", 10)
        assert len(item.affixes) == 3, item.affixes
        assert lib.affixes[item.affixes[0].affix].category == "keyword"
        assert item.affixes[-1].affix in RULES


@pytest.mark.parametrize("slot", ["head", "hands", "ring_1"])
def test_head_hands_ring_downgrade_to_epic(lib: ContentLibrary, slot: str) -> None:
    for seed in range(6):
        item = _gen(lib, seed, slot, 6)
        assert item.rarity == "epic" and not item.legendary
        assert not any(legendary_unique(lib.affixes[r.affix]) for r in item.affixes)
        _check(lib, item)


def test_slot_downgrade_matches_plain_epic(lib: ContentLibrary) -> None:
    """降級後就是一般的史詩（同種子同結果，只差在抽到的是傳說）。"""
    for seed in range(6):
        assert _gen(lib, seed, "head", 5) == _gen(lib, seed, "head", 5, "epic")


def test_no_unique_candidate_downgrades_to_epic() -> None:
    plain = library()
    affixes = {k: v for k, v in plain.affixes.items() if k not in RULES}
    lib = legendary_library(dataclasses.replace(plain, affixes=affixes))
    for seed in range(6):
        item = _gen(lib, seed, "feet", 6)
        assert item.rarity == "epic" and not item.legendary
        _check(lib, item)


def test_legendary_never_carries_an_extra_signature() -> None:
    lib = legendary_library(signature_library())
    for slot in SLOTS:
        for seed in range(6):
            item = _gen(lib, seed, slot, 8)
            uniques = [r.affix for r in item.affixes if legendary_unique(lib.affixes[r.affix])]
            assert len(uniques) == 1 and uniques[0] == item.affixes[-1].affix
            _check(lib, item)


def test_switch_on_does_not_change_other_rarities(lib: ContentLibrary) -> None:
    off = library()
    for rarity in ("common", "uncommon", "rare", "epic"):
        for slot in ("main_hand", "head", "neck"):
            for seed in range(4):
                assert _gen(lib, seed, slot, 4, rarity) == _gen(off, seed, slot, 4, rarity)


def test_signature_kind_cannot_target_a_legendary(lib: ContentLibrary) -> None:
    with pytest.raises(ItemGenError, match="獨特效果不能指定類型"):
        generate_item(lib, Rng(0), "neck", "legendary", 5, signature_kind="rule")


def test_deterministic(lib: ContentLibrary) -> None:
    assert _gen(lib, 7, "body", 6) == _gen(lib, 7, "body", 6)


@pytest.mark.parametrize("slot", ["main_hand", "off_hand", "body", "feet", "neck"])
def test_program_names_legendary(lib: ContentLibrary, slot: str) -> None:
    """E6-c1 第 3 項：程式命名「傳說〇〇」（08 8.30 第 10 點；LLM 命名另開一段）。"""
    for seed in range(4):
        item = _gen(lib, seed, slot, 5)
        epic = _gen(lib, seed, slot, 5, "epic")
        assert item.name_zh.startswith("傳說")
        assert item.name_zh.removeprefix("傳說") == epic.name_zh.removeprefix("史詩")
