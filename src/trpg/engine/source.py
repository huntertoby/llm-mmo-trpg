"""源力（Phase 3C-4a，``docs/design/06-技能.md`` 6.14.4）：傳說技能的代價。

- 開場值見 :func:`trpg.engine.setup.starting_source`（敵人一律 0）；上限 ``core.yaml`` 的
  ``source_max``。跨戰鬥保留由 Phase 3-5 處理（戰鬥結果帶出剩餘源力，見
  :func:`trpg.engine.results.battle_result`）。
- 戰鬥中取得：我方單位進入源泉格（:func:`take_source_well`）、我方單位擊倒精英
  （:func:`credit_elite_kill`），各 +1、不超過上限。
- 花費：施放有 ``cost.source`` 的技能（:func:`spend_source`）。

每次改變都發出 ``source_changed``。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, SourceChanged, SourceReason
from trpg.engine.state import UnitState
from trpg.shared.types import Pos, Team, UnitId

__all__ = ["ELITE_TAG", "change_source", "credit_elite_kill", "spend_source", "take_source_well"]

ELITE_TAG = "elite"
"""精英單位的標籤（單位範本的 ``tags``；落入致命地形的規則也用它）。"""


def change_source(
    ctx: Ctx,
    unit: UnitState,
    delta: int,
    reason: SourceReason,
    *,
    skill_id: str | None = None,
    pos: Pos | None = None,
    other_id: UnitId | None = None,
) -> list[EventBase]:
    """``unit`` 的源力 +``delta``（截斷在 0 與上限之間），發出 ``source_changed``。

    即使截斷後沒有改變（例如已滿時取得源泉）也發出事件，讓紀錄看得到源泉被取走。
    """
    before = unit.source
    after = max(0, min(ctx.core.source_max, before + delta))
    unit.source = after
    return [
        ctx.emit(
            SourceChanged,
            unit_id=unit.id,
            before=before,
            after=after,
            reason=reason,
            skill_id=skill_id,
            pos=pos,
            other_id=other_id,
        )
    ]


def spend_source(ctx: Ctx, unit: UnitState, amount: int, skill_id: str) -> list[EventBase]:
    """施放傳說技能：扣 ``amount`` 點源力（呼叫端已檢查足夠）。"""
    if amount <= 0:
        return []
    return change_source(ctx, unit, -amount, "skill", skill_id=skill_id)


def take_source_well(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """我方單位抵達源泉格：+1 源力（不超過上限），源泉消失。敵方單位不取用（源泉保留）。"""
    state = ctx.state
    xy = unit.xy
    if unit.team is not Team.ALLY or not unit.alive or xy not in state.source_wells:
        return []
    state.source_wells = tuple(w for w in state.source_wells if w != xy)
    return change_source(ctx, unit, 1, "well", pos=unit.pos)


def credit_elite_kill(ctx: Ctx, downed: UnitState, source_id: UnitId | None) -> list[EventBase]:
    """精英（``elite`` 標籤）被傷害擊倒時，造成這次傷害的我方單位（仍在場上、與精英不同陣營）
    +1 源力。追溯不到來源（環境、蔓延的火……）時沒有人得到。"""
    if ELITE_TAG not in downed.tags or source_id is None:
        return []
    killer = ctx.state.units.get(source_id)
    if (
        killer is None
        or killer.team is not Team.ALLY
        or killer.team is downed.team
        or not killer.alive
    ):
        return []
    return change_source(ctx, killer, 1, "kill_elite", other_id=downed.id)
