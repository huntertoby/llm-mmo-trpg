"""Phase 3E-1 #5：``skill_shapes.yaml`` 的 ``cell_count`` 與引擎的形狀幾何（空地圖上）一致，
區域預算不再寫死格數。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.engine.helpers import library, make_map, make_state, no_reactions, spawn
from tests.skillgen.helpers import skill
from trpg.engine import BattleState
from trpg.engine.rules.geometry import XY
from trpg.engine.skills import shapes
from trpg.shared.types import Team
from trpg.skillgen.budget import BudgetError, zone_cell_count

SIZE = 13
CENTER = (6, 6)


def _open_state() -> BattleState:
    rows = chr(10).join(["0" * SIZE] * SIZE)
    m = make_map(rows, ally=[(0, 0)], enemy=[(12, 12)])
    spawns = [spawn(Team.ALLY, (0, 0), no_reactions()), spawn(Team.ENEMY, (12, 12), no_reactions())]
    return make_state(m, spawns)


def _geometry(state: BattleState, shape_id: str, value: int) -> int:
    """引擎在 ``CENTER`` 往東施放時影響的格數（只影響選取的那一格或自身的形狀為 1）。"""
    tiles: dict[str, Callable[[], tuple[XY, ...]]] = {
        "line": lambda: shapes.line_tiles(state, CENTER, "east", value),
        "cone": lambda: shapes.cone_tiles(state, CENTER, "east", value),
        "cross": lambda: shapes.cross_tiles(state, CENTER),
        "square3": lambda: shapes.square3_tiles(state, CENTER),
        "ring": lambda: shapes.ring_tiles(state, CENTER, value),
        "allies_in_radius": lambda: shapes.radius_tiles(state, CENTER, value),
    }
    return len(tiles[shape_id]()) if shape_id in tiles else 1


GEOMETRIC = ("line", "cone", "cross", "square3", "ring", "allies_in_radius")
SINGLE_CELL = ("self", "single", "ground_tile", "object_then_tile")


def test_cell_counts_match_the_engine_geometry_on_an_open_map() -> None:
    state = _open_state()
    for shape in library().ruleset.shapes.shapes:
        cells = shape.cell_count
        if cells is None:
            assert shape.id == "chain"  # 連鎖沒有固定格數
            continue
        if cells.param is None:
            if shape.id in GEOMETRIC or shape.id in SINGLE_CELL:
                assert cells.base == _geometry(state, shape.id, 0), shape.id
            continue
        assert cells.by_value is not None
        for value, count in cells.by_value.items():
            assert count == _geometry(state, shape.id, value), (shape.id, value)


def test_every_geometric_shape_has_a_cell_count() -> None:
    by_id = library().ruleset.shapes.by_id()
    assert all(by_id[s].cell_count is not None for s in (*GEOMETRIC, *SINGLE_CELL))


def test_zone_cell_count_uses_the_shape_data() -> None:
    lib = library()
    cone = skill(shape={"type": "cone", "size": 3})
    assert zone_cell_count(cone, lib) == 9
    ring = skill(shape={"type": "ring", "radius": 2})
    assert zone_cell_count(ring, lib) == 16


def test_zone_cell_count_rejects_a_shape_without_a_cell_count() -> None:
    lib = library()
    chain = skill(shape={"type": "chain", "range": 4, "jumps": 2, "jump_range": 2})
    with pytest.raises(BudgetError, match="cell_count"):
        zone_cell_count(chain, lib)
    unknown = chain.model_copy(update={"shape": chain.shape.model_copy(update={"type": "blob"})})
    with pytest.raises(BudgetError, match="未知的形狀"):
        zone_cell_count(unknown, lib)
