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


def _pillar_map(terrain: str, pillar: tuple[int, int]) -> MapPushReport:
    m = make_map(
        "00000\n00000\n00000",
        terrain,
        ally=[(0, 1)],
        enemy=[(4, 1)],
        objects=[(*pillar, "stone_pillar")],
    )
    state = make_state(m, [spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (4, 1))])
    return check_state(state, "pillar", _ZONES)


def test_a_pillar_in_a_pocket_can_seal_the_corridor_by_toppling_into_it() -> None:
    """石柱站在走廊旁的凹槽：往南倒，倒塌物落在 1 格寬的走廊上，把通路永久封死（Phase 3C-5b）。"""
    report = _pillar_map("##.##\n.....\n#####", (2, 0))
    assert report.connected and not report.seals
    assert report.topplable == [("obj_0001", "stone_pillar", (2, 0))]
    assert [(t.object_id, t.direction, t.rubble_xy) for t in report.topple_seals] == [
        ("obj_0001", (0, 1), (2, 1))
    ]
    assert "往南倒" in report.topple_seals[0].text()
    assert "obj_0001" in render_report([report]).splitlines()[-1]


def test_a_pillar_that_blocks_the_corridor_can_be_toppled_away_when_it_lands_off_the_path() -> None:
    """石柱堵在走廊中央，旁邊有凹槽：往凹槽的方向倒下，倒塌物留在凹槽裡，通路打通。"""
    report = _pillar_map("##.##\n.....\n#####", (2, 1))
    assert not report.connected
    assert [(t.direction, t.rubble_xy) for t in report.topple_unblocks] == [((0, -1), (2, 0))]
    assert "需移動物件" in report.status and report.topple_seals == []


def test_official_maps_are_all_connected_and_the_table_renders() -> None:
    library = load_library()
    ids = sorted(m for m in library.maps if not m.startswith("test_"))
    assert len(ids) == 12  # 10 張正式地圖 ＋ 靶場（Phase 3F-1）＋ Boss 地圖（3-5b）
    reports = [check_map(library, m) for m in ids]
    assert all(r.connected and not r.seals and not r.topple_seals for r in reports)
    assert any(r.topplable for r in reports)
    table = render_report(reports)
    assert table.count("\n") == len(ids) + 1
