"""戰術指令（``docs/design/05-戰鬥.md`` 5.9.1；Phase 2C-2）。

指揮官（腳本，Phase 3 起也可以是 LLM）只能下「提議」：指令只有目標與格子，沒有任何數值、
骰子或結果欄位。效用 AI 把有效的指令轉成評分加成（數值在 ``content/ai_profiles.yaml`` 的
``orders:``），不改變合法動作；無效指令一律忽略。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_standable
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

__all__ = [
    "ORDER_ADAPTER",
    "FocusTarget",
    "HoldPosition",
    "IgnoredOrder",
    "OrderRecord",
    "OrderSet",
    "Protect",
    "RetreatTo",
    "TacticalOrder",
    "UseEnvironment",
    "validate_order",
]


class _OrderBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FocusTarget(_OrderBase):
    """集火指定敵人。"""

    kind: Literal["focus_target"] = "focus_target"
    target: UnitId


class HoldPosition(_OrderBase):
    """守在指定格子附近。"""

    kind: Literal["hold_position"] = "hold_position"
    at: XY
    radius: int = Field(default=1, ge=0, le=3)


class RetreatTo(_OrderBase):
    """撤往指定格子。"""

    kind: Literal["retreat_to"] = "retreat_to"
    at: XY


class Protect(_OrderBase):
    """保護指定友方。"""

    kind: Literal["protect"] = "protect"
    ward: UnitId


class UseEnvironment(_OrderBase):
    """優先利用環境（爆炸、推落、表面）。"""

    kind: Literal["use_environment"] = "use_environment"


type TacticalOrder = Annotated[
    FocusTarget | HoldPosition | RetreatTo | Protect | UseEnvironment, Field(discriminator="kind")
]

ORDER_ADAPTER: TypeAdapter[TacticalOrder] = TypeAdapter(TacticalOrder)


def _check_unique_kinds(orders: tuple[TacticalOrder, ...], where: str) -> None:
    kinds = [o.kind for o in orders]
    dup = sorted({k for k in kinds if kinds.count(k) > 1})
    if dup:
        raise ValueError(f"{where}的指令種類重複：{', '.join(dup)}")


class OrderSet(_OrderBase):
    """一個陣營目前的指令。單位有自己的指令時，**完全取代** 陣營指令。每種 ``kind`` 最多一個。"""

    team_orders: tuple[TacticalOrder, ...] = ()
    unit_orders: dict[UnitId, tuple[TacticalOrder, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> OrderSet:
        _check_unique_kinds(self.team_orders, "陣營")
        for uid, orders in self.unit_orders.items():
            _check_unique_kinds(orders, f"單位 {uid} ")
        return self

    def for_unit(self, unit_id: UnitId) -> tuple[TacticalOrder, ...]:
        """單位適用的指令：有自己的指令（即使是空的）就完全取代陣營指令。"""
        own = self.unit_orders.get(unit_id)
        return self.team_orders if own is None else own

    @property
    def empty(self) -> bool:
        return not self.team_orders and not any(self.unit_orders.values())


class IgnoredOrder(_OrderBase):
    """被忽略的指令與原因。``scope`` 為 ``"team"`` 或單位 ID。"""

    scope: str
    order: TacticalOrder
    reason: str


class OrderRecord(_OrderBase):
    """指揮官下達指令的紀錄（寫入 ``BattleLog.orders``）。"""

    round: int
    team: Team
    orders: OrderSet
    ignored: tuple[IgnoredOrder, ...] = ()


def _standable_problem(state: BattleState, at: XY) -> str | None:
    if not state.in_bounds(*at):
        return f"格子 {at} 超出地圖"
    if not is_standable(state, at):
        return f"格子 {at} 無法站立"
    return None


def validate_order(state: BattleState, team: Team, order: TacticalOrder) -> str | None:
    """指令無效的原因；有效時回傳 ``None``。"""
    problem: str | None = None
    match order:
        case FocusTarget(target=target):
            unit = state.units.get(target)
            if unit is None:
                problem = f"目標 {target} 不存在"
            elif not unit.alive:
                problem = f"目標 {target} 已倒下"
            elif unit.team is team:
                problem = f"目標 {target} 不是敵人"
        case Protect(ward=ward):
            unit = state.units.get(ward)
            if unit is None:
                problem = f"保護對象 {ward} 不存在"
            elif not unit.alive:
                problem = f"保護對象 {ward} 已倒下"
            elif unit.team is not team:
                problem = f"保護對象 {ward} 不是友方"
        case HoldPosition(at=at) | RetreatTo(at=at):
            problem = _standable_problem(state, at)
        case UseEnvironment():
            pass
    return problem
