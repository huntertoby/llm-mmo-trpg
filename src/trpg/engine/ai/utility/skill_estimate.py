"""效用 AI 的技能便宜估計（:func:`skill_estimate`）：不跑引擎先篩選與排序技能選取。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

from trpg.content.environment import (
    AiWeights,
    TrapAiRules,
)
from trpg.content.skills import (
    CHARGE_THROUGH,
    CHARGING,
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    EXTRA_REACTION,
    GRANT_AP,
    GRANT_SKILL,
    LEAP,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    RESET_COOLDOWN,
    RESTORE_RESOURCE,
    REVIVE,
    SACRIFICE_SUMMON,
    SHADOWSTEP,
    EffectSpec,
    SkillDef,
    weapon_problem,
)
from trpg.engine.actions import (
    UseSkill,
)
from trpg.engine.ai.composite import composite_estimate
from trpg.engine.ai.displace import DISPLACE_PRIMITIVES, displace_estimate
from trpg.engine.ai.rune import is_inscribe_skill, rune_estimate
from trpg.engine.ai.scene_objects import SCENE_PRIMITIVES, scene_estimate
from trpg.engine.ai.summon import (
    has_summon,
    sacrifice_estimate,
    summon_estimate,
    summon_template,
)
from trpg.engine.ai.terrain import is_terrain_only, terrain_estimate
from trpg.engine.ai.utility.gains import effective_skill
from trpg.engine.ai.utility.position import _harmful, _outgunners, _Scene, _unit_position_value
from trpg.engine.ai.zone import is_zone_skill, zone_estimate
from trpg.engine.grants import granted_remaining
from trpg.engine.resources import restorable_cooldowns
from trpg.engine.rewrites import grant_ap_problem, resettable_cooldowns
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.geometry import (
    XY,
    bresenham,
    manhattan,
)
from trpg.engine.rules.statuses import stance_status_ids
from trpg.engine.skills.conditions import unit_held
from trpg.engine.skills.mobility import shadowstep_behind
from trpg.engine.skills.scaling import mastery_duration_bonus
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    SkillArea,
    center_tiles,
    resolve_effects,
)
from trpg.engine.state import BattleState, UnitState
from trpg.engine.traps import own_traps
from trpg.shared.types import Pos


def _breath_locks_form(unit: UnitState, skill: SkillDef) -> bool:
    """``unit`` 正在定向蓄力（龍的吐息）時，進入別的形態的技能不選（切換形態會取消蓄力，3J-4）。
    AI 本來就不主動取消形態（``EndStance`` 不評分），所以只需擋進入。"""
    if skill.form_id is None:
        return False
    charging = unit.get_status(CHARGING)
    return charging is not None and charging.direction is not None


def skill_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    action: UseSkill,
    area: SkillArea,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
    *,
    trap: TrapAiRules,
) -> Fraction | None:
    """技能選取（影響範圍為 ``area``）的便宜估計（不跑引擎），用來篩出每個技能最值得完整評分的
    幾個選取；``None`` 表示不納入候選（這是 ``worth_previewing`` 在技能上的對應）。

    - 含 ``summon``（Phase 3D-4a）：召喚位置越靠近最近的敵人越高
      （:func:`~trpg.engine.ai.summon.summon_estimate`）；
    - 含 ``zone``（Phase 3D-5）：區域格內與移動路徑上的對象數
      （:func:`~trpg.engine.ai.zone.zone_estimate`）；
    - 含 ``charge_through``：沿途的敵人數 × 3 ＋ 終點的位置價值變化（沒有敵人就不納入）；
    - 含 ``teleport`` 或 ``leap``：把行動者放到目標格後的位置價值變化（同
      :func:`virtual_move_score`；跳躍用來脫離或上高處，Phase 3D-2）；
    - 含 ``hurl_object`` 或 ``topple``：落點與爆炸範圍內、或倒下壓住的敵人數
      （:func:`~trpg.engine.ai.scene_objects.scene_estimate`）；
    - 影響範圍內有敵方單位、可破壞物件，或（有治療的技能）受傷的友方：分數 ＝ 敵人數 × 3 ＋
      受傷友方 × 2 − 其他友方 × 3 ＋ 可破壞物件數；
    - 場地型技能（效果只作用在格子或自己身上：煙幕、石牆、隱匿……）沒有上述對象時，看它是否
      可能改變自己的處境（:func:`_field_value`）：涵蓋自己所在的格子，或擋在敵人與自己之間；
    - 其餘不納入。平手以與施放者的距離判定（近者優先，保持確定）。

    估計只決定「誰值得完整預覽」；值不值得施放由預覽的收益、位置價值的差與機會成本決定。
    """
    skill = effective_skill(state, action)
    in_form = unit.form is not None and skill.form_id is None
    stance_locked = skill.kind == "stance" and (in_form or stance_status_ids(state.ruleset, unit))
    if stance_locked or _breath_locks_form(unit, skill):
        # 已經有姿態：AI 不主動換（也不主動取消，Phase 2E-2、3J-1a）；形態可輪替（3J-1b）；
        # 定向蓄力中也不換形態（換形態會取消蓄力，3J-4）
        return None
    if skill.followup is not None:
        return composite_estimate(state, unit, skill, area, action)
    placed = _placement_estimate(state, unit, skill, area, scene, trap=trap)
    if not isinstance(placed, _Unhandled):
        return placed
    special = _special_estimate(state, unit, skill, action, area, scene, w, before)
    if not isinstance(special, _Unhandled):
        return special
    effects = resolve_effects(state, skill)
    score = Fraction(0)
    useful = False
    for uid in area.units:
        other = state.units[uid]
        if other.team is not unit.team:
            score += 3
            useful = True
        elif _supports(state, unit, skill, effects, other):
            score += 2
            useful = True
        elif other.id != unit.id:
            score -= 3
    for xy in area.tiles:
        obj = state.object_at(*xy)
        if obj is not None and obj.hp is not None:
            score += 1
            useful = True
    if not useful:
        field = _field_value(state, unit, area.tiles, scene) if _is_field_skill(effects) else 0
        if field == 0:
            return None
        score = Fraction(field)
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


class _Unhandled:
    """:func:`_special_estimate` 沒有處理這個技能（交給一般估計）。"""


_UNHANDLED = _Unhandled()


def _placement_estimate(
    state: BattleState,
    unit: UnitState,
    skill: SkillDef,
    area: SkillArea,
    scene: _Scene,
    *,
    trap: TrapAiRules,
) -> Fraction | _Unhandled | None:
    """放置類技能的估計：陷阱、召喚（3D-4a：位置越靠近敵人越好）、持續區域（3D-5：格內與移動
    路徑上的對象數）、常駐類傳說的啟動（3D-6：有敵人就是候選）、進入形態（3J-1a：一律是候選）；
    其他技能回傳 ``_UNHANDLED``。"""
    if skill.is_activatable:  # 常駐類傳說（Phase 3D-6）：場上還有敵人時才考慮啟動
        return Fraction(1) if scene.enemies else None
    # 復活（3D-8b）：每個可復活的友方都是候選；形態（3J-1a）：值不值得由預覽的 form_entered 收益決定
    if skill.form_id is not None or any(e.type == REVIVE for e in skill.effects):
        return Fraction(1)
    if skill.trap is not None:
        return _trap_estimate(state, unit, skill, area, scene, rules=trap)
    if has_summon(skill):
        return summon_estimate(state, unit, area.origin, summon_template(skill))
    if any(e.type == SACRIFICE_SUMMON for e in skill.effects):  # 獻祭召喚物（3-24c）
        target = next(
            (state.units[u] for u in area.units if state.units[u].owner_id == unit.id), None
        )
        return None if target is None else sacrifice_estimate(state, unit, skill, target.xy)
    return _field_placement_estimate(state, unit, skill, area)


def _field_placement_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, area: SkillArea
) -> Fraction | _Unhandled | None:
    """持續區域（3D-5：格內與移動路徑上的對象數）與刻印（3-23：有讀取技能時，敵人會停留的格子
    越多越好）的估計；其他技能回傳 ``_UNHANDLED``。"""
    if is_zone_skill(skill):
        return zone_estimate(
            state, unit, skill, tiles=area.tiles, direction=area.direction, origin=area.origin
        )
    if is_inscribe_skill(skill):
        return rune_estimate(state, unit, skill, area.tiles, area.origin)
    return _UNHANDLED


def _special_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    skill: SkillDef,
    action: UseSkill,
    area: SkillArea,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
) -> Fraction | _Unhandled | None:
    """位置型與組合型技能的估計：傳送與跳躍（自己的位置價值變化）、投擲物件與推倒（Phase 3C-5b）、
    位移他人（Phase 3D-2b）；其他技能回傳 ``_UNHANDLED``。"""
    effect_types = {e.type for e in skill.effects}
    if CHARGE_THROUGH in effect_types:  # 直線衝撞（3D-2c）：路徑上的敵人數 ＋ 終點的位置價值變化
        return _charge_estimate(state, unit, area, scene, w, before)
    if SHADOWSTEP in effect_types and action.target_id is not None:
        return _shadowstep_estimate(state, unit, action, scene, w, before)
    if effect_types & {"teleport", LEAP} and action.target_pos is not None:
        moved = unit.clone()
        moved.pos = action.target_pos
        return _unit_position_value(state, moved, w, scene) - before
    if effect_types & set(SCENE_PRIMITIVES):
        return scene_estimate(state, unit, skill, action, area)
    if effect_types & set(DISPLACE_PRIMITIVES):
        return displace_estimate(state, unit, skill, action, _harmful)
    # 純地形（3T-5）：隆起／下陷
    return (
        terrain_estimate(state, unit, skill, area, w.height)
        if is_terrain_only(skill)
        else _UNHANDLED
    )


def _charge_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    area: SkillArea,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
) -> Fraction | None:
    if not area.units:
        return None
    moved = unit.clone()
    moved.pos = Pos(x=area.origin[0], y=area.origin[1])
    gain = w.charge_per_enemy * len(area.units)
    return gain + _unit_position_value(state, moved, w, scene) - before


def _shadowstep_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    action: UseSkill,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
) -> Fraction | None:
    """瞬步（Phase 3D-8d）的估計：目標 ``shadowstep`` 分、落在目標背後再加 ``shadowstep_behind``
    分（權重，預設 3 與 2），加上落點（面向目標）的位置價值變化；找不到落點時不納入。"""
    assert action.target_id is not None
    target = state.units[action.target_id]
    if action.target_pos is not None:
        dest: XY | None = (action.target_pos.x, action.target_pos.y)
    else:
        dest = shadowstep_behind(state, unit, target)
    if dest is None:
        return None
    moved = unit.clone()
    moved.pos = Pos(x=dest[0], y=dest[1])
    behind = w.shadowstep_behind if is_behind(dest, target) else 0
    return w.shadowstep + behind + _unit_position_value(state, moved, w, scene) - before


def _trap_estimate(
    state: BattleState,
    unit: UnitState,
    skill: SkillDef,
    area: SkillArea,
    scene: _Scene,
    *,
    rules: TrapAiRules,
) -> Fraction | None:
    """陷阱選取的便宜估計：自己陣營的陷阱還沒滿、波及範圍內沒有友方（含自己）、且最近的敵人在
    1–3 格內。分數 ＝ 3 格內敵人數 × 4 − 最近敵人的距離。AI 只讀自己陣營的陷阱（隱藏規則）。"""
    assert skill.trap is not None
    if len(own_traps(state, unit.team)) >= rules.max_active:
        return None
    center = area.origin
    blast = center_tiles(state, skill.trap.shape, center)
    if any(u.team is unit.team and u.xy in blast for u in state.living_units()):
        return None
    distances = [manhattan(center, e.xy) for e in scene.enemies]
    near = [d for d in distances if d <= rules.near]
    if not near:
        return None
    return Fraction(len(near) * 4 - min(near)) - Fraction(manhattan(unit.xy, center), 1000)


def _supports(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    effects: tuple[ResolvedEffect, ...],
    target: UnitState,
) -> bool:
    """技能的支援效果（治療、護盾、淨化、增益）對友方 ``target`` 有沒有用（便宜的估計）。"""
    for resolved in effects:
        helps = resolved.affects in ("allies", "all") or (
            resolved.affects == "self" and target.id == caster.id
        )
        if not helps:
            continue
        spec = skill.effects[resolved.spec_index]
        if resolved.type == "heal" and target.hp < target.max_hp:
            return True
        if resolved.type == "shield":
            return True
        if _rewrite_supports(state, caster, skill, spec, target):
            return True
        if resolved.type == "cleanse" and any(
            state.ruleset.status_def(s.status_id).polarity == "debuff" and not s.cost_status
            for s in target.statuses  # 代價狀態淨化不掉（#62）
        ):
            return True
        if resolved.type == "apply_status" and spec.status is not None:
            definition = state.ruleset.status_def(spec.status)
            if not definition.beneficial:
                continue
            current = target.get_status(spec.status)
            duration = spec.duration or definition.duration
            if duration is not None:
                duration += mastery_duration_bonus(caster, skill)
            if current is None or (
                duration is not None
                and current.remaining is not None
                and current.remaining < duration
            ):
                return True
    return False


def _restore_supports(
    state: BattleState, _caster: UnitState, skill: SkillDef, spec: EffectSpec, target: UnitState
) -> bool:
    """``restore_resource`` 對 ``target`` 有沒有用：法力有空間或有可縮短的冷卻。"""
    if spec.resource == "mana":
        return target.max_mana - target.mana >= (spec.amount or 1) // 2 + 1
    return bool(restorable_cooldowns(state, target, skill))


def _grant_supports(
    state: BattleState, _caster: UnitState, _skill: SkillDef, spec: EffectSpec, target: UnitState
) -> bool:
    """``grant_skill`` 對 ``target`` 有沒有用（Phase 3D-8c）：被給的技能他沒有裝備、拿得動（武器
    相容），而且還沒有暫時擁有（或只剩最後一輪）。"""
    assert spec.skill is not None
    if spec.skill in target.skills:
        return False
    granted = state.ruleset.skill_def(spec.skill)
    if weapon_problem(granted, target.weapon.weapon_class, unit_held(target)) is not None:
        return False
    left = granted_remaining(target, spec.skill)
    return left is None or left <= 1


_SUPPORT_CHECKS: dict[
    str, Callable[[BattleState, UnitState, SkillDef, EffectSpec, UnitState], bool]
]
_SUPPORT_CHECKS = {
    GRANT_AP: lambda state, _c, _s, _spec, target: grant_ap_problem(state, target) is None,
    RESET_COOLDOWN: lambda state, caster, skill, spec, target: bool(
        resettable_cooldowns(state, caster, target, skill, spec)
    ),
    CHEAT_DEATH: lambda _st, _c, _s, _spec, target: not target.has_status(CHEAT_DEATH_STATUS),
    REDIRECT_DAMAGE: lambda _st, caster, _s, _spec, target: (
        target.id != caster.id and not target.has_status(REDIRECT_STATUS)
    ),
    EXTRA_REACTION: lambda _st, _c, _s, _spec, target: (
        bool(target.reactions) and target.extra_reactions == 0
    ),
    RESTORE_RESOURCE: _restore_supports,
    GRANT_SKILL: _grant_supports,
}


def _rewrite_supports(
    state: BattleState, caster: UnitState, skill: SkillDef, spec: EffectSpec, target: UnitState
) -> bool:
    """改寫規則型與資源原語（Phase 3C-4a、3D-1）對友方 ``target`` 有沒有用：這一輪還沒被給過 AP、
    有可以重置或縮短的冷卻、還沒有免死、法力有空間……。"""
    check = _SUPPORT_CHECKS.get(spec.type)
    return check is not None and check(state, caster, skill, spec, target)


def _is_field_skill(effects: tuple[ResolvedEffect, ...]) -> bool:
    """場地型技能：每個效果都只作用在格子或施放者自己身上。"""
    return all(e.affects in ("tiles", "self") for e in effects)


def _field_value(state: BattleState, unit: UnitState, tiles: tuple[XY, ...], scene: _Scene) -> int:
    """場地型技能的選取可能改變自己處境的程度（Phase 2A-2 決定 #2）。

    位置價值只在「有敵人打得到自己、自己卻打不到」時（``exposed``，:func:`_outgunned_by`）才會被
    煙幕與隱蔽改善，所以只看這些敵人：涵蓋自己的格子 2 分，每名這樣的敵人與自己之間的視線穿過
    影響範圍 1 分。
    """
    threats = _outgunners(state, unit, scene.enemies)
    if not threats:
        return 0
    covered = set(tiles)
    value = 2 if unit.xy in covered else 0
    for enemy in threats:
        if any(xy in covered for xy in bresenham(enemy.xy, unit.xy)[1:-1]):
            value += 1
    return value
