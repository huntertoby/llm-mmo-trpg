"""指揮官與 :class:`CommandedAI`（Phase 2C-2；``docs/design/05-戰鬥.md`` 5.9.1）。

指揮官 ``(狀態, 陣營) -> OrderSet | None`` 在戰況變化時下達戰術指令（``None`` ＝ 沿用上一個），
:class:`CommandedAI` 把指令交給效用 AI 轉成評分加成。LLM 指揮官（Phase 3）接同一個介面。
引擎內只有這個包裝器，腳本指揮官放在 ``trpg.sim.commanders``。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from trpg.engine.actions import Action
from trpg.engine.ai.orders import IgnoredOrder, OrderRecord, OrderSet, TacticalOrder, validate_order
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

__all__ = ["CommandedAI", "Commander", "OrderLogging", "OrderObserver", "ignored_orders"]

type Commander = Callable[[BattleState, Team], OrderSet | None]
"""指揮官：回傳 ``None`` 表示沿用上一個指令。"""

type OrderObserver = Callable[[OrderRecord, BattleState], None]
"""指令下達時的回呼（CLI 即時印出）。"""


@runtime_checkable
class OrderLogging(Protocol):
    """會記錄指令的 policy（``run_battle`` 據此把指令寫進 ``BattleRun.orders``）。"""

    @property
    def order_log(self) -> list[OrderRecord]: ...


class CommandedAI:
    """可當作 ``Policy``：效用 AI ＋ 各陣營的指揮官。

    **呼叫時機**：某陣營在每一輪的第一次決策，以及該陣營看到的存活單位數（目前沒有視野過濾：
    敵我全體）自上次呼叫後有變化時。沒有指揮官的陣營不受影響。指令在下達時驗證一次（無效者
    記入 ``ignored``）；每次決策時再驗證一次（目標之後倒下就悄悄忽略），所以無效指令的行為與
    沒有那條指令完全相同。
    """

    def __init__(
        self,
        ai: UtilityAI,
        commanders: Mapping[Team, Commander],
        *,
        on_order: OrderObserver | None = None,
    ) -> None:
        self.ai = ai
        self.commanders = dict(commanders)
        self.on_order = on_order
        self.order_log: list[OrderRecord] = []
        self._current: dict[Team, OrderSet] = {}
        self._called_round: dict[Team, int] = {}
        self._called_counts: dict[Team, tuple[int, int]] = {}
        ai.orders = self._orders_for

    def _orders_for(self, state: BattleState, unit_id: UnitId) -> tuple[TacticalOrder, ...]:
        current = self._current.get(state.units[unit_id].team)
        return () if current is None else current.for_unit(unit_id)

    def _consult(self, state: BattleState, team: Team) -> None:
        commander = self.commanders.get(team)
        if commander is None:
            return
        counts = (
            sum(1 for u in state.living_units() if u.team is team),
            sum(1 for u in state.living_units() if u.team is not team),
        )
        if self._called_round.get(team) == state.round and self._called_counts.get(team) == counts:
            return
        self._called_round[team] = state.round
        self._called_counts[team] = counts
        issued = commander(state, team)
        if issued is None:
            return
        self.issue(state, team, issued)

    def issue(self, state: BattleState, team: Team, orders: OrderSet) -> OrderRecord:
        """直接下達 ``team`` 的指令（下一次該陣營的決策即生效），並記入 ``order_log``。

        指揮官的指令也經過這裡；玩家操控的陣營（網頁 API 的隊友快捷指令）不註冊指揮官，
        直接呼叫本方法。無效的指令照常記入 ``ignored``。
        """
        self._current[team] = orders
        record = OrderRecord(
            round=state.round, team=team, orders=orders, ignored=_ignored(state, team, orders)
        )
        self.order_log.append(record)
        if self.on_order is not None:
            self.on_order(record, state)
        return record

    def restore_orders(self, records: list[OrderRecord]) -> None:
        """讀檔（Phase 3-5a）：以存下的指令紀錄還原 ``order_log`` 與各陣營目前的指令（每個陣營
        最後一筆）。不呼叫 ``on_order``，也不重新驗證（``ignored`` 照存檔）。效用 AI 本身沒有其他
        跨決策的狀態，所以還原後的決策與沒有中斷時相同。"""
        self.order_log = list(records)
        self._current = {}
        for record in records:
            self._current[record.team] = record.orders

    def current_orders(self, team: Team) -> OrderSet:
        """``team`` 目前的指令（沒有時為空的 :class:`OrderSet`）。"""
        return self._current.get(team, OrderSet())

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        self._consult(state, unit.team)
        return self.ai(state)


def ignored_orders(state: BattleState, team: Team, orders: OrderSet) -> tuple[IgnoredOrder, ...]:
    """``orders`` 在 ``state`` 中無法執行的指令與原因（AI 會略過；網頁側欄顯示用）。"""
    return _ignored(state, team, orders)


def _ignored(state: BattleState, team: Team, orders: OrderSet) -> tuple[IgnoredOrder, ...]:
    result: list[IgnoredOrder] = []
    for order in orders.team_orders:
        reason = validate_order(state, team, order)
        if reason is not None:
            result.append(IgnoredOrder(scope="team", order=order, reason=reason))
    for uid in sorted(orders.unit_orders):
        for order in orders.unit_orders[uid]:
            reason = validate_order(state, team, order)
            if reason is None and uid not in state.units:
                reason = f"單位 {uid} 不存在"
            if reason is not None:
                result.append(IgnoredOrder(scope=uid, order=order, reason=reason))
    return tuple(result)
