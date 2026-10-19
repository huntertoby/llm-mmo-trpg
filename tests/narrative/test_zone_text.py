"""持續區域的紀錄、CLI 與技能說明文字（Phase 3D-5）。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.test_zones import MOVING, U2, arena, cast, ctx_run, of
from trpg.cli.render import render_battle_grid, render_legend, render_telegraph, render_unit_table
from trpg.engine.environment import run_environment, telegraph
from trpg.engine.events import ZoneCreated, ZoneExpired, ZoneMoved, ZoneTriggered
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary


def test_zone_events_have_log_lines() -> None:
    result = cast(arena(MOVING, foes=((4, 3),)), direction="east")
    state = result.state
    [created] = of(result, ZoneCreated)
    text = describe_event(created, state)
    assert text is not None and "展開持續區域「測試技 t_zone」：(1, 3)、(2, 3)" in text
    assert "每次環境回合向東前進 1 格" in text and "回合結束時消失" in text
    state, events = ctx_run(state, run_environment)
    [moved] = of(events, ZoneMoved)
    assert describe_event(moved, state) == "  「測試技 t_zone」區域向東前進：(2, 3)、(3, 3)"
    state, events = ctx_run(state, run_environment)
    [hit] = of(events, ZoneTriggered)
    assert hit.unit_id == U2
    assert describe_event(hit, state) == "  ◇ 盜賊 進入「測試技 t_zone」區域（深度 1）"
    state.round = state.zones[0].expires_round
    _, events = ctx_run(state, run_environment)
    [gone] = of(events, ZoneExpired)
    assert describe_event(gone, state) == "  時間到了：法師 的「測試技 t_zone」區域消失了"


def test_the_cli_marks_zones_and_forecasts_their_move() -> None:
    state = cast(arena(MOVING), direction="east").state
    rows = render_battle_grid(state).splitlines()
    assert rows[4].startswith(" 3  0A  0!  0!  0. ")  # 第 3 列：施放者、兩格區域
    assert "! 持續區域" in render_legend(state)
    table = render_unit_table(state)
    assert "! 區域「測試技 t_zone」（法師，影響敵方，每次環境回合向東前進 1 格" in table
    assert "本輪結束時向東移到 (2, 3)、(3, 3)" in table
    forecast = render_telegraph(state, telegraph(state))
    assert "「測試技 t_zone」區域將向東前進到 (2, 3)、(3, 3)" in forecast


def test_skill_cards_describe_the_demo_zones() -> None:
    lib = library()
    wall = lib.skills["skill_fire_wall"]
    hymn = lib.skills["skill_war_hymn"]
    wall_text = effect_summary(lib, wall, wall.effects[0])
    assert wall_text.startswith("建立持續 2 輪的區域（每次環境回合向施放方向前進 1 格）")
    assert "敵人進入區域或在區域內開始回合時" in wall_text and "留下「火焰」" in wall_text
    hymn_text = effect_summary(lib, hymn, hymn.effects[0])
    assert hymn_text.startswith("建立持續 3 輪的區域（跟著你移動）：友方")
    assert "激昂" in hymn_text and "（友方）" not in hymn_text
