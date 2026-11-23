"""E6-a1：產生器放招牌（08 8.27、8.30 第 1、2、11 點）。

現有內容沒有標招牌的詞條，開關也預設關；這裡用測試內容庫：把幾條現有詞條標成招牌，另加一條腳的
地形規則、一條主手的行為改寫，再把開關打開。"""

from __future__ import annotations

import dataclasses
from collections import Counter
from fractions import Fraction

import pytest
from pydantic import TypeAdapter

from tests.engine.helpers import library
from trpg.content.equipment import AffixDef, ItemDef, item_problems
from trpg.content.item_budget import (
    ItemGenRules,
    affix_budget,
    affix_points,
    item_budget_problems,
    signature_points,
)
from trpg.content.item_gen import downscale_item, generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng

_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)
TAGS = {
    "affix_act_grapple": "action",  # 主手、副手、手
    "affix_act_smoke": "action",  # 副手、手、項鍊
    "affix_react_guard_ally": "reaction",  # 身體、副手
    "affix_rule_fire_mends": "rule",  # 限傳說：稀有、史詩抽不到
}
TERRAIN = "affix_test_sig_fire_walk"
BEHAVIOR = "affix_test_sig_behavior"
SLOTS = ("weapon", "offhand", "body", "feet", "neck")


def _extra() -> dict[str, AffixDef]:
    terrain = _ADAPTER.validate_python(
        {
            "id": TERRAIN,
            "name_zh": "火焰表面不會讓你燃燒",
            "category": "terrain",
            "slots": ["feet"],
            "rule": "burn_immunity_on",
            "surfaces": ["fire"],
            "signature": "terrain",
        }
    )
    behavior = _ADAPTER.validate_python(
        {
            "id": BEHAVIOR,
            "name_zh": "測試行為改寫",
            "category": "action",
            "slots": ["weapon"],
            "skill": "skill_attack_mastery",
            "signature": "behavior",
        }
    )
    return {TERRAIN: terrain, BEHAVIOR: behavior}


def signature_library(*, enabled: bool = True, **rule_update: object) -> ContentLibrary:
    lib = library()
    affixes = dict(lib.affixes)
    for affix_id, kind in TAGS.items():
        affixes[affix_id] = affixes[affix_id].model_copy(update={"signature": kind})
    affixes.update(_extra())
    assert lib.item_gen is not None
    rules = lib.item_gen.model_copy(update={"signature_enabled": enabled, **rule_update})
    return dataclasses.replace(lib, affixes=dict(sorted(affixes.items())), item_gen=rules)


def _rules(lib: ContentLibrary) -> ItemGenRules:
    assert lib.item_gen is not None
    return lib.item_gen


def _gen(lib: ContentLibrary, seed: int, slot: str, rarity: str, level: int) -> ItemDef:
    return generate_item(lib, Rng(seed), slot, rarity, level)  # type: ignore[arg-type]


def _signatures(lib: ContentLibrary, item: ItemDef) -> list[AffixDef]:
    return [lib.affixes[r.affix] for r in item.affixes if lib.affixes[r.affix].signature]


def _check(lib: ContentLibrary, item: ItemDef) -> None:
    problems = item_problems(
        item, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands
    ) + item_budget_problems(_rules(lib), item, lib.affixes)
    assert problems == [], (item.id, problems)


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return signature_library()


@pytest.mark.parametrize("slot", SLOTS)
@pytest.mark.parametrize("rarity", ["rare", "epic"])
def test_signature_always_present_and_priced_at_60_percent(
    lib: ContentLibrary, slot: str, rarity: str
) -> None:
    rules = _rules(lib)
    for level in range(1, 11):
        for seed in range(6):
            item = _gen(lib, seed, slot, rarity, level)
            sigs = _signatures(lib, item)
            assert len(sigs) == 1, (slot, rarity, level, seed)
            assert item.affixes[-1].affix == sigs[0].id  # 招牌放最後，第 1 條仍是 build 詞條
            budget = affix_budget(rules, level, item.slot_type)
            assert affix_points(rules, sigs[0], None, budget=budget) == signature_points(
                rules, budget
            )
            assert signature_points(rules, budget) == Fraction(budget * 600, 1000)
            _check(lib, item)


@pytest.mark.parametrize("slot", ["head", "hands", "ring"])
def test_other_slots_never_get_a_signature(lib: ContentLibrary, slot: str) -> None:
    for seed in range(20):
        assert _signatures(lib, _gen(lib, seed, slot, "epic", 6)) == []


@pytest.mark.parametrize("rarity", ["common", "uncommon"])
def test_lower_rarities_never_get_a_signature(lib: ContentLibrary, rarity: str) -> None:
    for slot in SLOTS:
        for seed in range(10):
            assert _signatures(lib, _gen(lib, seed, slot, rarity, 6)) == []


def test_signature_alone_when_the_rest_does_not_fit(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    budget = affix_budget(rules, 1, "feet")
    assert budget - signature_points(rules, budget) < rules.min_affix_points  # 4 − 2.4 ＝ 1.6
    for seed in range(20):
        item = _gen(lib, seed, "feet", "rare", 1)
        assert [r.affix for r in item.affixes] == [TERRAIN]
        _check(lib, item)


def test_counts_include_the_signature(lib: ContentLibrary) -> None:
    for seed in range(30):
        epic = _gen(lib, seed, "weapon", "epic", 10)
        assert len(epic.affixes) == 3  # 史詩＝招牌＋2 條
        assert lib.affixes[epic.affixes[0].affix].category == "keyword"  # 其中 1 條照 8.21.6
    counts: Counter[int] = Counter()
    for slot in SLOTS:
        for level in range(1, 11):
            for seed in range(6):
                counts[len(_gen(lib, seed, slot, "rare", level).affixes)] += 1
                assert len(_gen(lib, seed, slot, "epic", level).affixes) <= 3
    assert set(counts) <= {1, 2, 3}  # 稀有＝招牌＋1～2 條；放不下時只有招牌
    assert {2, 3} <= set(counts)


def test_rest_respects_the_70_percent_floor(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    for slot in SLOTS:
        for level in range(1, 11):
            for seed in range(4):
                item = _gen(lib, seed, slot, "rare", level)
                budget = affix_budget(rules, level, item.slot_type)
                room = budget - signature_points(rules, budget)
                rest = sum(
                    (
                        affix_points(rules, lib.affixes[r.affix], r.value, budget=budget)
                        for r in item.affixes
                        if lib.affixes[r.affix].signature is None
                    ),
                    Fraction(0),
                )
                assert rest == 0 or rest * 1000 >= room * rules.min_fill_permille
                assert rest <= room


def _kinds(lib: ContentLibrary, slot: str, n: int = 400) -> Counter[str]:
    found: Counter[str] = Counter()
    for seed in range(n):
        for sig in _signatures(lib, _gen(lib, seed, slot, "rare", 6)):
            found[sig.signature or ""] += 1
    return found


def test_slot_weights_favour_the_slot_kinds(lib: ContentLibrary) -> None:
    offhand = _kinds(lib, "offhand")  # 新動作 3、新反應 1；行為改寫、地形、改寫規則沒有候選
    assert set(offhand) == {"action", "reaction"}
    share = offhand["action"] / sum(offhand.values())
    assert 0.65 < share < 0.85
    assert set(_kinds(lib, "body", 40)) == {"reaction"}
    assert set(_kinds(lib, "feet", 40)) == {"terrain"}
    assert set(_kinds(lib, "neck", 40)) == {"action"}
    weapon = _kinds(lib, "weapon")  # 新動作 3、行為改寫 3
    assert set(weapon) == {"action", "behavior"}
    assert 0.35 < weapon["action"] / sum(weapon.values()) < 0.65


def test_weights_come_from_item_gen(lib: ContentLibrary) -> None:
    rules = _rules(lib)
    assert rules.signature_weights["weapon"] == {
        "action": 3,
        "reaction": 1,
        "terrain": 1,
        "behavior": 3,
        "rule": 1,
    }
    assert set(rules.signature_weights["neck"].values()) == {1}
    weights = {**rules.signature_weights, "offhand": {"reaction": 1}}
    only_reaction = signature_library(signature_weights=weights)
    assert set(_kinds(only_reaction, "offhand", 40)) == {"reaction"}


def test_kinds_without_candidates_are_never_drawn(lib: ContentLibrary) -> None:
    assert "rule" not in _kinds(lib, "neck", 60)  # 改寫規則只有限傳說的
    weights = {**_rules(lib).signature_weights, "weapon": {"terrain": 5, "rule": 5}}
    nothing = signature_library(signature_weights=weights)
    plain = signature_library(enabled=False)
    for seed in range(10):  # 五種都沒有候選：不帶招牌，照一般的產生
        assert _gen(nothing, seed, "weapon", "rare", 6) == _gen(plain, seed, "weapon", "rare", 6)


def test_material_leanings_do_not_change_the_signature(lib: ContentLibrary) -> None:
    for seed in range(20):
        plain = generate_item(lib, Rng(seed), "offhand", "rare", 6)
        leaning = generate_item(
            lib, Rng(seed), "offhand", "rare", 6, leanings={"affix_attr_str": 5}
        )
        assert _signatures(lib, plain) == _signatures(lib, leaning)


def test_switch_off_gives_bit_identical_items() -> None:
    tagged_off = signature_library(enabled=False)
    plain = library()
    assert _rules(plain).signature_enabled is False
    for slot in (*SLOTS, "head", "hands", "ring"):
        for rarity in ("common", "uncommon", "rare", "epic", "legendary"):
            for level in (1, 3, 6):
                for seed in range(3):
                    a = _gen(tagged_off, seed, slot, rarity, level)
                    b = _gen(plain, seed, slot, rarity, level)
                    assert a.model_dump_json() == b.model_dump_json()
                    if rarity != "legendary":  # 傳說照舊從測試物品挑
                        assert _signatures(tagged_off, a) == []


def test_downscale_keeps_the_signature(lib: ContentLibrary) -> None:
    for seed in range(10):
        item = _gen(lib, seed, "weapon", "epic", 10)
        small = downscale_item(lib, item, 1)
        assert small.affixes[-1] == item.affixes[-1]
