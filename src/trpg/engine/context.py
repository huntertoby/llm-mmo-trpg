"""``resolve`` 內部使用的結算環境：狀態複本、亂數產生器與事件收集。"""

from __future__ import annotations

from typing import Any, Literal

from trpg.content.library import Ruleset
from trpg.content.rules import CoreRules
from trpg.engine.events import EventBase
from trpg.engine.skill_triggers import Fired, PassiveIndex, observe
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng
from trpg.shared.types import UnitId

__all__ = ["Ctx", "FixedRng", "PreviewMode"]

type PreviewMode = Literal["min", "max"]
"""預覽模式：``min`` 為「最少後果」（傷害骰取最小、次要判定對守方有利、prompt 反應不使用），
``max`` 為「最多後果」（傷害骰取最大、次要判定對守方不利、prompt 反應使用）。"""


class FixedRng(Rng):
    """預覽用的亂數：``randint`` 一律回傳下限（``min``）或上限（``max``）。

    ``used`` 記錄是否被呼叫過（``lo < hi`` 時 ``min`` 與 ``max`` 的結果才會不同）。
    """

    __slots__ = ("_mode", "used")

    def __init__(self, mode: PreviewMode) -> None:
        super().__init__(0)
        self._mode = mode
        self.used = False

    def randint(self, lo: int, hi: int) -> int:
        if lo < hi:
            self.used = True
        return lo if self._mode == "min" else hi


class Ctx:
    """一次結算的工作環境。

    ``state`` 是呼叫端狀態的 **複本**，可以就地修改；``rng`` 由 ``state.rng_state`` 還原，
    結算結束時寫回（:meth:`finish_rng`）。

    - ``decisions``：``prompt`` 反應的決定（依詢問順序消耗，見 :mod:`trpg.engine.reactions`）。
    - ``preview``：預覽模式（``None`` 為正式結算）。
    - ``surface_entries``：等待觸發的「表面出現在腳下」進入效果
      （見 :mod:`trpg.engine.effects.queue`）。
    - ``trap_entries``：等待結算的陷阱進入（Phase 2E-3）。
    - 被動技能的觸發（見 :mod:`trpg.engine.skill_triggers`）：``fired`` 是收集到、尚未結算的觸發；
      ``trigger_depth`` 是目前正在結算的觸發深度（動作本身為 0）；``trigger_hold`` 大於 0 時暫不
      結算（施放技能、一次普攻的期間）；``settling`` 表示正在結算觸發（不重入）；
      ``passives`` 是被動技能的索引（第一次需要時建立）。
    - ``downed``：剛倒下、尚未讓友方反應（``ally_downed``，Phase 3D-3）的單位；與觸發一起在
      :func:`~trpg.engine.skill_triggers.settle` 處理。
    """

    __slots__ = (
        "branched",
        "core",
        "decisions",
        "downed",
        "events",
        "fired",
        "passives",
        "preview",
        "rng",
        "rules",
        "settling",
        "state",
        "surface_entries",
        "trap_entries",
        "trigger_depth",
        "trigger_hold",
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
        self.branched = False
        """預覽模式下是否經過任何「``min`` 與 ``max`` 會不同」的分歧點（擲骰、檢定、反應決定、
        強制命中結果）。沒有時兩種模式的結果完全相同，``preview`` 只需模擬一次。"""
        self.fired: list[Fired] = []
        self.downed: list[UnitId] = []
        self.trigger_depth = 0
        self.trigger_hold = 0
        self.settling = False
        self.passives: PassiveIndex | None = None
        self.surface_entries: list[tuple[UnitId, tuple[int, int], int]] = []
        """表面在單位腳下被建立或改變：``(單位, 格子, 深度)``，由效果佇列在清空前依單位 ID
        觸發進入效果（Phase 1C 決定 #6）。"""
        self.trap_entries: list[tuple[UnitId, tuple[int, int]]] = []
        """單位（主動或強制移動）進入敵方陷阱格：``(單位, 格子)``，效果佇列清空時依記錄順序
        結算（Phase 2E-3，:mod:`trpg.engine.traps`）。"""

    def emit[E: EventBase](self, cls: type[E], **fields: Any) -> E:
        """建立事件（自動填入 ``seq`` 與 ``round``）並加入事件列表。"""
        event = cls(seq=self.state.next_event_seq, round=self.state.round, **fields)
        self.state.next_event_seq += 1
        self.events.append(event)
        observe(self, event)
        return event

    def finish_rng(self) -> None:
        if self.preview is None:
            self.state.rng_state = self.rng.get_state()

    def mark_branch(self) -> None:
        """預覽模式下標記一個分歧點（見 :attr:`branched`）。"""
        if self.preview is not None:
            self.branched = True

    def preview_branched(self) -> bool:
        """這次預覽模擬的 ``min`` 與 ``max`` 結果是否可能不同。"""
        rng = self.rng
        return self.branched or (isinstance(rng, FixedRng) and rng.used)

    def check_d20(self) -> int:
        """守方的檢定骰（例如冰面滑倒）：預覽 ``min`` 回傳 20（通過，沒有後果）、``max`` 回傳 1。"""
        if self.preview is not None:
            self.branched = True
        if self.preview == "min":
            return 20
        if self.preview == "max":
            return 1
        return self.rng.d20()
