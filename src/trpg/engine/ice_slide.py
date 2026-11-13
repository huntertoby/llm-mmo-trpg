"""冰面滑倒並滑行（#123，Phase 6E-2；``docs/design/05-戰鬥.md`` 表面規則「冰面：滑倒並滑行」）。

自己走進一段連續冰面（表面檢定 ``slide_max > 0``）的 **第一格** 時擲一次檢定；同一次移動裡這段冰
後面的格子不再擲。失敗就沿走進來的方向滑到冰面外的第一格停下（最多 ``slide_max`` 格），停下後才
得到失敗的狀態（倒地），這次移動剩下的點數作廢。

- 怎麼停：下一格是牆／不可站立的地形、擋路的物件、其他單位（敵我都算）、地圖邊緣、高度差 1 以上、
  致命地形時停在目前這一格（不撞傷、不推人、不會因為自己滑行掉進致命地形）。
- 滑過的格子照「走進那一格」處理（``unit_moved`` 的 ``mode: slide``）：陷阱照樣觸發（讓人停下的
  陷阱就停在陷阱格），火、毒這類表面照樣生效；不觸發藉機攻擊與「敵人靠近」類反應（與強制位移相同）。
- 被推、拉進冰面照舊（:func:`trpg.engine.effects.handlers.enter_surface`：檢定、失敗倒地、不滑）。
- 矮人、鱗族（:func:`trpg.engine.rules.race.slip_immune`）與會飛的單位不擲、不滑。

純函式、確定性：檢定只用 ``ctx.check_d20("slide", ...)``（預覽時可以用
:class:`trpg.engine.context.CheckOverride` 指定每次滑行檢定的結果，見 ``Ctx.check_override``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import SurfaceCheck
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.handlers import ability_modifier
from trpg.engine.effects.models import ApplyStatusEffect, MoveUnitEffect
from trpg.engine.events import CheckRolled, SlideStopReason, UnitSlid
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_deadly, is_flying, is_standable
from trpg.engine.rules.race import slip_immune
from trpg.engine.rules.statuses import effective_attribute, is_rooted, skip_turn_status
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, Surface

__all__ = [
    "SlideRisk",
    "path_slide_risks",
    "slide_check",
    "slide_check_def",
    "slide_check_due",
    "slide_fail_chance",
    "slide_next_block",
    "slide_unit",
    "static_slide",
]


def slide_check_def(state: BattleState, xy: XY) -> SurfaceCheck | None:
    """``xy`` 的表面會滑行的檢定（冰面）；沒有時為 ``None``。"""
    surface = state.tile(*xy).surface
    if surface is Surface.NONE:
        return None
    on_enter = state.ruleset.surface_def(surface).on_enter
    check = on_enter.check if on_enter is not None else None
    return check if check is not None and check.slide_max > 0 else None


def slide_check_due(state: BattleState, unit: UnitState, before: XY, dest: XY) -> bool:
    """從 ``before`` 走到 ``dest`` 這一步要不要擲滑行檢定：``dest`` 是會滑行的表面、``before`` 不是
    同一種表面（同一段冰只擲一次；這次移動從冰上出發時，接著走的冰算同一段），且移動者會滑倒。"""
    if slide_check_def(state, dest) is None or is_flying(unit):
        return False
    surface = state.tile(*dest).surface
    if state.tile(*before).surface is surface:
        return False
    return not slip_immune(state.ruleset, unit, surface)


def slide_check(ctx: Ctx, unit: UnitState) -> CheckRolled:
    """在 ``unit`` 所在的冰面第一格擲滑行檢定（``check_rolled``，``slide: true``）。"""
    surface = ctx.state.tile(*unit.xy).surface
    check = slide_check_def(ctx.state, unit.xy)
    assert check is not None
    roll = ctx.check_d20("slide", f"surface:{surface.value}", unit.id)
    modifier = ability_modifier(ctx, effective_attribute(ctx.rules, unit, check.attr))
    total = roll + modifier
    return ctx.emit(
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
        slide=True,
    )


def slide_next_block(
    state: BattleState, unit: UnitState, cur: XY, nxt: XY
) -> SlideStopReason | None:
    """從 ``cur`` 滑向 ``nxt`` 時擋住的原因；可以滑過去時為 ``None``。"""
    if not state.in_bounds(*nxt):
        return "edge"
    if any(u.alive and u.id != unit.id and u.covers(*nxt) for u in state.units.values()):
        return "unit"
    if is_deadly(state, nxt):
        return "deadly"
    if not is_standable(state, nxt):
        return "object" if state.tile(*nxt).object_id is not None else "wall"
    if abs(state.tile(*nxt).height - state.tile(*cur).height) >= 1:
        return "height"
    return None


def _interrupted(ctx: Ctx, unit: UnitState, expected: XY) -> bool:
    """滑過的格子讓人停下（陷阱定身、暈眩、推離、倒下、撤離）。"""
    if not unit.alive or unit.xy != expected:
        return True
    return is_rooted(ctx.rules, unit) or skip_turn_status(ctx.rules, unit) is not None


def slide_unit(ctx: Ctx, unit: UnitState, direction: tuple[int, int], walked: list[XY]) -> None:
    """檢定失敗後的滑行：沿 ``direction`` 一格一格滑（每格 ``unit_moved`` ``mode: slide``，
    滑到的格子也加進 ``walked``），停下後發 ``unit_slid``、得到失敗的狀態（倒地），移動點數歸零。"""
    state = ctx.state
    check = slide_check_def(state, unit.xy)
    assert check is not None
    path: list[Pos] = [unit.pos]
    reason: SlideStopReason = (
        "interrupted"
        if _interrupted(ctx, unit, unit.xy)
        else _slide_steps(ctx, unit, direction, check.slide_max, path=path, walked=walked)
    )
    ctx.emit(UnitSlid, unit_id=unit.id, path=tuple(path), stop_reason=reason)
    unit.move_points = 0  # 這次移動剩下的點數作廢
    if unit.alive:
        execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=check.fail_status)])


def _slide_steps(
    ctx: Ctx,
    unit: UnitState,
    direction: tuple[int, int],
    limit: int,
    *,
    path: list[Pos],
    walked: list[XY],
) -> SlideStopReason:
    state = ctx.state
    for _ in range(limit):
        cur = unit.xy
        if slide_check_def(state, cur) is None:
            return "off_ice"
        nxt = (cur[0] + direction[0], cur[1] + direction[1])
        blocked = slide_next_block(state, unit, cur, nxt)
        if blocked is not None:
            return blocked
        execute(ctx, [MoveUnitEffect(unit_id=unit.id, dest=nxt, mode="slide")])
        if unit.alive and unit.xy == nxt:
            path.append(unit.pos)
            walked.append(nxt)
        if _interrupted(ctx, unit, nxt):
            return "interrupted"
    return "max_tiles" if slide_check_def(state, unit.xy) is not None else "off_ice"


# ---------------------------------------------------------------------------
# 不跑引擎的估計（敵人 AI 的移動評分用；陷阱與途中事件不計）
# ---------------------------------------------------------------------------


def slide_fail_chance(state: BattleState, unit: UnitState, xy: XY) -> Fraction:
    """``unit`` 在 ``xy`` 的滑行檢定失敗的機率（d20 + 屬性修正 < dc；精確計算，不擲骰）。"""
    check = slide_check_def(state, xy)
    if check is None:
        return Fraction(0)
    core = state.ruleset.core
    value = effective_attribute(state.ruleset, unit, check.attr)
    modifier = (value - core.ability_mod_base) // core.ability_mod_divisor
    return Fraction(max(0, min(20, check.dc - modifier - 1)), 20)


def static_slide(
    state: BattleState, unit: UnitState, start: XY, direction: tuple[int, int]
) -> tuple[XY, ...]:
    """從 ``start`` 沿 ``direction`` 滑行的格子（含起點；只看地形、物件、單位，不看陷阱）。"""
    check = slide_check_def(state, start)
    limit = check.slide_max if check is not None else 0
    path = [start]
    for _ in range(limit):
        cur = path[-1]
        if slide_check_def(state, cur) is None:
            break
        nxt = (cur[0] + direction[0], cur[1] + direction[1])
        if slide_next_block(state, unit, cur, nxt) is not None:
            break
        path.append(nxt)
    return tuple(path)


@dataclass(frozen=True, slots=True)
class SlideRisk:
    """路徑上一次滑行檢定：``index`` 為擲檢定的格子在路徑中的位置，``chance`` 為失敗率，
    ``stop`` 為失敗時的停點（不計陷阱）。"""

    index: int
    chance: Fraction
    stop: XY


def path_slide_risks(state: BattleState, unit: UnitState, path: tuple[XY, ...]) -> list[SlideRisk]:
    """沿 ``path`` 走的每一次滑行檢定（依序；不看前面的檢定是否已失敗）。"""
    risks: list[SlideRisk] = []
    for i in range(1, len(path)):
        before, dest = path[i - 1], path[i]
        if not slide_check_due(state, unit, before, dest):
            continue
        direction = (dest[0] - before[0], dest[1] - before[1])
        stop = static_slide(state, unit, dest, direction)[-1]
        risks.append(SlideRisk(i, slide_fail_chance(state, unit, dest), stop))
    return risks
