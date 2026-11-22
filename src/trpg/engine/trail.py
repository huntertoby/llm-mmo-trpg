"""每一步留下表面（地形規則 ``trail_surface``，例「霜行」；E3，08-裝備.md 8.29 E3）。

規則（8.29 E3 第 1～4 點）：

1. 只算自己主動的移動：步行（``battle._do_move``）與衝刺（``mode="dash"``：衝刺技能、直線衝撞）
   的每一步。跳躍、攀跳、瞬步、傳送、被推拉、冰上滑行都不算。
2. 踏進下一格之後，在 **離開的那一格** 留下表面：起點格與途經的格子會留，停下的那一格不留。
3. 那一格已經有表面時維持原樣（不蓋掉、不觸發元素互動）；只在沒有表面、可以有表面的格子留。
4. 有其他單位站著的格子（例如走過隊友）不留，免得表面直接出現在別人腳下。
5. 留下的表面持續 ``duration`` 個環境回合，到期直接消失（``Tile.surface_trail``，
   :func:`trpg.engine.environment` 的到期）；留下的人自己踩到不會滑倒（:func:`own_trail`），
   別人照一般規則檢定。

保守做法（E3 報告「待 PM 決定」）：會飛的單位、已倒下的單位不留。

表面走效果佇列（``create_surface``，``react=False``、``cause="trail"``），事件照常記進戰鬥紀錄：
``unit_moved`` 之後緊接著那一格的 ``surface_changed``。純函式、確定性。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import CreateSurfaceEffect
from trpg.engine.effects.world import surface_allowed
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_flying
from trpg.engine.rules.unit_rules import first_source
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface

__all__ = ["TRAIL_CAUSE", "TRAIL_RULE", "leave_trail", "own_trail"]

TRAIL_RULE = "trail_surface"
TRAIL_CAUSE = "trail"
"""``surface_changed`` 的 ``cause``：地形規則留下的表面。"""


def own_trail(state: BattleState, unit: UnitState, xy: XY) -> bool:
    """``xy`` 的表面是 ``unit`` 自己用 ``trail_surface`` 留下的（踩到不會滑倒）。"""
    return state.tile(*xy).surface_trail == unit.id


def leave_trail(ctx: Ctx, unit: UnitState, left: XY) -> None:
    """``unit`` 自己步行或衝刺離開 ``left`` 之後：有 ``trail_surface`` 時在那一格留下表面。
    呼叫端只在單位確實離開 ``left`` 時呼叫。"""
    if not unit.alive or is_flying(unit):
        return
    state = ctx.state
    if unit.race is None and not unit.gear.affixes:
        return
    source = first_source(state.ruleset, unit, TRAIL_RULE)
    if source is None or not source.rule.surfaces or source.rule.duration is None:
        return
    surface = source.rule.surfaces[0]
    tile = state.tile(*left)
    if tile.surface is not Surface.NONE or not surface_allowed(state, left):
        return
    if any(u.alive and u.id != unit.id and u.covers(*left) for u in state.units.values()):
        return
    effect = CreateSurfaceEffect(
        source_id=unit.id,
        pos=left,
        surface=surface,
        duration=source.rule.duration,
        team=unit.team,
        react=False,
        cause=TRAIL_CAUSE,
    )
    execute(ctx, [effect])
    placed = state.tile(*left)
    if placed.surface is surface and placed.surface_creator == unit.id:
        state.set_tile(*left, replace(placed, surface_trail=unit.id))
