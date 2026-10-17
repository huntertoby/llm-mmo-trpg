"""``resolve`` 內部使用的結算環境：狀態複本、亂數產生器與事件收集。"""

from __future__ import annotations

from typing import Any, Literal

from trpg.content.library import Ruleset
from trpg.content.rules import CoreRules
from trpg.engine.events import EventBase
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng
from trpg.shared.types import UnitId

__all__ = ["Ctx", "FixedRng", "PreviewMode"]

type PreviewMode = Literal["min", "max"]
"""預覽模式：``min`` 為「最少後果」（傷害骰取最小、次要判定對守方有利、prompt 反應不使用），
``max`` 為「最多後果」（傷害骰取最大、次要判定對守方不利、prompt 反應使用）。"""


class FixedRng(Rng):
    """預覽用的亂數：``randint`` 一律回傳下限（``min``）或上限（``max``）。"""

    __slots__ = ("_mode",)

    def __init__(self, mode: PreviewMode) -> None:
        super().__init__(0)
        self._mode = mode

    def randint(self, lo: int, hi: int) -> int:
        return lo if self._mode == "min" else hi


class Ctx:
    """一次結算的工作環境。

    ``state`` 是呼叫端狀態的 **複本**，可以就地修改；``rng`` 由 ``state.rng_state`` 還原，
    結算結束時寫回（:meth:`finish_rng`）。

    - ``decisions``：``prompt`` 反應的決定（依詢問順序消耗，見 :mod:`trpg.engine.reactions`）。
    - ``preview``：預覽模式（``None`` 為正式結算）。
    - ``surface_entries``：等待觸發的「表面出現在腳下」進入效果
      （見 :mod:`trpg.engine.effects.queue`）。
    """

    __slots__ = (
        "core",
        "decisions",
        "events",
        "preview",
        "rng",
        "rules",
        "state",
        "surface_entries",
    )

    def __init__(
        self,
        state: BattleState,
        *,
        decisions: tuple[bool, ...] = (),
        preview: PreviewMode | None = None,
    ) -> None:
        self.state = state
        self.rng: Rng = Rng.from_state(state.rng_state) if preview is None else FixedRng(preview)
        self.events: list[EventBase] = []
        self.rules: Ruleset = state.ruleset
        self.core: CoreRules = state.ruleset.core
        self.decisions = list(decisions)
        self.preview = preview
        self.surface_entries: list[tuple[UnitId, tuple[int, int], int]] = []
        """表面在單位腳下被建立或改變：``(單位, 格子, 深度)``，由效果佇列在清空前依單位 ID
        觸發進入效果（Phase 1C 決定 #6）。"""

    def emit[E: EventBase](self, cls: type[E], **fields: Any) -> E:
        """建立事件（自動填入 ``seq`` 與 ``round``）並加入事件列表。"""
        event = cls(seq=self.state.next_event_seq, round=self.state.round, **fields)
        self.state.next_event_seq += 1
        self.events.append(event)
        return event

    def finish_rng(self) -> None:
        if self.preview is None:
            self.state.rng_state = self.rng.get_state()

    def check_d20(self) -> int:
        """守方的檢定骰（例如冰面滑倒）：預覽 ``min`` 回傳 20（通過，沒有後果）、``max`` 回傳 1。"""
        if self.preview == "min":
            return 20
        if self.preview == "max":
            return 1
        return self.rng.d20()
