"""Phase 3-54b 小修 (b)：元素擴散的格數是技能參數 1 或 2（預設 1；06 6.33）。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.shared.types import Surface

DIRECTIONS = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
LINE = {"type": "line", "size": 1}


def _wind(spread: int | None, shape: dict[str, Any] | None = None) -> SkillDef:
    hit: dict[str, Any] = {"type": "damage", "dice": "1d4", "element": "wind", "affects": "tiles"}
    if spread is not None:
        hit["spread"] = spread
    return make_skill(SID, shape or LINE, [hit])


def _surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


@pytest.mark.parametrize("surface", ["fire", "ice", "poison"])
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
@pytest.mark.parametrize(("spread", "grown"), [(None, 1), (1, 1), (2, 2)])
def test_spread_distance_follows_the_skill_parameter(
    surface: str, direction: str, spread: int | None, grown: int
) -> None:
    dx, dy = DIRECTIONS[direction]
    start = (3 + dx, 3 + dy)
    # 施放者在 (3, 3)：七乘七的地圖往每個方向至少還有 2 格
    state = hit_with(battle(_wind(spread), surfaces=((*start, surface),), foes=[(0, 0)]))
    after = cast(state, direction=direction).state
    expected = {(start[0] + i * dx, start[1] + i * dy): Surface(surface) for i in range(grown + 1)}
    assert _surfaces(after) == expected


def test_spread_two_stops_at_a_wall_after_one_cell() -> None:
    state = battle(_wind(2), surfaces=((4, 3, "poison"),), foes=[(0, 0)])
    state.set_tile(6, 3, replace(state.tile(6, 3), terrain="wall"))
    after = cast(hit_with(state), direction="east").state
    assert _surfaces(after) == {(4, 3): Surface.POISON, (5, 3): Surface.POISON}


def test_spread_two_does_not_chain_and_zones_grow_two_cells() -> None:
    state = battle(_wind(2, {"type": "line", "size": 3}), surfaces=((4, 3, "fire"),))
    after = cast(hit_with(state), direction="east").state
    assert _surfaces(after) == {
        (4, 3): Surface.FIRE,
        (5, 3): Surface.FIRE,
        (6, 3): Surface.FIRE,
    }


def test_spread_is_only_for_wind_damage() -> None:
    with pytest.raises(ValueError, match="spread"):
        make_skill(
            "skill_t_spread",
            LINE,
            [{"type": "damage", "dice": "1d4", "element": "fire", "affects": "tiles", "spread": 2}],
        )


def test_spread_is_one_or_two() -> None:
    for bad in (0, 3):
        with pytest.raises(ValueError):
            _wind(bad)
