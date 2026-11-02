"""優先處理的目標與治療型強招的估值（Phase 5A-M1）。

- **先打補師**（``docs/design/18-雲嶺內容.md`` 18.2.1）：擊倒帶「同門相護」反應（``shield_ally``）
  的敵人，額外 ``rewrite.priority_kill_points``。
- **打斷強招**（05 5.7 強招預告、06 6.23 #5）：擊倒正在蓄力（``charging``）的敵人、或讓它帶上
  跳過回合的狀態（暈眩、冰凍；蓄力會被取消）、
  或沉默（只對法術型蓄力，5A-M1b），額外 ``rewrite.interrupt_points``。
- **治療型延遲段**（九轉回天）：開始蓄力時，預計範圍內每個受傷的友方（含自己）
  ``rewrite.delayed_heal_points``。
- **打散陣型**（Phase 5A-M2，18.2.1「劍陣」）：動作後對方存活的陣法持有者的倍率總和下降量
  ÷ 1000 × ``rewrite.formation_break_points``（擊倒、推開、拉走同門都算）。
- **連心**（Phase 5A-M2，詞綴「連心的」）：預覽中對方分傷持有者分給同門的傷害（min／max 平均 ×
  命中率）× ``rewrite.share_discount_permille`` ÷ 1000，從傷害收益扣掉——集火持有者的效益下降。

點數是「等值傷害點數」，收益 ＝ 行為模式的 ``damage`` 權重 × 點數；擊倒照 :func:`_kill_gains`
的機率（確定 × 命中率、只是可能 × 命中率 ÷ 4）。只有目標帶這些特性時才有分數，其他戰鬥不受影響。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import RewriteAiRules
from trpg.content.skills import CHARGING
from trpg.engine.delayed import silence_breaks_charge
from trpg.engine.events import (
    DamageRedirected,
    EventBase,
    FollowupCharged,
    StatusApplied,
    UnitDowned,
)
from trpg.engine.formation import formation_permille, formation_specs
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = [
    "delayed_heal_points",
    "formation_break",
    "is_kin_warden",
    "priority_points",
    "share_discount",
]

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


def _formation_total(state: BattleState, team: object) -> int:
    """``team`` 以外的陣營中，存活的陣法持有者的倍率（‰）總和。"""
    return sum(
        formation_permille(state, u)
        for u in state.living_units()
        if u.team is not team and formation_specs(state, u)
    )


def formation_break(
    state: BattleState, after: BattleState, actor: UnitState, rules: RewriteAiRules
) -> Fraction:
    """打散陣型（見模組說明）：只計動作前後都還存活的對方陣法持有者（擊倒持有者本身由擊倒計分）；
    倍率總和下降才有分，上升（例如把同門推進範圍）不扣分。"""
    if not rules.formation_break_points:
        return Fraction(0)
    holders = [
        u.id for u in state.living_units() if u.team is not actor.team and formation_specs(state, u)
    ]
    survivors = [uid for uid in holders if uid in after.units and after.units[uid].alive]
    if not survivors:
        return Fraction(0)
    before = sum(formation_permille(state, state.units[uid]) for uid in survivors)
    now = sum(formation_permille(after, after.units[uid]) for uid in survivors)
    drop = before - now
    if drop <= 0:
        return Fraction(0)
    return Fraction(drop * rules.formation_break_points, 1000)


def share_discount(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    min_events: tuple[EventBase, ...],
    max_events: tuple[EventBase, ...],
    hit: Fraction,
    rules: RewriteAiRules,
    only: UnitId | None = None,
) -> Fraction:
    """連心（見模組說明）：對方分傷持有者分給同門的傷害 × 折扣的等值點數（要扣掉的）。靈魂連結
    （``redirect_damage``）不算。"""
    if not rules.share_discount_permille:
        return Fraction(0)
    total = Fraction(0)
    for events in (min_events, max_events):
        for e in events:
            if not isinstance(e, DamageRedirected) or (only is not None and e.from_id != only):
                continue
            holder = state.units.get(e.from_id)
            if holder is None or holder.team is actor.team:
                continue
            if state.ruleset.status_def(e.status_id).share_damage is None:
                continue
            total += e.amount
    return total / 2 * hit * rules.share_discount_permille / 1000
