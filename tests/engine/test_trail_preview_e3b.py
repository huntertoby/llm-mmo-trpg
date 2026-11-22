"""E3b：走路預覽畫出這次會留下表面的格子（霜行，08 8.29 E3「顯示」）。

起點與途經的格子會留、停點不留；照 8.29 跳過不留的格子（已有表面、有其他單位站著、會飛、那一步倒下）
各一個例子。預覽取最少後果那次模擬（停點＝``stop``），和實走同一套判斷。
"""

from __future__ import annotations

from tests.engine.race_helpers import U1, race_state
from tests.engine.test_path_preview import _enemy_trap
from tests.engine.test_trail_e3 import _frost, _path, _walk
from tests.engine.test_unit_rules_e2 import terrain, wear
from trpg.api.path_schemas import path_preview_out
from trpg.engine.path_preview import TrailPreview, preview_path
from trpg.shared.types import Surface


def test_preview_lists_start_and_passed_tiles_not_the_stop() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    p = preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3), (5, 4)))
    assert p.trail == TrailPreview(tiles=((3, 3), (4, 3), (5, 3)), surface=Surface.ICE, duration=1)
    # 和實走留下的格子一樣
    after = _walk(state, (3, 3), (4, 3), (5, 3), (5, 4)).state
    assert set(p.trail.tiles) == {
        (x, y)
        for y in range(after.height)
        for x in range(after.width)
        if after.tile(x, y).surface_trail == U1
    }


def test_without_the_rule_there_is_no_trail() -> None:
    state = race_state(None, foes=((6, 6),))
    assert preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3))).trail is None


def test_tiles_that_already_have_a_surface_are_skipped() -> None:
    state = _frost(race_state(None, foes=((6, 6),), surfaces=[(4, 3, "water")]))
    p = preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3), (6, 3)))
    assert p.trail is not None
    assert p.trail.tiles == ((3, 3), (5, 3))


def test_tiles_with_another_unit_standing_are_skipped() -> None:
    state = _frost(race_state(None, foes=((6, 6),), allies=((4, 3),)))
    p = preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3), (6, 3)))
    assert p.trail is not None
    assert p.trail.tiles == ((3, 3), (5, 3))


def test_a_flying_unit_leaves_nothing() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    state.units[U1].tags = (*state.units[U1].tags, "flying")
    assert preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3))).trail is None


def test_the_step_the_unit_goes_down_leaves_nothing() -> None:
    # 第二步踩進看得見的捕獸夾，最少傷害也會倒下：起點那一格留、倒下那一步離開的格子不留
    state = _frost(_enemy_trap(race_state(None, foes=((6, 6),), my_hp=1), (5, 3), revealed=True))
    p = preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3), (6, 3)))
    assert any(e.kind == "downed" and e.certain for s in p.steps for e in s.events)
    assert p.trail is not None
    assert p.trail.tiles == ((3, 3),)


def test_other_surface_and_duration_come_from_the_rule() -> None:
    state = race_state(None, foes=((6, 6),))
    fire = terrain(
        "affix_t_fire_trail", "走過的格子留火", rule="trail_surface", surfaces=["fire"], duration=2
    )
    wear(state, {"feet": [fire]})
    p = preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3)))
    assert p.trail == TrailPreview(tiles=((3, 3), (4, 3)), surface=Surface.FIRE, duration=2)


def test_api_output_carries_the_trail() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    out = path_preview_out(preview_path(state, U1, path=_path((3, 3), (4, 3), (5, 3))))
    assert out.model_dump(mode="json")["trail"] == {
        "tiles": [[3, 3], [4, 3]],
        "surface": "ice",
        "duration": 1,
    }
    plain = race_state(None, foes=((6, 6),))
    assert path_preview_out(preview_path(plain, U1, path=_path((3, 3), (4, 3)))).trail is None
