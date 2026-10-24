"""Phase 3-54b 小修 (a)：吹送時推進致命地形（深淵、岩漿、冰窟）的表面直接消失（06 6.33）。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, battle, cast, of
from trpg.engine import BattleState
from trpg.engine.events import SurfaceBlown
from trpg.shared.types import Surface

LINE = {"type": "line", "size": 1}
SURFACES = ["fire", "poison", "ice", "water", "oil", "smoke"]


def _blow(shape: dict[str, Any], distance: int):  # type: ignore[no-untyped-def]
    return make_skill(SID, shape, [{"type": "blow_surface", "distance": distance}])


def _surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


def _terrain(state: BattleState, xy: tuple[int, int], terrain: str) -> BattleState:
    state.set_tile(*xy, replace(state.tile(*xy), terrain=terrain))
    return state


@pytest.mark.parametrize("terrain", ["chasm", "lava", "ice_hole"])
@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize(
    ("deadly_at", "distance", "lost"),
    [
        ((5, 3), 2, True),  # 第 1 步就進去：消失
        ((6, 3), 3, True),  # 走過第 1 格後進去：消失
        ((6, 3), 2, True),  # 剛好走到致命地形那一格：消失
        ((6, 3), 1, False),  # 距離不夠到：停在原地前一格
        (None, 2, False),  # 對照：沒有致命地形
    ],
)
def test_blow_into_deadly_terrain_removes_the_surface(
    terrain: str, surface: str, deadly_at: tuple[int, int] | None, distance: int, lost: bool
) -> None:
    state = battle(_blow(LINE, distance), surfaces=((4, 3, surface),), foes=[(0, 0)])
    if deadly_at is not None:
        _terrain(state, deadly_at, terrain)
    result = cast(state, direction="east")
    (blown,) = of(result, SurfaceBlown)
    assert blown.lost is lost
    after = _surfaces(result.state)
    if lost:
        assert after == {}
        assert deadly_at is not None
        assert (blown.to_pos.x, blown.to_pos.y) == deadly_at
    else:
        assert list(after.values()) == [Surface(surface)]  # 沒有消失：留在可站的格子上
        (xy,) = after
        assert not result.state.ruleset.terrain_def(result.state.tile(*xy).terrain).deadly


def test_only_the_pieces_that_enter_are_lost() -> None:
    """兩格長的火往東吹 2 格：前端進深淵消失，後面的留在 (4, 3)。"""
    skill = _blow({"type": "line", "size": 3}, 2)
    state = battle(
        skill, caster=(1, 3), surfaces=((2, 3, "fire"), (3, 3, "fire")), foes=[(0, 0)]
    )
    _terrain(state, (5, 3), "chasm")
    result = cast(state, direction="east")
    assert _surfaces(result.state) == {(4, 3): Surface.FIRE}
    assert sorted(b.lost for b in of(result, SurfaceBlown)) == [False, True]
    assert len(_surfaces(result.state)) == 1


def test_a_wall_still_stops_the_surface() -> None:
    state = battle(_blow(LINE, 2), surfaces=((4, 3, "oil"),), foes=[(0, 0)])
    _terrain(state, (5, 3), "wall")
    result = cast(state, direction="east")
    (blown,) = of(result, SurfaceBlown)
    assert not blown.lost
    assert _surfaces(result.state) == {(4, 3): Surface.OIL}


def test_a_bridge_over_the_chasm_is_not_deadly() -> None:
    state = battle(
        _blow(LINE, 2),
        surfaces=((4, 3, "oil"),),
        objects=((6, 3, "wooden_bridge"),),
        foes=[(0, 0)],
    )
    _terrain(state, (6, 3), "chasm")
    result = cast(state, direction="east")
    (blown,) = of(result, SurfaceBlown)
    assert not blown.lost
    assert _surfaces(result.state) == {(6, 3): Surface.OIL}
