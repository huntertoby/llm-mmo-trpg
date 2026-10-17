"""引擎 API 的回傳型別。"""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, ConfigDict

from trpg.engine.events import EventBase
from trpg.engine.state import BattleState
from trpg.shared.types import UnitId

__all__ = ["Pending", "ResolveResult"]


class Pending(BaseModel):
    """結算暫停、等待玩家決定（``prompt`` 反應）。

    以 ``resume(state, Decision(unit_id=..., accept=...))`` 繼續。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    unit_id: UnitId
    reaction: str = ""
    trigger_unit_id: UnitId | None = None


class ResolveResult(NamedTuple):
    state: BattleState
    events: list[EventBase]
    pending: Pending | None = None
