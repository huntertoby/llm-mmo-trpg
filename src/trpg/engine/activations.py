"""常駐類傳說的啟動（Phase 3D-6，``docs/design/06-技能.md`` 6.14.4、6.16 F）。

修正型傳說（``kind: modifier``）與規則改變型傳說（``rule_change`` 原語）寫了 ``activation``：
以 ``UseSkill`` 花 ``legendary_activation_ap`` AP ＋ 源力啟動，啟動前修正規則與規則改變都不生效。

- ``timed``：持續 ``legendary_timed_rounds`` 輪——``expires_round`` ＝ 啟動輪 ＋ N，持有者在那一輪
  （或之後）的回合開始時結束（:func:`expire_activations`），所以持有者連同啟動的那一回合共有 N 個
  回合，中間其他單位的回合也都有效。
- ``battle``：本場剩餘時間有效。
- 生效中的同一技能不能再啟動；每個單位同時最多 1 個生效中的規則改變。

生效中的狀態存在 :attr:`~trpg.engine.state.UnitState.activations`（可序列化、可重播）。這個模組的
查詢函式只讀狀態，引擎各處（修正規則、傷害、推動物件、移動、倒下）用它們判斷規則是否生效。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.rule_changes import PUSH_ANY_OBJECT, RuleChangeDef
from trpg.content.skills import SkillDef
from trpg.engine.events import ActivationExpired, SkillActivated
from trpg.engine.state import Activation, BattleState, UnitState
from trpg.shared.types import UnitId

if TYPE_CHECKING:
    from trpg.engine.context import Ctx

__all__ = [
    "ActiveRuleChange",
    "activate",
    "activation_problem",
    "active_rule_change",
    "expire_activations",
    "is_active",
    "moves_object",
    "remaining_rounds",
]


def is_active(unit: UnitState, skill_id: str) -> bool:
    """``unit`` 的常駐類傳說 ``skill_id`` 目前生效中。"""
    return any(a.skill_id == skill_id for a in unit.activations)


def remaining_rounds(state: BattleState, activation: Activation) -> int | None:
    """限時傳說還剩幾輪（持有者還有幾個回合可用，含目前這一輪）；整場為 ``None``。"""
    if activation.expires_round is None:
        return None
    return max(activation.expires_round - state.round, 0)


def _rule_of(state: BattleState, skill: SkillDef) -> RuleChangeDef | None:
    rule_id = skill.rule_change_id
    return None if rule_id is None else state.ruleset.rule_change_def(rule_id)


def activation_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """常駐類傳說現在不能啟動的原因（已在生效中、已有別的規則改變生效中）；可以時為 ``None``。"""
    if not skill.is_activatable:
        return None
    for activation in unit.activations:
        if activation.skill_id == skill.id:
            left = remaining_rounds(state, activation)
            when = "整場有效" if left is None else f"還剩 {left} 輪"
            return f"「{skill.name_zh}」已經啟動（{when}）"
    if skill.rule_change_id is not None:
        other = active_rule_change(state, unit)
        if other is not None:
            return f"已有生效中的規則改變「{other.skill.name_zh}」（每個單位同時最多 1 個）"
    return None


def activate(ctx: Ctx, unit: UnitState, skill: SkillDef) -> None:
    """啟動 ``skill``（代價已由呼叫端支付）：加進 ``unit.activations``，發出
    ``skill_activated``。"""
    assert skill.activation is not None
    state = ctx.state
    expires = (
        None if skill.activation == "battle" else state.round + ctx.core.legendary_timed_rounds
    )
    unit.activations = (*unit.activations, Activation(skill_id=skill.id, expires_round=expires))
    ctx.emit(
        SkillActivated,
        unit_id=unit.id,
        skill_id=skill.id,
        activation=skill.activation,
        expires_round=expires,
        rule=skill.rule_change_id,
    )


def expire_activations(ctx: Ctx, unit: UnitState) -> None:
    """持有者的回合開始：到期（``expires_round`` ≤ 目前輪數）的限時傳說結束（依啟動順序）。"""
    if not unit.activations:
        return
    now = ctx.state.round
    kept: list[Activation] = []
    for activation in unit.activations:
        if activation.expires_round is not None and activation.expires_round <= now:
            ctx.emit(ActivationExpired, unit_id=unit.id, skill_id=activation.skill_id)
        else:
            kept.append(activation)
    unit.activations = tuple(kept)


class ActiveRuleChange:
    """``unit`` 生效中的規則改變：來源技能與規則（每個單位最多 1 個）。"""

    __slots__ = ("rule", "skill")

    def __init__(self, skill: SkillDef, rule: RuleChangeDef) -> None:
        self.skill = skill
        self.rule = rule


def active_rule_change(
    state: BattleState, unit: UnitState | None, kind: str | None = None
) -> ActiveRuleChange | None:
    """``unit`` 生效中的規則改變（``kind`` 給定時只找這一類）；沒有時為 ``None``。"""
    if unit is None or not unit.activations:
        return None
    rules = state.ruleset
    for activation in unit.activations:
        skill = rules.skill_def(activation.skill_id)
        rule = _rule_of(state, skill)
        if rule is not None and (kind is None or rule.kind == kind):
            return ActiveRuleChange(skill, rule)
    return None


_FLOOR_TAGS = ("over_chasm",)
"""架在地形上、算地面一部分的物件（木橋、薄冰）：「移山」也推不動（不含地形）。"""


def moves_object(
    state: BattleState, pusher_id: UnitId | None, tags: tuple[str, ...]
) -> ActiveRuleChange | None:
    """規則改變 ``push_any_object``（Phase 3D-6）讓 ``pusher_id`` 能推動這個本來推不動的物件時，
    回傳生效中的規則改變；本來就能推（``pushable``）、不是擋路的物件（``blocks_move``）、
    是地面的一部分（``over_chasm``），或沒有這個規則改變時為 ``None``。可推倒的物件
    （``topplable``）照樣倒下，由呼叫端先處理。"""
    if pusher_id is None or "pushable" in tags or "blocks_move" not in tags:
        return None
    if any(t in tags for t in _FLOOR_TAGS):
        return None
    return active_rule_change(state, state.units.get(pusher_id), PUSH_ANY_OBJECT)
