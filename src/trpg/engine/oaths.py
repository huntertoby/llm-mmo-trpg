"""誓約的戰鬥判定（Phase 5C-3；06 6.26、#27；``docs/phases/Phase5計畫.md`` 24.6）。

``BattleSetup.oath``（:class:`OathSetup`）讓一個單位（大世界的主角）帶著誓約開戰：

- **開場**（:func:`open_oath`，開場狀態之後、擲先攻之前）：掛上加成狀態（依難度查表，由呼叫端給
  ``bonus_status``）；``solo``（單獨作戰）有其他我方非召喚單位時開場就違反。
- **戰鬥中**（:func:`observe_oath`，:meth:`~trpg.engine.context.Ctx.emit` 的掛鉤）：看每個事件，
  違反時只記下（``OathTracker.pending``），等這次結算收尾（:func:`settle_oath`，
  :func:`~trpg.engine.turns.finish_resolution`）才執行：移除加成、施加破誓 ``penalty_rounds`` 回合，
  發 ``oath_broken``。同一場只違反一次（#27「本場加成移除＋debuff 2 回合，下一場恢復」）。
- **戰鬥結束時**（``battle_ended``）：「每場至少……」的種類（``AT_END_CHECKS``）沒達到 → 發
  ``oath_broken``（``at_end=True``，沒有效果）。

判定只看事件與當下的戰鬥狀態，不擲骰、不讀時間；沒有誓約時 ``BattleState.oath`` 是 ``None``，結算與
沒有這個模組時完全相同。
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from trpg.engine.effects.models import ApplyStatusEffect, RemoveStatusEffect
from trpg.engine.effects.queue import execute
from trpg.engine.events import OathBroken, ReactionModeSet
from trpg.engine.oath_tracking import (
    BREACH_TEXT,
    ELEMENT_EXEMPT_CAUSES,
    VOLUNTARY_MOVES,
    OathSetup,
    OathTracker,
    breach_oath,
    oath_warning,
    observe_oath,
)
from trpg.shared.types import UnitId

if TYPE_CHECKING:
    from trpg.engine.context import Ctx

__all__ = [
    "BREACH_TEXT",
    "ELEMENT_EXEMPT_CAUSES",
    "VOLUNTARY_MOVES",
    "OathSetup",
    "OathTracker",
    "oath_warning",
    "observe_oath",
    "open_oath",
    "settle_oath",
]


# ---------------------------------------------------------------------------
# 開場與收尾
# ---------------------------------------------------------------------------


def open_oath(ctx: Ctx, oath: OathSetup | None, unit_ids: list[UnitId]) -> None:
    """開場：記下誓約、掛上加成；``solo`` 有其他我方非召喚單位時開場就違反。"""
    if oath is None or oath.unit >= len(unit_ids):
        return
    holder = unit_ids[oath.unit]
    state = ctx.state
    state.oath = OathTracker(holder=holder, setup=oath)
    if oath.bonus_status is not None:
        execute(
            ctx,
            [ApplyStatusEffect(target_id=holder, status_id=oath.bonus_status, source_id=holder)],
        )
    if oath.start_penalty_rounds > 0 and oath.penalty_status is not None:  # 上一場的破誓（5C-3b）
        execute(
            ctx,
            [
                ApplyStatusEffect(
                    target_id=holder,
                    status_id=oath.penalty_status,
                    source_id=holder,
                    duration=oath.start_penalty_rounds,
                )
            ],
        )
    if oath.check.kind == "forbid_reaction":  # 立「不使用反應」：自動把反應設定關掉（5C-3b）
        _turn_reactions_off(ctx, holder)
    if oath.check.kind == "solo" and not state.units[holder].lone_wolf:
        breach_oath(state)  # 和獨狼同一個判定（LW-1，06 6.37：開場時已由 mark_lone_wolves 算好）


def _turn_reactions_off(ctx: Ctx, holder: UnitId) -> None:
    """把持有者所有反應規則關掉（玩家之後自己再打開而觸發，仍算違反）。"""
    unit = ctx.state.units[holder]
    for reaction in sorted({rule.reaction for rule in unit.reactions if rule.mode != "off"}):
        unit.reactions = tuple(
            rule.model_copy(update={"mode": "off"}) if rule.reaction == reaction else rule
            for rule in unit.reactions
        )
        ctx.emit(ReactionModeSet, unit_id=holder, reaction=reaction, mode="off")


def settle_oath(ctx: Ctx) -> None:
    """結算收尾：剛違反的誓約執行後果（移除加成、施加破誓），發 ``oath_broken``。"""
    tracker = ctx.state.oath
    if tracker is None or not tracker.pending:
        return
    setup = tracker.setup
    ctx.state.oath = dataclasses.replace(tracker, pending=False, broken=True)
    holder = ctx.state.units.get(tracker.holder)
    effects: list[ApplyStatusEffect | RemoveStatusEffect] = []
    if holder is not None and holder.alive:
        if setup.bonus_status is not None:
            effects.append(RemoveStatusEffect(target_id=holder.id, status_id=setup.bonus_status))
        if setup.penalty_status is not None:
            effects.append(
                ApplyStatusEffect(
                    target_id=holder.id,
                    status_id=setup.penalty_status,
                    source_id=holder.id,
                    duration=setup.penalty_rounds,
                )
            )
    ctx.emit(OathBroken, unit_id=tracker.holder, template=setup.template, check=setup.check.kind)
    if effects:
        execute(ctx, effects)
