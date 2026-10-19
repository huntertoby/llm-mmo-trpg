"""召喚的紀錄文字（Phase 3D-4a）。"""

from __future__ import annotations

from tests.engine.test_summons import arena, cast, end, summon_skill
from tests.engine.test_totem import TOTEM
from tests.engine.test_totem import arena as totem_arena
from trpg.cli.render import (
    render_battle_grid,
    render_legend,
    render_unit_table,
    unit_markers,
)
from trpg.engine.events import EventBase, SummonExpired, TotemPulsed, UnitSummoned
from trpg.narrative.events import describe_event


def test_summon_and_expiry_have_log_lines() -> None:
    result = cast(arena(summon_skill(duration=1)), 2, 3)
    [summoned] = [e for e in result.events if isinstance(e, UnitSummoned)]
    text = describe_event(summoned, result.state)
    assert text is not None and "召喚了 骷髏戰士1" in text and "(2, 3)" in text
    state = result.state
    events: list[EventBase] = []
    while not any(isinstance(e, SummonExpired) for e in events):
        step = end(state)
        state, events = step.state, [*events, *step.events]
    [gone] = [e for e in events if isinstance(e, SummonExpired)]
    assert describe_event(gone, state) == "  時間到了：骷髏戰士1 消失了"


def test_the_totem_pulse_and_cli_marks_summons() -> None:
    state = cast(totem_arena(), 2, 3).state
    result = end(state)
    [pulse] = [e for e in result.events if isinstance(e, TotemPulsed)]
    text = describe_event(pulse, result.state)
    assert text is not None and "戰意圖騰1 散發光環（2 格內）" in text and "獲得「激昂」" in text
    state = result.state
    [totem] = [u for u in state.units_sorted() if u.template_id == TOTEM]
    # 召喚物用數字代號，不佔用隊伍字母；單位表標明召喚者與到期輪；圖例說明數字
    assert unit_markers(state)[totem.id] == "1"
    assert "01 " in render_battle_grid(state)  # 高度 0 ＋ 代號 1 ＋ 無表面
    assert "1–9 召喚物" in render_legend(state)
    row = next(line for line in render_unit_table(state).splitlines() if "戰意圖騰1" in line)
    assert row.lstrip().startswith("1 ") and "圖騰：" in row and "第 4 輪結束時消失" in row
