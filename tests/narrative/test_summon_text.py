"""召喚的紀錄文字（Phase 3D-4a）。"""

from __future__ import annotations

from tests.engine.test_summons import arena, cast, end, summon_skill
from trpg.engine.events import EventBase, SummonExpired, UnitSummoned
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
