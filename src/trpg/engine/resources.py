"""資源互動原語（Phase 3D-1，``docs/design/06-技能.md`` 6.16 H）：``restore_resource``、
``steal_buff``。

- ``restore_resource``：``resource: mana`` 回復法力（不超過上限）；``resource: cooldown`` 讓目標
  所有冷卻中的技能 −``amount``（下限 0）。不影響花源力的技能（``cost.source``）與施放中的這個
  技能本身（它的冷卻才剛開始，縮短自己等於白付代價）。
- ``steal_buff``：移除目標身上一個增益（``statuses.yaml`` 的 ``polarity: buff``），以相同的剩餘
  回合與數值施加到施放者身上。有多個增益時取剩餘回合最長者（永久最長），同長依狀態 ID 排序。
"""

from __future__ import annotations

from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine.context import Ctx
from trpg.engine.events import EffectFizzled, ResourceRestored, SkillCooldownChanged
from trpg.engine.state import BattleState, StatusInstance, UnitState

__all__ = [
    "dispelled_buffs",
    "pick_stolen_buff",
    "restorable_cooldowns",
    "restore_cooldowns",
    "restore_mana",
]


def _buffs_in_order(ctx: Ctx, target: UnitState) -> list[StatusInstance]:
    """``target`` 身上的增益（``polarity: buff``），依「永久最先、剩餘回合長者先、同長依狀態 ID」
    排序。"""
    buffs = [s for s in target.statuses if ctx.rules.status_def(s.status_id).polarity == "buff"]
    return sorted(
        buffs, key=lambda s: (0 if s.remaining is None else 1, -(s.remaining or 0), s.status_id)
    )


def pick_stolen_buff(ctx: Ctx, target: UnitState) -> StatusInstance | None:
    """``target`` 身上會被奪取（或驅散）的增益；沒有增益時為 ``None``。"""
    buffs = _buffs_in_order(ctx, target)
    return buffs[0] if buffs else None


def dispelled_buffs(ctx: Ctx, target: UnitState, count: int | str) -> list[StatusInstance]:
    """``dispel`` 驅散的增益（Phase 3D-8a）：``count`` 個（取 :func:`pick_stolen_buff` 的順序）或
    ``"all"`` 全部；中性狀態（姿態、隱蔽……）不是增益，不會被驅散。"""
    buffs = _buffs_in_order(ctx, target)
    return buffs if count == "all" else buffs[: int(count)]


def restore_mana(ctx: Ctx, caster: UnitState, target: UnitState, amount: int) -> None:
    """``resource: mana``：回復法力；已滿時發出 ``effect_fizzled``（``mana_full``）。"""
    gained = min(amount, target.max_mana - target.mana)
    if gained <= 0:
        ctx.emit(EffectFizzled, effect_kind="restore_resource", pos=target.pos, reason="mana_full")
        return
    target.mana += gained
    ctx.emit(
        ResourceRestored,
        unit_id=target.id,
        source_id=caster.id,
        resource="mana",
        amount=gained,
        mana_after=target.mana,
        skill_ids=(),
    )


def restorable_cooldowns(state: BattleState, target: UnitState, skill: SkillDef) -> list[str]:
    """``resource: cooldown`` 會縮短的技能（依技能 ID 排序）：冷卻中、不花源力、不是施放中的
    技能。"""
    found: list[str] = []
    for skill_id in sorted(target.cooldowns):
        if target.cooldowns[skill_id] <= 0 or skill_id == skill.id:
            continue
        if state.ruleset.skill_def(skill_id).cost.source is not None:
            continue
        found.append(skill_id)
    return found


def restore_cooldowns(
    ctx: Ctx, caster: UnitState, target: UnitState, skill: SkillDef, spec: EffectSpec
) -> None:
    """``resource: cooldown``：縮短冷卻；沒有可縮短的技能時發出 ``effect_fizzled``。"""
    amount = spec.amount or 1
    changed = restorable_cooldowns(ctx.state, target, skill)
    if not changed:
        ctx.emit(
            EffectFizzled, effect_kind="restore_resource", pos=target.pos, reason="no_cooldown"
        )
        return
    for skill_id in changed:
        left = max(0, target.cooldowns[skill_id] - amount)
        if left == 0:
            del target.cooldowns[skill_id]
        else:
            target.cooldowns[skill_id] = left
        ctx.emit(SkillCooldownChanged, unit_id=target.id, skill_id=skill_id, remaining=left)
    ctx.emit(
        ResourceRestored,
        unit_id=target.id,
        source_id=caster.id,
        resource="cooldown",
        amount=amount,
        mana_after=None,
        skill_ids=tuple(changed),
    )
