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
    COPY_SKILL,
    HURL_OBJECT,
    PIERCE_SHAPES,
    TOPPLE,
    Affects,
    EffectSpec,
    PrimitiveDef,
    SkillDef,
    default_affects,
    weapon_problem,
)
from trpg.engine import modifiers
from trpg.engine.actions import Direction, UseSkill
from trpg.engine.rules.combat import AttackProfile, attack_value, concealment_problem
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.rules.statuses import (
    attack_range_cap,
    blocks_spells,
    skip_turn_status,
)
from trpg.engine.skills import shapes
from trpg.engine.skills.conditions import skill_condition_problem
from trpg.engine.skills.scaling import mastery_reach_bonus, skill_scaling_value
from trpg.engine.state import BattleState, ObjectState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, ObjectId, Pos, UnitId

__all__ = [
    "DamageParameters",
    "PaidCost",
    "ResolvedEffect",
    "SkillArea",
    "center_tiles",
    "checked_area",
    "compute_area",
    "damage_parameters",
    "has_selection",
    "hp_cost",
    "hurl_object_problem",
    "pay_skill_cost",
    "pierce_active",
    "reaction_problem",
    "reaction_target_problem",
    "resolve_effects",
    "resource_problem",
    "selections",
    "skill_ap_cost",
    "skill_is_height_limited",
    "skill_problem",
    "skill_profile",
    "stack_problem",
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


def shape_reach(state: BattleState, skill: SkillDef, caster: UnitState) -> int:
    """形狀的射程：``single``／``chain`` 的 ``range``（``"weapon"`` 為武器射程）、中心格型的
    ``range``；其他形狀為 0。``mastery: range`` 生效時再 +1（Phase 2H-2；不改範圍形狀的大小），
    修正規則的 ``range_delta`` 再加上去（Phase 3C-2；結果至少 1）。"""
    reach = skill.shape.range
    if reach is None:
        return 0
    base = _base_reach(skill, caster)
    delta = modifiers.range_delta(state, caster, modifiers.skill_use(skill))
    return max(1, base + delta) if delta else base


def _base_reach(skill: SkillDef, caster: UnitState) -> int:
    """沒有修正規則時的射程（形狀的 ``range`` ＋ 專精）。"""
    reach = skill.shape.range
    if reach is None:
        return 0
    base = caster.weapon.range if reach == "weapon" else reach
    return base + mastery_reach_bonus(caster, skill)


def skill_is_height_limited(state: BattleState, caster: UnitState, skill: SkillDef) -> bool:
    """近戰性質的技能（無視半掩護、受近戰高度差限制）。

    武器技看施放者的武器（射程 ≤ ``melee_height_limit_max_range``）；法術技只有射程不超過
    該值的單體技才算。
    """
    limit = state.ruleset.core.melee_height_limit_max_range
    if skill.category == "weapon":
        return caster.weapon.range <= limit
    # 近戰性質看沒有修正的射程：修正規則加長射程不會讓近戰法術變成遠程（3C-2）
    return skill.shape.type == "single" and _base_reach(skill, caster) <= limit


def pierce_active(state: BattleState, caster: UnitState, skill: SkillDef) -> bool:
    """這次施放有穿透（Phase 3C-5b）：技能本身的 ``pierce`` 或修正規則的 ``grant_pierce``，而且
    形狀是單體或直線、不是近戰性質（只有技能能穿透，基本動作不行）。"""
    if skill.shape.type not in PIERCE_SHAPES or skill_is_height_limited(state, caster, skill):
        return False
    return skill.pierce or modifiers.grants_pierce(state, caster, modifiers.skill_use(skill))


def skill_profile(state: BattleState, caster: UnitState, skill: SkillDef) -> AttackProfile:
    """技能命中判定的攻擊參數。

    - 武器技：沿用 ``attack_value``（武器的縮放屬性值 ＋ 武器加值）與武器的近戰性質。
    - 法術技：技能縮放屬性值 ＋ 武器加值（只有法器類武器才加）；一律視為遠程。
    - 暴擊：武器技使用武器的 ``crit_range``（Phase 2A-2 決定 #3）；法術技只有自然 20。
    """
    height_limited = skill_is_height_limited(state, caster, skill)
    pierce = pierce_active(state, caster, skill)
    if skill.category == "weapon":
        return AttackProfile(
            attack_value=attack_value(caster, state.ruleset),
            melee=caster.weapon.is_melee,
            height_limited=height_limited,
            crit_range=caster.weapon.crit_range,
            pierce=pierce,
        )
    bonus = caster.weapon.attack_bonus if caster.weapon.weapon_class == "focus" else 0
    return AttackProfile(
        attack_value=skill_scaling_value(state.ruleset, caster, skill) + bonus,
        melee=False,
        height_limited=height_limited,
        crit_range=20,
        pierce=pierce,
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


def skill_ap_cost(state: BattleState, skill: SkillDef, caster: UnitState | None = None) -> int:
    """施放技能花的 AP：主動技能是 ``ap_cost``、姿態是 ``core.yaml`` 的 ``stance_ap_cost``，
    反應技與被動不花 AP。給了 ``caster`` 時加上其修正規則的 ``ap_delta``（Phase 3C-2；至少 1）。"""
    base = state.ruleset.core.stance_ap_cost if skill.kind == "stance" else skill.ap_cost or 0
    if caster is None:
        return base
    return modifiers.ap_cost(state, caster, modifiers.skill_use(skill), base)


@dataclass(frozen=True, slots=True)
class PaidCost:
    """:func:`pay_skill_cost` 支付後的結果，供呼叫端發出事件（``ap``／``hp``／``cooldown``）。"""

    ap: int
    hp: int
    cooldown: int | None


def pay_skill_cost(caster: UnitState, skill: SkillDef, *, ap: int = 0) -> PaidCost:
    """支付技能代價（AP、法力、HP、冷卻、每場次數）；主動技能、反應技與被動觸發共用
    （Phase 2F-1 3.1，取代 ``skill_triggers._pay`` 與 ``interpreter._pay_costs`` 的重複邏輯）。

    不發出事件——呼叫端的事件型別不同（``SkillUsed``／``SkillTriggered``），且發出順序
    （主事件先、``SkillCooldownChanged`` 後）要維持不變，由呼叫端自己處理。
    """
    hp = hp_cost(caster, skill)
    caster.ap -= ap
    caster.mana -= skill.cost.mana
    caster.hp -= hp
    if skill.cost.uses_per_battle is not None:
        caster.skill_uses[skill.id] = caster.skill_uses.get(skill.id, 0) + 1
    cooldown = skill.cost.cooldown
    if cooldown is not None:
        caster.cooldowns[skill.id] = cooldown
    return PaidCost(ap=ap, hp=hp, cooldown=cooldown)


def resource_problem(  # noqa: PLR0911
    state: BattleState, unit: UnitState, skill: SkillDef
) -> str | None:
    """武器相容、沉默、法力、冷卻、每場次數、HP 代價與源力（Phase 3C-4a）（不含 AP）。"""
    problem = weapon_problem(skill, unit.weapon.weapon_class)
    if problem is not None:
        return problem
    if skill.category == "spell" and blocks_spells(state.ruleset, unit):
        return f"沉默中：不能使用法術技：{skill.name_zh}"
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
    source = skill.cost.source
    if source is not None and unit.source < source:
        return f"源力不足：需要 {source}，目前 {unit.source}"
    return stack_problem(state, unit, skill)


def stack_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """層數需求（``cost.stacks``）不足的原因；沒有需求或足夠時為 ``None``。

    對應的層數定義與 :func:`trpg.engine.stacks.required_stack` 共用同一份「找第一個
    ``owner: self`` 的 ``consume_stack``」（Phase 2F-1 3.1）。
    """
    # 延後匯入：trpg.engine.stacks 匯入 context（context 匯入 skill_triggers，skill_triggers
    # 又匯入本模組），模組層級匯入會造成循環匯入。
    from trpg.engine.stacks import required_stack  # noqa: PLC0415

    need = skill.cost.stacks
    if need is None:
        return None
    definition = required_stack(state, skill)
    if definition is None:
        return None
    have = unit.stacks.get(definition.id, 0)
    if have < need:
        return f"層數不足：需要「{definition.name_zh}」{need} 層，目前 {have} 層"
    return None


def skill_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """技能目前不能使用的原因（繁體中文）；可以使用時回傳 ``None``（不檢查選取）。

    主動技能與姿態可以用 ``UseSkill`` 施放；姿態另外檢查「已經在這個姿態」（Phase 2E-2）。
    """
    if not skill.is_actionable:
        return f"只有主動技能與姿態可以使用：{skill.name_zh}"
    ap_cost = skill_ap_cost(state, skill, unit)
    if unit.ap < ap_cost:
        return f"AP 不足：需要 {ap_cost}，剩餘 {unit.ap}"
    if skill.kind == "stance" and any(
        e.type == "apply_status" and e.status is not None and unit.has_status(e.status)
        for e in skill.effects
    ):
        return f"已經在這個姿態中：{skill.name_zh}"
    problem = resource_problem(state, unit, skill)
    if problem is None and any(e.type == COPY_SKILL for e in skill.effects):
        # 延後匯入：trpg.engine.copying 匯入本模組的 selections
        from trpg.engine.copying import copy_problem  # noqa: PLC0415

        return copy_problem(state, unit)  # Phase 3C-4b：沒有可複製的技能時不能施放
    return problem


def reaction_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """反應技目前不能施放的原因（單位、狀態與代價；不含每輪次數與目標）。反應不花 AP。"""
    if not unit.alive:
        return f"{unit.name_zh} 已不在戰場上"
    if skip_turn_status(state.ruleset, unit) is not None:
        return f"{unit.name_zh} 暈眩中，不能執行反應"
    return resource_problem(state, unit, skill)


def reaction_target_problem(
    state: BattleState, unit: UnitState, skill: SkillDef, trigger: UnitState
) -> str | None:
    """``shape: single`` 的反應技能不能打觸發者的原因：必須在射程內（含高度與視線），並套用致盲的
    距離上限與隱蔽限制（同一般技能的單位目標）。``shape: self`` 沒有目標限制。"""
    if skill.shape.type != "single":
        return None
    effects = resolve_effects(state, skill)
    reach = shape_reach(state, skill, unit)
    return _unit_target_problem(state, unit, skill, effects, trigger, reach)


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
    cap = attack_range_cap(state.ruleset, caster)  # 致盲：以單位為目標的技能只能選近處的單位
    if cap is not None and manhattan(caster.xy, target.xy) > cap:
        return f"致盲中：只能選擇 {cap} 格內的單位（距離 {manhattan(caster.xy, target.xy)}）"
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
    if any(e.type == TOPPLE for e in effects):  # 推倒技能（Phase 3C-5a）：目標必須能推倒
        if "topplable" not in definition.tags:
            return f"{definition.name_zh}無法推倒"
        return _reach_problem(state, caster, skill, obj.xy, definition.name_zh, reach)
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


def _unit_area(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    action: UseSkill,
    *,
    effects: tuple[ResolvedEffect, ...],
    reach: int,
) -> tuple[tuple[XY, ...], list[UnitState] | None]:
    """``targeting: unit``：單位或物件目標；連鎖回傳依序跳到的單位。"""
    spec = skill.shape
    _require_fields(action, ("target_id", "target_object_id"), "unit（單位或物件）")
    if (action.target_id is None) == (action.target_object_id is None):
        raise IllegalActionError("此技能必須恰好指定 target_id 或 target_object_id 其中之一")
    if action.target_id is not None:
        target = state.units.get(action.target_id)
        if target is None:
            raise IllegalActionError(f"找不到目標：{action.target_id}")
        if any(e.type == TOPPLE for e in effects):
            raise IllegalActionError(f"推倒技能只能以可推倒的物件為目標：{skill.name_zh}")
        problem = _unit_target_problem(state, caster, skill, effects, target, reach)
        if problem is not None:
            raise IllegalActionError(problem)
        if spec.type != "chain":
            return (target.xy,), None
        assert spec.jumps is not None and spec.jump_range is not None
        chain = shapes.chain_units(state, caster, target, spec.jumps, spec.jump_range)
        return tuple(sorted({u.xy for u in chain}, key=lambda p: (p[1], p[0]))), chain
    assert action.target_object_id is not None
    if spec.type == "chain":
        raise IllegalActionError("連鎖技能的第一個目標必須是單位")
    obj = state.objects.get(action.target_object_id)
    if obj is None or obj.destroyed:
        raise IllegalActionError(f"找不到物件：{action.target_object_id}")
    problem = _object_target_problem(state, caster, skill, effects, obj, reach)
    if problem is not None:
        raise IllegalActionError(problem)
    return (obj.xy,), None


def _tile_area(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    action: UseSkill,
    *,
    effects: tuple[ResolvedEffect, ...],
    reach: int,
) -> tuple[tuple[XY, ...], XY]:
    """``targeting: tile``：目標格（傳送與陷阱另有落點限制）；回傳影響格與中心格。"""
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
    if skill.trap is not None:
        problem = _trap_site_problem(state, center)
        if problem is not None:
            raise IllegalActionError(problem)
    return center_tiles(state, skill.shape.type, center), center


def hurl_object_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, obj: ObjectState
) -> str | None:
    """投擲物件（Phase 3C-5a）能不能舉起 ``obj``：``pushable``、在 ``hurl_object`` 效果的
    ``range`` 內、看得到。"""
    definition = state.object_def(obj)
    if obj.destroyed:
        return f"物件已被摧毀：{definition.name_zh}"
    if "pushable" not in definition.tags:
        return f"{definition.name_zh}無法投擲（不是可推動的物件）"
    spec = next(e for e in skill.effects if e.type == HURL_OBJECT)
    assert spec.range is not None
    distance = manhattan(caster.xy, obj.xy)
    if distance > spec.range:
        return f"物件超出投擲距離：距離 {distance}，上限 {spec.range}"
    if not has_line_of_sight(state, caster.xy, obj.xy):
        return f"視線被阻擋：{caster.name_zh} 看不到 {definition.name_zh}"
    return None


def _object_tile_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, *, reach: int
) -> tuple[tuple[XY, ...], XY]:
    """``targeting: object_tile``（投擲物件，Phase 3C-5a）：被舉起的物件與落點；只影響落點。
    物件的飛行路徑不檢查阻擋，落點要在射程與視線內、不是牆壁，也不能是物件原本的格子。"""
    _require_fields(action, ("target_object_id", "target_pos"), "object_tile（物件與落點）")
    if action.target_object_id is None or action.target_pos is None:
        raise IllegalActionError(
            "投擲物件必須同時指定 target_object_id（物件）與 target_pos（落點）"
        )
    obj = state.objects.get(action.target_object_id)
    if obj is None or obj.destroyed:
        raise IllegalActionError(f"找不到物件：{action.target_object_id}")
    problem = hurl_object_problem(state, caster, skill, obj)
    if problem is not None:
        raise IllegalActionError(problem)
    center = (action.target_pos.x, action.target_pos.y)
    if center == obj.xy:
        raise IllegalActionError("落點不能是物件原本的格子")
    problem = shapes.center_problem(state, caster.xy, center, reach)
    if problem is not None:
        raise IllegalActionError(problem)
    return (center,), center


def _direction_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> tuple[tuple[XY, ...], XY]:
    """``targeting: direction``：直線或錐形；回傳影響格與方向向量。"""
    _require_fields(action, ("direction",), "direction（方向）")
    if action.direction is None:
        raise IllegalActionError("此技能必須指定 direction（north／east／south／west）")
    spec = skill.shape
    assert spec.size is not None
    if spec.type == "line":
        tiles = shapes.line_tiles(state, caster.xy, action.direction, spec.size)
    else:
        tiles = shapes.cone_tiles(state, caster.xy, action.direction, spec.size)
    return tiles, shapes.DIRECTIONS[action.direction]


def _self_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, targeting: str
) -> tuple[XY, ...]:
    """不需要選取的形狀（自身、環、半徑）。"""
    _require_fields(action, (), targeting)
    spec = skill.shape
    if spec.type == "self":
        return (caster.xy,)
    assert spec.radius is not None
    if spec.type == "ring":
        return shapes.ring_tiles(state, caster.xy, spec.radius)
    return shapes.radius_tiles(state, caster.xy, spec.radius)


def compute_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> SkillArea:
    """驗證 ``action`` 的選取並計算影響範圍；不合法或影響範圍為空時拋出 ``IllegalActionError``。"""
    targeting = state.ruleset.shape_def(skill.shape.type).targeting
    effects = resolve_effects(state, skill)
    reach = shape_reach(state, skill, caster)
    origin = caster.xy
    direction: XY | None = None
    chain: list[UnitState] | None = None
    if targeting == "unit":
        tiles, chain = _unit_area(state, caster, skill, action, effects=effects, reach=reach)
    elif targeting == "tile":
        tiles, origin = _tile_area(state, caster, skill, action, effects=effects, reach=reach)
    elif targeting == "direction":
        tiles, direction = _direction_area(state, caster, skill, action)
    elif targeting == "object_tile":
        tiles, origin = _object_tile_area(state, caster, skill, action, reach=reach)
    else:
        tiles = _self_area(state, caster, skill, action, targeting)
    if not tiles:
        raise IllegalActionError("影響範圍為空：沒有任何格子會受到影響")
    return SkillArea(
        tiles=tiles, units=_tiles_to_units(state, tiles, chain), origin=origin, direction=direction
    )


def _trap_site_problem(state: BattleState, center: XY) -> str | None:
    """陷阱的放置格：可站立、不是致命地形、沒有單位、沒有其他陷阱（同一格只能有一個；這個檢查
    不分陣營，所以放置的合法性會洩漏對方陷阱的存在——2E 敵人沒有陷阱技能，記錄在報告）。"""
    if not is_standable(state, center) or is_deadly(state, center):
        return f"無法在不可站立的格子放置陷阱：{center}"
    other = state.unit_at(*center)
    if other is not None:
        return f"無法在已有單位的格子放置陷阱：{center}（{other.name_zh}）"
    if state.trap_at(*center) is not None:
        return f"這一格已經有陷阱：{center}"
    return None


def checked_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> SkillArea:
    """:func:`compute_area` 再加上技能層級的條件（``condition``）；不成立時拋出
    ``IllegalActionError``。``legal_actions``、AI 與解譯器都用這個。"""
    area = compute_area(state, caster, skill, action)
    problem = skill_condition_problem(state, caster, skill, area.tiles)
    if problem is not None:
        raise IllegalActionError(problem)
    return area


def center_tiles(state: BattleState, shape_type: str, center: XY) -> tuple[XY, ...]:
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
        reach = shape_reach(
            state, skill, caster
        )  # 射程外的目標不可能合法，先篩掉（省下例外的成本）
        for unit in state.living_units():
            if manhattan(caster.xy, unit.xy) <= reach:
                yield UseSkill(unit_id=uid, skill_id=sid, target_id=unit.id)
        if skill.shape.type != "chain":
            for obj in state.objects_sorted():
                if manhattan(caster.xy, obj.xy) <= reach:
                    yield UseSkill(unit_id=uid, skill_id=sid, target_object_id=ObjectId(obj.id))
    elif shape.targeting == "tile":
        reach = shape_reach(state, skill, caster)
        for x, y in shapes.center_candidates(state, caster.xy, reach):
            yield UseSkill(unit_id=uid, skill_id=sid, target_pos=Pos(x=x, y=y))
    elif shape.targeting == "object_tile":
        yield from _hurl_candidates(state, caster, skill)
    elif shape.targeting == "direction":
        for name in shapes.DIRECTION_ORDER:
            direction: Direction = name  # type: ignore[assignment]
            yield UseSkill(unit_id=uid, skill_id=sid, direction=direction)
    else:
        yield UseSkill(unit_id=uid, skill_id=sid)


def _hurl_candidates(state: BattleState, caster: UnitState, skill: SkillDef) -> Iterator[UseSkill]:
    """投擲物件的候選：可舉起的物件（依 ID）× 射程內的落點（依 ``(y, x)``）。"""
    reach = shape_reach(state, skill, caster)
    tiles = shapes.center_candidates(state, caster.xy, reach)
    for obj in state.objects_sorted():
        if hurl_object_problem(state, caster, skill, obj) is not None:
            continue
        for x, y in tiles:
            if (x, y) != obj.xy:
                yield UseSkill(
                    unit_id=caster.id,
                    skill_id=skill.id,
                    target_object_id=ObjectId(obj.id),
                    target_pos=Pos(x=x, y=y),
                )


def selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """技能目前所有合法的選取與其影響範圍（確定性順序）。不檢查代價（:func:`skill_problem`）。

    單體與連鎖：先單位（依 ID）再物件（依 ID）；中心格型：射程內每個合法格（依 ``(y, x)``）；
    方向型：東南西北（影響範圍為空的不列）。
    """
    for action in _candidates(state, caster, skill):
        try:
            area = checked_area(state, caster, skill, action)
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
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    spec: EffectSpec,
    *,
    modified: bool = False,
) -> DamageParameters:
    """法術技：效果自己的骰子與元素、屬性 × ``spell_attr_multiplier``；武器技：武器的骰子與
    固定值、屬性 × 普攻倍率、效果的 ``multiplier_permille``，元素省略時繼承武器（元素灌注）。

    ``modified``：這次施放受修正規則影響（主動、姿態、反應技；被動與陷阱觸發不受影響）時，物理
    傷害改為修正規則的 ``add_element``（Phase 3C-2）。傷害‰ 的修正依目標而定，由解譯器另外乘上。
    """
    core = state.ruleset.core
    attr = skill_scaling_value(state.ruleset, caster, skill)
    if skill.category == "spell":
        assert spec.element is not None
        element = spec.element
        dice, flat, scaled = spec.dice, 0, attr * core.spell_attr_multiplier_permille
        multiplier = _PERMILLE
    else:
        weapon = caster.weapon
        element = spec.element or weapon.element
        dice, flat, scaled = (
            weapon.dice,
            weapon.flat,
            attr * core.basic_attack_attr_multiplier_permille,
        )
        multiplier = spec.multiplier_permille or _PERMILLE
    if modified:
        element = modifiers.damage_element(state, caster, modifiers.skill_use(skill), element)
    return DamageParameters(dice, flat, scaled, multiplier, element)
