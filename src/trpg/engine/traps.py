"""陷阱（Phase 2E-3 5.2，``docs/phases/Phase2E計畫.md`` 決定 D）。

- 放置：原語 ``place_trap``（技能的 ``trap`` 欄位）在目標格放一個陷阱（:func:`place_trap`），
  放置時快照施放者的有效屬性；技能其餘的效果在陷阱觸發時以陷阱格為中心、依 ``trap.shape`` 結算
  （自動命中，狀態照常擲抵抗），帶 ``trigger_depth`` +1。
- 觸發：``enter`` ——敵方單位在主動或強制移動中 **進入** 陷阱格（``arrive`` 記錄進入，效果佇列清空時
  結算，見 :func:`flush_trap_entries`）；``delay`` ——放置者的回合開始時倒數（:func:`tick_traps`），
  歸零時觸發；``enter`` 倒數歸零時消失。傳送不算進入。放置者離場（倒下、撤離）時陷阱消失。
- 隱藏：陷阱只有放置者陣營看得到（``reveal`` 揭露後，揭露者的陣營也看得到：
  ``revealed_to``）。敵方的路徑規劃、AI 評分與預覽一律經過 :func:`visible_traps`
  （預覽用 :func:`strip_hidden_traps`），不得讀取對方陣營的陷阱；事件紀錄是全知的。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from trpg.content.skills import SkillDef
from trpg.engine.context import Ctx
from trpg.engine.events import (
    EventBase,
    TrapExpired,
    TrapPlaced,
    TrapRevealed,
    TrapTriggered,
)
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skill_triggers import check_trigger_depth
from trpg.engine.skills.targeting import center_tiles
from trpg.engine.state import BattleState, TrapState, UnitState
from trpg.shared.types import Attribute, Pos, Team, UnitId

__all__ = [
    "flush_trap_entries",
    "own_traps",
    "place_trap",
    "queue_trap_entry",
    "remove_traps_of",
    "reveal_traps",
    "strip_hidden_traps",
    "tick_traps",
    "visible_traps",
]


def visible_traps(state: BattleState, team: Team) -> list[TrapState]:
    """``team`` 看得到的陷阱：自己陣營放置的，加上被 ``reveal`` 揭露給 ``team`` 的（Phase 3D-8a）。
    畫面與預覽讀取陷阱時一律經過這裡。"""
    return [t for t in state.traps if t.team is team or team in t.revealed_to]


def own_traps(state: BattleState, team: Team) -> list[TrapState]:
    """``team`` 自己放置的陷阱（AI 的上限與「推到自己的陷阱上」只算這些，不含被揭露的敵方陷阱）。"""
    return [t for t in state.traps if t.team is team]


def reveal_traps(ctx: Ctx, caster: UnitState, tiles: Iterable[tuple[int, int]]) -> None:
    """``reveal``：``tiles`` 內施放者敵方陣營的陷阱對施放者的陣營顯示（尚未被揭露的才發出
    ``trap_revealed``；依 ``(y, x)`` 排序固定）。"""
    state = ctx.state
    for xy in sorted(set(tiles), key=lambda p: (p[1], p[0])):
        trap = state.trap_at(*xy)
        if trap is None or trap.team is caster.team or caster.team in trap.revealed_to:
            continue
        revealed = replace(trap, revealed_to=(*trap.revealed_to, caster.team))
        state.traps = [revealed if t is trap else t for t in state.traps]
        ctx.emit(
            TrapRevealed,
            unit_id=caster.id,
            team=caster.team,
            pos=trap.pos,
            skill_id=trap.skill_id,
        )


def strip_hidden_traps(state: BattleState, team: Team) -> BattleState:
    """``team`` 視角的狀態：看不到的（對方陣營的）陷阱從複本移除。沒有需要移除的陷阱時回傳 ``state``
    本身（不複製）。預覽用——預覽不能洩漏看不見的陷阱。"""
    if all(t.team is team for t in state.traps):
        return state
    seen = state.clone()
    seen.traps = visible_traps(state, team)
    return seen


def place_trap(ctx: Ctx, caster: UnitState, skill: SkillDef, xy: tuple[int, int]) -> None:
    """在 ``xy`` 放置 ``skill`` 的陷阱（目標格已由 ``compute_area`` 驗證可放置）。"""
    spec = skill.trap
    assert spec is not None
    state = ctx.state
    assert state.trap_at(*xy) is None
    trap = TrapState(
        owner_id=caster.id,
        team=caster.team,
        pos=Pos(x=xy[0], y=xy[1]),
        skill_id=skill.id,
        remaining=spec.rounds,
        attributes=tuple(
            (attr, effective_attribute(ctx.rules, caster, attr)) for attr in Attribute
        ),
    )
    state.traps = sorted([*state.traps, trap], key=lambda t: (t.pos.y, t.pos.x))
    ctx.emit(
        TrapPlaced,
        owner_id=caster.id,
        team=caster.team,
        pos=trap.pos,
        skill_id=skill.id,
        trigger=spec.trigger,
        rounds=spec.rounds,
    )


def queue_trap_entry(ctx: Ctx, unit: UnitState, xy: tuple[int, int]) -> None:
    """單位（主動或強制移動）進入 ``xy``：該格有敵方陣營的 ``enter`` 陷阱時記下，等效果佇列清空
    時結算（與表面的進入效果同一個時點）。"""
    if not ctx.state.traps:
        return
    trap = ctx.state.trap_at(*xy)
    if trap is not None and trap.team is not unit.team:
        ctx.trap_entries.append((unit.id, xy))


def flush_trap_entries(ctx: Ctx) -> None:
    """結算記下的陷阱進入：單位仍存活、陷阱仍在且是 ``enter`` 陷阱才觸發（依記錄順序）。"""
    entries = ctx.trap_entries
    ctx.trap_entries = []
    for unit_id, xy in entries:
        unit = ctx.state.units.get(unit_id)
        trap = ctx.state.trap_at(*xy)
        if unit is None or not unit.alive or trap is None or trap.team is unit.team:
            continue
        skill = ctx.rules.skill_def(trap.skill_id)
        assert skill.trap is not None
        if skill.trap.trigger == "enter":
            _trigger(ctx, trap, skill, unit)


def _remove(state: BattleState, trap: TrapState) -> None:
    state.traps = [t for t in state.traps if t is not trap]


def _trigger(ctx: Ctx, trap: TrapState, skill: SkillDef, unit: UnitState | None) -> None:
    """觸發 ``trap``：深度檢查（超過 ``max_trigger_depth`` 時陷阱保留、不結算）、移除、結算。"""
    # 延後匯入：技能解譯器匯入效果佇列，而效果佇列匯入本模組。
    from trpg.engine.skills.interpreter import use_trap_skill  # noqa: PLC0415

    assert skill.trap is not None
    depth = ctx.trigger_depth + 1
    if not check_trigger_depth(ctx, trap.owner_id, skill.id, depth):
        return
    _remove(ctx.state, trap)
    ctx.emit(
        TrapTriggered,
        owner_id=trap.owner_id,
        pos=trap.pos,
        skill_id=skill.id,
        cause=skill.trap.trigger,
        unit_id=None if unit is None else unit.id,
        trigger_depth=depth,
        tiles=tuple(Pos(x=x, y=y) for x, y in center_tiles(ctx.state, skill.trap.shape, trap.xy)),
    )
    use_trap_skill(ctx, trap, skill, depth=depth)


def tick_traps(ctx: Ctx, owner: UnitState) -> None:
    """``owner`` 的回合開始：他的陷阱剩餘輪數 −1；歸零時 ``delay`` 觸發、``enter`` 消失。"""
    for trap in [t for t in ctx.state.traps if t.owner_id == owner.id]:
        if not owner.alive:
            return
        skill = ctx.rules.skill_def(trap.skill_id)
        assert skill.trap is not None
        remaining = trap.remaining - 1
        if remaining > 0:
            ctx.state.traps = [
                replace(trap, remaining=remaining) if t is trap else t for t in ctx.state.traps
            ]
        elif skill.trap.trigger == "delay":
            _trigger(ctx, trap, skill, None)
        else:
            _remove(ctx.state, trap)
            ctx.emit(
                TrapExpired,
                owner_id=trap.owner_id,
                pos=trap.pos,
                skill_id=skill.id,
                reason="timeout",
            )


def remove_traps_of(ctx: Ctx, owner_id: UnitId) -> list[EventBase]:
    """放置者離場（倒下、撤離）：他的陷阱全部消失（``source_lost``）。"""
    events: list[EventBase] = []
    for trap in [t for t in ctx.state.traps if t.owner_id == owner_id]:
        _remove(ctx.state, trap)
        events.append(
            ctx.emit(
                TrapExpired,
                owner_id=trap.owner_id,
                pos=trap.pos,
                skill_id=trap.skill_id,
                reason="source_lost",
            )
        )
    return events
