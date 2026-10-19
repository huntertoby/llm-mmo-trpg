"""持續區域的 AI（Phase 3D-5，最簡單的近似；係數在 ``content/ai_profiles.yaml`` 的 ``zone:``）。

- **選位置**（:func:`zone_estimate`，不跑引擎）：以「區域格內與移動路徑上的對象數」評分——有害區域
  數敵人（``affects: all`` 時扣掉格內的友方），有益區域數友方（含自己）；沒有對象時不納入候選。
- **評分**（:func:`zone_gains`，預覽收益的一部分）：建立當下就在區域內的對象由預覽事件計算；之後的
  觸發估計為「每次觸發的價值 × 格內與路徑上的對象數 × 持續輪數 × ``likelihood_permille``」。
- **避開**（:func:`hostile_zone_at`）：AI 計算位置價值時，把敵方會傷害自己的區域格當成有害表面。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.skills import ZONE, EffectSpec, SkillDef
from trpg.engine.events import EventBase, ZoneCreated
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.skills import shapes
from trpg.engine.state import BattleState, UnitState
from trpg.engine.zones import affects_team, zone_cells, zone_is_harmful, zone_spec
from trpg.shared.types import Team

__all__ = ["hostile_zone_at", "is_zone_skill", "zone_estimate", "zone_gains"]

_PERMILLE = 1000


def is_zone_skill(skill: SkillDef) -> bool:
    return any(e.type == ZONE for e in skill.effects)


def hostile_zone_at(state: BattleState, xy: XY, team: Team) -> bool:
    """``xy`` 在別的陣營建立、會對 ``team`` 結算有害效果的區域內。"""
    for zone in state.zones:
        if zone.team is team and zone_spec(state, zone).affects != "all":
            continue
        if not affects_team(state, zone, team) or not zone_is_harmful(
            state, zone_spec(state, zone)
        ):
            continue
        if xy in zone_cells(state, zone):
            return True
    return False


def _path(state: BattleState, cells: tuple[XY, ...], direction: XY, steps: int) -> set[XY]:
    """移動型區域之後 ``steps`` 格會經過的格子（不含目前的格子；只看幾何）。"""
    seen: set[XY] = set()
    current = set(cells)
    for _ in range(steps):
        current = {
            (x + direction[0], y + direction[1])
            for x, y in current
            if shapes.in_play(state, (x + direction[0], y + direction[1]))
        }
        seen |= current
    return seen - set(cells)


def _counts(
    state: BattleState, unit: UnitState, spec: EffectSpec, cells: tuple[XY, ...], path: set[XY]
) -> tuple[int, int]:
    """區域格內、路徑上的「對象」數（有害區域：敵人；有益區域：友方，含自己）。"""
    harmful = zone_is_harmful(state, spec)
    inside = 0
    along = 0
    covered = set(cells)
    for other in state.living_units():
        wanted = (other.team is not unit.team) if harmful else (other.team is unit.team)
        if other.xy in covered:
            if wanted:
                inside += 1
            elif harmful and spec.affects == "all":
                inside -= 1
        elif wanted and other.xy in path:
            along += 1
    return inside, along


def _zone_geometry(
    state: BattleState, spec: EffectSpec, cells: tuple[XY, ...], direction: XY | None
) -> set[XY]:
    if spec.anchor != "moving" or direction is None or spec.duration is None:
        return set()
    return _path(state, cells, direction, spec.duration * (spec.speed or 1))


def zone_estimate(
    state: BattleState,
    unit: UnitState,
    skill: SkillDef,
    *,
    tiles: tuple[XY, ...],
    direction: XY | None,
    origin: XY,
) -> Fraction | None:
    """區域選取的便宜估計：格內對象 × 3 ＋ 路徑上的對象 × 2；沒有對象時 ``None``。"""
    spec = next(e for e in skill.effects if e.type == ZONE)
    path = _zone_geometry(state, spec, tiles, direction)
    inside, along = _counts(state, unit, spec, tiles, path)
    score = 3 * inside + 2 * along
    if score <= 0:
        return None
    return Fraction(score) - Fraction(manhattan(unit.xy, origin), _PERMILLE)


def _status_value(state: BattleState, status_id: str, profile: AiProfile) -> Fraction:
    """區域施加一次狀態的價值：增益用 ``ally_status_values`` × ``support``（沒列出的用 3），
    減益用 ``status_values`` × ``damage``（沒列出的用 ``status`` 權重）。"""
    w = profile.weights
    if state.ruleset.status_def(status_id).beneficial:
        return Fraction(w.support * profile.ally_status_values.get(status_id, 3))
    points = profile.status_values.get(status_id)
    return Fraction(w.status) if points is None else Fraction(w.damage * points)


def _trigger_value(state: BattleState, spec: EffectSpec, profile: AiProfile) -> Fraction:
    """區域每次觸發的價值（等值傷害點數 × 權重）。"""
    w = profile.weights
    value = Fraction(0)
    for sub in spec.effects or ():
        dice = sub.dice
        average = Fraction(0) if dice is None else Fraction(dice.count * (dice.sides + 1), 2)
        if sub.type == "damage":
            value += w.damage * average
        elif sub.type == "heal":
            value += w.heal * average
        elif sub.type == "shield":
            value += w.shield * (sub.amount or average)
        elif sub.type == "apply_status" and sub.status is not None:
            value += _status_value(state, sub.status, profile)
    return value


def zone_gains(
    state: BattleState, actor: UnitState, events: Sequence[EventBase], profile: AiProfile
) -> Fraction:
    """預覽事件中建立的區域之後的預估收益（``state`` 為動作前的狀態）。"""
    gains = Fraction(0)
    rules = profile.zone
    for e in events:
        if not isinstance(e, ZoneCreated) or e.owner_id != actor.id:
            continue
        spec = state.ruleset.skill_def(e.skill_id).effects[0]
        cells = tuple((p.x, p.y) for p in e.cells)
        direction = None if e.direction is None else shapes.DIRECTIONS[e.direction]
        path = _zone_geometry(state, spec, cells, direction)
        inside, along = _counts(state, actor, spec, cells, path)
        targets = Fraction(max(inside, 0)) + Fraction(along * rules.path_permille, _PERMILLE)
        rounds = max(e.expires_round - state.round, 0)
        gains += (
            _trigger_value(state, spec, profile)
            * targets
            * rounds
            * Fraction(rules.likelihood_permille, _PERMILLE)
        )
    return gains
