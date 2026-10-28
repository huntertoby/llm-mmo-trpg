"""位移與場景物件原語：推、拉、傳送、跳躍、交換、直線衝撞、擊倒、推倒、投擲物件。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from trpg.content.skills import (
    CHARGE_THROUGH,
    ConditionSpec,
    EffectSpec,
    is_wind_skill,
)
from trpg.engine import modifiers
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    EffectBase,
    HurlObjectEffect,
    MoveUnitEffect,
    PushEffect,
    SwapUnitsEffect,
)
from trpg.engine.events import (
    EffectFizzled,
    UnitCharged,
)
from trpg.engine.ids import PRONE, TOPPLABLE
from trpg.engine.maneuvers import contest
from trpg.engine.reactions import (
    enemy_enters_adjacent_reactions,
    enemy_moves_in_range_reactions,
)
from trpg.engine.rules.geometry import XY, axis_direction
from trpg.engine.rules.movement import is_deadly, is_flying
from trpg.engine.skill_triggers import collect_move
from trpg.engine.skills.charge import aside_direction
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.mobility import ChargeRoute, charge_route
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.skills.scaling import skill_scaling_attr, skill_scaling_value
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    shape_reach,
)
from trpg.engine.state import UnitState
from trpg.shared.types import Pos

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast


def _displace_direction(cast: Cast, unit: UnitState, *, pull: bool) -> XY | None:
    area = cast.area
    if area.direction is not None:
        dx, dy = area.direction
        return (-dx, -dy) if pull else (dx, dy)
    direction = axis_direction(unit.pos.x - area.origin[0], unit.pos.y - area.origin[1])
    if direction is None:
        return None
    return (-direction[0], -direction[1]) if pull else direction


def _displace(
    cast: Cast, effect: ResolvedEffect, spec: EffectSpec, *, pull: bool
) -> list[EffectBase]:
    assert spec.distance is not None
    batch: list[EffectBase] = [] if pull else _topple_in_area(cast, spec)
    # 風壓撞擊（Phase 3-54a，06 6.33）：風元素技能的推擊（拉扯不算）撞擊傷害 × collision_permille
    wind = not pull and is_wind_skill(cast.skill)
    collision_permille = cast.ctx.core.wind.collision_permille if wind else 1000
    for unit in cast.targets(effect.affects, spec.condition):
        direction = _displace_direction(cast, unit, pull=pull)
        if direction is None:
            continue
        distance, extra = spec.distance, 0
        if cast.modified:
            state, subject = cast.ctx.state, Subject(unit, unit.xy)
            distance, extra = modifiers.displace_split(
                state, cast.caster, cast.use, subject, distance
            )
        batch.append(
            PushEffect(
                source_id=cast.caster.id,
                target_id=unit.id,
                direction=direction,
                distance=distance,
                collision_dice=spec.collision_dice,
                collision_permille=collision_permille,
                extra_collisions=extra,
            )
        )
    return batch


def _away_from_caster(cast: Cast, xy: XY) -> XY | None:
    """``xy`` 遠離施放者的方向：方向型形狀為形狀的方向，其他為「施放者 → 該格」的主要軸向。"""
    if cast.area.direction is not None:
        return cast.area.direction
    return axis_direction(xy[0] - cast.caster.pos.x, xy[1] - cast.caster.pos.y)


def _topple_effects(cast: Cast, xy: XY, condition: ConditionSpec | None) -> list[EffectBase]:
    """``xy`` 上的 ``topplable`` 物件往遠離施放者的方向推倒（以一格推擊結算，見
    :mod:`trpg.engine.effects.world`）。"""
    obj = cast.ctx.state.object_at(*xy)
    if obj is None or TOPPLABLE not in cast.ctx.rules.object_def(obj.kind).tags:
        return []
    direction = _away_from_caster(cast, xy)
    if direction is None or not cast.tile_holds(condition, xy):
        return []
    return [PushEffect(source_id=cast.caster.id, object_id=obj.id, direction=direction, distance=1)]


def _topple_in_area(cast: Cast, spec: EffectSpec) -> list[EffectBase]:
    """技能的推擊（不含拉扯）也會推倒影響範圍內的 ``topplable`` 物件（通用規則）。"""
    batch: list[EffectBase] = []
    for xy in cast.area.tiles:
        batch += _topple_effects(cast, xy, spec.condition)
    return batch


def topple(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``topple``：推倒目標物件（形狀 ``single``，選取時已確認是 ``topplable``）。"""
    return _topple_in_area(cast, spec)


def hurl_object(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``hurl_object``：落點被命中的單位先受 ``dice`` 物理傷害（暴擊、格擋與修正規則照常；
    ``knock_prone`` 時再以對抗判定擊倒），然後物件落地（:class:`HurlObjectEffect`）。"""
    action = cast.action
    assert action is not None and action.target_object_id is not None
    assert action.target_pos is not None and spec.dice is not None
    batch: list[EffectBase] = []
    gamble, element = cast.gamble_for(effect), cast.physical_element()
    for unit in cast.targets(effect.affects, spec.condition):
        batch.append(cast.attack_damage(unit, spec, dice=spec.dice, element=element, gamble=gamble))
    if batch:
        execute(cast.ctx, batch)
    if spec.knock_prone:
        prone = knock_prone(cast, effect, spec)
        if prone:
            execute(cast.ctx, prone)
    dest = (action.target_pos.x, action.target_pos.y)
    return [
        HurlObjectEffect(
            source_id=cast.caster.id,
            object_id=action.target_object_id,
            dest=dest,
            ignite=modifiers.skill_is_fiery(cast.ctx.state, cast.caster, cast.skill),
        )
    ]


def knock_prone(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    batch: list[EffectBase] = []
    for unit in cast.targets(effect.affects, spec.condition):
        batch += cast.knock_down(unit)
    return batch


SHOCKWAVE = "shockwave"
"""震波原語 ID（Phase 3-54b，06 6.33，#58）。"""


def _shockwave_targets(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[UnitState]:
    """震波的對象（Phase 3-54d）：敵方要先命中（未命中的不倒地）；友方不擲命中、一律受影響
    （``affects: all`` 時不含施放者自己）。依單位 ID 排序。"""
    chosen: list[UnitState] = []
    if effect.affects in ("enemies", "all"):
        chosen += [u for u in cast.enemies if cast.is_hit(u)]
    if effect.affects == "allies":
        chosen += list(cast.allies)
    elif effect.affects == "all":
        chosen += [u for u in cast.allies if u is not cast.caster]
    alive = (u for u in chosen if u.alive and cast.holds(spec.condition, Subject(u, u.xy)))
    return sorted(alive, key=lambda u: u.id)


def shockwave(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """震波（Phase 3-54b／3-54d）：影響格（直線）上的對象單位倒地，不擲對抗；敵方先擲命中（未命中
    不倒地），友方不擲命中；帶 ``flying`` 標籤（會飛）的單位不受影響（``effect_fizzled``，原因
    ``shockwave_flying``）；已經倒地的略過。"""
    batch: list[EffectBase] = []
    for unit in _shockwave_targets(cast, effect, spec):
        if unit.has_status(PRONE):
            continue
        if is_flying(unit):
            cast.ctx.emit(
                EffectFizzled, effect_kind=SHOCKWAVE, pos=unit.pos, reason="shockwave_flying"
            )
            continue
        batch.append(
            ApplyStatusEffect(source_id=cast.caster.id, target_id=unit.id, status_id=PRONE)
        )
    return batch


def teleport(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    assert cast.action is not None
    pos = cast.action.target_pos
    assert pos is not None
    if not cast.holds(spec.condition, Subject(cast.caster, cast.caster.xy)):
        return []
    return [
        MoveUnitEffect(
            source_id=cast.caster.id,
            unit_id=cast.caster.id,
            dest=(pos.x, pos.y),
            mode="teleport",
        )
    ]


def leap(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``leap``（Phase 3D-2）：跳到指定的空格（選取時已檢查落點與路徑）；不觸發藉機攻擊。"""
    assert cast.action is not None
    pos = cast.action.target_pos
    assert pos is not None
    if not cast.holds(spec.condition, Subject(cast.caster, cast.caster.xy)):
        return []
    return [
        MoveUnitEffect(
            source_id=cast.caster.id,
            unit_id=cast.caster.id,
            dest=(pos.x, pos.y),
            mode="leap",
        )
    ]


def _charge(cast: Cast, spec: EffectSpec, gamble: int) -> None:
    """``charge_through``（Phase 3D-2c）：沿直線衝向選取的終點。一格一格走：空格移動
    （``mode: dash``，陷阱、表面與墜落照常結算，被定身、倒地或倒下就停下；不給藉機攻擊的機會）；
    有單位的格子穿過去，敵人在被穿過時各擲一次命中（依路徑順序）。隊友不受影響。"""
    action, caster, ctx = cast.action, cast.caster, cast.ctx
    assert action is not None and action.target_pos is not None
    if not cast.holds(spec.condition, Subject(caster, caster.xy)):
        return
    dest = (action.target_pos.x, action.target_pos.y)
    route = charge_route(ctx.state, caster, dest, shape_reach(ctx.state, cast.skill, caster))
    if not isinstance(route, ChargeRoute):
        ctx.emit(EffectFizzled, effect_kind=CHARGE_THROUGH, pos=None, reason="charge_no_path")
        return
    start = caster.xy
    ctx.emit(
        UnitCharged,
        unit_id=caster.id,
        target=action.target_pos,
        path=tuple(Pos(x=x, y=y) for x, y in (start, *route.walked)),
    )
    moved = _charge_walk(cast, spec, route, start, gamble)
    if moved and caster.alive:
        collect_move(ctx, caster)  # on_move 被動：衝撞算主動移動
    if cast.modified:
        cast.update_cooldown_delta()


def _charge_walk(cast: Cast, spec: EffectSpec, route: ChargeRoute, start: XY, gamble: int) -> bool:
    """衝撞沿路線前進；回傳施放者有沒有移動過。"""
    caster, state = cast.caster, cast.ctx.state
    first = route.cells[0]
    travel = (first[0] - start[0], first[1] - start[1])
    moved = False
    for cell in route.cells:
        if not caster.alive:
            break
        occupant = state.unit_at(*cell)
        if occupant is not None and occupant.id != caster.id:
            if occupant.team is not caster.team:
                _charge_hit(cast, spec, occupant, travel, gamble, bump=cell == route.bump)
            if state.unit_at(*cell) is not None:
                continue  # 還站在那裡：穿過去；倒下或被推開了就走進這一格
        before = caster.xy
        execute(
            cast.ctx,
            [MoveUnitEffect(source_id=caster.id, unit_id=caster.id, dest=cell, mode="dash")],
        )
        enemy_enters_adjacent_reactions(cast.ctx, caster, before)
        enemy_moves_in_range_reactions(cast.ctx, caster)
        moved = True
        if not cast.dash_continues(cell):
            break
    return moved


def _charge_hit(
    cast: Cast, spec: EffectSpec, unit: UnitState, travel: XY, gamble: int, *, bump: bool = False
) -> None:
    """衝撞穿過敵人 ``unit``：擲命中；命中受 ``dice`` 物理傷害（暴擊、格擋與修正規則照常），
    還活著時依 ``on_hit`` 擊倒或推到路徑旁。``bump``（3-29）：他背後走不過去（牆、地圖邊、
    擋路物件），命中後若還站在原地，另往前推一格——被擋下而受一次撞擊傷害（``collided``）。"""
    assert spec.dice is not None
    route_cell = unit.xy
    roll = cast.roll_one(unit, force_block=True)
    if not roll.hit:
        return
    damage = cast.attack_damage(
        unit, spec, dice=spec.dice, element=cast.physical_element(), gamble=gamble
    )
    execute(cast.ctx, [damage])
    if not unit.alive:
        return
    if spec.on_hit == "knock_prone":
        follow = cast.knock_down(unit)
    else:
        direction = aside_direction(cast.ctx.state, unit, travel)
        follow = [
            PushEffect(source_id=cast.caster.id, target_id=unit.id, direction=direction, distance=1)
        ]
    if follow:
        execute(cast.ctx, follow)
    if bump and unit.alive and unit.xy == route_cell:
        execute(
            cast.ctx,
            [
                PushEffect(
                    source_id=cast.caster.id,
                    target_id=unit.id,
                    direction=travel,
                    distance=1,
                    collision_dice=spec.collision_dice,
                )
            ],
        )


def _displace_check(
    cast: Cast, kind: Literal["teleport", "swap"], target: UnitState, bonus: int
) -> bool:
    """位移的抵抗判定（Phase 3D-2b，``swap``、``swap_any``、``teleport_target`` 共用）：敵方
    目標擲對抗判定（技能的縮放屬性 vs 目標同屬性，目標加 ``bonus``，沿用技巧動作的
    :func:`~trpg.engine.maneuvers.contest`），攻方勝出才位移；友方不檢定。預覽：抵抗判定是
    分歧點（``min`` 視為抵抗成功、``max`` 視為失敗）。"""
    if target.team is cast.caster.team:
        return True
    return contest(
        cast.ctx,
        kind,
        cast.caster,
        target,
        skill_scaling_attr(cast.caster, cast.skill),
        skill_id=cast.skill.id,
        primary=False,
        attack_value=skill_scaling_value(cast.ctx.rules, cast.caster, cast.skill),
        resist_bonus=bonus,
    )


def swap(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``swap``（Phase 3D-2）：與目標單位交換位置；對敵人要過一般位移檢定（3D-2b 起，
    不再用命中判定），抵抗成功就不交換。"""
    pool = cast.enemies if effect.affects == "enemies" else cast.allies
    units = sorted((u for u in pool if u.alive and u.id != cast.caster.id), key=lambda u: u.id)
    return [
        SwapUnitsEffect(source_id=cast.caster.id, unit_id=cast.caster.id, other_id=unit.id)
        for unit in units
        if cast.holds(spec.condition, Subject(unit, unit.xy))
        and _displace_check(cast, "swap", unit, 0)
    ]


def teleport_target(cast: Cast, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
    """``teleport_target``（Phase 3D-2b）：把選取的單位傳送到落點（選取時已檢查）。友方一定
    成功；敵方抵抗加成 ``teleport_enemy_resist_bonus``，落點是致命地形時再加
    ``teleport_lethal_resist_bonus``；失敗時目標不移動。"""
    action = cast.action
    assert action is not None and action.target_id is not None and action.target_pos is not None
    state, core = cast.ctx.state, cast.ctx.core
    target = state.units[action.target_id]
    dest = (action.target_pos.x, action.target_pos.y)
    bonus = core.teleport_enemy_resist_bonus
    if is_deadly(state, dest):
        bonus += core.teleport_lethal_resist_bonus
    if not target.alive or not _displace_check(cast, "teleport", target, bonus):
        return []
    return [
        MoveUnitEffect(source_id=cast.caster.id, unit_id=target.id, dest=dest, mode="teleported")
    ]


def swap_any(cast: Cast, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
    """``swap_any``（Phase 3D-2b）：選取的兩個單位互換位置。每個敵方各自過一般位移檢定
    （依單位 ID 全部擲出），任一個抵抗成功則整個互換失敗；全是友方時不檢定。"""
    action = cast.action
    assert action is not None and action.target_id is not None
    assert action.second_target_id is not None
    units = cast.ctx.state.units
    first, second = units[action.target_id], units[action.second_target_id]
    if not (first.alive and second.alive):
        return []
    foes = sorted((u for u in (first, second) if u.team is not cast.caster.team), key=_unit_id)
    passed = [_displace_check(cast, "swap", unit, 0) for unit in foes]
    if not all(passed):
        return []
    return [SwapUnitsEffect(source_id=cast.caster.id, unit_id=first.id, other_id=second.id)]


def _unit_id(unit: UnitState) -> str:
    return unit.id


def push(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``push``：往遠離原點的方向推開；也推倒影響範圍內的 ``topplable`` 物件。"""
    return _displace(cast, effect, spec, pull=False)


def pull(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``pull``：往原點的方向拉近。"""
    return _displace(cast, effect, spec, pull=True)


def charge_through(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``charge_through``：自己一步一步結算（移動、命中、傷害、擊倒或推開交錯），回傳空列表。"""
    _charge(cast, spec, cast.gamble_for(effect))
    return []


HANDLERS: dict[str, Handler] = {
    "push": push,
    "pull": pull,
    "teleport": teleport,
    "leap": leap,
    "swap": swap,
    "teleport_target": teleport_target,
    "swap_any": swap_any,
    "charge_through": charge_through,
    "knock_prone": knock_prone,
    SHOCKWAVE: shockwave,
    "topple": topple,
    "hurl_object": hurl_object,
}
