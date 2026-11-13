"""``resolve`` 內部使用的結算環境：狀態複本、亂數產生器與事件收集。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from trpg.content.library import Ruleset
from trpg.content.rules import CoreRules
from trpg.engine.events import EventBase
from trpg.engine.oath_tracking import observe_oath
from trpg.engine.skill_triggers import Fired, PassiveIndex, observe
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng
from trpg.shared.types import UnitId

__all__ = [
    "CHECK_KINDS",
    "CheckKind",
    "CheckOutcome",
    "CheckOverride",
    "CheckPoint",
    "CheckRule",
    "Ctx",
    "FixedRng",
    "GambleBranch",
    "PreviewMode",
]

type PreviewMode = Literal["min", "max"]
"""預覽模式：``min`` 為「最少後果」（傷害骰取最小、次要判定對守方有利、prompt 反應不使用），
``max`` 為「最多後果」（傷害骰取最大、次要判定對守方不利、prompt 反應使用）。"""


type GambleBranch = Literal["win", "lose"]
"""預覽時強制的賭注分支（Phase 3D-7a）：``win`` 成功、``lose`` 失敗。"""


type CheckKind = Literal["slide", "surface", "status_save", "contest"]
"""預覽可以覆寫的檢定種類（Phase 7 前置；都是「守方」的檢定，結果以守方的角度說好壞）：

- ``slide``：自己走進冰面第一格的滑行檢定（:func:`trpg.engine.ice_slide.slide_check`）；
- ``surface``：其他表面的進入檢定，例如被推、拉進冰面
  （:func:`trpg.engine.effects.handlers.enter_surface`）；
- ``status_save``：狀態的抵抗，例如陷阱的定身、技能的暈眩
  （:func:`trpg.engine.control.status_effect`）；
- ``contest``：次要的對抗判定，例如技能附帶的擊倒（:func:`trpg.engine.maneuvers.contest`；
  ``primary`` 的推擊、絆倒本身不算：預覽一律視為成功，成功率另外計算）。
"""

CHECK_KINDS: tuple[CheckKind, ...] = ("slide", "surface", "status_save", "contest")

type CheckOutcome = Literal["best", "worst"]
"""一次檢定對守方的結果：``best`` 對守方最有利（滑行通過、抵抗成功），``worst`` 最不利。
與預覽模式相同的語意：``min`` 一律 ``best``、``max`` 一律 ``worst``。"""


@dataclass(frozen=True, slots=True)
class CheckPoint:
    """預覽模擬中擲過的一次檢定（依擲的順序記在 :attr:`Ctx.check_log`）。"""

    kind: CheckKind
    reason: str
    """檢定的來源：表面為 ``surface:<表面>``、狀態為 ``status:<狀態>``、對抗為
    ``contest:<種類>``。"""
    unit_id: UnitId | None
    """守方（檢定的對象）。"""
    outcome: CheckOutcome
    """這次模擬採用的結果（覆寫指定的，或照預覽模式）。"""
    forced: bool
    """結果由 :class:`CheckOverride` 指定（``False`` 為照預覽模式）。"""


@dataclass(frozen=True, slots=True)
class CheckRule:
    """一條覆寫規則：符合 ``kinds``（``None`` 為全部種類）與 ``reason``（``None`` 為不限）的檢定，
    依「符合這條規則的第幾次（0 起）」指定結果。

    - ``outcomes``：第 ``i`` 次的結果；
    - ``rest``：超出 ``outcomes`` 的：``best``／``worst`` 一律指定、``None`` 照預覽模式。
    """

    kinds: tuple[CheckKind, ...] | None = None
    reason: str | None = None
    outcomes: tuple[CheckOutcome, ...] = ()
    rest: CheckOutcome | None = None

    def matches(self, kind: CheckKind, reason: str) -> bool:
        if self.kinds is not None and kind not in self.kinds:
            return False
        return self.reason is None or self.reason == reason

    def outcome(self, index: int) -> CheckOutcome | None:
        """第 ``index`` 次的指定結果；``None`` 為不指定（照預覽模式）。"""
        return self.outcomes[index] if index < len(self.outcomes) else self.rest


@dataclass(frozen=True, slots=True)
class CheckOverride:
    """純預覽用的檢定結果覆寫（Phase 7 前置；由 Phase 6P-1 的 ``SlideOverride`` 泛化）。

    每次檢定依序比對 ``rules``，由 **第一條** 符合的規則決定（也只有那一條計數）；沒有規則符合、
    或規則沒有指定這一次時照預覽模式（``min``／``max``）。正式結算不能使用（:class:`Ctx` 拒絕）。
    指定的結果走與 :meth:`Ctx.check_d20` 相同的 d20 語意：守方自己擲的檢定 ``best`` 為 20、
    ``worst`` 為 1；攻方擲、守方抵抗的（:meth:`Ctx.opposed_d20`）反過來。
    """

    rules: tuple[CheckRule, ...] = ()

    @classmethod
    def of(
        cls,
        kinds: tuple[CheckKind, ...] | None = None,
        *,
        reason: str | None = None,
        outcomes: tuple[CheckOutcome, ...] = (),
        rest: CheckOutcome | None = None,
    ) -> CheckOverride:
        """只有一條規則的覆寫。"""
        return cls((CheckRule(kinds, reason, outcomes, rest),))

    @classmethod
    def worst_at(
        cls,
        index: int,
        kinds: tuple[CheckKind, ...] | None = None,
        *,
        rest: CheckOutcome | None = None,
    ) -> CheckOverride:
        """符合 ``kinds`` 的第 ``index`` 次最差、之前的最好，之後照 ``rest``。"""
        outcomes: tuple[CheckOutcome, ...] = tuple(
            "worst" if i == index else "best" for i in range(index + 1)
        )
        return cls.of(kinds, outcomes=outcomes, rest=rest)


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
    - ``gamble``：預覽時強制的賭注分支（Phase 3D-7a）。
    - ``surface_entries``：等待觸發的「表面出現在腳下」進入效果
      （見 :mod:`trpg.engine.effects.queue`）。
    - ``trap_entries``：等待結算的陷阱進入（Phase 2E-3）。
    - ``zone_entries``：等待結算的區域進入（Phase 3D-5）。
    - 被動技能的觸發（見 :mod:`trpg.engine.skill_triggers`）：``fired`` 是收集到、尚未結算的觸發；
      ``trigger_depth`` 是目前正在結算的觸發深度（動作本身為 0）；``trigger_hold`` 大於 0 時暫不
      結算（施放技能、一次普攻的期間）；``settling`` 表示正在結算觸發（不重入）；
      ``passives`` 是被動技能的索引（第一次需要時建立）。
    - ``downed``：剛倒下、尚未讓友方反應（``ally_downed``，Phase 3D-3）的單位；與觸發一起在
      :func:`~trpg.engine.skill_triggers.settle` 處理。
    """

    __slots__ = (
        "branched",
        "check_counts",
        "check_log",
        "check_override",
        "core",
        "decisions",
        "downed",
        "events",
        "fire_lock",
        "fired",
        "gamble",
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
        "zone_entries",
    )

    def __init__(
        self,
        state: BattleState,
        *,
        decisions: tuple[bool, ...] = (),
        preview: PreviewMode | None = None,
        gamble: GambleBranch | None = None,
        check_override: CheckOverride | None = None,
        fire_lock: bool = False,
    ) -> None:
        if check_override is not None and preview is None:
            raise ValueError("check_override 只能用在預覽模擬")
        if fire_lock and preview is None:
            raise ValueError("fire_lock 只能用在預覽模擬")
        self.state = state
        self.rng: Rng = Rng.from_state(state.rng_state) if preview is None else FixedRng(preview)
        self.events: list[EventBase] = []
        self.rules: Ruleset = state.ruleset
        self.core: CoreRules = state.ruleset.core
        self.decisions = list(decisions)
        self.preview = preview
        self.gamble = gamble
        """預覽時強制的賭注分支（Phase 3D-7a）；預覽沒有指定時賭注不結算（``None``）。正式結算
        不使用（擲 d1000）。"""
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
        self.check_override = check_override
        """預覽的檢定結果覆寫（:class:`CheckOverride`；Phase 6P-1 的冰面覆寫泛化而來）；正式結算
        固定為 ``None``。"""
        self.check_counts = [0] * (len(check_override.rules) if check_override else 0)
        """每條覆寫規則已符合的檢定次數。"""
        self.check_log: list[CheckPoint] = []
        """預覽模擬擲過的檢定（依序；正式結算不記）。分支推演用它找分歧點
        （:mod:`trpg.engine.branching`）。"""
        self.fire_lock = fire_lock
        """AI 估值用的預覽（RG-1）：瞄準預告的技能假設「現在就射出」（照一般施放結算），
        :attr:`trpg.engine.preview.Preview.lock_fire`。正式結算固定為 ``False``。"""
        self.zone_entries: list[tuple[int, UnitId]] = []
        """單位進入持續區域：``(區域, 單位)``，效果佇列清空時（陷阱之後）依記錄順序結算
        （Phase 3D-5，:mod:`trpg.engine.zones`）。"""

    def emit[E: EventBase](self, cls: type[E], **fields: Any) -> E:
        """建立事件（自動填入 ``seq`` 與 ``round``）並加入事件列表。"""
        event = cls(seq=self.state.next_event_seq, round=self.state.round, **fields)
        self.state.next_event_seq += 1
        self.events.append(event)
        observe(self, event)
        observe_oath(self, event)  # 誓約的違反判定（Phase 5C-3）
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

    def _check(self, kind: CheckKind, reason: str, unit_id: UnitId | None) -> CheckOutcome | None:
        """預覽時這次檢定的結果（覆寫指定的，或照預覽模式）並記進 :attr:`check_log`；正式結算為
        ``None``（擲骰）。"""
        if self.preview is None:
            return None
        self.branched = True
        forced = self._forced(kind, reason)
        outcome: CheckOutcome = forced or ("best" if self.preview == "min" else "worst")
        self.check_log.append(CheckPoint(kind, reason, unit_id, outcome, forced is not None))
        return outcome

    def _forced(self, kind: CheckKind, reason: str) -> CheckOutcome | None:
        override = self.check_override
        if override is None:
            return None
        for i, rule in enumerate(override.rules):
            if rule.matches(kind, reason):
                index = self.check_counts[i]
                self.check_counts[i] += 1
                return rule.outcome(index)
        return None

    def check_d20(self, kind: CheckKind, reason: str, unit_id: UnitId | None = None) -> int:
        """守方自己擲的檢定骰（例如冰面滑倒）：預覽 ``min``（或覆寫 ``best``）回傳 20（通過，沒有
        後果）、``max``（或 ``worst``）回傳 1；正式結算擲 d20。"""
        outcome = self._check(kind, reason, unit_id)
        if outcome is None:
            return self.rng.d20()
        return 20 if outcome == "best" else 1

    def opposed_d20(self, kind: CheckKind, reason: str, unit_id: UnitId | None = None) -> int:
        """攻方擲、守方抵抗的 d20（狀態抵抗、次要對抗）：預覽 ``min``（守方 ``best``）回傳 1、
        ``max``（``worst``）回傳 20；正式結算擲 d20。"""
        outcome = self._check(kind, reason, unit_id)
        if outcome is None:
            return self.rng.d20()
        return 1 if outcome == "best" else 20
