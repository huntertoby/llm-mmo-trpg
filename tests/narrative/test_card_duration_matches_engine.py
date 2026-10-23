"""卡片寫的持續輪數 ＝ 實戰裡效果存在的輪數（Phase 3-48e）。

符文：施放當輪算第 1 輪，卡片「持續 N 輪」＝ 施放者在第 1～N 輪都讀得到這個符文，第 N 輪結束時
消失。障礙物同理（「N 回合後消失」＝ 環境回合倒數 N 次）。
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast
from tests.engine.test_runes import _finish_round
from trpg.engine import BattleState
from trpg.narrative.skills import skill_card
from trpg.shared.types import Pos


def _skill(effect: dict[str, object]):  # type: ignore[no-untyped-def]
    return make_skill(SID, {"type": "ground_tile", "range": 5}, [effect])


def _rounds_alive(state: BattleState, present: Callable[[BattleState], bool]) -> int:
    """施放當輪算第 1 輪；之後每過一輪還在就 +1。"""
    alive = 1
    for _ in range(8):
        state, _events = _finish_round(state)
        if not present(state):
            break
        alive += 1
    return alive


@pytest.mark.parametrize("duration", [1, 2, 3, 4, 5, None])
def test_rune_card_rounds_equal_rounds_the_rune_exists(duration: int | None) -> None:
    effect: dict[str, object] = {"type": "inscribe", "element": "physical"}
    if duration is not None:
        effect["duration"] = duration
    skill = _skill(effect)
    (shown,) = re.findall(r"持續 (\d+) 輪", skill_card(library(), skill).effects[0])
    state = cast(battle(skill, foes=[(6, 3)]), target_pos=Pos(x=5, y=3)).state
    assert _rounds_alive(state, lambda s: bool(s.runes)) == int(shown)
    if duration is not None:
        assert int(shown) == duration


@pytest.mark.parametrize("duration", [1, 2, 3])
def test_obstacle_card_rounds_equal_environment_rounds(duration: int) -> None:
    objects = library().ruleset.objects
    kind = next(k for k in objects.by_id() if "breakable" in objects.by_id()[k].tags)
    skill = _skill({"type": "create_obstacle", "object": kind, "duration": duration})
    (shown,) = re.findall(r"(\d+) 回合後消失", skill_card(library(), skill).effects[0])
    state = cast(battle(skill, foes=[(6, 3)]), target_pos=Pos(x=5, y=3)).state
    assert int(shown) == duration
    assert _rounds_alive(state, lambda s: s.tile(5, 3).object_id is not None) == duration
