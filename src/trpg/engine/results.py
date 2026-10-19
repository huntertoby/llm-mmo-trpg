"""引擎 API 的回傳型別。"""

from __future__ import annotations

from typing import Literal, NamedTuple

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

    kind: Literal["reaction"]
    unit_id: UnitId
    reaction: str = ""
    trigger_unit_id: UnitId | None = None
    skill_id: str | None = None
    """以反應技回應時為該技能 ID；一般（內建）反應規則為 ``None``。"""
    trigger_event_seq: int | None = None
    """引發這次詢問的事件 ``seq``（格擋類為擊中判定 ``attack_rolled``、反應技為造成傷害的
    ``damage_dealt`` 或攻擊判定；``enemy_leaves_adjacent`` 的移動事件尚未發出，為 ``None``）。"""
    stamina_cost: int = 0
    """接受時要付出的耐力（內建反應）。"""
    mana_cost: int = 0
    """接受時要付出的法力（反應技）。"""
    hp_cost_permille: int = 0
    """接受時要付出的最大 HP 千分比（反應技的 ``hp_percent``）。"""


class ResolveResult(NamedTuple):
    state: BattleState
    events: list[EventBase]
    pending: Pending | None = None
