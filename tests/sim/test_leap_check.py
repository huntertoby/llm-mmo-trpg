"""獸躍捷徑檢查（Phase 6R-1 驗收 C，#138；:mod:`trpg.sim.leap_check`）。

- 合成地圖：牆圍起來的封閉區跳不進去；矮牆圍起來的跳得進去（照 07 7.7：可以越過矮牆、物件）。
- 正式內容：每張戰鬥地圖與實地地圖都跑一次。被標出的只能是 6R-1 報告列給 PM 決定的那幾項
  （:data:`KNOWN`）；新出現的就失敗。
- 6R-1 新加的 2 層崖台：獸躍、攀爬上得去，也有走得上去的坡（不是唯一的路）。
"""

from __future__ import annotations

from functools import cache

import pytest

from tests.engine.helpers import library, make_map
from trpg.content.library import ContentLibrary
from trpg.engine.rules.movement import step_cost
from trpg.sim.leap_check import (
    MAX_SHORTCUT,
    LeapReport,
    battle_map_report,
    field_as_battle_map,
    field_map_report,
    probe_state,
)

KNOWN: dict[str, str] = {
    # 6R-1 報告「待 PM 決定」：照 7.7 字面（深淵、岩漿不擋、矮牆與物件可以越過）算出來的
    "dark_forest": "(4, 4)、(5, 5) 兩格被牆、倒木與枯樹圍住，只有越過倒木才進得去",
    "lava_cave": "跳過 2 格寬的岩漿溝，到熔岩洞主（cave_lord）的路短 6～8 格",
}


@cache
def _lib() -> ContentLibrary:
    return library()


def _report(heights: str, terrain: str, objects: list[tuple[int, int, str]]) -> LeapReport:
    m = make_map(heights, terrain, ally=[(0, 3)], enemy=[(6, 6)], objects=objects)
    return battle_map_report(_lib(), m)


FLAT = "\n".join(["0000000"] * 7)


def test_walled_pocket_cannot_be_leapt_into() -> None:
    terrain = "\n".join(
        [".......", "...###.", "...#.#.", "...###.", ".......", ".......", "......."]
    )
    report = _report(FLAT, terrain, [])
    assert report.leap_only == []


@pytest.mark.parametrize("blocker", ["stone_pillar", "earth_wall"])
def test_pillar_pocket_cannot_be_leapt_into(blocker: str) -> None:
    ring = [(3, 1), (4, 1), (5, 1), (3, 2), (5, 2), (3, 3), (4, 3), (5, 3)]
    report = _report(FLAT, "\n".join(["......."] * 7), [(x, y, blocker) for x, y in ring])
    assert report.leap_only == []


def test_low_wall_pocket_can_be_leapt_into() -> None:
    ring = [(3, 1), (4, 1), (5, 1), (3, 2), (5, 2), (3, 3), (4, 3), (5, 3)]
    report = _report(FLAT, "\n".join(["......."] * 7), [(x, y, "low_wall") for x, y in ring])
    assert report.leap_only == [(4, 2)]


@pytest.mark.slow
def test_bundled_maps_have_no_new_leap_shortcuts() -> None:
    lib = _lib()
    reports = [battle_map_report(lib, m) for _, m in sorted(lib.maps.items())]
    reports += [
        field_map_report(lib, f) for _, f in sorted(lib.field_maps.items()) if f.region != "capital"
    ]
    bad = {r.map_id: r for r in reports if not r.ok}
    assert set(bad) == set(KNOWN), {k: (v.flagged, v.leap_only) for k, v in bad.items()}
    walls_crossed = [
        r.map_id
        for r in reports
        if any(c.walk is None and c.vault is None and c.leap is not None for c in r.routes)
    ]
    assert walls_crossed == []  # 沒有任何目標是「只有獸躍到得了」
    assert all(
        c.shortcut <= MAX_SHORTCUT for r in reports if r.map_id not in KNOWN for c in r.routes
    )


LEDGES = {
    "north_slope": [(12, 9), (12, 10)],
    "cliff_gang_fort": [(8, 5), (9, 5)],
    "crane_cliff": [(12, 10), (12, 11)],
}


@pytest.mark.parametrize("map_id", sorted(LEDGES))
def test_new_two_level_ledges_have_a_walking_ramp(map_id: str) -> None:
    lib = _lib()
    field = lib.field_maps[map_id]
    state = probe_state(lib, field_as_battle_map(lib, field))
    for x, y in LEDGES[map_id]:
        neighbours = [(x + dx, y + dy) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))]
        heights = [state.tile(*n).height for n in neighbours if state.in_bounds(*n)]
        assert any(state.tile(x, y).height - h == 2 for h in heights)  # 有一邊高 2 層
        walkable_in = [n for n in neighbours if state.in_bounds(*n) and step_cost(state, n, (x, y))]
        assert walkable_in, f"{map_id} {(x, y)}：沒有走得上去的鄰格"
