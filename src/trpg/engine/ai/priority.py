"""優先處理的目標與治療型強招的估值（Phase 5A-M1）。

- **先打補師**（``docs/design/18-雲嶺內容.md`` 18.2.1）：擊倒帶「同門相護」反應（``shield_ally``）
  的敵人，額外 ``rewrite.priority_kill_points``。
- **打斷強招**（05 5.7 強招預告、06 6.23 #5）：擊倒正在蓄力（``charging``）的敵人、或讓它帶上
  跳過回合的狀態（暈眩、冰凍；蓄力會被取消）、
  或沉默（只對法術型蓄力，5A-M1b），額外 ``rewrite.interrupt_points``。
- **治療型延遲段**（九轉回天）：開始蓄力時，預計範圍內每個受傷的友方（含自己）
  ``rewrite.delayed_heal_points``。

點數是「等值傷害點數」，收益 ＝ 行為模式的 ``damage`` 權重 × 點數；擊倒照 :func:`_kill_gains`
的機率（確定 × 命中率、只是可能 × 命中率 ÷ 4）。只有目標帶這些特性時才有分數，其他戰鬥不受影響。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import RewriteAiRules
from trpg.content.skills import CHARGING
from trpg.engine.delayed import silence_breaks_charge
from trpg.engine.events import EventBase, FollowupCharged, StatusApplied, UnitDowned
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = ["delayed_heal_points", "is_kin_warden", "priority_points"]

_POSSIBLE_DIVISOR = 4
"""只在最多結果裡發生的擊倒 ÷ 這個數（同 ``utility._POSSIBLE_KILL_DIVISOR``）。"""


def is_kin_warden(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 有一條沒關掉的「同門相護」（``shield_ally``）反應規則。"""
    for rule in unit.reactions:
        if rule.mode == "off" or rule.reaction in unit.skills:
            continue
        if state.ruleset.reaction_def(rule.reaction).effect == "shield_ally":
            return True
    return False


def _kill_value(state: BattleState, unit: UnitState, rules: RewriteAiRules) -> int:
    value = rules.priority_kill_points if is_kin_warden(state, unit) else 0
    if unit.has_status(CHARGING):
        value += rules.interrupt_points
    return value


def priority_points(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    min_events: tuple[EventBase, ...],
    max_events: tuple[EventBase, ...],
    hit: Fraction,
    rules: RewriteAiRules,
    only: UnitId | None = None,
) -> Fraction:
    """預覽事件中「優先處理」的點數（見模組說明）；``only`` 給定時只計該單位。"""
    certain = {e.unit_id for e in min_events if isinstance(e, UnitDowned)}
    possible = {e.unit_id for e in max_events if isinstance(e, UnitDowned)} - certain
    points = Fraction(0)
    for uid, factor in [(u, hit) for u in sorted(certain)] + [
        (u, hit / _POSSIBLE_DIVISOR) for u in sorted(possible)
    ]:
        unit = state.units.get(uid)
        if unit is None or unit.team is actor.team or (only is not None and uid != only):
            continue
        points += factor * _kill_value(state, unit, rules)
    controlled: set[UnitId] = set()
    for e in min_events:
        if not isinstance(e, StatusApplied) or e.target_id in certain | controlled:
            continue
        target = state.units.get(e.target_id)
        if target is None or target.team is actor.team or not target.has_status(CHARGING):
            continue
        definition = state.ruleset.status_def(e.status_id)
        if only is not None and target.id != only:
            continue
        if not definition.skip_turn and not (
            definition.blocks_spells and silence_breaks_charge(state, target)
        ):
            continue
        controlled.add(target.id)
        points += hit * rules.interrupt_points
    return points


def delayed_heal_points(
    state: BattleState, actor: UnitState, event: FollowupCharged, rules: RewriteAiRules
) -> Fraction | None:
    """``event``（``actor`` 開始蓄力）的第二段是治療時：預計範圍內受傷友方（含自己）數 ×
    ``delayed_heal_points``；不是治療型延遲段時為 ``None``（照原本的敵人數估值）。"""
    if event.direction is not None:
        return None
    skill = state.ruleset.skill_def(event.skill_id)
    follow = skill.followup_skill()
    if follow is None or not any(e.type == "heal" for e in follow.effects):
        return None
    tiles = {(t.x, t.y) for t in event.tiles}
    hurt = [
        u
        for u in state.living_units()
        if u.team is actor.team and u.xy in tiles and u.hp < u.max_hp
    ]
    return Fraction(len(hurt) * rules.delayed_heal_points)
