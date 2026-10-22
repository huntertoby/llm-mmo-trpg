"""技能的可用性與選取（``docs/phases/Phase2A計畫.md`` 3.3、3.5、4.6）。

- :func:`skill_problem`：代價與冷卻（AP、法力、冷卻、每場次數、HP、武器相容）。
- :func:`compute_area`：驗證一次 ``UseSkill`` 的選取並計算影響範圍（:class:`SkillArea`）；不合法時
  拋出 :class:`~trpg.shared.errors.IllegalActionError`（繁體中文原因）。
- :func:`selections`：某個技能目前所有合法的選取（``legal_actions`` 與 AI 共用）。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from itertools import combinations
from typing import NamedTuple

from trpg.content.battle import Dice
from trpg.content.skills import (
    CHARGE_THROUGH,
    COPY_SKILL,
    DASH,
    FOLLOWUP_AUTO_WHENS,
    FOLLOWUP_CENTERED,
    GAMBLE,
    HURL_OBJECT,
    LEAP,
    PIERCE_SHAPES,
    REVIVE,
    SACRIFICE_SUMMON,
    SHADOWSTEP,
    SUMMON,
    SWAP,
    TOPPLE,
    Affects,
    EffectSpec,
    PrimitiveDef,
    SkillDef,
    default_affects,
    weapon_problem,
)
from trpg.engine import modifiers
from trpg.engine.actions import Direction, FollowupTarget, UseSkill
from trpg.engine.activations import activation_problem
from trpg.engine.gear import gear_cooldown
from trpg.engine.gear_summon import gear_summon_cooldown
from trpg.engine.ids import BOSS_TAG
from trpg.engine.infusion import check_infusion
from trpg.engine.rules.combat import AttackProfile, attack_value, concealment_problem
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.landing import LandingBlock, landing_problem
from trpg.engine.rules.movement import is_deadly
from trpg.engine.rules.statuses import (
    attack_range_cap,
    blocks_spells,
    skip_turn_status,
)
from trpg.engine.rules.weapons import crit_range_cut
from trpg.engine.skill_levels import level_multiplier
from trpg.engine.skills import shapes
from trpg.engine.skills.conditions import skill_condition_problem
from trpg.engine.skills.mobility import (
    ChargeRoute,
    charge_candidates,
    charge_route,
    dash_route,
    leap_candidates,
    leap_problem,
    self_move_landing,
    self_move_problem,
    shadowstep_behind,
    shadowstep_choices,
    shadowstep_spot_problem,
    swap_pair_problem,
    swap_problem,
)
from trpg.engine.skills.revive import revive_candidates, revive_target_problem
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
    "composite_area",
    "compute_area",
    "damage_parameters",
    "fires_gun",
    "followup_origin",
    "followup_selection",
    "gather_pick",
    "gather_point",
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
    "summon_site_problem",
    "teleport_landing_problem",
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


def fires_gun(caster: UnitState, skill: SkillDef) -> bool:
    """這次施放是火器開火（Phase 3-24c，08 8.11）：拿有彈匣的武器施放「用武器攻擊」的主動技
    （武器技、有傷害效果）。法術技不受影響；開火要消耗 1 發、觸發槍聲，並套用站定、遠距、貼臉、
    距離衰減等修正。"""
    return (
        skill.kind == "active"
        and skill.category == "weapon"
        and caster.weapon.magazine > 0
        and any(e.type == "damage" for e in skill.effects)
    )


def skill_profile(state: BattleState, caster: UnitState, skill: SkillDef) -> AttackProfile:
    """技能命中判定的攻擊參數。

    - 武器技：沿用 ``attack_value``（武器的縮放屬性值 ＋ 武器加值）與武器的近戰性質。
    - 法術技：技能縮放屬性值 ＋ 武器加值（只有法器類武器才加）；一律視為遠程。
    - 暴擊：武器技使用武器的 ``crit_range``（Phase 2A-2 決定 #3）；法術技只有自然 20。
    """
    height_limited = skill_is_height_limited(state, caster, skill)
    pierce = pierce_active(state, caster, skill)
    if skill.category == "weapon":
        profile = AttackProfile(
            attack_value=attack_value(caster, state.ruleset),
            melee=caster.weapon.is_melee,
            height_limited=height_limited,
            crit_range=caster.weapon.crit_range,
            pierce=pierce,
        )
        if fires_gun(caster, skill):  # 火器武器技套用武器的特性（3-24c）：站定、穿甲、無視掩護
            weapon = caster.weapon
            profile = replace(
                profile,
                crit_range=max(2, weapon.crit_range - crit_range_cut(caster)),
                defense_cut_permille=weapon.armor_pierce_permille,
                weapon_attack=True,
                ignore_cover=weapon.ignore_cover,
            )
    else:
        bonus = caster.weapon.attack_bonus if caster.weapon.weapon_class == "focus" else 0
        profile = AttackProfile(
            attack_value=skill_scaling_value(state.ruleset, caster, skill) + bonus,
            melee=False,
            height_limited=height_limited,
            crit_range=20,
            pierce=pierce,
        )
    if skill.crit_range is not None and skill.crit_range < profile.crit_range:
        profile = replace(profile, crit_range=skill.crit_range)  # 高變異（3D-7b）：取較寬的
    return profile


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
    """施放技能花的 AP：主動技能是 ``ap_cost``、姿態是 ``core.yaml`` 的 ``stance_ap_cost``、修正型
    傳說的啟動是 ``legendary_activation_ap``（Phase 3D-6），反應技與被動不花 AP。給了 ``caster``
    時加上其修正規則的 ``ap_delta``（Phase 3C-2；至少 1）。"""
    core = state.ruleset.core
    if skill.kind == "stance":
        base = core.stance_ap_cost
    elif skill.is_modifier and skill.is_activatable:  # 修正型傳說的啟動（Phase 3D-6）
        base = core.legendary_activation_ap
    else:
        base = skill.ap_cost or 0
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
    cooldown = gear_cooldown(caster, skill.cost.cooldown)  # 裝備的冷卻修正（3G-G1，下限 1）
    cooldown = gear_summon_cooldown(caster, skill, cooldown)  # 召喚技能冷卻詞條（3-33f2）
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
    if fires_gun(unit, skill) and unit.ammo <= 0:  # 火器武器技要有子彈（3-24c）
        return f"空膛：{unit.weapon.name_zh}需要先裝填才能施放：{skill.name_zh}"
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


def _already_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """已經生效、不能重複使用：已經在這個姿態（Phase 2E-2），或常駐類傳說已經啟動、已有別的規則
    改變生效中（Phase 3D-6）。"""
    if skill.kind == "stance" and any(
        e.type == "apply_status" and e.status is not None and unit.has_status(e.status)
        for e in skill.effects
    ):
        return f"已經在這個姿態中：{skill.name_zh}"
    return activation_problem(state, unit, skill)


def skill_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """技能目前不能使用的原因（繁體中文）；可以使用時回傳 ``None``（不檢查選取）。

    主動技能與姿態可以用 ``UseSkill`` 施放；姿態另外檢查「已經在這個姿態」（Phase 2E-2）。
    """
    if not skill.is_actionable:
        return f"只有主動技能、姿態與修正型傳說的啟動可以使用：{skill.name_zh}"
    ap_cost = skill_ap_cost(state, skill, unit)
    if unit.ap < ap_cost:
        return f"AP 不足：需要 {ap_cost}，剩餘 {unit.ap}"
    problem = _already_problem(state, unit, skill)
    if problem is not None:
        return problem
    if any(
        e.type in (DASH, LEAP, CHARGE_THROUGH, SHADOWSTEP) for e in skill.effects
    ):  # 自身位移（3D-2；瞬步 3D-8d）：定身、倒地不能衝跳
        problem = self_move_problem(state, unit)
        if problem is not None:
            return problem
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
    if skill.followup is not None and skill.followup.when == "after_move":
        # 複合技能（3F-3a）的位移段：目標只是位移的參照，敵我都可以
        return _visible_problem(state, caster, skill, target, reach)
    if any(e.type == SACRIFICE_SUMMON for e in effects) and target.owner_id != caster.id:
        return f"只能獻祭自己的召喚物：{target.name_zh} 不是你的召喚物"  # 獻祭召喚物（3-24c）
    enemy = target.team is not caster.team
    if enemy and not any(e.affects in ("enemies", "all", "tiles") for e in effects):
        return f"此技能無法對敵方使用：{target.name_zh}"
    if not enemy:
        helps = any(  # 賭注（gamble）的對象是施放者，但不讓技能能選自己當目標（Phase 3D-7a）
            e.type != GAMBLE
            and (
                e.affects in ("allies", "all", "tiles")
                or (e.affects == "self" and target is caster)
            )
            for e in effects
        )
        if not helps:
            return f"此技能無法對友方使用：{target.name_zh}"
    return _visible_problem(state, caster, skill, target, reach)


def _visible_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, target: UnitState, reach: int
) -> str | None:
    """單位目標看得到嗎：射程、高度、視線，致盲的距離上限，對敵人的隱蔽限制。"""
    problem = _reach_problem(state, caster, skill, target.xy, target.name_zh, reach)
    if problem is not None:
        return problem
    cap = attack_range_cap(state.ruleset, caster)  # 致盲：以單位為目標的技能只能選近處的單位
    if cap is not None and manhattan(caster.xy, target.xy) > cap:
        return f"致盲中：只能選擇 {cap} 格內的單位（距離 {manhattan(caster.xy, target.xy)}）"
    enemy = target.team is not caster.team
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
    lob = caster.weapon.lob if skill.category == "weapon" else 0  # 弓的拋射（3-24a1）
    if not has_line_of_sight(state, caster.xy, xy, lob=lob):
        return f"視線被阻擋：{caster.name_zh} 看不到 {what}"
    return None


def _self_move_target_problem(
    state: BattleState,
    caster: UnitState,
    effects: tuple[ResolvedEffect, ...],
    target: UnitState,
    reach: int,
) -> str | None:
    """衝鋒（路徑與射程）、交換位置（兩格都能站）與瞬步背刺（目標是敵人、身旁有落點）對單位目標的
    額外限制（Phase 3D-2、3D-8d）。"""
    if target.id == caster.id and any(e.type in (DASH, SWAP, SHADOWSTEP) for e in effects):
        return "不能以自己為目標（衝鋒、交換位置與瞬步需要另一個單位）"
    for effect in effects:
        if effect.type == SHADOWSTEP:
            return _shadowstep_target_problem(state, caster, target)
        if effect.type == DASH and dash_route(state, caster, target.xy, reach) is None:
            return f"無法衝鋒到 {target.name_zh}：沒有路徑能在射程 {reach} 內抵達相鄰的格子"
        if effect.type == SWAP:
            problem = swap_problem(state, caster, target)
            if problem is not None:
                return problem
    return None


def _shadowstep_target_problem(
    state: BattleState, caster: UnitState, target: UnitState
) -> str | None:
    """瞬步背刺類（``landing: behind``，Phase 3D-8d）的目標：敵方單位，身旁至少有一個落點。"""
    if target.team is caster.team:
        return f"瞬步只能以敵人為目標：{target.name_zh}"
    if shadowstep_behind(state, caster, target) is None:
        return f"{target.name_zh} 身旁沒有可以瞬步落腳的空格"
    return None


def _unit_pick_problem(  # noqa: PLR0917
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    effects: tuple[ResolvedEffect, ...],
    target: UnitState,
    reach: int,
) -> str | None:
    """單位目標的選取問題：一般技能看 :func:`_unit_target_problem` 與自身位移的額外限制；復活
    （Phase 3D-8b）的目標是倒下的友方。"""
    if any(e.type == REVIVE for e in effects):
        return _revive_pick_problem(state, caster, skill, target, reach)
    problem = _unit_target_problem(state, caster, skill, effects, target, reach)
    if problem is None:
        problem = _self_move_target_problem(state, caster, effects, target, reach)
    return problem


def _revive_pick_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, target: UnitState, reach: int
) -> str | None:
    """復活（Phase 3D-8b）的目標：射程與視線內、倒下而且可以被復活的友方。"""
    problem = revive_target_problem(state, caster, target)
    if problem is not None:
        return problem
    return _reach_problem(state, caster, skill, target.xy, target.name_zh, reach)


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
        "second_target_id": action.second_target_id,
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
        problem = _unit_pick_problem(state, caster, skill, effects, target, reach)
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
    if any(e.type in (DASH, SWAP, SHADOWSTEP) for e in effects):
        raise IllegalActionError(f"衝鋒、交換位置與瞬步的技能必須以單位為目標：{skill.name_zh}")
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
    if any(e.type == CHARGE_THROUGH for e in effects):  # 直線衝撞（3D-2c）：影響格是沿途的格子
        route = charge_route(state, caster, center, reach)
        if not isinstance(route, ChargeRoute):
            raise IllegalActionError(route)
        return route.cells, route.stop
    if any(e.type == LEAP for e in effects):  # 跳躍：無視視線與中間的單位，另有自己的落點規則
        problem = leap_problem(state, caster, center, reach)
        if problem is not None:
            raise IllegalActionError(problem)
        return center_tiles(state, skill.shape.type, center), center
    problem = shapes.center_problem(state, caster.xy, center, reach)
    if problem is not None:
        raise IllegalActionError(problem)
    if any(e.type == "teleport" for e in effects):
        block = landing_problem(state, center, mover=caster.id)
        if block in (LandingBlock.OUT_OF_BOUNDS, LandingBlock.NOT_STANDABLE):
            raise IllegalActionError(f"無法傳送到不可站立的格子：{center}")
        if block is LandingBlock.OCCUPIED:
            other = state.unit_at(*center)
            assert other is not None
            raise IllegalActionError(f"無法傳送到已有單位的格子：{center}（{other.name_zh}）")
    problem = _site_problem(state, skill, effects, center)
    if problem is not None:
        raise IllegalActionError(problem)
    return center_tiles(state, skill.shape.type, center), center


def _site_problem(
    state: BattleState, skill: SkillDef, effects: tuple[ResolvedEffect, ...], center: XY
) -> str | None:
    """放置類技能的目標格限制：陷阱（2E-3）與召喚（3D-4a）都必須是空格。"""
    if skill.trap is not None:
        problem = _trap_site_problem(state, center)
        if problem is not None:
            return problem
    if any(e.type == SUMMON for e in effects):
        return summon_site_problem(state, center)
    return None


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


def teleport_landing_problem(state: BattleState, target: UnitState, dest: XY) -> str | None:
    """傳送他人（Phase 3D-2b）的落點能不能放 ``target``：沒有單位；可站立，或是致命地形（深淵、
    岩漿；Boss 對致命地形免疫，不能選）。地圖範圍、射程與視線由呼叫端檢查。"""
    other = state.unit_at(*dest)
    if other is not None:
        return f"無法傳送到已有單位的格子：{dest}（{other.name_zh}）"
    if is_deadly(state, dest):
        if target.has_tag(BOSS_TAG):
            return f"{target.name_zh} 是 Boss，對傳送到致命地形免疫：{dest}"
        return None
    if landing_problem(state, dest) is not None:
        return f"無法傳送到不可站立的格子：{dest}"
    return None


def _sorted_tiles(*cells: XY) -> tuple[XY, ...]:
    return tuple(sorted(set(cells), key=lambda p: (p[1], p[0])))


def _pair_unit(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    unit_id: UnitId | None,
    reach: int,
) -> UnitState:
    """位移他人要選的單位：存在、存活、射程與視線內（含致盲與隱蔽限制）。"""
    unit = None if unit_id is None else state.units.get(unit_id)
    if unit is None:
        raise IllegalActionError(f"找不到目標：{unit_id}")
    if not unit.alive:
        raise IllegalActionError(f"目標已不在戰場上：{unit.name_zh}")
    problem = _visible_problem(state, caster, skill, unit, reach)
    if problem is not None:
        raise IllegalActionError(problem)
    return unit


def _unit_tile_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, *, reach: int
) -> tuple[tuple[XY, ...], XY]:
    """``targeting: unit_tile``（傳送他人，Phase 3D-2b）：被傳送的單位（不能是自己）與落點；影響
    原位置與落點兩格。落點要在射程與視線內，沒有單位，可站立或是致命地形（Boss 不行）。"""
    _require_fields(action, ("target_id", "target_pos"), "unit_tile（單位與落點）")
    if action.target_id is None or action.target_pos is None:
        raise IllegalActionError("必須同時指定 target_id（單位）與 target_pos（落點）")
    target = _pair_unit(state, caster, skill, action.target_id, reach)
    if any(e.type == SHADOWSTEP for e in skill.effects):
        return _shadowstep_tile_area(state, caster, target, action.target_pos)
    if target.id == caster.id:
        raise IllegalActionError("不能傳送自己（傳送他人要選另一個單位）")
    dest = (action.target_pos.x, action.target_pos.y)
    problem = shapes.center_problem(state, caster.xy, dest, reach)
    if problem is None:
        problem = teleport_landing_problem(state, target, dest)
    if problem is not None:
        raise IllegalActionError(problem)
    return _sorted_tiles(target.xy, dest), dest


def _shadowstep_tile_area(
    state: BattleState, caster: UnitState, target: UnitState, pos: Pos
) -> tuple[tuple[XY, ...], XY]:
    """一般瞬步（``landing: choose``，Phase 3D-8d）：第 1 段是敵人、第 2 段是他相鄰的落點；影響
    範圍只有目標所在的格子（之後的效果作用在目標身上），原點是落點。"""
    if target.team is caster.team:
        raise IllegalActionError(f"瞬步只能以敵人為目標：{target.name_zh}")
    dest = (pos.x, pos.y)
    problem = shadowstep_spot_problem(state, caster, target, dest)
    if problem is not None:
        raise IllegalActionError(problem)
    return (target.xy,), dest


def _unit_pair_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, *, reach: int
) -> tuple[tuple[XY, ...], XY]:
    """``targeting: unit_pair``（任意兩者互換，Phase 3D-2b）：兩個不同的單位（順序不拘），都在射程
    與視線內，兩格都要能讓對方站上去；影響這兩格。"""
    _require_fields(action, ("target_id", "second_target_id"), "unit_pair（兩個單位）")
    if action.target_id is None or action.second_target_id is None:
        raise IllegalActionError("任意兩者互換必須同時指定 target_id 與 second_target_id")
    if action.target_id == action.second_target_id:
        raise IllegalActionError("要互換的兩個單位必須不同")
    first = _pair_unit(state, caster, skill, action.target_id, reach)
    second = _pair_unit(state, caster, skill, action.second_target_id, reach)
    problem = swap_pair_problem(state, first, second)
    if problem is not None:
        raise IllegalActionError(problem)
    return _sorted_tiles(first.xy, second.xy), caster.xy


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


_AREA_TARGETING = frozenset({"direction", "tile", "none"})
"""``include_caster`` 會把施放者加進影響範圍的選取方式（範圍型形狀）。"""


def compute_area(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> SkillArea:
    """驗證 ``action`` 的選取並計算影響範圍；不合法或影響範圍為空時拋出 ``IllegalActionError``。"""
    check_infusion(state, caster, skill, action.infusion)
    if action.followup_target is not None and skill.followup is None:
        raise IllegalActionError(f"只有複合技能可以指定 followup_target：{skill.name_zh}")
    if action.followup_target is not None and _auto_followup(skill):
        raise IllegalActionError(
            f"{skill.name_zh} 的第二段由引擎決定目標，不能指定 followup_target"
        )
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
    elif targeting == "unit_tile":
        tiles, origin = _unit_tile_area(state, caster, skill, action, reach=reach)
    elif targeting == "unit_pair":
        tiles, origin = _unit_pair_area(state, caster, skill, action, reach=reach)
    else:
        tiles = _self_area(state, caster, skill, action, targeting)
    if not tiles:
        raise IllegalActionError("影響範圍為空：沒有任何格子會受到影響")
    if skill.include_caster and caster.xy not in tiles and targeting in _AREA_TARGETING:
        tiles = _sorted_tiles(*tiles, caster.xy)  # allow_self_target（3D-3）：施放者自己也算在內
    units = _tiles_to_units(state, tiles, chain)
    if any(e.type == CHARGE_THROUGH for e in effects):  # 隊友讓路：只有沿途的敵人會被撞
        units = tuple(u for u in units if state.units[u].team is not caster.team)
    return SkillArea(tiles=tiles, units=units, origin=origin, direction=direction)


def _trap_site_problem(state: BattleState, center: XY) -> str | None:
    """陷阱的放置格：可站立、不是致命地形、沒有單位、沒有其他陷阱（同一格只能有一個；這個檢查
    不分陣營，所以放置的合法性會洩漏對方陷阱的存在——2E 敵人沒有陷阱技能，記錄在報告）。"""
    block = landing_problem(state, center)
    if block in (LandingBlock.OUT_OF_BOUNDS, LandingBlock.NOT_STANDABLE):
        return f"無法在不可站立的格子放置陷阱：{center}"
    if block is LandingBlock.OCCUPIED:
        other = state.unit_at(*center)
        assert other is not None
        return f"無法在已有單位的格子放置陷阱：{center}（{other.name_zh}）"
    if state.trap_at(*center) is not None:
        return f"這一格已經有陷阱：{center}"
    return None


def summon_site_problem(state: BattleState, xy: XY) -> str | None:
    """召喚位置（Phase 3D-4a）的問題（``None`` 為可以）：在地圖內、可站立、不是致命地形、沒有
    單位。射程與視線由技能形狀檢查。"""
    block = landing_problem(state, xy)
    if block is LandingBlock.OUT_OF_BOUNDS:
        return f"召喚位置超出地圖：{xy}"
    if block is LandingBlock.NOT_STANDABLE:
        return f"無法在不可站立的格子召喚：{xy}"
    if block is LandingBlock.OCCUPIED:
        other = state.unit_at(*xy)
        assert other is not None
        return f"無法在已有單位的格子召喚：{xy}（{other.name_zh}）"
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
        revive = any(e.type == REVIVE for e in skill.effects)
        for unit in revive_candidates(state, caster) if revive else state.living_units():
            if manhattan(caster.xy, unit.xy) <= reach:
                yield UseSkill(unit_id=uid, skill_id=sid, target_id=unit.id)
        if skill.shape.type != "chain" and not revive:
            for obj in state.objects_sorted():
                if manhattan(caster.xy, obj.xy) <= reach:
                    yield UseSkill(unit_id=uid, skill_id=sid, target_object_id=ObjectId(obj.id))
    elif shape.targeting == "tile":
        for x, y in _tile_candidates(state, caster, skill):
            yield UseSkill(unit_id=uid, skill_id=sid, target_pos=Pos(x=x, y=y))
    elif shape.targeting in _TWO_STAGE:
        yield from _TWO_STAGE[shape.targeting](state, caster, skill)
    elif shape.targeting == "direction":
        for name in shapes.DIRECTION_ORDER:
            direction: Direction = name  # type: ignore[assignment]
            yield UseSkill(unit_id=uid, skill_id=sid, direction=direction)
    else:
        yield UseSkill(unit_id=uid, skill_id=sid)


def _tile_candidates(state: BattleState, caster: UnitState, skill: SkillDef) -> list[XY]:
    """中心格型的候選格：射程內看得到的格子；跳躍無視視線，另有自己的落點規則。"""
    reach = shape_reach(state, skill, caster)
    if any(e.type == CHARGE_THROUGH for e in skill.effects):
        return charge_candidates(state, caster, reach)
    if any(e.type == LEAP for e in skill.effects):
        return leap_candidates(state, caster, reach)
    tiles = shapes.center_candidates(state, caster.xy, reach)
    if any(e.type == SUMMON for e in skill.effects):  # 召喚（3D-4a）：只列出可以召喚的空格
        return [xy for xy in tiles if summon_site_problem(state, xy) is None]
    return tiles


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


def _reachable_units(state: BattleState, caster: UnitState, skill: SkillDef) -> list[UnitState]:
    """位移他人可以選的單位（依 ID；射程、視線與隱蔽限制已檢查）。"""
    reach = shape_reach(state, skill, caster)
    return [
        unit
        for unit in sorted(state.living_units(), key=lambda u: u.id)
        if manhattan(caster.xy, unit.xy) <= reach
        and _visible_problem(state, caster, skill, unit, reach) is None
    ]


def _teleport_candidates(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[UseSkill]:
    """傳送他人的候選：可選的單位（依 ID，不含自己）× 合法的落點（依 ``(y, x)``）。一般瞬步
    （Phase 3D-8d）：可選的敵人 × 他相鄰的落點（上、右、下、左）。"""
    if any(e.type == SHADOWSTEP for e in skill.effects):
        yield from _shadowstep_candidates(state, caster, skill)
        return
    tiles = shapes.center_candidates(state, caster.xy, shape_reach(state, skill, caster))
    for unit in _reachable_units(state, caster, skill):
        if unit.id == caster.id:
            continue
        for x, y in tiles:
            if teleport_landing_problem(state, unit, (x, y)) is None:
                yield UseSkill(
                    unit_id=caster.id,
                    skill_id=skill.id,
                    target_id=unit.id,
                    target_pos=Pos(x=x, y=y),
                )


def _shadowstep_candidates(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[UseSkill]:
    for unit in _reachable_units(state, caster, skill):
        if unit.team is caster.team:
            continue
        for x, y in shadowstep_choices(state, caster, unit):
            yield UseSkill(
                unit_id=caster.id, skill_id=skill.id, target_id=unit.id, target_pos=Pos(x=x, y=y)
            )


def _pair_candidates(state: BattleState, caster: UnitState, skill: SkillDef) -> Iterator[UseSkill]:
    """任意兩者互換的候選：可選的單位兩兩組合（每組只列一次，依單位 ID 排序）。"""
    for first, second in combinations(_reachable_units(state, caster, skill), 2):
        yield UseSkill(
            unit_id=caster.id, skill_id=skill.id, target_id=first.id, second_target_id=second.id
        )


_TWO_STAGE: dict[str, Callable[[BattleState, UnitState, SkillDef], Iterator[UseSkill]]] = {
    "object_tile": _hurl_candidates,
    "unit_tile": _teleport_candidates,
    "unit_pair": _pair_candidates,
}
"""兩段選取的形狀（投擲物件、傳送他人、任意兩者互換）的候選列舉。"""


def selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """技能目前所有合法的選取與其影響範圍（確定性順序）。不檢查代價（:func:`skill_problem`）。

    單體與連鎖：先單位（依 ID）再物件（依 ID）；中心格型：射程內每個合法格（依 ``(y, x)``）；
    方向型：東南西北（影響範圍為空的不列）。複合技能（Phase 3F-3a）：位移段的每個選取 × 動作段
    在落點的每個選取（:func:`_composite_selections`）。
    """
    when = None if skill.followup is None else skill.followup.when
    if when == "after_move":
        yield from _composite_selections(state, caster, skill)
        return
    if when == "after_gather":
        yield from _gather_selections(state, caster, skill)
        return
    for action in _candidates(state, caster, skill):
        try:
            area = checked_area(state, caster, skill, action)
        except IllegalActionError:
            continue
        yield action, area


# ---------------------------------------------------------------------------
# 複合技能（Phase 3F-3a，docs/design/06-技能.md 6.23）
# ---------------------------------------------------------------------------


def _after_move_origin(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> XY | None:
    """「位移 → 動作」：位移段預定的落點。"""
    target = None if action.target_id is None else state.units.get(action.target_id)
    pos = None if action.target_pos is None else (action.target_pos.x, action.target_pos.y)
    reach = shape_reach(state, skill, caster)
    return self_move_landing(state, caster, skill.effects[0], target, pos, reach)


_FOLLOWUP_ORIGINS: dict[str, Callable[[BattleState, UnitState, SkillDef, UseSkill], XY | None]] = {
    "after_move": _after_move_origin,
}
"""動作段的原點，依 ``followup.when`` 分派（之後的 ``after_action``、``on_kill`` 等加在這裡）。"""


def followup_origin(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> XY | None:
    """複合技能動作段的原點（以施放前的狀態推算；算不出來時為 ``None``）。"""
    assert skill.followup is not None
    return _FOLLOWUP_ORIGINS[skill.followup.when](state, caster, skill, action)


def _at(state: BattleState, caster: UnitState, origin: XY) -> tuple[BattleState, UnitState]:
    """假設施放者已站在 ``origin`` 的狀態（已經在時就是原狀態；否則是複本）。"""
    if caster.xy == origin:
        return state, caster
    ghost = state.clone()
    mover = ghost.units[caster.id]
    mover.pos = Pos(x=origin[0], y=origin[1])
    return ghost, mover


def _followup_action(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, origin: XY
) -> UseSkill:
    """``action.followup_target`` 展開成動作段的 ``UseSkill``；以落點為中心的形狀補上落點。"""
    follow = skill.followup_skill()
    assert follow is not None
    pick = action.followup_target or FollowupTarget()
    pos = pick.target_pos
    if state.ruleset.shape_def(follow.shape.type).targeting == "tile":
        if pos is not None and (pos.x, pos.y) != origin:
            raise IllegalActionError(
                f"動作段以落點 {origin} 為中心：followup_target 不用指定 target_pos"
            )
        pos = Pos(x=origin[0], y=origin[1])
    return UseSkill(
        unit_id=caster.id,
        skill_id=skill.id,
        target_id=pick.target_id,
        target_object_id=pick.target_object_id,
        target_pos=pos,
        direction=pick.direction,
    )


def followup_selection(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill, origin: XY
) -> tuple[UseSkill, SkillArea]:
    """以 ``origin`` 為施放者位置驗證動作段的選取（``action.followup_target``），回傳動作段的
    ``UseSkill`` 與影響範圍；不合法時拋出 ``IllegalActionError``（「動作段：…」）。"""
    follow = skill.followup_skill()
    assert follow is not None
    here, mover = _at(state, caster, origin)
    try:
        pick = _followup_action(here, mover, skill, action, origin)
        return pick, checked_area(here, mover, follow, pick)
    except IllegalActionError as exc:
        raise IllegalActionError(f"動作段：{exc}") from None


def composite_area(first: SkillArea, second: SkillArea) -> SkillArea:
    """兩段合起來的影響範圍（格子與單位取聯集；原點與方向取動作段的）。"""
    return SkillArea(
        tiles=_sorted_tiles(*first.tiles, *second.tiles),
        units=tuple(sorted({*first.units, *second.units})),
        origin=second.origin,
        direction=second.direction,
    )


def _followup_pick(state: BattleState, follow: SkillDef, pick: UseSkill) -> FollowupTarget | None:
    """動作段的候選 → ``followup_target``（以落點為中心或不用選取的形狀為 ``None``）。"""
    if state.ruleset.shape_def(follow.shape.type).targeting in ("tile", "none", "self"):
        return None
    return FollowupTarget(
        target_id=pick.target_id, target_object_id=pick.target_object_id, direction=pick.direction
    )


def _composite_selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """複合技能的選取：位移段的每個合法選取 × 動作段在預定落點的每個合法選取。組合數有上限：
    方向型動作段只有東南西北 4 個；單體只列落點射程內的目標；以落點為中心的形狀只有 1 個。"""
    follow = skill.followup_skill()
    assert follow is not None
    ghost = state.clone()
    mover = ghost.units[caster.id]
    for action in _candidates(state, caster, skill):
        try:
            first = checked_area(state, caster, skill, action)
        except IllegalActionError:
            continue
        origin = followup_origin(state, caster, skill, action)
        if origin is None:
            continue
        mover.pos = Pos(x=origin[0], y=origin[1])
        for pick in _candidates(ghost, mover, follow):
            try:
                second = checked_area(ghost, mover, follow, pick)
            except IllegalActionError:
                continue
            full = action.model_copy(
                update={"followup_target": _followup_pick(ghost, follow, pick)}
            )
            yield full, composite_area(first, second)


def _auto_followup(skill: SkillDef) -> bool:
    """第二段的選取由引擎決定（聚集點、命中的同一個目標；Phase 3F-4a）。"""
    return skill.followup is not None and skill.followup.when in FOLLOWUP_AUTO_WHENS


def gather_point(caster: UnitState, skill: SkillDef, action: UseSkill) -> XY:
    """「聚集 → 範圍打擊」（Phase 3F-4a）的聚集點：十字、方陣是選的中心格（``pull`` 朝它拉），
    環形是施放者自己。"""
    if skill.shape.type in FOLLOWUP_CENTERED and action.target_pos is not None:
        return (action.target_pos.x, action.target_pos.y)
    return caster.xy


def gather_pick(caster: UnitState, skill: SkillDef, action: UseSkill) -> UseSkill:
    """聚集後打擊段的選取：以聚集點為中心（打擊段的射程與聚集段相同，schema 已檢查）。"""
    x, y = gather_point(caster, skill, action)
    return UseSkill(unit_id=caster.id, skill_id=skill.id, target_pos=Pos(x=x, y=y))


def _gather_selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """「聚集 → 範圍打擊」的選取：聚集段的每個合法選取；影響範圍是聚集段與「以聚集點為中心的打擊段」
    （以施放前的位置推算）的聯集。不用 ``followup_target``。"""
    follow = skill.followup_skill()
    assert follow is not None
    for action in _candidates(state, caster, skill):
        try:
            first = checked_area(state, caster, skill, action)
        except IllegalActionError:
            continue
        try:
            second = checked_area(state, caster, follow, gather_pick(caster, skill, action))
        except IllegalActionError:
            yield action, first
            continue
        yield action, composite_area(first, second)


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
    if skill.damage_permille is not None:  # 高變異（3D-7b）：基礎傷害折扣
        multiplier = multiplier * skill.damage_permille // _PERMILLE
    multiplier = multiplier * level_multiplier(state.ruleset, caster, skill) // _PERMILLE  # 3-26a
    if modified:
        element = modifiers.damage_element(state, caster, modifiers.skill_use(skill), element)
    return DamageParameters(dice, flat, scaled, multiplier, element)
