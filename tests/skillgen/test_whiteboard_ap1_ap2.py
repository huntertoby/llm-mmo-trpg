"""白板主動技預設 1 AP（AP-2 第 6 項，06 6.34.1 ⚠ #168 題 5「白板預設改1AP」）：預設 1 AP，調不進
預算窗時照預算調退回 2 AP；配方自己寫 AP 的不變；驗證器收 1 或 2。"""

from __future__ import annotations

from collections import Counter

from tests.engine.helpers import library, with_whiteboard_ap
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import ComposeError
from trpg.skillgen.whiteboard import compose_whiteboard, whiteboard_problems

LIB = library()
RULES = LIB.composer.whiteboard


def test_the_default_is_one_ap_with_a_two_ap_fallback() -> None:
    assert (RULES.ap_cost, RULES.fallback_ap_cost) == (1, 2)


def test_active_whiteboards_are_mostly_one_ap_and_fall_back_to_two() -> None:
    seen: Counter[int | None] = Counter()
    for tier in (1, 2, 3):
        for seed in range(40):
            try:
                skill = compose_whiteboard(seed, kind="active", tier=tier, library=LIB)
            except ComposeError:
                continue
            seen[skill.ap_cost] += 1
            assert whiteboard_problems(skill, LIB, tier) == [], (seed, tier)
            assert skill_budget(skill, LIB).ok, (seed, tier)
    assert seen[1] > seen[2] > 0  # 多數 1 AP，少數調不進窗退回 2 AP
    assert set(seen) <= {None, 1, 2}  # 姿態沒有 AP


def test_recipes_with_their_own_ap_keep_it() -> None:
    summon = compose_whiteboard(1, keyword="summon", tier=1, library=LIB, starter=True)
    assert summon.ap_cost == RULES.summon_ap_cost


def test_the_workshop_value_turns_the_old_default_back() -> None:
    """工坊把預設調回 2 AP 時，白板一律 2 AP（同 AP-2 之前；配方自己寫 AP 的照舊）。"""
    old = with_whiteboard_ap(LIB, 2)
    for seed in range(10):
        try:
            skill = compose_whiteboard(seed, kind="active", tier=1, library=old)
        except ComposeError:
            continue
        if skill.effects[0].type not in ("summon", "raise_terrain") and skill.shape.type != "self":
            assert skill.ap_cost == 2, seed
