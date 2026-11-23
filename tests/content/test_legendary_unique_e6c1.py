"""E6-c1 第 2 項：傳說的獨特效果（08 8.27、8.30 第 7 點；走 E6-a1 的招牌那一步）。

池子＝招牌詞條 ＋ 改寫規則 ＋ 標了 ``legendary_only`` 的詞條；依部位權重抽種類，點數是詞條預算的
60%；沒有候選時為 ``None``（產生器降成史詩，見 ``test_legendary_gen_e6c1.py``）。"""

from __future__ import annotations

import dataclasses
from collections import Counter

import pytest

from tests.content.test_signature_gen_e6a1 import signature_library
from tests.engine.helpers import library
from trpg.content import item_gen
from trpg.content.item_budget import affix_budget, signature_points
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng

RULES = ("affix_rule_bleeding_wake", "affix_rule_fire_mends", "affix_rule_move_any_object")
LEGEND_ONLY = "affix_test_legend_only_str"


def _base(lib: ContentLibrary, slot: str) -> item_gen._Base:
    return item_gen._base(lib, Rng(0), slot, None)  # type: ignore[arg-type]


def _uniques(lib: ContentLibrary, slot: str, seeds: int = 60) -> Counter[str]:
    base = _base(lib, slot)
    assert lib.item_gen is not None
    budget = affix_budget(lib.item_gen, 5, base.slot_type)
    found: Counter[str] = Counter()
    for seed in range(seeds):
        pick = item_gen._unique_effect(lib, Rng(seed), base, budget)
        assert pick is not None
        assert pick.points == signature_points(lib.item_gen, budget)
        found[pick.affix.id] += 1
    return found


def _with_legend_only(lib: ContentLibrary) -> ContentLibrary:
    extra = lib.affixes["affix_attr_str"].model_copy(
        update={"id": LEGEND_ONLY, "legendary_only": True}
    )
    affixes = dict(sorted({**lib.affixes, LEGEND_ONLY: extra}.items()))
    return dataclasses.replace(lib, affixes=affixes)


def test_rule_changes_are_candidates_without_signature_tags() -> None:
    """現有內容：沒有標招牌的詞條，改寫規則（限傳說）就是全部候選。"""
    found = _uniques(library(), "weapon")
    assert set(found) == set(RULES)


def test_pool_has_signatures_rules_and_legendary_only() -> None:
    lib = _with_legend_only(signature_library())
    found = _uniques(lib, "neck", seeds=200)
    # 項鍊：新動作（煙霧，招牌）、改寫規則（3 條，含標了招牌的 fire_mends）、沒標種類的限傳說詞條
    assert set(found) == {"affix_act_smoke", *RULES, LEGEND_ONLY}


def test_kind_weights_follow_slot_weights() -> None:
    """副手：新動作權重 3、新反應 1、改寫規則 1（同招牌的部位權重）。"""
    lib = signature_library()
    found = _uniques(lib, "offhand", seeds=400)
    actions = found["affix_act_grapple"] + found["affix_act_smoke"]
    reactions = found["affix_react_guard_ally"]
    rules = sum(found[r] for r in RULES)
    assert actions > 2 * reactions
    assert actions > 2 * rules
    assert reactions > 0 and rules > 0


def test_zero_weight_kind_is_not_drawn() -> None:
    lib = signature_library()
    assert lib.item_gen is not None
    weights = {**lib.item_gen.signature_weights, "offhand": {"action": 1}}
    rules = lib.item_gen.model_copy(update={"signature_weights": weights})
    lib = dataclasses.replace(lib, item_gen=rules)
    assert set(_uniques(lib, "offhand")) == {"affix_act_grapple", "affix_act_smoke"}


def test_unique_and_held_back_affixes_are_excluded() -> None:
    lib = library()
    assert lib.item_gen is not None
    rules = lib.item_gen.model_copy(update={"held_back_affixes": ("affix_rule_fire_mends",)})
    lib = dataclasses.replace(lib, item_gen=rules)
    assert set(_uniques(lib, "neck")) == {"affix_rule_bleeding_wake", "affix_rule_move_any_object"}


def test_no_candidate_returns_none_without_rng() -> None:
    lib = library()
    affixes = {k: v for k, v in lib.affixes.items() if k not in RULES}
    lib = dataclasses.replace(lib, affixes=affixes)
    base = _base(lib, "feet")
    rng = Rng(3)
    before = rng.get_state()
    assert lib.item_gen is not None
    assert item_gen._unique_effect(lib, rng, base, 8) is None
    assert rng.get_state() == before


@pytest.mark.parametrize("slot", ["weapon", "offhand", "body", "feet", "neck"])
def test_value_is_strongest(slot: str) -> None:
    lib = _with_legend_only(library())
    base = _base(lib, slot)
    for seed in range(20):
        pick = item_gen._unique_effect(lib, Rng(seed), base, 10)
        assert pick is not None
        assert pick.value == item_gen._signature_value(pick.affix)
