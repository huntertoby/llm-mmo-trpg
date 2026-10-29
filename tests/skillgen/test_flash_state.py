"""Phase 3W-1：閃現狀態與規則（次數、先上場用過、預算上限加成、種子標籤、花掉的點數與溶掉退回）。"""

from __future__ import annotations

import pytest

from trpg.content.flash_templates import FlashPricing, FlashRules
from trpg.skillgen.flash_state import (
    COMPLETE_SLOT,
    SkillFlash,
    Variation,
    acquire,
    after_battle,
    bonus_permille,
    counts_as_used,
    dissolve_refund,
    flash_count,
    flash_problem,
    next_nth,
    price,
    reflash_problem,
    seed_tag,
    slot_is_major,
    with_flash,
    with_reflash,
)

RULES = FlashRules()
V1 = Variation(source="minor", template="area_plus", category="area")
V2 = Variation(source="minor", template="range_plus", category="area")


def _flashed(times: int, *, used: bool = True) -> SkillFlash:
    state = acquire("skill_x")
    for _ in range(times):
        state = with_flash(state.model_copy(update={"used": True}), V1, cost=1)
    return state.model_copy(update={"used": used})


@pytest.mark.parametrize(
    ("flashes", "bonus"), [(0, 0), (1, 40), (2, 80), (3, 120), (4, 160), (5, 200)]
)
def test_each_flash_raises_the_budget_cap_by_forty_permille(flashes: int, bonus: int) -> None:
    state = _flashed(flashes)
    assert flash_count(RULES, state) == flashes
    assert bonus_permille(RULES, state) == bonus


def test_a_complete_skill_counts_as_three_flashes_with_120_permille() -> None:
    state = acquire("skill_x", complete=True)
    assert flash_count(RULES, state) == 3
    assert bonus_permille(RULES, state) == 120
    assert flash_problem(RULES, state.model_copy(update={"used": True})) is not None
    assert reflash_problem(RULES, state, COMPLETE_SLOT) is None  # 不需要先上場用過
    assert reflash_problem(RULES, state, 1) is not None
    assert not slot_is_major(RULES, state, COMPLETE_SLOT)


@pytest.mark.parametrize(
    ("state", "ok"),
    [
        (acquire("skill_x"), False),  # 剛取得、還沒用過
        (acquire("skill_x").model_copy(update={"used": True}), True),
        (_flashed(2, used=False), False),  # 閃完後要重新用過
        (_flashed(2, used=True), True),
        (_flashed(5, used=True), False),  # 已到 5 次
    ],
)
def test_flash_needs_use_and_stops_at_five(state: SkillFlash, ok: bool) -> None:
    assert (flash_problem(RULES, state) is None) is ok


def test_needs_use_can_be_switched_off_in_content() -> None:
    rules = FlashRules(needs_use=False)
    assert flash_problem(rules, acquire("skill_x")) is None


@pytest.mark.parametrize(
    ("kind", "casts", "finished", "used"),
    [
        ("active", 0, True, False),  # 主動技：裝備著打完一場不算
        ("active", 1, False, True),  # 放出 1 次就算（不用打中）
        ("passive", 0, True, True),  # 被動：裝備著打完一場
        ("passive", 0, False, False),
        ("reaction", 0, True, True),
        ("stance", 0, True, True),
        ("stance", 3, False, False),  # 姿態：放出不算，要打完一場
        ("modifier", 0, True, True),
    ],
)
def test_counts_as_used_by_skill_kind(kind: str, casts: int, finished: bool, used: bool) -> None:
    assert counts_as_used(kind, casts=casts, finished_equipped=finished) is used  # type: ignore[arg-type]
    state = after_battle(acquire("skill_x"), kind, casts=casts, finished_equipped=finished)  # type: ignore[arg-type]
    assert state.used is used


def test_after_battle_never_clears_a_recorded_use() -> None:
    state = acquire("skill_x").model_copy(update={"used": True})
    assert after_battle(state, "active", casts=0, finished_equipped=True).used


def test_flash_appends_and_resets_use_reflash_replaces_and_keeps_count() -> None:
    state = _flashed(3)
    assert [r.nth for r in state.records] == [1, 2, 3] and next_nth(state) == 4
    again = with_reflash(state, 2, V2, cost=2)
    assert flash_count(RULES, again) == 3  # 重閃不加次數
    assert again.used  # 也不清掉「用過」
    assert again.record(2) is not None and again.record(2).variation == V2  # type: ignore[union-attr]
    assert again.record(2).reflashes == 1  # type: ignore[union-attr]
    assert with_reflash(again, 2, V1).record(2).reflashes == 2  # type: ignore[union-attr]
    assert reflash_problem(RULES, state, 4) is not None
    assert reflash_problem(RULES, state.model_copy(update={"used": False}), 1) is None
    with pytest.raises(ValueError, match="沒有第 9 次"):
        with_reflash(state, 9, V1)


def test_the_third_flash_or_reflashing_it_is_major() -> None:
    state = _flashed(3)
    assert [slot_is_major(RULES, state, n) for n in (1, 2, 3, 4, 5)] == [
        False,
        False,
        True,
        False,
        False,
    ]


def test_seed_tags() -> None:
    assert seed_tag("skill_x", 3, 0) == "flash/skill_x/3/0"
    assert seed_tag("skill_x", 2, 1, "area") == "flash/skill_x/2/1/area"


def test_pricing_follows_decision_70() -> None:
    pricing = FlashPricing()
    assert (price(pricing, focused=False).cost, price(pricing, focused=False).options) == (1, 4)
    assert price(pricing, focused=False).min_categories == 2
    assert (price(pricing, focused=True).cost, price(pricing, focused=True).options) == (2, 3)


@pytest.mark.parametrize(
    ("spent", "refund"), [(0, 0), (1, 0), (2, 1), (3, 1), (5, 2), (6, 3), (11, 5)]
)
def test_dissolve_refunds_half_rounded_down(spent: int, refund: int) -> None:
    state = acquire("skill_x").model_copy(update={"spent": spent})
    assert dissolve_refund(RULES, state) == refund


def test_dissolve_example_from_decision_71() -> None:
    """閃 3 次（其中 1 次指定類別）＋重閃 1 次 ＝ 5 點，退 2 點；完整技能只算重閃。"""
    state = acquire("skill_x")
    for cost in (1, 2, 1):
        state = with_flash(state.model_copy(update={"used": True}), V1, cost=cost)
    state = with_reflash(state, 1, V2, cost=1)
    assert state.spent == 5
    assert dissolve_refund(RULES, state) == 2
    complete = acquire("skill_y", complete=True)
    assert dissolve_refund(RULES, complete) == 0
    complete = with_reflash(complete, COMPLETE_SLOT, V1, cost=2)
    assert complete.spent == 2 and dissolve_refund(RULES, complete) == 1


def test_state_round_trips_through_json() -> None:
    state = with_reflash(_flashed(3), 3, V2, cost=1)
    assert SkillFlash.model_validate_json(state.model_dump_json()) == state
