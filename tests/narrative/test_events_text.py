"""``trpg.narrative.events`` 的測試（Phase 3-1 3.4）：註冊表涵蓋所有事件類型。"""

from __future__ import annotations

from trpg.engine.events import EventBase
from trpg.narrative import events as narrative_events
from trpg.narrative.events import SILENT_EVENT_TYPES


def _all_event_types() -> set[type[EventBase]]:
    found: set[type[EventBase]] = set()
    stack = list(EventBase.__subclasses__())
    while stack:
        cls = stack.pop()
        found.add(cls)
        stack.extend(cls.__subclasses__())
    return found


def test_every_event_type_has_a_handler_or_is_explicitly_silent() -> None:
    handled = set(narrative_events._HANDLERS)
    silent = set(SILENT_EVENT_TYPES)
    assert not handled & silent
    missing = _all_event_types() - handled - silent
    names = sorted(c.__name__ for c in missing)
    assert not missing, f"事件類型沒有中文描述也沒有登記為靜默：{names}"


def test_source_and_rewrite_events_read_in_chinese() -> None:
    """Phase 3C-4a：源力、給予 AP、不死的紀錄文字。"""
    from tests.engine.test_source import _well_state  # noqa: PLC0415
    from trpg.engine.events import ApGranted, DeathCheated, SourceChanged  # noqa: PLC0415
    from trpg.narrative.events import describe_event  # noqa: PLC0415
    from trpg.shared.types import Pos  # noqa: PLC0415

    state = _well_state([(2, 3)])
    u1, u2 = (u.id for u in state.units_sorted())
    name = state.units[u1].name_zh
    well = SourceChanged(
        seq=0, round=1, unit_id=u1, before=1, after=2, reason="well", pos=Pos(x=2, y=3)
    )
    assert describe_event(well, state) == f"  ✦ {name} 汲取了源泉 (2, 3)：源力 1 → 2，源泉消失了"
    spent = SourceChanged(
        seq=0, round=1, unit_id=u1, before=2, after=0, reason="skill", skill_id="x"
    )
    assert describe_event(spent, state) == f"    ✦ {name} 花費源力：源力 2 → 0"
    kill = SourceChanged(
        seq=0, round=1, unit_id=u1, before=1, after=2, reason="kill_elite", other_id=u2
    )
    assert "擊倒了" in (describe_event(kill, state) or "")
    granted = ApGranted(seq=0, round=1, unit_id=u1, source_id=u1, amount=2, ap_after=4)
    assert describe_event(granted, state) == f"    {name} 獲得 2 AP（現在 4 AP）"
    later = ApGranted(seq=0, round=1, unit_id=u1, source_id=u1, amount=1, ap_after=1, deferred=True)
    assert "下次回合開始時加上" in (describe_event(later, state) or "")
    cheated = DeathCheated(seq=0, round=1, unit_id=u1, status_id="undying", prevented=3)
    assert describe_event(cheated, state) == f"  ✦ {name} 的「不死」擋下了致命傷害，HP 留在 1"
