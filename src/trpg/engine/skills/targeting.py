"""技能的可用性與選取（``docs/phases/Phase2A計畫.md`` 3.3、3.5、4.6）。

- :func:`skill_problem`：代價與冷卻（AP、法力、冷卻、每場次數、HP、武器相容）。
- :func:`compute_area`：驗證一次 ``UseSkill`` 的選取並計算影響範圍（:class:`SkillArea`）；不合法時
  拋出 :class:`~trpg.shared.errors.IllegalActionError`（繁體中文原因）。
- :func:`selections`：某個技能目前所有合法的選取（``legal_actions`` 與 AI 共用）。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import NamedTuple

from trpg.content.battle import Dice
from trpg.content.skills import (
    Affects,
    EffectSpec,
    PrimitiveDef,
    SkillDef,
    default_affects,
    weapon_problem,
)
from trpg.engine.actions import Direction, UseSkill
from trpg.engine.rules.combat import AttackProfile, attack_value, concealment_problem
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.skills import shapes
from trpg.engine.state import BattleState, ObjectState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, ObjectId, Pos, UnitId

__all__ = [
    "DamageParameters",
    "ResolvedEffect",
    "SkillArea",
    "compute_area",
    "damage_parameters",
    "has_selection",
    "hp_cost",
    "resolve_effects",
    "selections",
    "skill_is_height_limited",
    "skill_problem",
    "skill_profile",
]

_PERMILLE = 1000
_HOSTILE: tuple[str, ...] = ("enemies", "all")
_TILE_ONLY_DAMAGE_KINDS: tuple[str, ...] = ("damage", "destroy_object")


@dataclass(frozen=True, slots=True)
class ResolvedEffect:
    """技能的一個效果，連同原語定義與解析後的 ``affects``（省略時依原語的預設值）。"""

    spec_index: int
    type: str
    primitive: PrimitiveDef
    affects: Affects

    @property
    def hostile(self) -> bool:
        """對敵方單位生效（需要命中判定）：``enemies`` 或 ``all``。"""
        return self.affects in _HOSTILE


def resolve_effects(state: BattleState, skill: SkillDef) -> tuple[ResolvedEffect, ...]:
    rules = state.ruleset
    result: list[ResolvedEffect] = []
    for index, spec in enumerate(skill.effects):
        primitive = rules.primitive_def(spec.type)
        result.append(
            ResolvedEffect(index, spec.type, primitive, spec.affects or default_affects(primitive))
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class SkillArea:
    """一次施放的影響範圍。

    - ``tiles``：影響的格子（依 ``(y, x)`` 排序，不含地圖外與牆壁）。
    - ``units``：站在這些格子上的存活單位（連鎖為擊中的順序，其餘依單位 ID）。
    - ``origin``：推擊與拉扯的原點（中心格型為中心，其他為施放者所在格）。
    - ``direction``：方向型形狀的前進向量。
    """

    tiles: tuple[XY, ...]
    units: tuple[UnitId, ...]
    origin: XY
    direction: XY | None = None


# ---------------------------------------------------------------------------
# 命中參數
# ---------------------------------------------------------------------------


def shape_reach(skill: SkillDef, caster: UnitState) -> int:
    """形狀的射程：``single``／``chain`` 的 ``range``（``"weapon"`` 為武器射程）、中心格型的
    ``range``；其他形狀為 0。"""
    reach = skill.shape.range
    if reach is None:
        return 0
    return caster.weapon.range if reach == "weapon" else reach


def skill_is_height_limited(state: BattleState, caster: UnitState, skill: SkillDef) -> bool:
    """近戰性質的技能（無視半掩護、受近戰高度差限制）。

    武器技看施放者的武器（射程 ≤ ``melee_height_limit_max_range``）；法術技只有射程不超過
    該值的單體技才算。
    """
    limit = state.ruleset.core.melee_height_limit_max_range
    if skill.category == "weapon":
        return caster.weapon.range <= limit
    return skill.shape.type == "single" and shape_reach(skill, caster) <= limit


def skill_profile(state: BattleState, caster: UnitState, skill: SkillDef) -> AttackProfile:
    """技能命中判定的攻擊參數。

    - 武器技：沿用 ``attack_value``（武器的縮放屬性值 ＋ 武器加值）與武器的近戰性質。
    - 法術技：技能縮放屬性值 ＋ 武器加值（只有法器類武器才加）；一律視為遠程。
    - 暴擊：自然 20。
    """
    height_limited = skill_is_height_limited(state, caster, skill)
    if skill.category == "weapon":
        return AttackProfile(
            attack_value=attack_value(caster),
            melee=caster.weapon.is_melee,
            height_limited=height_limited,
            crit_range=20,
        )
    bonus = caster.weapon.attack_bonus if caster.weapon.weapon_class == "focus" else 0
    return AttackProfile(
        attack_value=caster.attributes[skill.scaling_attr] + bonus,
        melee=False,
        height_limited=height_limited,
        crit_range=20,
    )


# ---------------------------------------------------------------------------
# 代價
# ---------------------------------------------------------------------------


def hp_cost(unit: UnitState, skill: SkillDef) -> int:
    """HP 代價：最大 HP 的 ``hp_percent``‰，無條件進位。"""
    permille = skill.cost.hp_percent
    if permille is None:
        return 0
    return -(-unit.max_hp * permille // _PERMILLE)


def skill_problem(  # noqa: PLR0911
    state: BattleState, unit: UnitState, skill: SkillDef
) -> str | None:
    """技能目前不能使用的原因（繁體中文）；可以使用時回傳 ``None``（不檢查選取）。"""
    if not skill.is_active:
        return f"只有主動技能可以使用：{skill.name_zh}"
    ap_cost = skill.ap_cost or 0
    if unit.ap < ap_cost:
        return f"AP 不足：需要 {ap_cost}，剩餘 {unit.ap}"
    problem = weapon_problem(skill, unit.weapon.weapon_class)
    if problem is not None:
        return problem
    if unit.mana < skill.cost.mana:
        return f"法力不足：需要 {skill.cost.mana}，剩餘 {unit.mana}"
    remaining = unit.cooldowns.get(skill.id, 0)
    if remaining > 0:
        return f"技能冷卻中：{skill.name_zh} 還要 {remaining} 回合"
    limit = skill.cost.uses_per_battle
    if limit is not None and unit.skill_uses.get(skill.id, 0) >= limit:
        return f"技能已用完：{skill.name_zh} 每場限用 {limit} 次"
    cost = hp_cost(unit, skill)
    if cost and unit.hp <= cost:
        return f"HP 不足以支付代價：需要 {cost}，目前 {unit.hp}（支付後不可倒下）"
    return None


# ---------------------------------------------------------------------------
# 選取
# ---------------------------------------------------------------------------


def _unit_target_problem(  # noqa: PLR0917
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    effects: tuple[ResolvedEffect, ...],
    target: UnitState,
    reach: int,
) -> str | None:
    if not target.alive:
        return f"目標已不在戰場上：{target.name_zh}"
    enemy = target.team is not caster.team
    if enemy and not any(e.affects in ("enemies", "all", "tiles") for e in effects):
        return f"此技能無法對敵方使用：{target.name_zh}"
    if not enemy:
        helps = any(
            e.affects in ("allies", "all", "tiles") or (e.affects == "self" and target is caster)
            for e in effects
        )
        if not helps:
            return f"此技能無法對友方使用：{target.name_zh}"
    problem = _reach_problem(state, caster, skill, target.xy, target.name_zh, reach)
    if problem is not None:
        return problem
    return concealment_problem(state, caster, target) if enemy else None


def _reach_problem(  # noqa: PLR0917
    state: BattleState, caster: UnitState, skill: SkillDef, xy: XY, what: str, reach: int
) -> str | None:
    distance = manhattan(caster.xy, xy)
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    core = state.ruleset.core
    if reach <= core.melee_height_limit_max_range:
        diff = abs(state.tile(*caster.xy).height - state.tile(*xy).height)
        if diff > core.melee_height_limit:
            return f"高度差過大，無法近戰：相差 {diff} 層（上限 {core.melee_height_limit} 層）"
    if not has_line_of_sight(state, caster.xy, xy):
        return f"視線被阻擋：{caster.name_zh} 看不到 {what}"
    return None


def _object_target_problem(  # noqa: PLR0917
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    effects: tuple[ResolvedEffect, ...],
    obj: ObjectState,
    reach: int,
) -> str | None:
    definition = state.object_def(obj)
    if obj.destroyed:
        return f"物件已被摧毀：{definition.name_zh}"
    if "breakable" not in definition.tags or obj.hp is None:
        return f"{definition.name_zh}無法被攻擊"
    if not any(e.type in _TILE_ONLY_DAMAGE_KINDS or e.affects == "tiles" for e in effects):
        return f"此技能無法以物件為目標：{definition.name_zh}"
    return _reach_problem(state, caster, skill, obj.xy, definition.name_zh, reach)


def _require_fields(action: UseSkill, allowed: tuple[str, ...], targeting: str) -> None:
    """``UseSkill`` 只能帶形狀 ``targeting`` 對應的欄位。"""
    given = {
        "target_id": action.target_id,
        "target_object_id": action.target_object_id,
        "target_pos": action.target_pos,
        "direction": action.direction,
    }
    extra = [name for name, value in given.items() if value is not None and name not in allowed]
    if extra:
        raise IllegalActionError(f"此技能的選取方式是 {targeting}，不能指定：{'、'.join(extra)}")


def _tiles_to_units(
    state: BattleState, tiles: tuple[XY, ...], chain: list[UnitState] | None
) -> tuple[UnitId, ...]:
    if chain is not None:
        return tuple(u.id for u in chain)
    units = [u for xy in tiles if (u := state.unit_at(*xy)) is not None]
    return tuple(sorted(u.id for u in units))


def compute_area(  # noqa: PLR0912, PLR0915
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> SkillArea:
    """驗證 ``action`` 的選取並計算影響範圍；不合法或影響範圍為空時拋出 ``IllegalActionError``。"""
    rules = state.ruleset
    shape = rules.shape_def(skill.shape.type)
    spec = skill.shape
    effects = resolve_effects(state, skill)
    reach = shape_reach(skill, caster)
    origin = caster.xy
    direction: XY | None = None
    chain: list[UnitState] | None = None
    tiles: tuple[XY, ...]
    targeting = shape.targeting

    if targeting == "unit":
        _require_fields(action, ("target_id", "target_object_id"), "unit（單位或物件）")
        if (action.target_id is None) == (action.target_object_id is None):
            raise IllegalActionError("此技能必須恰好指定 target_id 或 target_object_id 其中之一")
        if action.target_id is not None:
            target = state.units.get(action.target_id)
            if target is None:
                raise IllegalActionError(f"找不到目標：{action.target_id}")
            problem = _unit_target_problem(state, caster, skill, effects, target, reach)
            if problem is not None:
                raise IllegalActionError(problem)
            tiles = (target.xy,)
            if spec.type == "chain":
                assert spec.jumps is not None and spec.jump_range is not None
                chain = shapes.chain_units(state, caster, target, spec.jumps, spec.jump_range)
                tiles = tuple(sorted({u.xy for u in chain}, key=lambda p: (p[1], p[0])))
        else:
            assert action.target_object_id is not None
            if spec.type == "chain":
                raise IllegalActionError("連鎖技能的第一個目標必須是單位")
            obj = state.objects.get(action.target_object_id)
            if obj is None or obj.destroyed:
                raise IllegalActionError(f"找不到物件：{action.target_object_id}")
            problem = _object_target_problem(state, caster, skill, effects, obj, reach)
            if problem is not None:
                raise IllegalActionError(problem)
            tiles = (obj.xy,)
    elif targeting == "tile":
        _require_fields(action, ("target_pos",), "tile（格子）")
        if action.target_pos is None:
            raise IllegalActionError("此技能必須指定 target_pos（目標格）")
        center = (action.target_pos.x, action.target_pos.y)
        problem = shapes.center_problem(state, caster.xy, center, reach)
        if problem is not None:
            raise IllegalActionError(problem)
        if any(e.type == "teleport" for e in effects):
            if not is_standable(state, center) or is_deadly(state, center):
                raise IllegalActionError(f"無法傳送到不可站立的格子：{center}")
            other = state.unit_at(*center)
            if other is not None and other.id != caster.id:
                raise IllegalActionError(f"無法傳送到已有單位的格子：{center}（{other.name_zh}）")
        origin = center
        tiles = _center_tiles(state, spec.type, center)
    elif targeting == "direction":
        _require_fields(action, ("direction",), "direction（方向）")
        if action.direction is None:
            raise IllegalActionError("此技能必須指定 direction（north／east／south／west）")
        direction = shapes.DIRECTIONS[action.direction]
        assert spec.size is not None
        if spec.type == "line":
            tiles = shapes.line_tiles(state, caster.xy, action.direction, spec.size)
        else:
            tiles = shapes.cone_tiles(state, caster.xy, action.direction, spec.size)
    else:
        _require_fields(action, (), targeting)
        if spec.type == "self":
            tiles = (caster.xy,)
        elif spec.type == "ring":
            assert spec.radius is not None
            tiles = shapes.ring_tiles(state, caster.xy, spec.radius)
        else:
            assert spec.radius is not None
            tiles = shapes.radius_tiles(state, caster.xy, spec.radius)
    if not tiles:
        raise IllegalActionError("影響範圍為空：沒有任何格子會受到影響")
    return SkillArea(
        tiles=tiles, units=_tiles_to_units(state, tiles, chain), origin=origin, direction=direction
    )


def _center_tiles(state: BattleState, shape_type: str, center: XY) -> tuple[XY, ...]:
    if shape_type == "cross":
        return shapes.cross_tiles(state, center)
    if shape_type == "square3":
        return shapes.square3_tiles(state, center)
    return (center,)  # ground_tile


# ---------------------------------------------------------------------------
# 列舉
# ---------------------------------------------------------------------------


def _candidates(state: BattleState, caster: UnitState, skill: SkillDef) -> Iterator[UseSkill]:
    """可能的選取（尚未驗證）；順序固定。"""
    shape = state.ruleset.shape_def(skill.shape.type)
    sid = skill.id
    uid = caster.id
    if shape.targeting == "unit":
        for unit in state.living_units():
            yield UseSkill(unit_id=uid, skill_id=sid, target_id=unit.id)
        if skill.shape.type != "chain":
            for obj in state.objects_sorted():
                yield UseSkill(unit_id=uid, skill_id=sid, target_object_id=ObjectId(obj.id))
    elif shape.targeting == "tile":
        for x, y in shapes.center_candidates(state, caster.xy, shape_reach(skill, caster)):
            yield UseSkill(unit_id=uid, skill_id=sid, target_pos=Pos(x=x, y=y))
    elif shape.targeting == "direction":
        for name in shapes.DIRECTION_ORDER:
            direction: Direction = name  # type: ignore[assignment]
            yield UseSkill(unit_id=uid, skill_id=sid, direction=direction)
    else:
        yield UseSkill(unit_id=uid, skill_id=sid)


def selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """技能目前所有合法的選取與其影響範圍（確定性順序）。不檢查代價（:func:`skill_problem`）。

    單體與連鎖：先單位（依 ID）再物件（依 ID）；中心格型：射程內每個合法格（依 ``(y, x)``）；
    方向型：東南西北（影響範圍為空的不列）。
    """
    for action in _candidates(state, caster, skill):
        try:
            area = compute_area(state, caster, skill, action)
        except IllegalActionError:
            continue
        yield action, area


def has_selection(state: BattleState, caster: UnitState, skill: SkillDef) -> bool:
    """是否至少有一個合法的選取（不建立完整列表）。"""
    return next(selections(state, caster, skill), None) is not None


class DamageParameters(NamedTuple):
    """技能一個傷害效果的結算參數（4.2）：骰子、固定值、屬性加成（‰）、倍率（‰）與元素。"""

    dice: Dice | None
    flat: int
    scaled_permille: int
    multiplier_permille: int
    element: Element


def damage_parameters(
    state: BattleState, caster: UnitState, skill: SkillDef, spec: EffectSpec
) -> DamageParameters:
    """法術技：效果自己的骰子與元素、屬性 × ``spell_attr_multiplier``；武器技：武器的骰子與
    固定值、屬性 × 普攻倍率、效果的 ``multiplier_permille``，元素省略時繼承武器（元素灌注）。"""
    core = state.ruleset.core
    attr = caster.attributes[skill.scaling_attr]
    if skill.category == "spell":
        assert spec.element is not None
        return DamageParameters(
            spec.dice, 0, attr * core.spell_attr_multiplier_permille, _PERMILLE, spec.element
        )
    weapon = caster.weapon
    return DamageParameters(
        weapon.dice,
        weapon.flat,
        attr * core.basic_attack_attr_multiplier_permille,
        spec.multiplier_permille or _PERMILLE,
        spec.element or weapon.element,
    )
