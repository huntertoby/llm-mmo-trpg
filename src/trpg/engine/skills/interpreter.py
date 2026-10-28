"""技能解譯器：把一次 ``UseSkill`` 轉成效果佇列中的效果（Phase2A計畫 3.4、4.1–4.4）。

流程：

1. 檢查可用性與選取（:mod:`~trpg.engine.skills.targeting`），支付代價（AP、法力、HP、冷卻、
   每場次數），產生 ``skill_used``。
2. 命中：對每個受影響的 **敵方** 單位（效果的 ``affects`` 含 ``enemies``／``all``；``all`` 時
   友方也算）依單位 ID 排序各擲一次命中，公式同普攻；命中的目標才吃到以敵方為對象的效果。
   以友方、自己或格子為對象的效果不擲骰；地面效果在所有目標都失手時照樣生效。
3. 依技能裡效果的順序，每個效果原語展開成效果模型，**經由效果佇列**（:func:`execute`）結算；
   一個原語結算完（含連鎖）才處理下一個，所以「先傷害再推開」的順序與技能寫的一致。
4. 帶元素的傷害：每個受影響的格子恰好被該元素觸及一次——有單位或物件受到傷害的格子由傷害事件的
   觸發表觸及，其餘的格子（沒有人受到傷害：空格、失手的目標、帶 ``blocks_move`` 的非破壞物件……）
   以 ``tile_only`` 的 ``element_touch`` 補上（例如火焰錐形點燃空格的油）。

模組結構（Phase 3E-2b）：本模組是施放的入口（檢查、付代價、複合技能與第二段、被動／陷阱／區域／
反應等的施放），載入時登錄到 :mod:`trpg.engine.skills.casting`（其他引擎模組經由它呼叫）；一次
施放的工作狀態與流程在 :mod:`trpg.engine.skills.cast`；每個效果原語的展開在
:mod:`trpg.engine.skills.primitives`（「原語 → handler」登錄表）。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.skills import (
    EffectSpec,
    SkillDef,
    on_hit_carrier,
)
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.activations import activate
from trpg.engine.context import Ctx
from trpg.engine.copying import copy_free_problem, copy_source, has_copy_effect
from trpg.engine.delayed import charge
from trpg.engine.events import (
    EffectFizzled,
    SkillCooldownChanged,
    SkillFollowup,
    SkillUsed,
)
from trpg.engine.reactions import (
    PauseForDecision,
    after_attack,
)
from trpg.engine.results import Pending
from trpg.engine.rules.geometry import XY
from trpg.engine.self_costs import pay_self_costs
from trpg.engine.skill_triggers import collect_cast, holding
from trpg.engine.skills import casting
from trpg.engine.skills.cast import Cast, GearCast, TriggeredCast
from trpg.engine.skills.followups import (
    followup_options,
    hit_pick,
    hit_unit,
    killed_enemy,
    second_pick,
)
from trpg.engine.skills.targeting import (
    PaidCost,
    SkillArea,
    center_tiles,
    checked_area,
    composite_area,
    fires_gun,
    followup_origin,
    followup_selection,
    gather_pick,
    gather_point,
    pay_skill_cost,
    skill_ap_cost,
    skill_problem,
)
from trpg.engine.source import spend_source
from trpg.engine.state import BattleState, LastCast, TrapState, UnitState, ZoneState
from trpg.engine.traps import place_trap
from trpg.engine.variants import target_point, varied_skill
from trpg.engine.weapon_traits import gunshot_reveals, reveal_after_gunshot, spend_ammo
from trpg.engine.zones import zone_spec
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos

__all__ = [
    "run_delayed",
    "use_gear_effects",
    "use_modifier_effects",
    "use_reaction_skill",
    "use_skill",
    "use_trap_skill",
    "use_triggered_skill",
]


def _unit_id(unit: UnitState) -> str:
    return unit.id


def use_skill(ctx: Ctx, caster: UnitState, action: UseSkill) -> None:
    """``UseSkill`` 的動作處理器（``ACTION_HANDLERS["use_skill"]``）。"""
    try:
        skill = ctx.rules.skill_def(action.skill_id)
    except KeyError:
        raise IllegalActionError(f"找不到技能：{action.skill_id}") from None
    # 戰場變奏（3-25a）：依目標點選型態，再套技能等級與修正規則的變形（3D-3）
    skill, variant = varied_skill(ctx.state, caster, skill, target_point(ctx.state, action))
    skill = modifiers.shaped_skill(ctx.state, caster, skill)
    if skill.id not in caster.all_skills:
        raise IllegalActionError(f"{caster.name_zh} 沒有裝備技能：{skill.name_zh}")
    problem = skill_problem(ctx.state, caster, skill)
    if problem is not None:
        raise IllegalActionError(problem)
    area = checked_area(ctx.state, caster, skill, action)
    origin = _planned_followup(ctx.state, caster, skill, action)
    paid_area = area
    if origin is not None:
        paid_area = composite_area(
            area, followup_selection(ctx.state, caster, skill, action, origin)[1]
        )
    _check_copy(ctx, caster, skill, action)
    gun = fires_gun(caster, skill)
    reveal = gun and gunshot_reveals(ctx.state, caster)  # 槍聲：開火前是隱蔽的，開火後被揭露
    with holding(ctx):  # 被動的觸發等整個技能結算完才處理
        _pay_costs(ctx, caster, skill, paid_area, variant=variant)
        if gun:
            spend_ammo(caster)  # 火器武器技也算開火：用掉 1 發（3-24c）
        if skill.is_activatable:  # 常駐類傳說（Phase 3D-6）：施放＝啟動，沒有立即的效果
            activate(ctx, caster, skill)
        elif skill.trap is not None:  # 陷阱技能：施放時只放置陷阱，其餘效果等觸發時結算
            assert action.target_pos is not None
            place_trap(ctx, caster, skill, (action.target_pos.x, action.target_pos.y))
        else:
            _resolve_cast(ctx, caster, skill, action, area, origin)
            if reveal:
                reveal_after_gunshot(ctx, caster)
        if skill.kind == "active":  # copy_skill 的複製對象（Phase 3C-4b）
            _record_cast(ctx.state, caster, skill)
        _apply_self_status(ctx, caster, skill)
        collect_cast(ctx, caster, skill)  # on_cast_tag：在該技能結算之後
        _record_turn_tags(ctx.state, caster, skill)


def _resolve_cast(  # noqa: PLR0917
    ctx: Ctx,
    caster: UnitState,
    skill: SkillDef,
    action: UseSkill,
    area: SkillArea,
    origin: XY | None,
) -> None:
    """一般技能（含複合技能的第二段）的結算與施放後的轉向、潛行偷襲脫離。"""
    cast = Cast(ctx, caster, skill, action, area)
    face = _primary_xy(ctx.state, caster, action)
    start = len(ctx.events)
    cast.run()
    ambushed, victims = cast.ambushed, cast.melee_victims
    second: Cast | None = None
    if origin is not None:  # 複合技能（Phase 3F-3a）：到達落點才結算動作段
        second = _run_followup(ctx, caster, skill, action, origin)
    elif skill.followup is not None and skill.followup.when == "delayed":
        charge(ctx, caster, skill)  # 延遲段（Phase 3F-4b）：開始蓄力，之後才結算
    elif skill.followup is not None:  # 其他四種即時的第二段（Phase 3F-4a）
        second = _run_second(ctx, caster, skill, action, cast, start)
    if second is not None:
        ambushed = ambushed or second.ambushed
        victims = [*victims, *second.melee_victims]
        face = _primary_xy(ctx.state, caster, second.action) or face
    after_attack(ctx, caster, face, ambushed=ambushed, turns=victims)


def _planned_followup(
    state: BattleState, caster: UnitState, skill: SkillDef, action: UseSkill
) -> XY | None:
    """複合技能（Phase 3F-3a）動作段的預定原點；不是複合技能時為 ``None``。算不出原點時（位移段
    的選取已經合法，理論上不會發生）拋出 ``IllegalActionError``。"""
    if skill.followup is None or skill.followup.when != "after_move":
        return None
    origin = followup_origin(state, caster, skill, action)
    if origin is None:
        raise IllegalActionError(f"算不出 {skill.name_zh} 的落點")
    return origin


def _run_followup(
    ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill, origin: XY
) -> Cast | None:
    """結算複合技能的動作段：施放者還站著、而且真的到了預定的落點（沒被擋下、沒倒下）時，以落點
    為原點重新檢查動作段的選取並結算（``skill_followup`` 之後是動作段的事件）；否則發出
    ``effect_fizzled``（``followup_blocked``；選取在位移後不再合法時為 ``followup_no_target``）。"""
    pos = Pos(x=origin[0], y=origin[1])
    if not caster.alive or caster.xy != origin:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_blocked")
        return None
    try:
        pick, area = followup_selection(ctx.state, caster, skill, action, origin)
    except IllegalActionError:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return None
    follow = skill.followup_skill()
    assert follow is not None and skill.followup is not None
    ctx.emit(
        SkillFollowup,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        when=skill.followup.when,
        origin=pos,
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
    )
    cast = Cast(ctx, caster, follow, pick, area)
    cast.run()
    return cast


def _run_second(  # noqa: PLR0917
    ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill, first: Cast, start: int
) -> Cast | None:
    """結算「動作 → 位移」「聚集 → 範圍打擊」「擊殺 → 接下一段」「命中 → 加碼段」的第二段
    （Phase 3F-4a）：施放者還站著、而且觸發條件成立（擊殺：``start`` 之後的第一段事件裡有敵人倒下；
    命中：第一段命中了敵人）時，決定第二段的選取並結算；否則發出 ``effect_fizzled``
    （``followup_caster_down``：施放者倒下；``followup_not_triggered``：沒有擊殺或沒有命中）。"""
    assert skill.followup is not None
    when = skill.followup.when
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if not caster.alive:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_caster_down")
        return None
    hit = hit_unit(ctx.state, caster, first.hits) if when == "on_hit" else None
    if (when == "on_hit" and hit is None) or (
        when == "on_kill" and not killed_enemy(ctx.state, caster, ctx.events[start:])
    ):
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_not_triggered")
        return None
    pick = _second_selection(ctx, caster, skill, action, hit)
    if pick is None:
        return None
    follow = skill.followup_skill()
    assert follow is not None
    try:
        area = checked_area(ctx.state, caster, follow, pick)
    except IllegalActionError:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return None
    origin = gather_point(caster, skill, action) if when == "after_gather" else caster.xy
    ctx.emit(
        SkillFollowup,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        when=when,
        origin=Pos(x=origin[0], y=origin[1]),
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
    )
    cast = Cast(ctx, caster, follow, pick, area)
    cast.run()
    return cast


def run_delayed(
    ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
) -> None:
    """結算延遲段（Phase 3F-4b，:mod:`trpg.engine.delayed`）：``skill_followup``
    （``when: delayed``，原點是施放者當下的位置）之後是第二段的事件；不付代價（施放時已付）。
    被動觸發等第二段結算完才處理。"""
    follow = skill.followup_skill() if skill.followup is not None else skill  # 定向蓄力：吐息本身
    assert follow is not None
    with holding(ctx):
        ctx.emit(
            SkillFollowup,
            unit_id=caster.id,
            skill_id=skill.id,
            name_zh=skill.name_zh,
            when="delayed",
            origin=Pos(x=caster.xy[0], y=caster.xy[1]),
            tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
        )
        cast = Cast(ctx, caster, follow, pick, area)
        cast.run()
        after_attack(ctx, caster, None, ambushed=cast.ambushed, turns=cast.melee_victims)


def run_infused(
    ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
) -> None:
    """結算召喚物施放的灌注技能（Phase 3-33d，:mod:`trpg.engine.skill_infusion`）：
    ``infused_skill_cast`` 已由呼叫端發出；不付代價（灌注時施放者已付），也沒有失手反噬。命中、
    傷害照常（施放者的數字由呼叫端借給召喚物）；施放後面向主要目標。被動觸發等技能結算完才處理。"""
    with holding(ctx):
        cast = Cast(ctx, caster, skill, pick, area)
        cast.pays_miss_cost = False
        cast.run()
        face = _primary_xy(ctx.state, caster, pick)
        after_attack(ctx, caster, face, ambushed=cast.ambushed, turns=cast.melee_victims)


def _second_selection(
    ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill, hit: UnitState | None
) -> UseSkill | None:
    """第二段的選取（Phase 3F-4a）：聚集點、命中的同一個目標，或施放者自己選的
    （``followup_target``；沒帶時見 :func:`_ask_second`）。沒有選取時發出 ``effect_fizzled`` 並
    回傳 ``None``。"""
    assert skill.followup is not None
    when = skill.followup.when
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if when == "after_gather":
        return gather_pick(caster, skill, action)
    if when == "on_hit":
        assert hit is not None
        pick = hit_pick(ctx.state, caster, skill, hit)
        if pick is None:
            ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return pick
    if action.followup_target is not None:
        try:
            return second_pick(caster, skill, action.followup_target)
        except IllegalActionError:
            ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
            return None
    _ask_second(ctx, caster, skill)
    return None


def _ask_second(ctx: Ctx, caster: UnitState, skill: SkillDef) -> None:
    """``after_action``／``on_kill`` 沒有帶 ``followup_target``：沒有合法選取時第二段不結算
    （``followup_no_target``）；預覽時只算到第二段之前；重新結算時依序取用 ``Decision``（放棄時
    ``followup_declined``）；正式結算則暫停（``Pending.kind == "followup"``），等玩家選第二段的
    目標。
    接受時 :func:`trpg.engine.battle.resume` 會帶著選取重新結算，不會再走到這裡。"""
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if not followup_options(ctx.state, caster, skill):
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return
    if ctx.preview is not None:
        return
    if ctx.decisions:
        if ctx.decisions.pop(0):
            raise IllegalActionError("必須指定第二段的目標（或放棄第二段）")
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_declined")
        return
    raise PauseForDecision(Pending(kind="followup", unit_id=caster.id, skill_id=skill.id))


def _primary_xy(state: BattleState, caster: UnitState, action: UseSkill | None) -> XY | None:
    """施放時主要目標的位置（Phase 3D-8d：施放後面向它）：選取的單位（不是自己）或物件；沒有時
    為 ``None``。"""
    if action is None:
        return None
    if action.target_id is not None and action.target_id != caster.id:
        unit = state.units.get(action.target_id)
        return None if unit is None else unit.xy
    if action.target_object_id is not None:
        obj = state.objects.get(action.target_object_id)
        return None if obj is None else obj.xy
    return None


def _record_turn_tags(state: BattleState, caster: UnitState, skill: SkillDef) -> None:
    """記錄這回合施放過的標籤（``cast_tag_this_turn`` 條件）；在技能結算完之後才記，所以條件
    不含這次施放。"""
    caster.turn_cast_tags += modifiers.effective_tags(state, caster, skill)


def _record_cast(state: BattleState, caster: UnitState, skill: SkillDef) -> None:
    """記錄這次施放（``copy_skill`` 的複製對象）；舊輪的記錄一併丟掉。"""
    kept = tuple(c for c in state.casts if c.round == state.round)
    state.casts = (*kept, LastCast(caster.id, skill.id, state.round))


def _check_copy(ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill) -> None:
    """``UseSkill.copy_cast`` 的檢查（Phase 3C-4b）：只有 ``copy_skill`` 技能可以帶；``copy_skill``
    沒帶時（正式結算）暫停，等玩家選複製技能的目標；帶了就必須是目前可複製的技能，而且選取合法。"""
    if not has_copy_effect(skill):
        if action.copy_cast is not None:
            raise IllegalActionError(f"只有複製技能的技能可以指定 copy_cast：{skill.name_zh}")
        return
    found = copy_source(ctx.state, caster)
    if isinstance(found, str):
        raise IllegalActionError(found)
    copied = found[0]
    pick = action.copy_cast
    if pick is None:
        if ctx.preview is None:
            raise PauseForDecision(
                Pending(
                    kind="copy_skill",
                    unit_id=caster.id,
                    skill_id=skill.id,
                    copy_skill_id=copied.id,
                )
            )
        return  # 預覽：沒有選取就只算到複製之前
    if pick.unit_id != caster.id or pick.skill_id != copied.id or pick.copy_cast is not None:
        raise IllegalActionError(f"只能複製「{copied.name_zh}」，由施放者自己選目標")
    problem = copy_free_problem(ctx.state, caster, copied)
    if problem is not None:
        raise IllegalActionError(problem)
    checked_area(ctx.state, caster, copied, pick)


def use_triggered_skill(
    ctx: Ctx, owner: UnitState, skill: SkillDef, other: UnitState | None
) -> None:
    """結算被動技能的效果（代價與 ``skill_triggered`` 已由呼叫端處理）。

    作用的單位是 ``other``（``trigger.target: other``，倒下時沒有對象）或持有者自己；效果自動命中
    （不擲命中、沒有格擋與暴擊），狀態照常擲抵抗。
    """
    subject = owner if other is None else other
    units = (subject.id,) if subject.alive else ()
    area = SkillArea(tiles=(subject.xy,), units=units, origin=owner.xy)
    TriggeredCast(ctx, owner, skill, area).run()


def use_gear_effects(
    ctx: Ctx, owner: UnitState, carrier: SkillDef, subject: UnitState | None
) -> None:
    """結算裝備詞條（第 6、7 類，Phase 3G-G3a）的效果：``carrier`` 是詞條包成的被動技能
    （:func:`trpg.engine.gear_triggers.gear_carrier`），作用在 ``subject``（沒有時為持有者自己）；
    比照被動觸發：自動命中、狀態照常擲抵抗，不受修正規則影響；``grant_ap`` 受裝備的每回合 AP 回復
    上限約束。"""
    target = owner if subject is None else subject
    units = (target.id,) if target.alive else ()
    area = SkillArea(tiles=(target.xy,), units=units, origin=owner.xy)
    GearCast(ctx, owner, carrier, area).run()


def use_modifier_effects(
    ctx: Ctx, owner: UnitState, skill: SkillDef, effects: tuple[EffectSpec, ...], target: UnitState
) -> None:
    """結算修正規則的命中後效果（Phase 3C-2 ``on_hit_effects``；``skill_triggered`` 已由呼叫端
    發出）。

    比照被動觸發：作用在被命中的 ``target``（倒下時沒有單位對象，地面效果仍作用在其所在格），
    自動命中、狀態照常擲抵抗；這些效果本身不再受修正規則影響。
    """
    units = (target.id,) if target.alive else ()
    area = SkillArea(tiles=(target.xy,), units=units, origin=owner.xy)
    TriggeredCast(ctx, owner, on_hit_carrier(skill, effects), area).run()


def use_rule_change_effects(
    ctx: Ctx,
    owner: UnitState,
    skill: SkillDef,
    effects: tuple[EffectSpec, ...],
    target: UnitState,
    *,
    depth: int,
) -> None:
    """結算規則改變對 ``target`` 的效果（Phase 3D-6 ``pass_through_apply``；
    ``rule_change_triggered`` 已由呼叫端發出）。

    比照被動觸發：施放者是持有者本人，對象只有 ``target``，自動命中、狀態照常擲抵抗；這些效果不受
    修正規則影響；期間引起的被動觸發與反應的深度從 ``depth`` 起算。
    """
    area = SkillArea(tiles=(target.xy,), units=(target.id,), origin=owner.xy)
    carrier = skill.model_copy(update={"effects": effects})
    outer = ctx.trigger_depth
    ctx.trigger_depth = depth
    try:
        with holding(ctx):
            TriggeredCast(ctx, owner, carrier, area).run()
    finally:
        ctx.trigger_depth = outer


def use_trap_skill(ctx: Ctx, trap: TrapState, skill: SkillDef, *, depth: int) -> None:
    """結算陷阱觸發的效果（``trap_triggered`` 已由呼叫端發出，陷阱已移除；Phase 2E-3）。

    施放者是放置者在放置時的快照（屬性取 ``trap.attributes``、沒有狀態），影響範圍是以陷阱格為
    中心的 ``trap.shape``；效果自動命中（不擲命中、沒有格擋與暴擊），狀態照常擲抵抗。期間引起的
    被動觸發與反應的深度從 ``depth`` 起算。
    """
    assert skill.trap is not None
    state = ctx.state
    caster = state.units[trap.owner_id].clone()
    caster.attributes = dict(trap.attributes)
    caster.statuses = []
    center = trap.xy
    tiles = center_tiles(state, skill.trap.shape, center)
    units = tuple(sorted(u.id for xy in tiles if (u := state.unit_at(*xy)) is not None))
    area = SkillArea(tiles=tiles, units=units, origin=center)
    outer = ctx.trigger_depth
    ctx.trigger_depth = depth
    try:
        with holding(ctx):
            TriggeredCast(ctx, caster, skill, area).run()
    finally:
        ctx.trigger_depth = outer


def use_zone_effects(ctx: Ctx, zone: ZoneState, unit: UnitState, *, depth: int) -> None:
    """結算持續區域對 ``unit`` 的效果（``zone_triggered`` 已由呼叫端發出；Phase 3D-5）。

    施放者是區域建立時的快照（屬性取 ``zone.attributes``、沒有狀態），對象只有 ``unit``；``effects``
    的對象一律是區域的 ``affects``。效果自動命中（不擲命中、沒有格擋與暴擊），狀態照常擲抵抗；
    期間引起的被動觸發與反應的深度從 ``depth`` 起算。
    """
    state = ctx.state
    skill = state.ruleset.skill_def(zone.skill_id)
    spec = zone_spec(state, zone)
    caster = state.units[zone.owner_id].clone()
    caster.attributes = dict(zone.attributes)
    caster.statuses = []
    subs = tuple(e.model_copy(update={"affects": spec.affects}) for e in spec.effects or ())
    carrier = skill.model_copy(update={"effects": subs})
    area = SkillArea(tiles=(unit.xy,), units=(unit.id,), origin=unit.xy)
    outer = ctx.trigger_depth
    ctx.trigger_depth = depth
    try:
        with holding(ctx):
            TriggeredCast(ctx, caster, carrier, area).run()
    finally:
        ctx.trigger_depth = outer


def use_reaction_skill(
    ctx: Ctx,
    owner: UnitState,
    skill: SkillDef,
    trigger: UnitState | None,
    *,
    depth: int,
    on_paid: Callable[[], None] | None = None,
) -> None:
    """立刻施放反應技（Phase 2E-2；``ReactionTriggered`` 已由呼叫端發出）：不花 AP，付法力、HP 與
    冷卻，產生 ``skill_used``，然後照一般技能擲命中與抵抗。

    ``shape: single`` 的目標固定為 ``trigger``；``shape: self`` 的目標是持有者自己。
    ``depth``：這次反應的觸發深度（外層深度 + 1）；施放期間引起的被動觸發與反應再 +1。
    ``on_paid``：代價付完、效果結算之前呼叫（攔截用它發出 ``attack_intercepted``）。
    """
    if skill.shape.type == "single":
        assert trigger is not None
        area = SkillArea(tiles=(trigger.xy,), units=(trigger.id,), origin=owner.xy)
    else:
        area = SkillArea(tiles=(owner.xy,), units=(owner.id,), origin=owner.xy)
    outer = ctx.trigger_depth
    ctx.trigger_depth = depth
    try:
        with holding(ctx):
            _pay_costs(ctx, owner, skill, area)
            if on_paid is not None:
                on_paid()
            cast = Cast(ctx, owner, skill, None, area)
            single = skill.shape.type == "single" and trigger is not None and trigger is not owner
            face = trigger.xy if single and trigger is not None else None
            cast.run()
            after_attack(ctx, owner, face, ambushed=cast.ambushed, turns=cast.melee_victims)
            collect_cast(ctx, owner, skill)
    finally:
        ctx.trigger_depth = outer


def _pay_costs(
    ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea, *, variant: str | None = None
) -> None:
    ap = skill_ap_cost(ctx.state, skill, caster)
    paid: PaidCost = pay_skill_cost(caster, skill, ap=ap)
    ctx.emit(
        SkillUsed,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        ap=paid.ap,
        mana=skill.cost.mana,
        mana_after=caster.mana,
        stamina=skill.cost.stamina,
        stamina_after=caster.stamina,
        hp_spent=paid.hp,
        cooldown=paid.cooldown,
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
        source=skill.cost.source or 0,
        variant=variant,
    )
    if paid.cooldown is not None:
        ctx.emit(
            SkillCooldownChanged, unit_id=caster.id, skill_id=skill.id, remaining=paid.cooldown
        )
    spend_source(ctx, caster, skill.cost.source or 0, skill.id)  # 傳說技能（Phase 3C-4a）


def _apply_self_status(ctx: Ctx, caster: UnitState, skill: SkillDef) -> None:
    """自身狀態代價（``cost.self_status``，Phase 2H-1）：施放結算完之後，施放者獲得該狀態
    （不擲抵抗）。

    放在結算之後而不是支付代價當下，這樣虛弱不會削弱這次施放本身的傷害；施放者在結算中倒下則
    不施加。
    """
    pay_self_costs(ctx, caster, skill)


class _Interpreter:
    """登錄到 :mod:`trpg.engine.skills.casting` 的實作（其他模組經由 ``casting`` 呼叫）。"""

    use_skill = staticmethod(use_skill)
    use_triggered_skill = staticmethod(use_triggered_skill)
    use_gear_effects = staticmethod(use_gear_effects)
    use_modifier_effects = staticmethod(use_modifier_effects)
    use_rule_change_effects = staticmethod(use_rule_change_effects)
    use_trap_skill = staticmethod(use_trap_skill)
    use_zone_effects = staticmethod(use_zone_effects)
    use_reaction_skill = staticmethod(use_reaction_skill)
    run_delayed = staticmethod(run_delayed)
    run_infused = staticmethod(run_infused)


casting.install(_Interpreter())
