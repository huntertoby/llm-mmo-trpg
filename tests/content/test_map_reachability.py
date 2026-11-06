"""正式戰鬥地圖沒有「可站立卻走不到」的格子（MAP-1）。

從雙方起始區出發，用地圖檢查共用的移動規則（:func:`passable_grid`、:func:`reachable_from`：
``blocks_move`` 物件、牆壁、爬升上限）做連通性檢查；可破壞物件不算通路。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.maps import TEST_ARCHETYPE, MapDef, passable_grid, reachable_from

KNOWN_EXCEPTIONS: dict[str, set[tuple[int, int]]] = {}
"""已知、尚未修的封閉格（地圖 id → 格子）；目前沒有。"""


def _formal_maps() -> list[str]:
    return sorted(k for k, v in library().maps.items() if v.archetype != TEST_ARCHETYPE)


def _unreachable(map_def: MapDef) -> set[tuple[int, int]]:
    rules = library().ruleset
    grid = map_def.grid()
    passable = passable_grid(map_def, rules.terrain.by_id(), rules.objects.by_id())
    reach: set[tuple[int, int]] = set()
    for cell in sorted({c for cells in map_def.start_zones.values() for c in cells}):
        reach |= reachable_from(cell, grid, passable, rules.core)
    return {
        (x, y)
        for y, row in enumerate(passable)
        for x, ok in enumerate(row)
        if ok and (x, y) not in reach
    }


@pytest.mark.parametrize("map_id", _formal_maps())
def test_no_enclosed_standable_tiles(map_id: str) -> None:
    assert _unreachable(library().maps[map_id]) == KNOWN_EXCEPTIONS.get(map_id, set())


def test_dark_forest_former_pockets_reachable() -> None:
    """MAP-1：原被倒木、枯樹與牆圍住的 [4, 4]、[5, 5] 走得進去。"""
    unreachable = _unreachable(library().maps["dark_forest"])
    assert (4, 4) not in unreachable
    assert (5, 5) not in unreachable
