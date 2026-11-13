"""表面的進入效果與檢定的屬性修正（Phase R3 自 :mod:`trpg.engine.effects.handlers` 抽出）。

效果佇列（:mod:`trpg.engine.effects.queue`）在清空前要觸發「表面出現在腳下」的進入效果
（:func:`enter_surface`），而處理器模組會向佇列註冊處理器；放在這裡，佇列可以在模組頂端匯入，
不必延後匯入處理器模組。:mod:`trpg.engine.effects.handlers` 照舊轉出這兩個函式。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import CheckRolled, EventBase, SurfaceEntered
from trpg.engine.rules.movement import is_flying
from trpg.engine.rules.race import slip_immune
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.state import UnitState
from trpg.shared.types import Surface

__all__ = ["ability_modifier", "enter_surface"]


def ability_modifier(ctx: Ctx, value: int) -> int:
    """檢定的屬性修正：``(屬性 − ability_mod_base) // ability_mod_divisor``。"""
    return (value - ctx.core.ability_mod_base) // ctx.core.ability_mod_divisor


def enter_surface(ctx: Ctx, unit: UnitState, *, own_move: bool = False) -> list[EventBase]:
    """``unit`` 所在格表面的進入效果：``surface_entered``（套用狀態），有檢定時擲骰
    （``check_rolled``）。走進表面、被推進表面，以及表面出現在腳下時都會呼叫。

    ``own_move``（自己走進、滑行進來）時，會滑行的檢定（``slide_max > 0``，冰面 #123）不在這裡擲：
    由 :func:`trpg.engine.ice_slide.slide_check` 在一段的第一格擲一次。"""
    surface = ctx.state.tile(*unit.xy).surface
    if surface is Surface.NONE or is_flying(unit):  # 會飛的單位不受地面表面影響（3-33e2b）
        return []
    if unit.footprint > 1:  # 巨型單位（GB-1a，T10）：不觸發表面的進入效果
        return []
    definition = ctx.rules.surface_def(surface)
    if definition.on_enter is None:
        return []
    events: list[EventBase] = [
        ctx.emit(SurfaceEntered, unit_id=unit.id, pos=unit.pos, surface=surface)
    ]
    check = definition.on_enter.check
    if check is not None and own_move and check.slide_max > 0:
        return events
    if check is not None and not slip_immune(ctx.rules, unit, surface):  # 矮人、鱗族不滑倒（3R-2）
        roll = ctx.check_d20("surface", f"surface:{surface.value}", unit.id)
        modifier = ability_modifier(ctx, effective_attribute(ctx.rules, unit, check.attr))
        total = roll + modifier
        events.append(
            ctx.emit(
                CheckRolled,
                unit_id=unit.id,
                reason=f"surface:{surface.value}",
                attr=check.attr,
                roll=roll,
                modifier=modifier,
                total=total,
                dc=check.dc,
                success=total >= check.dc,
                fail_status=check.fail_status,
            )
        )
    return events
