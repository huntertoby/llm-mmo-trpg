"""規則改變的結算（Phase 3D-6，``docs/design/06-技能.md`` 6.16 F）：需要施放效果或召喚的兩類。

- ``pass_through_apply``（:func:`pass_through`）：持有者步行時，每踏進一格，就對相鄰（曼哈頓距離 1）
  的敵人施加狀態；同一次移動動作每個敵人最多一次。效果比照被動觸發：自動命中、狀態照常擲抵抗、
  觸發深度 +1（受 ``max_trigger_depth`` 限制）。只算步行（``Move`` 動作），衝鋒、跳躍、傳送、
  被推都不算。
- ``on_downed_spawn``（:func:`spawn_on_downed`）：持有者倒下時，在原地留下召喚物（分身），排在持有
  者原本的先攻位置。召喚者已不在場，所以分身在第「倒下輪 ＋ ``duration`` − 1」輪的環境回合消失
  （:func:`expire_orphan_summons`），也就是持續 ``duration`` 輪（含倒下的那一輪）。

另外兩類在各自的規則模組直接判斷：``element_heals_allies``（傷害處理器）、``push_any_object``
（推動物件）；查詢見 :mod:`trpg.engine.activations`。
"""

from __future__ import annotations

from trpg.content.rule_changes import ON_DOWNED_SPAWN, PASS_THROUGH_APPLY
from trpg.content.skills import EffectSpec
from trpg.engine.activations import active_rule_change
from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, RuleChangeTriggered
from trpg.engine.lifecycle import dismiss_summon
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skill_triggers import check_trigger_depth
from trpg.engine.state import UnitState
from trpg.engine.summons import summon_unit
from trpg.shared.types import UnitId

__all__ = ["expire_orphan_summons", "pass_through", "spawn_on_downed"]


def pass_through(ctx: Ctx, unit: UnitState, touched: set[UnitId]) -> None:
    """``unit`` 步行踏進一格之後：生效中的 ``pass_through_apply`` 對相鄰、這次移動還沒碰過的敵人
    （依 ID）施加狀態。``touched`` 由呼叫端在整個移動動作中共用。"""
    if not unit.activations or not unit.alive:
        return
    state = ctx.state
    change = active_rule_change(state, unit, PASS_THROUGH_APPLY)
    if change is None:
        return
    # 延後匯入：技能解譯器匯入效果佇列，而效果佇列（經由傷害處理器）匯入規則改變的查詢。
    from trpg.engine.skills.interpreter import use_rule_change_effects  # noqa: PLC0415

    rule = change.rule
    assert rule.status is not None
    spec = EffectSpec(
        type="apply_status", status=rule.status, duration=rule.duration, affects="enemies"
    )
    for other in state.living_units():
        if not unit.alive:
            return
        if other.team is unit.team or other.id in touched or manhattan(unit.xy, other.xy) != 1:
            continue
        touched.add(other.id)
        depth = ctx.trigger_depth + 1
        if not check_trigger_depth(ctx, unit.id, change.skill.id, depth):
            continue
        ctx.emit(
            RuleChangeTriggered,
            unit_id=unit.id,
            skill_id=change.skill.id,
            rule=rule.id,
            kind=PASS_THROUGH_APPLY,
            other_id=other.id,
        )
        use_rule_change_effects(ctx, unit, change.skill, (spec,), other, depth=depth)


def spawn_on_downed(ctx: Ctx, unit: UnitState, order_index: int | None) -> list[EventBase]:
    """``unit`` 剛倒下：生效中的 ``on_downed_spawn`` 在它的位置留下分身（排在 ``order_index``，
    也就是它原本的先攻位置）。位置不能站（例如掉進深淵）時 ``effect_fizzled``。"""
    change = active_rule_change(ctx.state, unit, ON_DOWNED_SPAWN)
    if change is None:
        return []
    rule = change.rule
    assert rule.unit is not None and rule.duration is not None
    events: list[EventBase] = [
        ctx.emit(
            RuleChangeTriggered,
            unit_id=unit.id,
            skill_id=change.skill.id,
            rule=rule.id,
            kind=ON_DOWNED_SPAWN,
        )
    ]
    events += summon_unit(
        ctx,
        unit,
        rule.unit,
        unit.xy,
        rule.duration - 1,
        change.skill.id,
        order_index=order_index,
        orphan=True,
    )
    return events


def expire_orphan_summons(ctx: Ctx) -> None:
    """環境回合：召喚者已不在場的召喚物（目前只有 ``on_downed_spawn`` 的分身；一般召喚物在召喚者
    離場時就消失）到期（``summon_expires_round`` ≤ 目前輪數）時消失（依 ID）。"""
    state = ctx.state
    for summon in state.living_units():
        owner_id = summon.owner_id
        if owner_id is None or state.units[owner_id].alive:
            continue
        expires = summon.summon_expires_round
        if expires is not None and expires <= state.round:
            dismiss_summon(ctx, summon, "expired")
