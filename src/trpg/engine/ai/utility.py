"""效用評分 AI（``docs/專案計畫.md`` 5.9）：對每個合法動作跑 ``preview`` 評分，取最高分。

分數 ＝ 預覽收益 ＋ 命中率 × Σ 權重 × (動作後的位置價值 − 動作前的位置價值)，權重來自
``content/ai_profiles.yaml`` 的行為模式（莽夫、弓手、狡猾、守衛）。分數為正的動作中取最高者，
平手依 ``legal_actions`` 的順序；沒有正分的動作時結束回合。全部以 :class:`~fractions.Fraction`
計算，完全確定。

收益的估計：攻擊主要目標的傷害用預覽的精確期望值；其他傷害（爆炸、擴散……）取最少與最多後果
的平均再乘上命中率；「確定」的連鎖乘上命中率，「只是可能」的擊倒再除以 4。這些是啟發式，
供 Phase 2 以模擬調整。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import AiProfile, AiProfileTable, AiWeights
from trpg.engine.actions import Action, Attack, Defend, EndTurn
from trpg.engine.battle import legal_actions
from trpg.engine.events import DamageDealt, EventBase, StatusApplied, UnitDowned, UnitMoved
from trpg.engine.preview import Preview, preview
from trpg.engine.rules.combat import attack_problem
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface, Team, UnitId

__all__ = ["ActionScore", "UtilityAI", "position_value", "score_action"]

_DEFEND_RADIUS = 6
_POSSIBLE_KILL_DIVISOR = 4
_DOWNED_PENALTY = 1000
_ESCAPED_BONUS = 1000
_ATTACK_CAUSES = ("attack",)


@dataclass(frozen=True, slots=True)
class ActionScore:
    action: Action
    score: Fraction
    preview: Preview | None


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team]


def _harmful(state: BattleState, xy: tuple[int, int]) -> bool:
    surface = state.tile(*xy).surface
    if surface is Surface.NONE:
        return False
    definition = state.ruleset.surface_def(surface)
    start = definition.on_turn_start
    enter = definition.on_enter
    if start is not None:
        if start.damage is not None and start.damage.only_tag is None:
            return True
        if start.apply_status is not None:
            return True
    return enter is not None and enter.apply_status is not None


def _objective_distance(state: BattleState, unit: UnitState) -> int:
    objective = state.objective
    if objective.kind == "eliminate" or not objective.tiles:
        return 0
    if objective.kind == "escape" and unit.team is not Team.ALLY:
        return 0
    return min(manhattan(unit.xy, t) for t in objective.tiles)


def _protect_distance(state: BattleState, unit: UnitState) -> int:
    allies = [u for u in state.living_units() if u.team is unit.team and u.id != unit.id]
    if not allies:
        return 0
    ward = min(allies, key=lambda u: (Fraction(u.hp, u.max_hp), u.id))
    return manhattan(unit.xy, ward.xy)


def position_value(state: BattleState, unit_id: UnitId, w: AiWeights) -> Fraction:
    """行動者在 ``state`` 中所在位置的價值。"""
    unit = state.units[unit_id]
    if unit.escaped:
        return Fraction(_ESCAPED_BONUS * max(w.objective, 1))
    if unit.downed:
        return Fraction(-_DOWNED_PENALTY)
    enemies = _enemies(state, unit)
    value = 0
    if enemies:
        value -= w.approach * min(manhattan(unit.xy, e.xy) for e in enemies)
        value += w.threat * sum(1 for e in enemies if attack_problem(state, unit, e) is None)
        value -= w.keep_distance * sum(1 for e in enemies if manhattan(unit.xy, e.xy) <= 2)  # noqa: PLR2004
    value += w.height * state.tile(*unit.xy).height
    value -= w.protect * _protect_distance(state, unit)
    value -= w.objective * _objective_distance(state, unit)
    if _harmful(state, unit.xy):
        value -= w.hazard
    return Fraction(value)


def _last_cause(events: tuple[EventBase, ...]) -> dict[UnitId, str]:
    cause: dict[UnitId, str] = {}
    for e in events:
        if isinstance(e, DamageDealt):
            cause[e.target_id] = e.cause
    return cause


def _gains(state: BattleState, actor: UnitState, p: Preview, w: AiWeights) -> Fraction:  # noqa: PLR0912
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    team = actor.team

    def is_enemy(uid: UnitId) -> bool:
        return state.units[uid].team is not team if uid in state.units else False

    primary = None
    if isinstance(p.action, Attack) and p.action.target_id is not None and p.damage is not None:
        primary = p.action.target_id
    gains = Fraction(0)
    # 傷害：主要傷害用精確期望；其他取 min/max 平均 × 命中率
    other_enemy = Fraction(0)
    env_enemy = Fraction(0)
    friendly = Fraction(0)
    for events in (p.min_events, p.max_events):
        primary_seen = False
        for e in events:
            if not isinstance(e, DamageDealt) or e.cause == "deadly_terrain":
                continue  # 致命地形的「傷害」是擊倒本身，由 kill／env_kill 計分
            if e.target_id == primary and e.cause == "attack" and not primary_seen:
                primary_seen = True
                continue
            if is_enemy(e.target_id):
                other_enemy += e.amount
                if e.cause not in _ATTACK_CAUSES:
                    env_enemy += e.amount
            elif e.target_id in state.units:
                friendly += e.amount
    if p.damage is not None and primary is not None:
        gains += w.damage * p.damage.expected
    gains += w.damage * hit * other_enemy / 2
    gains += w.env_damage * hit * env_enemy / 2
    gains -= w.friendly_fire * friendly / 2
    # 擊倒
    certain_down = {e.unit_id for e in p.min_events if isinstance(e, UnitDowned)}
    possible_down = {e.unit_id for e in p.max_events if isinstance(e, UnitDowned)} - certain_down
    causes = _last_cause(p.max_events) | _last_cause(p.min_events)
    for uid, factor in [(u, hit) for u in sorted(certain_down)] + [
        (u, hit / _POSSIBLE_KILL_DIVISOR) for u in sorted(possible_down)
    ]:
        if is_enemy(uid):
            gains += w.kill * factor
            if causes.get(uid, "attack") not in _ATTACK_CAUSES:
                gains += w.env_kill * factor
        elif uid in state.units:
            gains -= w.kill * factor
    # 推擊、狀態、表面
    pushed = {
        e.unit_id
        for e in p.min_events
        if isinstance(e, UnitMoved) and e.mode == "forced" and is_enemy(e.unit_id)
    }
    gains += w.push * hit * len(pushed)
    statuses = {
        (e.target_id, e.status_id)
        for e in p.min_events
        if isinstance(e, StatusApplied) and is_enemy(e.target_id)
    }
    gains += w.status * hit * len(statuses)
    after = p.min_state
    before_harm = sum(1 for u in _enemies(state, actor) if _harmful(state, u.xy))
    after_harm = sum(
        1 for u in after.living_units() if u.team is not team and _harmful(after, u.xy)
    )
    gains += w.surface * hit * (after_harm - before_harm)
    if isinstance(p.action, Defend):
        near = sum(1 for e in _enemies(state, actor) if manhattan(actor.xy, e.xy) <= _DEFEND_RADIUS)
        gains += w.defend * near
    return gains


def score_action(state: BattleState, action: Action, profile: AiProfile) -> ActionScore:
    """單一動作的分數（``EndTurn`` 固定為 0）。"""
    if isinstance(action, EndTurn):
        return ActionScore(action, Fraction(0), None)
    w = profile.weights
    actor = state.units[action.unit_id]
    p = preview(state, action)
    before = position_value(state, actor.id, w)
    after = position_value(p.min_state, actor.id, w)
    # 位置變化只在動作成功時發生（攻擊、技巧動作乘上命中率／成功率）
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    return ActionScore(action, _gains(state, actor, p, w) + hit * (after - before), p)


class UtilityAI:
    """效用評分 AI（可當作 ``Policy`` 使用：``UtilityAI(profiles)(state) -> Action``）。

    行動者的行為模式取 ``UnitState.ai_profile``；``override`` 可強制所有單位使用同一模式
    （測試用）。
    """

    def __init__(self, profiles: AiProfileTable, *, override: str | None = None) -> None:
        self._profiles = profiles.by_id()
        self._override = override

    def profile_for(self, unit: UnitState) -> AiProfile:
        key = self._override or unit.ai_profile or "brute"
        return self._profiles.get(key, self._profiles["brute"])

    def rank(self, state: BattleState) -> list[ActionScore]:
        """所有合法動作的分數（依 ``legal_actions`` 的順序）。"""
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        return [score_action(state, a, profile) for a in legal_actions(state)]

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        best: ActionScore | None = None
        for scored in self.rank(state):
            if scored.score > 0 and (best is None or scored.score > best.score):
                best = scored
        return best.action if best is not None else EndTurn(unit_id=unit.id)
