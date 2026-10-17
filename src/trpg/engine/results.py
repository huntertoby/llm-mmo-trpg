"""引擎 API 的回傳型別。"""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, ConfigDict

from trpg.engine.events import EventBase
from trpg.engine.state import BattleState

__all__ = ["Pending", "ResolveResult"]


class Pending(BaseModel):
    """結算暫停、等待玩家決定（Phase 1B 的 ``prompt`` 反應使用；1A 一律為 ``None``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    unit_id: str


class ResolveResult(NamedTuple):
    state: BattleState
    events: list[EventBase]
    pending: Pending | None = None
