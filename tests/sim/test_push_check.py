"""地圖卡路檢查（Phase 3C-1 3.3）。"""

from __future__ import annotations

from tests.engine.helpers import make_map, make_state, spawn
from trpg.content.library import load_library
from trpg.shared.types import Team
from trpg.sim.push_check import MapPushReport, check_map, check_state, render_report

_ZONES = {Team.ALLY: [(0, 1)], Team.ENEMY: [(4, 1)]}


def _corridor(terrain: str) -> MapPushReport:
    m = make_map(
        "00000\n00000\n00000",
        terrain,
        ally=[(0, 1)],
        enemy=[(4, 1)],
        objects=[(2, 1, "crate")],
    )
    state = make_state(m, [spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (4, 1))])
    return check_state(state, "corridor", _ZONES)


def test_crate_in_a_one_tile_corridor_is_a_stuck_blocker() -> None:
    report = _corridor("#####\n.....\n#####")
    assert not report.connected
    assert report.blockers == [("obj_0001", (2, 1))]
    assert report.sole_blockers == ["obj_0001"]
    assert report.unblocks == []
    assert report.status.startswith("不通")


def test_crate_with_a_side_pocket_can_be_moved_out_of_the_way() -> None:
    report = _corridor("##.##\n.....\n#####")
    assert not report.connected
    assert [(u.object_id, u.to_xy) for u in report.unblocks] == [("obj_0001", (2, 0))]
    assert "需移動物件" in report.status


def test_official_maps_are_all_connected_and_the_table_renders() -> None:
    library = load_library()
    ids = sorted(m for m in library.maps if not m.startswith("test_"))
    assert len(ids) == 10
    reports = [check_map(library, m) for m in ids]
    assert all(r.connected and not r.seals for r in reports)
    table = render_report(reports)
    assert table.count("\n") == len(ids) + 1
