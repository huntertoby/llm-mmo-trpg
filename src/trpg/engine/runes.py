"""刻印的符文（Phase 3-23，``docs/design/06-技能.md`` 6.25、``docs/phases/Phase3計畫.md`` 23）。

- **刻下**：原語 ``inscribe`` 在技能形狀的格子上留下施放者專屬的符文（:func:`inscribe_rune`），
  帶一個元素或標籤，持續 ``duration`` 個環境回合（省略為 ``core.rune_default_rounds``）。符文本身
  沒有效果，敵我都看得到。同一施放者在同一格再刻一次是更新（舊的以 ``replaced`` 消失）；同一施放者
  同時存在的符文格超過 ``core.rune_limit_per_owner`` 時，最舊的（編號最小）消失。
- **時效**：每次環境回合 −1，歸零時消失（:func:`tick_runes`）。施放者倒下、撤離時符文保留到時效
  結束（保守）。
- **讀取**：條件 ``on_own_rune``（:func:`has_own_rune`，修正型被動沿用條件機制）與消耗型原語
  ``detonate_runes``（:func:`remove_rune` 原因 ``detonated``）。只有刻下它的施放者讀得到：別人的
  符文不算。
- 狀態放在 :attr:`BattleState.runes`（依編號排序），可序列化、可重播；全程不使用亂數。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, RuneInscribed, RuneRemovalReason, RuneRemoved
from trpg.engine.rules.geometry import XY
from trpg.engine.rune_queries import has_own_rune, own_runes, own_runes_at, rune_matches, runes_at
from trpg.engine.state import RuneState
from trpg.shared.types import Element, Pos, Team, UnitId

__all__ = [
    "has_own_rune",
    "inscribe_rune",
    "own_runes",
    "own_runes_at",
    "remove_rune",
    "rune_matches",
    "runes_at",
    "tick_runes",
]


def remove_rune(ctx: Ctx, rune: RuneState, reason: RuneRemovalReason) -> EventBase:
    """移除 ``rune`` 並發出 ``rune_removed``。"""
    ctx.state.runes = [r for r in ctx.state.runes if r.id != rune.id]
    return ctx.emit(
        RuneRemoved,
        rune_id=rune.id,
        owner_id=rune.owner_id,
        pos=rune.pos,
        element=rune.element,
        tag=rune.tag,
        reason=reason,
    )


def inscribe_rune(
    ctx: Ctx,
    owner_id: UnitId,
    team: Team,
    xy: XY,
    *,
    element: Element | None,
    tag: str | None,
    duration: int | None,
) -> list[EventBase]:
    """在 ``xy`` 刻下 ``owner_id`` 的符文；回傳事件（含被取代與被擠掉的舊符文）。"""
    assert (element is None) != (tag is None), "符文恰好帶元素或標籤其中一個"
    state, core = ctx.state, ctx.core
    events: list[EventBase] = []
    for old in own_runes_at(state, owner_id, xy):
        events.append(remove_rune(ctx, old, "replaced"))
    owned = own_runes(state, owner_id)
    while len(owned) >= core.rune_limit_per_owner:
        events.append(remove_rune(ctx, owned.pop(0), "limit"))
    rune = RuneState(
        id=state.next_rune_id,
        owner_id=owner_id,
        team=team,
        pos=Pos(x=xy[0], y=xy[1]),
        remaining=duration if duration is not None else core.rune_default_rounds,
        element=element,
        tag=tag,
    )
    state.next_rune_id += 1
    state.runes = [*state.runes, rune]
    events.append(
        ctx.emit(
            RuneInscribed,
            rune_id=rune.id,
            owner_id=owner_id,
            pos=rune.pos,
            element=element,
            tag=tag,
            remaining=rune.remaining,
        )
    )
    return events


def tick_runes(ctx: Ctx) -> None:
    """環境回合：符文的剩餘輪數 −1，歸零時消失（依編號）。"""
    state = ctx.state
    expired = [r for r in state.runes if r.remaining <= 1]
    state.runes = [
        r if r.remaining <= 1 else replace(r, remaining=r.remaining - 1) for r in state.runes
    ]
    for rune in expired:
        remove_rune(ctx, rune, "expired")
