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
