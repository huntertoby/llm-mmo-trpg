"""GB-1a ``rules/footprint.py``：一格的單位時每個函式都和 ``manhattan`` 逐值相同（不變比對成立的
前提）；3×3 時等於「逐格取最小」的暴力算法。"""

from __future__ import annotations

from dataclasses import replace
from functools import cache

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import make_map, make_state, spawn
from trpg.engine.rules.footprint import (
    adjacent,
    dist_to,
    is_giant,
    nearest_tile,
    occupies,
    tiles_of,
    unit_dist,
)
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import UnitState
from trpg.shared.types import Pos, Team

coords = st.tuples(st.integers(0, 30), st.integers(0, 30))


@cache
def _base() -> UnitState:
    state = make_state(make_map("000\n000"), [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 1))])
    return state.units_sorted()[0]


def unit_at(xy: tuple[int, int], footprint: int = 1) -> UnitState:
    return replace(_base(), pos=Pos(x=xy[0], y=xy[1]), footprint=footprint)


@settings(deadline=None)  # 第一次建場較慢
@given(coords, coords)
def test_one_tile_functions_match_manhattan(a: tuple[int, int], b: tuple[int, int]) -> None:
    unit, other = unit_at(a), unit_at(b)
    assert not is_giant(unit)
    assert tiles_of(unit) == (a,)
    assert nearest_tile(unit, b) == a
    assert dist_to(unit, b) == manhattan(a, b)
    assert unit_dist(unit, other) == manhattan(a, b)
    assert adjacent(unit, other) == (manhattan(a, b) == 1)
    assert occupies(unit, b) == (a == b)


@settings(deadline=None)  # 第一次建場較慢
@given(coords, coords)
def test_giant_distance_is_the_minimum_over_its_tiles(
    center: tuple[int, int], xy: tuple[int, int]
) -> None:
    giant = unit_at(center, 3)
    tiles = tiles_of(giant)
    assert len(tiles) == 9 and tiles == tuple(sorted(tiles, key=lambda c: (c[1], c[0])))
    best = min(manhattan(t, xy) for t in tiles)
    assert dist_to(giant, xy) == best
    assert nearest_tile(giant, xy) in tiles
    assert manhattan(nearest_tile(giant, xy), xy) == best
    assert occupies(giant, xy) == (xy in tiles)


@settings(deadline=None)  # 第一次建場較慢
@given(coords, coords, st.sampled_from([1, 3]), st.sampled_from([1, 3]))
def test_unit_distance_is_the_minimum_over_both_footprints(
    a: tuple[int, int], b: tuple[int, int], fa: int, fb: int
) -> None:
    one, two = unit_at(a, fa), unit_at(b, fb)
    best = min(manhattan(p, q) for p in tiles_of(one) for q in tiles_of(two))
    assert unit_dist(one, two) == best == unit_dist(two, one)
    assert adjacent(one, two) == (best == 1)


def test_twelve_side_tiles_are_adjacent_and_corners_are_not() -> None:
    """D4：和任何一格相鄰就算（3×3 外圍 12 格）；斜角不算。"""
    giant = unit_at((5, 5), 3)
    ring = [(x, y) for y in range(2, 9) for x in range(2, 9) if dist_to(giant, (x, y)) == 1]
    assert len(ring) == 12
    for corner in ((3, 3), (7, 3), (3, 7), (7, 7)):
        assert not adjacent(giant, unit_at(corner))
    assert adjacent(giant, unit_at((5, 7)))
