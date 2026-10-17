"""單位倒下與先攻順序維護（效果處理器與回合流程共用）。"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, UnitDowned
from trpg.engine.state import UnitState

__all__ = ["down_unit"]


def down_unit(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """單位倒下（HP ≤ 0）：標記倒下、立即移出先攻順序，產生 ``unit_downed``。

    若倒下的是目前行動者，``active_unit`` 設為 ``None``，``turn_pos`` 保持不變
    （此時指向順序中的下一位），由回合流程接著開始下一位的回合。
    """
    if unit.downed:
        return []
    unit.downed = True
    unit.hp = 0
    unit.ap = 0
    unit.move_points = 0
    state = ctx.state
    if unit.id in state.turn_order:
        index = state.turn_order.index(unit.id)
        state.turn_order.pop(index)
        if state.active_unit == unit.id:
            state.active_unit = None
        elif index < state.turn_pos:
            state.turn_pos -= 1
    return [ctx.emit(UnitDowned, unit_id=unit.id)]
