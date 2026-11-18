"""戰前佈置事件（SK-3，``docs/design/06-技能.md`` 6.38 第 11 點；:mod:`trpg.engine.prep`）。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import EventBase
from trpg.shared.types import Pos, UnitId


class PrepPlaced(EventBase):
    """``unit_id`` 開戰前用 ``skill_id`` 在我方起始區的 ``pos`` 放了 1 個 ``kind``（陷阱、刻印、
    表面）；緊接著是那件事本身的事件（``trap_placed``／``rune_inscribed``／``surface_changed``）與
    冷卻。陷阱的佈置對方看不到（:mod:`trpg.engine.event_filter`）。"""

    type: Literal["prep_placed"] = "prep_placed"
    unit_id: UnitId
    skill_id: str
    kind: Literal["trap", "rune", "surface"]
    pos: Pos


class PrepSkipped(EventBase):
    """``unit_id`` 開戰前不佈置、直接開戰。"""

    type: Literal["prep_skipped"] = "prep_skipped"
    unit_id: UnitId
