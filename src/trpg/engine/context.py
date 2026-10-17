"""``resolve`` 內部使用的結算環境：狀態複本、亂數產生器與事件收集。"""

from __future__ import annotations

from typing import Any

from trpg.content.library import Ruleset
from trpg.content.rules import CoreRules
from trpg.engine.events import EventBase
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng

__all__ = ["Ctx"]


class Ctx:
    """一次結算的工作環境。

    ``state`` 是呼叫端狀態的 **複本**，可以就地修改；``rng`` 由 ``state.rng_state`` 還原，
    結算結束時寫回（:meth:`finish_rng`）。
    """

    __slots__ = ("core", "events", "rng", "rules", "state")

    def __init__(self, state: BattleState) -> None:
        self.state = state
        self.rng = Rng.from_state(state.rng_state)
        self.events: list[EventBase] = []
        self.rules: Ruleset = state.ruleset
        self.core: CoreRules = state.ruleset.core

    def emit[E: EventBase](self, cls: type[E], **fields: Any) -> E:
        """建立事件（自動填入 ``seq`` 與 ``round``）並加入事件列表。"""
        event = cls(seq=self.state.next_event_seq, round=self.state.round, **fields)
        self.state.next_event_seq += 1
        self.events.append(event)
        return event

    def finish_rng(self) -> None:
        self.state.rng_state = self.rng.get_state()
