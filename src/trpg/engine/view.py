"""依陣營過濾的戰場視圖（Phase 3-1）：把 :class:`~trpg.engine.state.BattleState` 轉成可以交給
某一方玩家的 pydantic 模型，之後直接當 API 回應。

- **不包含**：``rng_state``、``seed``、暫停結算的內部欄位（``base_state_json``、``action_json``、
  ``decisions``、``events_emitted``）、其他陣營的陷阱、``ruleset`` 本體。
- 陷阱一律經過 :func:`trpg.engine.traps.visible_traps`（唯一的陷阱可見性邏輯）。
- 確定性：相同狀態與陣營 → 相同 JSON（單位、物件、陷阱、層數、冷卻都排序；先攻順序保留原順序）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import ReactionRule
from trpg.content.maps import Objective
from trpg.engine.state import BattleState, PendingResolution, StatusInstance, UnitState
from trpg.engine.traps import visible_traps
from trpg.shared.types import Pos, Surface, Team, UnitId

__all__ = [
    "REACTION_TRIGGER_TEXT",
    "BattleView",
    "ObjectView",
    "PendingView",
    "ReactionRuleView",
    "StatusView",
    "TileView",
    "TrapView",
    "UnitView",
    "project_for",
]


class _ViewModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TileView(_ViewModel):
    x: int
    y: int
    height: int
    terrain: str
    surface: Surface
    surface_remaining: int | None
    surface_team: Team | None
    object_id: str | None


class ObjectView(_ViewModel):
    id: str
    kind: str
    pos: Pos
    hp: int | None
    max_hp: int | None
    burning: int | None


class StatusView(_ViewModel):
    status_id: str
    remaining: int | None
    source_id: UnitId | None
    amount: int | None


REACTION_TRIGGER_TEXT: dict[str, str] = {
    "targeted_by_melee": "被近戰攻擊命中時",
    "targeted_by_attack": "被攻擊命中時",
    "enemy_leaves_adjacent": "敵人離開相鄰格時",
    "hit_by_melee": "被近戰攻擊命中後",
    "hit_by_attack": "被攻擊命中後",
    "ally_hit_adjacent": "相鄰友方被攻擊命中時",
}
"""反應規則觸發事件的中文說明（``ReactionWhen.event`` → 文字）。"""


class ReactionRuleView(_ViewModel):
    """單位身上的一條反應規則（玩家可以用 ``set_reaction_mode`` 切換 ``mode``）。"""

    reaction: str
    name_zh: str
    description_zh: str
    event: str
    trigger_zh: str
    mode: Literal["auto", "prompt", "off"]
    unless_stamina_below: int | None
    stamina_cost: int
    mana_cost: int
    hp_cost_permille: int


class UnitView(_ViewModel):
    id: UnitId
    template_id: str
    name_zh: str
    team: Team
    pos: Pos
    hp: int
    max_hp: int
    shield: int
    """護盾的剩餘吸收量（所有吸收傷害的狀態加總）。"""
    mana: int
    max_mana: int
    stamina: int
    max_stamina: int
    ap: int
    move_points: int
    speed: int
    initiative: int
    weapon_name_zh: str
    tags: tuple[str, ...]
    skills: tuple[str, ...]
    """裝備的技能 ID；只有自己陣營的單位會列出（其他陣營的單位為空，避免洩漏陷阱技能）。"""
    statuses: tuple[StatusView, ...]
    stacks: dict[str, int]
    cooldowns: dict[str, int]
    """冷卻中的技能；其他陣營單位的陷阱技能冷卻不列出。"""
    reaction_available: bool
    """還有反應次數，且身上有（未關閉的）反應規則。"""
    reaction_rules: tuple[ReactionRuleView, ...]
    """反應規則與目前模式；只有自己陣營的單位會列出（其他陣營的單位為空）。"""
    ap_carry: int
    """結束回合時保留、下回合開始時加上的 AP（自己的回合中為 0，已併入 ``ap``）。"""
    downed: bool
    escaped: bool


class TrapView(_ViewModel):
    owner_id: UnitId
    team: Team
    pos: Pos
    skill_id: str
    remaining: int


class PendingView(_ViewModel):
    """目前的反應詢問（只有公開欄位；內部的重播資料不外流）。"""

    kind: str
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None
    skill_id: str | None
    trigger_event_seq: int | None
    stamina_cost: int
    mana_cost: int
    hp_cost_permille: int


class BattleView(_ViewModel):
    """``team`` 視角的戰場。"""

    team: Team
    map_id: str
    map_name_zh: str
    width: int
    height: int
    tiles: tuple[TileView, ...]
    """列優先（先 y 後 x）。"""
    objects: tuple[ObjectView, ...]
    units: tuple[UnitView, ...]
    traps: tuple[TrapView, ...]
    """只有 ``team`` 看得見的陷阱（自己陣營放置的）。"""
    turn_order: tuple[UnitId, ...]
    active_unit: UnitId | None
    round: int
    max_rounds: int | None
    weather_id: str | None
    weather_name_zh: str | None
    objective: Objective
    ended: bool
    winner: Team | None
    end_reason: str | None
    pending: PendingView | None


def _status_view(status: StatusInstance) -> StatusView:
    return StatusView(
        status_id=status.status_id,
        remaining=status.remaining,
        source_id=status.source_id,
        amount=status.amount,
    )


def _visible_cooldowns(state: BattleState, unit: UnitState, team: Team) -> dict[str, int]:
    """冷卻中的技能；其他陣營看不到陷阱技能的冷卻（否則會洩漏「剛放過陷阱」）。"""
    cooldowns = sorted(unit.cooldowns.items())
    if unit.team is not team:
        cooldowns = [(s, n) for s, n in cooldowns if state.ruleset.skill_def(s).trap is None]
    return dict(cooldowns)


def _rule_view(state: BattleState, unit: UnitState, rule: ReactionRule) -> ReactionRuleView:
    rules = state.ruleset
    if rule.reaction in unit.skills:  # 反應技：規則的 reaction 是技能 ID
        skill = rules.skill_def(rule.reaction)
        name, description = skill.name_zh, skill.narrative.concept
        stamina, mana, hp = 0, skill.cost.mana, skill.cost.hp_percent or 0
    else:
        definition = rules.reaction_def(rule.reaction)
        name, description = definition.name_zh, definition.description_zh
        stamina, mana, hp = definition.stamina_cost, 0, 0
    return ReactionRuleView(
        reaction=rule.reaction,
        name_zh=name,
        description_zh=description,
        event=rule.when.event,
        trigger_zh=REACTION_TRIGGER_TEXT[rule.when.event],
        mode=rule.mode,
        unless_stamina_below=None if rule.unless is None else rule.unless.self_stamina_below,
        stamina_cost=stamina,
        mana_cost=mana,
        hp_cost_permille=hp,
    )


def _unit_view(state: BattleState, unit: UnitState, team: Team) -> UnitView:
    per_round = state.ruleset.core.reactions_per_round
    return UnitView(
        id=unit.id,
        template_id=unit.template_id,
        name_zh=unit.name_zh,
        team=unit.team,
        pos=unit.pos,
        hp=unit.hp,
        max_hp=unit.max_hp,
        shield=sum(s.amount for s in unit.statuses if s.amount is not None),
        mana=unit.mana,
        max_mana=unit.max_mana,
        stamina=unit.stamina,
        max_stamina=unit.max_stamina,
        ap=unit.ap,
        move_points=unit.move_points,
        speed=unit.speed,
        initiative=unit.initiative,
        weapon_name_zh=unit.weapon.name_zh,
        tags=unit.tags,
        skills=unit.skills if unit.team is team else (),
        statuses=tuple(_status_view(s) for s in unit.statuses),
        stacks=dict(sorted(unit.stacks.items())),
        cooldowns=_visible_cooldowns(state, unit, team),
        reaction_available=unit.alive
        and any(r.mode != "off" for r in unit.reactions)
        and unit.reactions_used < per_round,
        reaction_rules=(
            tuple(_rule_view(state, unit, r) for r in unit.reactions) if unit.team is team else ()
        ),
        ap_carry=unit.ap_carry,
        downed=unit.downed,
        escaped=unit.escaped,
    )


def _pending_view(pending: PendingResolution) -> PendingView:
    return PendingView(
        kind=pending.kind,
        unit_id=pending.unit_id,
        reaction=pending.reaction,
        trigger_unit_id=pending.trigger_unit_id,
        skill_id=pending.skill_id,
        trigger_event_seq=pending.trigger_event_seq,
        stamina_cost=pending.stamina_cost,
        mana_cost=pending.mana_cost,
        hp_cost_permille=pending.hp_cost_permille,
    )


def project_for(state: BattleState, team: Team) -> BattleView:
    """``team`` 看得到的戰場。純函式；暫停中的狀態也可以。"""
    tiles = tuple(
        TileView(
            x=x,
            y=y,
            height=t.height,
            terrain=t.terrain,
            surface=t.surface,
            surface_remaining=t.surface_remaining,
            surface_team=t.surface_team,
            object_id=t.object_id,
        )
        for y in range(state.height)
        for x in range(state.width)
        for t in (state.tile(x, y),)
    )
    return BattleView(
        team=team,
        map_id=state.map_id,
        map_name_zh=state.map_name_zh,
        width=state.width,
        height=state.height,
        tiles=tiles,
        objects=tuple(
            ObjectView(id=o.id, kind=o.kind, pos=o.pos, hp=o.hp, max_hp=o.max_hp, burning=o.burning)
            for o in state.objects_sorted()
        ),
        units=tuple(_unit_view(state, u, team) for u in state.units_sorted()),
        traps=tuple(
            TrapView(
                owner_id=t.owner_id,
                team=t.team,
                pos=t.pos,
                skill_id=t.skill_id,
                remaining=t.remaining,
            )
            for t in sorted(visible_traps(state, team), key=lambda t: (t.pos.y, t.pos.x))
        ),
        turn_order=tuple(state.turn_order),
        active_unit=state.active_unit,
        round=state.round,
        max_rounds=state.max_rounds,
        weather_id=None if state.weather is None else state.weather.id,
        weather_name_zh=None if state.weather is None else state.weather.name_zh,
        objective=state.objective,
        ended=state.ended,
        winner=state.winner,
        end_reason=state.end_reason,
        pending=None if state.pending is None else _pending_view(state.pending),
    )
