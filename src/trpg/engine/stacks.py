"""層數的增減與過期（Phase 2E-3 5.1；定義在 ``content/stacks.yaml``）。

層數存放在 ``UnitState.stacks``（層數 ID → 層數，只列 > 0 的）。三個入口：

- :func:`add_stacks`：累積，超過 ``max`` 截斷；有 ``expires_after_rounds`` 的層數每次累積（含已在
  上限）都會刷新到期輪數；
- :func:`consume_stacks`：消耗全部，回傳消耗的層數；
- :func:`expire_stacks`：每輪開始時清空到期的層數。

每次層數改變都發出 ``stacks_changed``。引擎不判斷層數 ID，一切依資料表。
"""

from __future__ import annotations

from trpg.content.skills import CONSUME_STACK, SkillDef
from trpg.content.stacks import StackDef
from trpg.engine.context import Ctx
from trpg.engine.events import StacksChanged
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = ["add_stacks", "consume_stacks", "expire_stacks", "required_stack"]


def add_stacks(
    ctx: Ctx, unit: UnitState, stack_id: str, amount: int, *, source_id: UnitId | None
) -> None:
    """``unit`` 累積 ``amount`` 層（超過上限截斷；層數沒有變化時不發事件，但仍刷新到期輪數）。"""
    definition = ctx.rules.stack_def(stack_id)
    before = unit.stacks.get(stack_id, 0)
    after = min(before + amount, definition.max)
    if definition.expires_after_rounds is not None:
        unit.stack_expiry[stack_id] = ctx.state.round + definition.expires_after_rounds
    if after == before:
        return
    unit.stacks[stack_id] = after
    ctx.emit(
        StacksChanged,
        unit_id=unit.id,
        stack_id=stack_id,
        before=before,
        after=after,
        reason="gained",
        source_id=source_id,
    )


def consume_stacks(ctx: Ctx, unit: UnitState, stack_id: str, *, source_id: UnitId | None) -> int:
    """消耗 ``unit`` 身上全部的 ``stack_id``，回傳消耗的層數（沒有層數時為 0，不發事件）。"""
    before = unit.stacks.pop(stack_id, 0)
    unit.stack_expiry.pop(stack_id, None)
    if before > 0:
        ctx.emit(
            StacksChanged,
            unit_id=unit.id,
            stack_id=stack_id,
            before=before,
            after=0,
            reason="consumed",
            source_id=source_id,
        )
    return before


def expire_stacks(ctx: Ctx) -> None:
    """每輪開始（``RoundStarted`` 之後）：到期輪數已到的層數整個清空（依單位 ID、層數 ID 排序）。"""
    state = ctx.state
    for unit in state.units_sorted():
        for stack_id in sorted(unit.stack_expiry):
            if state.round < unit.stack_expiry[stack_id]:
                continue
            del unit.stack_expiry[stack_id]
            before = unit.stacks.pop(stack_id, 0)
            if before > 0:
                ctx.emit(
                    StacksChanged,
                    unit_id=unit.id,
                    stack_id=stack_id,
                    before=before,
                    after=0,
                    reason="expired",
                )


def required_stack(state: BattleState, skill: SkillDef) -> StackDef | None:
    """``cost.stacks`` 對應的層數：技能裡第一個 ``owner: self`` 的 ``consume_stack`` 的層數。"""
    if skill.cost.stacks is None:
        return None
    rules = state.ruleset
    for effect in skill.effects:
        if effect.type == CONSUME_STACK and effect.stack is not None:
            definition = rules.stack_def(effect.stack)
            if definition.owner == "self":
                return definition
    return None
