"""自己付的代價的 AI 使用條件（Phase 3-50，06 6.5 共通規則 6；數值在 ``self_cost:``）。

- **自暈**（``cost.self_status`` 是會跳過回合的狀態，例暈眩）：施放者 HP 低於
  ``stun_hp_below_permille`` 且 ``stun_enemy_radius`` 格內有敵人（暈眩換護盾是保命用，沒有危險時
  不自廢一個回合）。
- **透支**（``cost.overdraft``）：這一擊能擊殺敵人，或波及的敵人至少 ``overdraft_min_targets`` 個。

- **預支**（``borrow_ap``，AP-2，06 6.3）：只在本回合差 AP、湊不出大招時才用——手上有另一招
  主動技能（姿態、修正型傳說的啟動也算）現在 AP 不夠、預支後就夠，而且除了 AP 之外都能施放。

其他自身狀態沒有額外條件（照 ``skill_cost`` 的機會成本評分）。條件不成立時，技能的分數壓到負數
（比結束回合差），AI 不會選它。
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.skills import SkillDef
from trpg.engine.preview import Preview
from trpg.engine.rewrites import borrow_gain
from trpg.engine.rules.footprint import unit_dist
from trpg.engine.skills.targeting import skill_ap_cost, skill_problem
from trpg.engine.state import BattleState, UnitState

__all__ = ["borrow_allowed", "self_cost_gate"]

_PERMILLE = 1000
_BLOCKED = Fraction(-1)


def _stun_allowed(state: BattleState, actor: UnitState, profile: AiProfile) -> bool:
    rules = profile.self_cost
    if actor.hp * _PERMILLE >= actor.max_hp * rules.stun_hp_below_permille:
        return False
    return any(
        unit_dist(actor, u) <= rules.stun_enemy_radius
        for u in state.living_units()
        if u.team is not actor.team
    )


def _overdraft_allowed(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile
) -> bool:
    enemies = [
        uid
        for uid in p.affected_units
        if (u := state.units.get(uid)) is not None and u.alive and u.team is not actor.team
    ]
    if len(enemies) >= profile.self_cost.overdraft_min_targets:
        return True
    return any(not p.max_state.units[uid].alive for uid in enemies)


def borrow_allowed(state: BattleState, actor: UnitState, skill: SkillDef) -> bool:
    """預支（AP-2）的使用條件：預支後才放得出的另一招（見模組說明）。"""
    amount = sum(e.amount or 1 for e in skill.effects if e.type == "borrow_ap")
    gain = borrow_gain(state.ruleset.core, actor, amount)
    if gain <= 0:
        return False
    richer = dataclasses.replace(actor, ap=actor.ap + gain)
    for skill_id in actor.skills:
        other = state.ruleset.skill_def(skill_id)
        if other.id == skill.id or other.borrows_ap or not other.is_actionable:
            continue
        cost = skill_ap_cost(state, other, actor)
        if actor.ap < cost <= actor.ap + gain and skill_problem(state, richer, other) is None:
            return True
    return False


def self_cost_gate(
    state: BattleState,
    actor: UnitState,
    skill: SkillDef,
    p: Preview,
    profile: AiProfile,
    *,
    score: Fraction,
) -> Fraction:
    """使用條件不成立的自身代價技能，分數壓成負數；其他情形原分數。"""
    status = skill.cost.self_status
    stun = status is not None and state.ruleset.status_def(status.status).skip_turn
    if stun and not _stun_allowed(state, actor, profile):
        return min(score, _BLOCKED)
    if skill.cost.overdraft is not None and not _overdraft_allowed(state, actor, p, profile):
        return min(score, _BLOCKED)
    if skill.borrows_ap and not borrow_allowed(state, actor, skill):
        return min(score, _BLOCKED)
    return score
