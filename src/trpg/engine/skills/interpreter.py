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
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import ClassVar, Literal

from trpg.content.battle import Dice
from trpg.content.skills import (
    ADD_STACK,
    CHARGE_THROUGH,
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    CONSUME_STACK,
    CONSUME_STATUS,
    COPY_SKILL,
    DAMAGE_MULTIPLIER,
    DASH,
    DELAYED_DAMAGE,
    DISPEL,
    EXTRA_REACTION,
    GAMBLE,
    GRANT_AP,
    GRANT_SKILL,
    HURL_OBJECT,
    INTERCEPT,
    LEAP,
    PLACE_TRAP,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    REFUND_AP,
    REFUND_COOLDOWN,
    RESET_COOLDOWN,
    RESTORE_RESOURCE,
    REVEAL,
    REVIVE,
    SELF_DAMAGE_OF_HIT,
    SHADOWSTEP,
    STEAL_BUFF,
    SUMMON,
    SWAP,
    SWAP_ANY,
    TELEPORT_TARGET,
    TIME_BOMB,
    TOPPLE,
    ZONE,
    ConditionSpec,
    EffectSpec,
    SkillDef,
    default_affects,
    on_hit_carrier,
)
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.activations import activate
from trpg.engine.context import Ctx
from trpg.engine.control import status_effect
from trpg.engine.copying import copy_free_problem, copy_source, has_copy_effect
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CleanseEffect,
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DamageEffect,
    DamageObjectEffect,
    DestroyObjectEffect,
    EffectBase,
    ElementTouchEffect,
    HealEffect,
    HurlObjectEffect,
    LowerTerrainEffect,
    MoveUnitEffect,
    PushEffect,
    RaiseTerrainEffect,
    RemoveStatusEffect,
    ShieldEffect,
    SwapUnitsEffect,
)
from trpg.engine.events import (
    AttackRolled,
    BacklashTriggered,
    DamageDealt,
    EffectFizzled,
    GambleRolled,
    ObjectDamaged,
    ShotPierced,
    SkillCooldownChanged,
    SkillCopied,
    SkillUsed,
    UnitCharged,
    UnitDashed,
    UnitDowned,
)
from trpg.engine.grants import grant_skill
from trpg.engine.maneuvers import contest
from trpg.engine.pierce import NO_PIERCE, PierceTrace, pierce_trace
from trpg.engine.reactions import (
    PauseForDecision,
    after_attack,
    ally_targeted_reactions,
    block_multiplier,
    enemy_enters_adjacent_reactions,
    enemy_moves_in_range_reactions,
    hit_reactions,
    opportunity_attacks,
    spell_hit_reactions,
    try_intercept,
)
from trpg.engine.refunds import refund_ap, refund_cooldown
from trpg.engine.resources import (
    dispelled_buffs,
    pick_stolen_buff,
    restore_cooldowns,
    restore_mana,
)
from trpg.engine.results import Pending
from trpg.engine.rewrites import grant_ap, grant_reactions, reset_cooldowns
from trpg.engine.rules.combat import PERMILLE, AttackProfile, AttackRoll, ForcedOutcome, roll_attack
from trpg.engine.rules.facing import face_toward
from trpg.engine.rules.geometry import XY, axis_direction, manhattan
from trpg.engine.rules.movement import is_deadly
from trpg.engine.rules.statuses import is_rooted, skip_turn_status
from trpg.engine.skill_triggers import collect_cast, collect_move, holding
from trpg.engine.skills.charge import aside_direction
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.skills.mobility import ChargeRoute, charge_route, dash_route, shadowstep_behind
from trpg.engine.skills.revive import revive_unit
from trpg.engine.skills.scaling import mastery_duration_bonus, skill_scaling_value
from trpg.engine.skills.targeting import (
    PaidCost,
    ResolvedEffect,
    SkillArea,
    center_tiles,
    checked_area,
    damage_parameters,
    pay_skill_cost,
    resolve_effects,
    shape_reach,
    skill_ap_cost,
    skill_problem,
    skill_profile,
)
from trpg.engine.skills.variance import overload_bonus, scale_bonus
from trpg.engine.source import spend_source
from trpg.engine.stacks import add_stacks, consume_stacks
from trpg.engine.state import BattleState, LastCast, TrapState, UnitState, ZoneState
from trpg.engine.summons import summon_unit
from trpg.engine.traps import place_trap, reveal_traps
from trpg.engine.zones import create_zone, zone_spec
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, UnitId

__all__ = [
    "use_modifier_effects",
    "use_reaction_skill",
    "use_skill",
    "use_trap_skill",
    "use_triggered_skill",
]

PRONE = "prone"
TOPPLABLE = "topplable"
REWRITE_PRIMITIVES = (
    GRANT_AP,
    RESET_COOLDOWN,
    CHEAT_DEATH,
    REDIRECT_DAMAGE,
    COPY_SKILL,
    EXTRA_REACTION,
)
"""由 :meth:`_Cast.rewrite` 結算的改寫規則型原語。"""
_TOUCHING_AFFECTS = ("enemies", "all", "tiles")
_OWN_CHECK = (SWAP, SWAP_ANY, TELEPORT_TARGET, ZONE, REVEAL)
"""位移類原語自己擲抵抗判定（Phase 3D-2b），不另外擲命中；揭露（Phase 3D-8a）自動命中範圍內的
敵人。"""
REVEALED = "revealed"
"""``reveal`` 施加的狀態（``statuses.yaml``，``prevents_concealment``）。"""
CONCEALED = "concealed"


def _unit_id(unit: UnitState) -> str:
    return unit.id


def use_skill(ctx: Ctx, caster: UnitState, action: UseSkill) -> None:
    """``UseSkill`` 的動作處理器（``ACTION_HANDLERS["use_skill"]``）。"""
    try:
        skill = ctx.rules.skill_def(action.skill_id)
    except KeyError:
        raise IllegalActionError(f"找不到技能：{action.skill_id}") from None
    skill = modifiers.shaped_skill(ctx.state, caster, skill)  # 修正規則的變形（3D-3）
    if skill.id not in caster.all_skills:
        raise IllegalActionError(f"{caster.name_zh} 沒有裝備技能：{skill.name_zh}")
    problem = skill_problem(ctx.state, caster, skill)
    if problem is not None:
        raise IllegalActionError(problem)
    area = checked_area(ctx.state, caster, skill, action)
    _check_copy(ctx, caster, skill, action)
    with holding(ctx):  # 被動的觸發等整個技能結算完才處理
        _pay_costs(ctx, caster, skill, area)
        if skill.is_activatable:  # 常駐類傳說（Phase 3D-6）：施放＝啟動，沒有立即的效果
            activate(ctx, caster, skill)
        elif skill.trap is not None:  # 陷阱技能：施放時只放置陷阱，其餘效果等觸發時結算
            assert action.target_pos is not None
            place_trap(ctx, caster, skill, (action.target_pos.x, action.target_pos.y))
        else:
            cast = _Cast(ctx, caster, skill, action, area)
            face = _primary_xy(ctx.state, caster, action)
            cast.run()
            after_attack(ctx, caster, face, ambushed=cast.ambushed, turns=cast.melee_victims)
        if skill.kind == "active":  # copy_skill 的複製對象（Phase 3C-4b）
            _record_cast(ctx.state, caster, skill)
        _apply_self_status(ctx, caster, skill)
        collect_cast(ctx, caster, skill)  # on_cast_tag：在該技能結算之後
        _record_turn_tags(ctx.state, caster, skill)


def _primary_xy(state: BattleState, caster: UnitState, action: UseSkill) -> XY | None:
    """施放時主要目標的位置（Phase 3D-8d：施放後面向它）：選取的單位（不是自己）或物件；沒有時
    為 ``None``。"""
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
    _TriggeredCast(ctx, owner, skill, area).run()


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
    _TriggeredCast(ctx, owner, on_hit_carrier(skill, effects), area).run()


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
            _TriggeredCast(ctx, owner, carrier, area).run()
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
            _TriggeredCast(ctx, caster, skill, area).run()
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
            _TriggeredCast(ctx, caster, carrier, area).run()
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
            cast = _Cast(ctx, owner, skill, None, area)
            single = skill.shape.type == "single" and trigger is not None and trigger is not owner
            face = trigger.xy if single and trigger is not None else None
            cast.run()
            after_attack(ctx, owner, face, ambushed=cast.ambushed, turns=cast.melee_victims)
            collect_cast(ctx, owner, skill)
    finally:
        ctx.trigger_depth = outer


def _pay_costs(ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
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
        hp_spent=paid.hp,
        cooldown=paid.cooldown,
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
        source=skill.cost.source or 0,
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
    cost = skill.cost.self_status
    if cost is None:
        return
    execute(
        ctx,
        [
            ApplyStatusEffect(
                source_id=caster.id,
                target_id=caster.id,
                status_id=cost.status,
                duration=cost.duration,
            )
        ],
    )


class _Cast:
    """一次施放的工作狀態（命中結果、格擋倍率與影響範圍）。

    ``modified``：這次施放受施放者的修正規則影響（主動、姿態、反應技；Phase 3C-2）。
    """

    modified = True
    _SIMPLE: ClassVar[dict[str, _Builder]]

    def __init__(
        self,
        ctx: Ctx,
        caster: UnitState,
        skill: SkillDef,
        action: UseSkill | None,
        area: SkillArea,
    ) -> None:
        self.ctx = ctx
        self.caster = caster
        self.skill = skill
        self.action = action
        self.area = area
        self.effects: tuple[ResolvedEffect, ...] = resolve_effects(ctx.state, skill)
        self.profile: AttackProfile = skill_profile(ctx.state, caster, skill)
        self.trace: PierceTrace = NO_PIERCE
        """穿透的射線（Phase 3C-5b；沒有穿透或被動、陷阱的施放為 ``NO_PIERCE``）。"""
        if self.modified and self.profile.pierce:
            self.trace = pierce_trace(ctx.state, caster, skill.shape.type, area)
        units = [ctx.state.units[uid] for uid in area.units]
        self.enemies = [u for u in units if u.team is not caster.team]
        self.allies = [u for u in units if u.team is caster.team]
        self.hits: dict[str, AttackRoll] = {}
        self.blocks: dict[str, int] = {}
        self.caster_bonus = 0
        """消耗施放者層數得到的傷害加成（‰，所有目標共用；``consume_stack`` 的結果）。"""
        self.target_bonus: dict[str, int] = {}
        """消耗目標層數得到的傷害加成（‰），單位 ID → 加成。"""
        self.use = modifiers.skill_use(skill)
        self.cooldown_delta = 0
        """修正規則的命中後冷卻修正（≤ 0；命中判定當下決定，全部效果結算後套用）。"""
        self.gamble_mult = PERMILLE
        """賭注成功分支的 ``damage_multiplier``（‰）：本次施放的傷害效果再乘上它（Phase 3D-7a）。"""
        self.gamble_branch: tuple[EffectSpec, ...] = ()
        """賭注擲出的分支（``win`` 或 ``lose`` 的效果）；沒有賭注或賭注沒有結算時為空。"""
        self.cast_start = 0
        """賭注擲骰時的事件數：``self_damage_of_hit`` 以這之後造成的傷害計算。"""
        self.pays_miss_cost = True
        """失手反噬（``cost.on_miss``）是否適用：複製的技能不付代價，所以不適用。"""
        self.melee_victims: list[tuple[UnitState, XY]] = []
        """被這次施放的近戰命中判定打到的單位與當時施放者的位置：結算完轉身（Phase 3C-6a）。"""

    # ------------------------------------------------------------------
    # 命中
    # ------------------------------------------------------------------

    @property
    def ambushed(self) -> bool:
        """這次施放在隱蔽中擲過命中（潛行偷襲，Phase 3D-8d）：結算完要移除隱蔽。"""
        return any(roll.ambush > 0 for roll in self.hits.values())

    def _affected_by_damage(self, unit: UnitState) -> bool:
        enemy = unit.team is not self.caster.team
        return any(
            e.type == "damage" and (e.affects == "all" or (enemy and e.affects == "enemies"))
            for e in self.effects
        )

    def react_to_targeting(self) -> bool:
        """單體的敵對技能選定目標、命中判定之前：目標的相鄰友方可以用 ``ally_targeted`` 反應技反應
        （Phase 3D-3；被動觸發、陷阱不是施放者的動作，不呼叫）。回傳這次施放是否繼續：反應讓施放者
        或目標倒下時為 ``False``（發出的反應事件保留，其餘效果不結算）。"""
        if not self.modified or self.skill.shape.type != "single" or len(self.enemies) != 1:
            return True
        if any(e.hostile for e in self.effects):
            ally_targeted_reactions(self.ctx, self.caster, self.enemies[0])
        return self.caster.alive and self.enemies[0].alive

    def roll_hits(self) -> None:
        rolled: list[UnitState] = []
        rolling = [e for e in self.effects if e.type not in _OWN_CHECK]  # 位移他人自己擲抵抗
        if any(e.affects in ("enemies", "all") for e in rolling):
            rolled += self.enemies
        if any(e.affects == "all" and not self._splits(e) for e in rolling):
            rolled += [u for u in self.allies if u is not self.caster]  # 敵我不分也不打到自己
        for unit in sorted(rolled, key=lambda u: u.id):
            self._roll_one(unit)
        if self.modified:
            self._update_cooldown_delta()

    def _splits(self, effect: ResolvedEffect) -> bool:
        """這個效果是聖光雙效（``split_heal``，Phase 3D-8a）：友方改為治療、不擲命中。"""
        return effect.spec_index >= 0 and bool(self.skill.effects[effect.spec_index].split_heal)

    def _update_cooldown_delta(self) -> None:
        """修正規則的命中後冷卻修正：以目前已命中的敵人計算（命中判定之後呼叫）。"""
        hit = [Subject(u, u.xy) for u in self.enemies if self._hit(u)]
        self.cooldown_delta = modifiers.cooldown_delta(self.ctx.state, self.caster, self.use, hit)

    def _roll_one(self, unit: UnitState, *, force_block: bool = False) -> AttackRoll:
        """對 ``unit`` 擲一次命中（發出 ``attack_rolled``、記錄結果；單體命中時給守護者攔截的機會，
        命中且受傷害效果影響——或 ``force_block``（直線衝撞自己結算傷害）——時決定格擋倍率）。"""
        ctx = self.ctx
        forced: ForcedOutcome | None = None
        if ctx.preview is not None:
            ctx.mark_branch()
            forced = "hit" if ctx.preview == "min" else "crit"
        bonus = self._modifier(modifiers.hit_bonus, unit)
        roll = roll_attack(ctx.state, ctx.rng, self.caster, unit, forced, self.profile, bonus=bonus)
        rolled_event = ctx.emit(
            AttackRolled,
            attacker_id=self.caster.id,
            target_id=unit.id,
            rolls=roll.rolls,
            advantage=roll.advantage,
            natural=roll.natural,
            attack_value=roll.attack_value,
            defense_value_permille=roll.defense_value_permille,
            hit_modifier=roll.hit_modifier,
            proficiency=roll.proficiency,
            situational=roll.situational,
            total=roll.total,
            cover=roll.cover,
            cover_object_id=roll.cover_object_id,
            target_number=roll.target_number,
            hit=roll.hit,
            crit=roll.crit,
            skill_id=self.skill.id,
            modifier_bonus=roll.modifier_bonus,
            backstab=roll.backstab,
            ambush=roll.ambush,
        )
        self.hits[unit.id] = roll
        if self.profile.melee and unit is not self.caster:
            self.melee_victims.append((unit, self.caster.xy))
        if roll.hit and self.skill.shape.type == "single":
            guardian = try_intercept(
                ctx, self.caster, unit, rolled_event.seq, skill_id=self.skill.id
            )
            if guardian is not None:
                self._redirect(unit, guardian)
                unit = guardian
        if roll.hit and self.skill.category == "spell" and unit.team is not self.caster.team:
            spell_hit_reactions(ctx, self.caster, unit)  # 被法術命中、傷害之前（3D-3）
        if roll.hit and (force_block or self._affected_by_damage(unit)):
            self.blocks[unit.id] = block_multiplier(
                ctx, self.caster, unit, melee=self.profile.height_limited
            )
        return roll

    def _modifier(
        self,
        query: Callable[[BattleState, UnitState, modifiers.Use, Subject], int],
        unit: UnitState | None,
        xy: XY | None = None,
    ) -> int:
        """修正規則對 ``unit``（或格子 ``xy`` 上的物件）的命中加值或傷害‰；不受修正的施放為
        中性值（命中 0、傷害 1000）。"""
        neutral = PERMILLE if query is modifiers.damage_permille else 0
        if not self.modified:
            return neutral
        where = unit.xy if unit is not None else xy
        assert where is not None
        return query(self.ctx.state, self.caster, self.use, Subject(unit, where))

    def _redirect(self, original: UnitState, guardian: UnitState) -> None:
        """替隊友擋攻擊：這次單體攻擊的所有效果改為作用在守護者身上（沿用原本的命中結果，不重擲；
        位移方向由施放者到守護者重新計算）。"""
        roll = self.hits.pop(original.id)
        self.hits[guardian.id] = roll
        self.enemies = [guardian if u.id == original.id else u for u in self.enemies]
        area = self.area
        self.area = SkillArea(
            tiles=(guardian.xy,), units=(guardian.id,), origin=area.origin, direction=area.direction
        )

    # ------------------------------------------------------------------
    # 選出效果的對象
    # ------------------------------------------------------------------

    def _hit(self, unit: UnitState) -> bool:
        roll = self.hits.get(unit.id)
        return roll is not None and roll.hit

    def targets(self, affects: str, condition: ConditionSpec | None = None) -> list[UnitState]:
        """``affects`` 對應的存活單位（敵方與 ``all`` 的友方需命中），再套用效果層級的條件。"""
        if affects == "enemies":
            chosen = [u for u in self.enemies if self._hit(u)]
        elif affects == "allies":
            chosen = list(self.allies)
        elif affects == "all":
            chosen = [u for u in self.enemies if self._hit(u)]
            chosen += [u for u in self.allies if self._hit(u)]
        elif affects == "self":
            chosen = [self.caster]
        else:
            chosen = []
        alive = (u for u in chosen if u.alive and self.holds(condition, Subject(u, u.xy)))
        return sorted(alive, key=lambda u: u.id)

    def holds(self, condition: ConditionSpec | None, subject: Subject) -> bool:
        """效果層級的條件對 ``subject`` 是否成立（判斷「結算到這個效果當下」的狀態）。"""
        return condition_met(self.ctx.state, self.caster, condition, subject)

    def tile_holds(self, condition: ConditionSpec | None, xy: XY) -> bool:
        """條件對格子 ``xy``（連同站在上面的單位）是否成立。"""
        return self.holds(condition, Subject(self.ctx.state.unit_at(*xy), xy))

    def tiles(self, affects: str, condition: ConditionSpec | None = None) -> list[XY]:
        """地形類效果的作用格：``tiles`` 為全部影響格；其他為對象單位目前所在的格子。
        效果層級的條件對每個格子分別判斷。"""
        if affects == "tiles":
            return [xy for xy in self.area.tiles if self.tile_holds(condition, xy)]
        cells = {u.xy for u in self.targets(affects, condition)}
        return sorted(cells, key=lambda p: (p[1], p[0]))

    # ------------------------------------------------------------------
    # 展開
    # ------------------------------------------------------------------

    def run(self) -> None:
        if not self.dash():  # 衝鋒一律最先結算；被擋下時其餘效果不結算
            return
        if not self.shadowstep():  # 瞬步一律最先結算（Phase 3D-8d）
            return
        if not self.react_to_targeting():
            return
        self.roll_hits()
        self.announce_pierce()
        self.consume_stacks()
        self.roll_gamble()
        for effect in self.effects:
            spec = self.skill.effects[effect.spec_index]
            start = len(self.ctx.events)
            batch = self.build(effect, spec)
            if batch:
                execute(self.ctx, batch)
            if effect.type == "damage":
                if effect.affects in _TOUCHING_AFFECTS:
                    self.touch_untouched_tiles(spec, start)
                if spec.lifesteal_permille is not None:
                    self.lifesteal(spec.lifesteal_permille, start)
                if spec.on_kill:
                    self.on_kill(spec.on_kill, start)
        self.backlash_on_miss()
        self.react_to_hits()
        self.shorten_cooldown()

    # -- 賭博型（Phase 3D-7a）-----------------------------------------------

    def roll_gamble(self) -> None:
        """``gamble``：命中判定之後、第一個效果之前擲一次 d1000（``≤ chance_permille`` 成功）。
        技能有對敵方的效果、卻一個敵人都沒命中時整個賭注不結算（不擲、沒有事件）。成功分支的
        ``damage_multiplier`` 在這裡決定，之後的傷害效果乘上它；其餘分支效果在 ``gamble`` 效果
        自己的位置（技能的最後一個）結算。預覽時沿用 ``ctx.gamble`` 指定的分支（沒有指定就不
        結算），不消耗亂數。"""
        found = (e for e in self.effects if e.type == GAMBLE)
        gamble = next(found, None)
        if gamble is None:
            return
        spec = self.skill.effects[gamble.spec_index]
        assert spec.chance_permille is not None
        ctx = self.ctx
        if any(e.hostile for e in self.effects) and not any(self._hit(u) for u in self.enemies):
            return
        self.cast_start = len(ctx.events)
        if ctx.preview is not None:
            if ctx.gamble is None:
                return
            roll = spec.chance_permille if ctx.gamble == "win" else PERMILLE
        else:
            roll = ctx.rng.randint(1, PERMILLE)
        success = roll <= spec.chance_permille
        ctx.emit(
            GambleRolled,
            unit_id=self.caster.id,
            skill_id=self.skill.id,
            roll=roll,
            chance_permille=spec.chance_permille,
            success=success,
        )
        self.gamble_branch = tuple((spec.win if success else spec.lose) or ())
        for sub in self.gamble_branch:
            if sub.type == DAMAGE_MULTIPLIER:
                assert sub.damage_multiplier_permille is not None
                self.gamble_mult = self.gamble_mult * sub.damage_multiplier_permille // PERMILLE

    def gamble_effect(self, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
        """``gamble`` 在效果列表的位置（最後一個）：結算擲出的分支（擲骰見 roll_gamble）。"""
        self.resolve_branch(self.gamble_branch)
        return []

    def resolve_branch(self, branch: tuple[EffectSpec, ...]) -> None:
        """賭注分支或失手反噬的效果：一般效果展開後結算（對象 ``self`` 的傷害是反噬，不致命）；
        ``damage_multiplier`` 已在擲骰時處理；``self_damage_of_hit`` 依本次造成的傷害結算。"""
        for sub in branch:
            if sub.type == DAMAGE_MULTIPLIER:
                continue
            if sub.type == SELF_DAMAGE_OF_HIT:
                self.self_damage_of_hit(sub)
                continue
            if sub.type in (REFUND_AP, REFUND_COOLDOWN):
                self.refund(sub)
                continue
            primitive = self.ctx.rules.primitive_def(sub.type)
            affects = sub.affects or default_affects(primitive)
            batch = self.build(ResolvedEffect(-1, sub.type, primitive, affects), sub)
            if batch:
                execute(self.ctx, batch)

    # -- 技能內的擊殺時效果（Phase 3D-8b）-----------------------------------

    def on_kill(self, branch: tuple[EffectSpec, ...], start: int) -> None:
        """``on_kill``：這個傷害效果（``start`` 之後的事件，含連鎖）讓施放者造成傷害的敵人倒下時，
        對施放者結算 ``branch``（對象一律是施放者；一個效果只結算一次，施放者自己倒下則不結算）。"""
        caster, state = self.caster, self.ctx.state
        events = self.ctx.events[start:]
        hurt = {
            e.target_id
            for e in events
            if isinstance(e, DamageDealt) and e.source_id == caster.id and e.cause == "attack"
        }
        killed = any(
            isinstance(e, UnitDowned)
            and e.unit_id in hurt
            and state.units[e.unit_id].team is not caster.team
            for e in events
        )
        if killed and caster.alive:
            self.resolve_branch(tuple(sub.model_copy(update={"affects": "self"}) for sub in branch))

    def refund(self, spec: EffectSpec) -> None:
        """``refund_ap``（返還 AP）與 ``refund_cooldown``（本技能冷卻歸零，見
        :mod:`trpg.engine.refunds`）。"""
        if spec.type == REFUND_AP:
            refund_ap(self.ctx, self.caster, self.skill.id, spec.amount or 1)
        else:
            refund_cooldown(self.ctx, self.caster, self.skill.id)

    def self_damage_of_hit(self, spec: EffectSpec) -> None:
        """``self_damage_of_hit``：施放者受到「本次施放對敵人造成的傷害（扣掉護盾吸收）」的
        n‰（無條件捨去，至少 1）；反噬傷害不會讓施放者 HP 低於 1。"""
        assert spec.self_damage_permille_of_hit is not None
        caster, state = self.caster, self.ctx.state
        dealt = sum(
            e.amount - e.absorbed
            for e in self.ctx.events[self.cast_start :]
            if isinstance(e, DamageDealt)
            and e.source_id == caster.id
            and e.cause == "attack"
            and e.target_id in state.units
            and state.units[e.target_id].team is not caster.team
        )
        if dealt <= 0 or not caster.alive:
            return
        amount = max(1, dealt * spec.self_damage_permille_of_hit // PERMILLE)
        execute(
            self.ctx,
            [
                DamageEffect(
                    target_id=caster.id,
                    source_id=caster.id,
                    cause="backlash",
                    element=Element.PHYSICAL,
                    flat=amount,
                    apply_element_mod=False,
                    apply_weather=False,
                )
            ],
        )

    def backlash_on_miss(self) -> None:
        """失手反噬（``cost.on_miss``）：攻擊沒命中任何敵人（含自然 1）時，對施放者結算反噬效果
        （命中則不結算）。被動、陷阱與複製的技能不付代價，不適用。"""
        branch = self.skill.cost.on_miss
        if not branch or not self.modified or not self.pays_miss_cost or not self.caster.alive:
            return
        if not self.hits or any(roll.hit for roll in self.hits.values()):
            return
        self.ctx.emit(BacklashTriggered, unit_id=self.caster.id, skill_id=self.skill.id)
        self.resolve_branch(tuple(sub.model_copy(update={"affects": "self"}) for sub in branch))

    def dash(self) -> bool:
        """``dash``（Phase 3D-2）：施放者沿最短路徑衝到目標的相鄰格，一步一步走（每一步先給相鄰
        的敵人藉機攻擊的機會；陷阱與墜落照常結算，被定身、倒地或倒下就停下）。衝完之後影響範圍的
        原點改為施放者的新位置（推擊由這裡往外推）。回傳其餘效果是否繼續結算：施放者倒下，或
        目標已不在相鄰格（被擋下）時為 ``False``（發出 ``effect_fizzled``）。"""
        action, caster, ctx = self.action, self.caster, self.ctx
        spec = self.skill.effects[0] if self.skill.effects else None
        if spec is None or spec.type != DASH or action is None or action.target_id is None:
            return True
        if not self.holds(spec.condition, Subject(caster, caster.xy)):
            return True
        target = ctx.state.units[action.target_id]
        reach = shape_reach(ctx.state, self.skill, caster)
        path = dash_route(ctx.state, caster, target.xy, reach)
        if path is None:
            return self._dash_failed("no_path")
        ctx.emit(
            UnitDashed,
            unit_id=caster.id,
            target_id=target.id,
            path=tuple(Pos(x=x, y=y) for x, y in path),
        )
        if not self._dash_walk(path):
            return False
        if not target.alive or manhattan(caster.xy, target.xy) != 1:
            return self._dash_failed("blocked")
        self.area = replace(self.area, origin=caster.xy)
        return True

    def shadowstep(self) -> bool:
        """``shadowstep``（Phase 3D-8d）：施放者瞬間出現在目標相鄰的格子（``landing: choose`` 用選取
        的落點、``behind`` 用目標的背後格或最近的替代格），不觸發藉機攻擊；落點的陷阱與表面照常
        結算，落地後面向目標，影響範圍的原點改為落點。回傳其餘效果是否繼續結算：沒有落點、目標
        已不在場，或施放者倒下時為 ``False``。"""
        action, caster, ctx = self.action, self.caster, self.ctx
        spec = self.skill.effects[0] if self.skill.effects else None
        if spec is None or spec.type != SHADOWSTEP or action is None or action.target_id is None:
            return True
        if not self.holds(spec.condition, Subject(caster, caster.xy)):
            return True
        target = ctx.state.units[action.target_id]
        dest: XY | None
        if spec.landing == "choose":
            assert action.target_pos is not None
            dest = (action.target_pos.x, action.target_pos.y)
        else:
            dest = shadowstep_behind(ctx.state, caster, target)
        if dest is None or not target.alive:
            ctx.emit(EffectFizzled, effect_kind=SHADOWSTEP, pos=None, reason="shadowstep_blocked")
            return False
        if dest != caster.xy:
            move = MoveUnitEffect(
                source_id=caster.id, unit_id=caster.id, dest=dest, mode="shadowstep"
            )
            execute(ctx, [move])
        if not caster.alive or caster.xy != dest:
            return False
        face_toward(caster, target.xy)
        self.area = replace(self.area, origin=caster.xy)
        return True

    def _dash_walk(self, path: list[XY]) -> bool:
        """沿 ``path`` 一步一步衝（每步先給藉機攻擊的機會）；施放者倒下時回傳 ``False``。"""
        caster, ctx = self.caster, self.ctx
        for step in path[1:]:
            opportunity_attacks(ctx, caster, caster.xy, step)
            if not caster.alive:
                return False
            before = caster.xy
            move = MoveUnitEffect(source_id=caster.id, unit_id=caster.id, dest=step, mode="dash")
            execute(ctx, [move])
            enemy_enters_adjacent_reactions(ctx, caster, before)
            enemy_moves_in_range_reactions(ctx, caster)
            if not self._dash_continues(step):
                break
        if len(path) > 1 and caster.alive:
            collect_move(ctx, caster)  # on_move 被動：衝鋒算主動移動
        return caster.alive

    def _dash_continues(self, step: XY) -> bool:
        """衝鋒走完這一步之後能不能繼續：還在預期的格子上，沒有被定身、擊倒、暈眩。"""
        caster, rules = self.caster, self.ctx.rules
        if not caster.alive or caster.xy != step or caster.has_status(PRONE):
            return False
        return not is_rooted(rules, caster) and skip_turn_status(rules, caster) is None

    def _dash_failed(self, reason: str) -> bool:
        self.ctx.emit(EffectFizzled, effect_kind=DASH, pos=None, reason=f"dash_{reason}")
        return False

    def announce_pierce(self) -> None:
        """穿透的射線穿過了物件：發出 ``shot_pierced``（Phase 3C-5b）。"""
        trace = self.trace
        if not trace.objects:
            return
        self.ctx.emit(
            ShotPierced,
            unit_id=self.caster.id,
            skill_id=self.skill.id,
            objects=trace.objects,
            object_tiles=tuple(Pos(x=x, y=y) for x, y in trace.object_tiles),
            behind=trace.behind,
            behind_permille=self.ctx.core.pierce_behind_permille,
            route=tuple(Pos(x=x, y=y) for x, y in trace.route),
        )

    def behind_permille(self, unit: UnitState) -> int:
        """穿透：位於 ``penetrable`` 物件後方的單位只受這個千分比的傷害。"""
        if unit.id in self.trace.behind:
            return self.ctx.core.pierce_behind_permille
        return PERMILLE

    def shorten_cooldown(self) -> None:
        """修正規則的 ``cooldown_delta``：命中後該技能的剩餘冷卻減少（下限 0）。"""
        if self.cooldown_delta == 0 or not self.caster.alive:
            return
        remaining = self.caster.cooldowns.get(self.skill.id, 0)
        if remaining <= 0:
            return
        after = max(0, remaining + self.cooldown_delta)
        if after:
            self.caster.cooldowns[self.skill.id] = after
        else:
            del self.caster.cooldowns[self.skill.id]
        self.ctx.emit(
            SkillCooldownChanged, unit_id=self.caster.id, skill_id=self.skill.id, remaining=after
        )

    def consume_stacks(self) -> None:
        """``consume_stack``：命中判定之後、第一個效果之前消耗層數，換成同一技能傷害效果的加成。
        ``owner: self`` 的層數從施放者消耗（沒有命中也消耗）；``owner: target`` 的從每個被命中的
        目標各自消耗。沒有層數也可施放（加成 0）。"""
        rules = self.ctx.rules
        for effect in self.effects:
            if effect.type != CONSUME_STACK:
                continue
            spec = self.skill.effects[effect.spec_index]
            assert spec.stack is not None and spec.per_stack_permille is not None
            if rules.stack_def(spec.stack).owner == "self":
                spent = consume_stacks(self.ctx, self.caster, spec.stack, source_id=self.caster.id)
                self.caster_bonus += spent * spec.per_stack_permille
                continue
            for unit in self.targets(effect.affects, spec.condition):
                spent = consume_stacks(self.ctx, unit, spec.stack, source_id=self.caster.id)
                self.target_bonus[unit.id] = (
                    self.target_bonus.get(unit.id, 0) + spent * spec.per_stack_permille
                )

    def add_stack(self, effect: ResolvedEffect, spec: EffectSpec) -> None:
        """``add_stack``：``owner: self`` 的層數加在施放者身上（技能有對敵方的效果時，至少命中一名
        敵人才累積）；``owner: target`` 的加在每個被命中的目標身上。"""
        assert spec.stack is not None
        amount = spec.amount or 1
        if self.ctx.rules.stack_def(spec.stack).owner == "self":
            # 命中的敵人即使被這一擊擊倒也算（命中判定在效果結算之前就決定了）
            connected = not any(e.hostile for e in self.effects) or any(
                self._hit(u) for u in self.enemies
            )
            subject = Subject(self.caster, self.caster.xy)
            if connected and self.caster.alive and self.holds(spec.condition, subject):
                add_stacks(self.ctx, self.caster, spec.stack, amount, source_id=self.caster.id)
            return
        for unit in self.targets(effect.affects, spec.condition):
            add_stacks(self.ctx, unit, spec.stack, amount, source_id=self.caster.id)

    def react_to_hits(self) -> None:
        """全部效果結算之後：每個被命中的單位（依單位 ID）各自可以用 ``hit_by_*`` 反應技反應。"""
        melee = self.profile.height_limited
        for uid in sorted(self.hits):
            roll = self.hits[uid]
            unit = self.ctx.state.units[UnitId(uid)]
            if roll.hit and unit.team is not self.caster.team:
                hit_reactions(self.ctx, self.caster, unit, melee=melee)

    def build(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:  # noqa: PLR0911
        kind = effect.type
        simple = self._SIMPLE.get(kind)
        if simple is not None:
            return simple(self, effect, spec)
        if kind in ("push", "pull"):
            return self.displace(effect, spec, pull=kind == "pull")
        if kind == "teleport":
            return self.teleport(spec)
        if kind == CHARGE_THROUGH:
            self.charge(spec)  # 自己一步一步結算（移動、命中、傷害、擊倒或推開交錯）
            return []
        if kind == LEAP:
            return self.leap(spec)
        if kind == SWAP:
            return self.swap(effect, spec)
        if kind == TELEPORT_TARGET:
            return self.teleport_target()
        if kind == SWAP_ANY:
            return self.swap_any()
        if kind in (INTERCEPT, PLACE_TRAP, CONSUME_STACK, DASH, SHADOWSTEP):
            # 攔截：反應機制；陷阱：use_skill；消耗層數：consume_stacks；衝鋒、瞬步：先結算
            return []
        if kind == ADD_STACK:
            self.add_stack(effect, spec)
            return []
        if kind == TOPPLE:
            return self.topple(spec)
        if kind in REWRITE_PRIMITIVES:
            return self.rewrite(effect, spec)
        return self.tile_effect(effect, spec)

    def cleanse(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        return [
            CleanseEffect(target_id=unit.id, source_id=self.caster.id)
            for unit in self.targets(effect.affects, spec.condition)
        ]

    # -- 資源互動（Phase 3D-1）------------------------------------------

    def restore_resource(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``restore_resource``：對每個對象直接結算（:mod:`trpg.engine.resources`）。"""
        for unit in self.targets(effect.affects, spec.condition):
            if spec.resource == "mana":
                restore_mana(self.ctx, self.caster, unit, spec.amount or 1)
            else:
                restore_cooldowns(self.ctx, self.caster, unit, self.skill, spec)
        return []

    def dispel(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``dispel``（Phase 3D-8a）：每個對象失去 ``count`` 個增益（剩餘回合最長者先，永久最長；
        ``all`` 為全部；原因 ``dispelled``）。沒有任何對象有增益時發出 ``effect_fizzled``。"""
        batch: list[EffectBase] = [
            RemoveStatusEffect(
                source_id=self.caster.id,
                target_id=unit.id,
                status_id=buff.status_id,
                reason="dispelled",
            )
            for unit in self.targets(effect.affects, spec.condition)
            for buff in dispelled_buffs(self.ctx, unit, spec.count or 1)
        ]
        if not batch:
            self.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_buff")
        return batch

    def reveal(self, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``reveal``（Phase 3D-8a）：範圍內的敵人不擲命中就失去 ``concealed`` 狀態（原因
        ``revealed``）並獲得 ``revealed`` 狀態 ``duration`` 回合（期間不算隱蔽、不能再隱蔽）；
        範圍內的敵方陷阱對施放者的陣營顯示。範圍內沒有敵人也沒有敵方陷阱時發出
        ``effect_fizzled``。"""
        batch: list[EffectBase] = []
        for unit in sorted((u for u in self.enemies if u.alive), key=lambda u: u.id):
            if unit.has_status(CONCEALED):
                batch.append(
                    RemoveStatusEffect(
                        source_id=self.caster.id,
                        target_id=unit.id,
                        status_id=CONCEALED,
                        reason="revealed",
                    )
                )
            batch.append(
                ApplyStatusEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    status_id=REVEALED,
                    duration=spec.duration,
                )
            )
        before = len(self.ctx.events)
        reveal_traps(self.ctx, self.caster, self.area.tiles)
        if not batch and len(self.ctx.events) == before:
            self.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="nothing_hidden")
        return batch

    def revive(self, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``revive``（Phase 3D-8b）：選定的倒下友方站起來（:mod:`trpg.engine.skills.revive`）。"""
        assert self.action is not None and self.action.target_id is not None
        assert spec.hp_permille is not None
        target = self.ctx.state.units[self.action.target_id]
        revive_unit(self.ctx, self.caster, target, self.skill.id, spec.hp_permille)
        return []

    def grant_skill(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``grant_skill``（Phase 3D-8c）：每個對象暫時獲得 ``spec.skill``（``engine.grants``）。"""
        assert spec.skill is not None and spec.duration is not None
        for unit in self.targets(effect.affects, spec.condition):
            grant_skill(self.ctx, self.caster, unit, spec.skill, spec.duration)
        return []

    def delayed_damage(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``delayed_damage``（Phase 3D-8b）：命中的敵人身上附加定時炸彈（狀態 ``time_bomb``，剩餘
        回合 ＝ 倒數；已經有炸彈的目標不再附加）。爆炸見 :mod:`trpg.engine.bombs`。"""
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            if unit.has_status(TIME_BOMB):
                self.ctx.emit(
                    EffectFizzled, effect_kind=spec.type, pos=unit.pos, reason="already_bombed"
                )
                continue
            batch.append(
                ApplyStatusEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    status_id=TIME_BOMB,
                    duration=spec.rounds,
                    skill_id=self.skill.id,
                )
            )
        return batch

    def steal_buff(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``steal_buff``：每個有增益的對象先失去一個增益（原因 ``stolen``），再把同一個狀態以相同
        的剩餘回合與數值施加到施放者身上。沒有任何對象有增益時發出 ``effect_fizzled``。"""
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            buff = pick_stolen_buff(self.ctx, unit)
            if buff is None:
                continue
            batch.append(
                RemoveStatusEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    status_id=buff.status_id,
                    reason="stolen",
                )
            )
            batch.append(
                ApplyStatusEffect(
                    source_id=self.caster.id,
                    target_id=self.caster.id,
                    status_id=buff.status_id,
                    duration=buff.remaining,
                    amount=buff.amount,
                )
            )
        if not batch:
            self.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_buff")
        return batch

    # -- 改寫規則型（Phase 3C-4a）------------------------------------------

    def rewrite(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """改寫規則型原語：``grant_ap``、``reset_cooldown``、``extra_reaction`` 直接結算
        （:mod:`trpg.engine.rewrites`）；``copy_skill`` 複製施放；``cheat_death`` 與
        ``redirect_damage`` 對每個對象施加狀態（不擲抵抗）。"""
        kind = effect.type
        if kind == COPY_SKILL:
            self.copy_skill()
            return []
        targets = self.targets(effect.affects, spec.condition)
        if kind == GRANT_AP:
            for unit in targets:
                grant_ap(self.ctx, self.caster, unit, spec.amount or 1)
            return []
        if kind == RESET_COOLDOWN:
            done = [reset_cooldowns(self.ctx, self.caster, u, self.skill, spec) for u in targets]
            if not any(done):
                self.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_cooldown")
            return []
        if kind == EXTRA_REACTION:
            for unit in targets:
                grant_reactions(self.ctx, self.caster, unit, spec.amount or 1)
            return []
        return self.rewrite_status(kind, spec, targets)

    def rewrite_status(
        self, kind: str, spec: EffectSpec, targets: list[UnitState]
    ) -> list[EffectBase]:
        """``cheat_death``（不死）與 ``redirect_damage``（靈魂連結；對象不含施放者自己）。"""
        if kind == CHEAT_DEATH:
            return [
                ApplyStatusEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    status_id=CHEAT_DEATH_STATUS,
                    duration=spec.duration,
                )
                for unit in targets
            ]
        linked = [u for u in targets if u.id != self.caster.id]
        if not linked:
            self.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="self_link")
        return [
            ApplyStatusEffect(
                source_id=self.caster.id,
                target_id=unit.id,
                status_id=REDIRECT_STATUS,
                duration=spec.duration,
                amount=spec.permille,
            )
            for unit in linked
        ]

    def copy_skill(self) -> None:
        """``copy_skill``：以施放者的身分立即施放本輪最後施放的技能（不扣法力與 AP、不進冷卻、
        不花源力；``casts`` 在這次施放結束之後才更新，所以這裡看到的仍是被複製的那一次）。
        預覽沒有選取時不結算。"""
        pick = None if self.action is None else self.action.copy_cast
        if pick is None:
            return
        state = self.ctx.state
        found = copy_source(state, self.caster)
        assert not isinstance(found, str)  # use_skill 開頭已檢查
        copied, origin = found
        area = checked_area(state, self.caster, copied, pick)
        self.ctx.emit(
            SkillCopied,
            unit_id=self.caster.id,
            source_id=origin.id,
            skill_id=copied.id,
            name_zh=copied.name_zh,
            tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
        )
        cast = _Cast(self.ctx, self.caster, copied, pick, area)
        cast.pays_miss_cost = False  # 複製的技能不付代價（失手反噬也是代價）
        cast.run()
        collect_cast(self.ctx, self.caster, copied)

    # -- 消耗狀態（Phase 3C-3b）------------------------------------------

    def consume_status(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``consume_status``：每個有該狀態的對象先移除狀態（立刻結算），再對它（與 ``splash``
        範圍內的敵方單位）結算 ``then``。沒有任何對象有該狀態時發出 ``effect_fizzled``。"""
        assert spec.status is not None and spec.then
        ctx = self.ctx
        batch: list[EffectBase] = []
        consumed = False
        for unit in self.targets(effect.affects, spec.condition):
            instance = unit.get_status(spec.status)
            if instance is None:
                continue
            consumed = True
            scale = self._consume_scale(unit, spec, instance.remaining)
            execute(
                ctx,
                [
                    RemoveStatusEffect(
                        source_id=self.caster.id,
                        target_id=unit.id,
                        status_id=spec.status,
                        reason="consumed",
                    )
                ],
            )
            batch += self._consume_then(unit, spec, scale)
        if not consumed:
            ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_status")
        return batch

    def _consume_scale(self, unit: UnitState, spec: EffectSpec, remaining: int | None) -> int:
        """``then`` 的骰數倍率：``remaining_rounds``（永久狀態為 1）或同時消耗的目標型層數；
        至少 1、至多 ``consume_status_max_scale``。"""
        cap = self.ctx.core.consume_status_max_scale
        if spec.scale == "remaining_rounds":
            return max(1, min(cap, remaining or 1))
        if spec.scale == "stacks":
            assert spec.stack is not None
            spent = consume_stacks(self.ctx, unit, spec.stack, source_id=self.caster.id)
            return max(1, min(cap, spent))
        return 1

    def _consume_then(self, unit: UnitState, spec: EffectSpec, scale: int) -> list[EffectBase]:
        recipients = [unit]
        if spec.splash is not None:
            near = [
                u
                for u in self.ctx.state.units_sorted()
                if u.alive
                and u.id != unit.id
                and u.team is not self.caster.team
                and manhattan(u.xy, unit.xy) <= spec.splash
            ]
            recipients += near
        batch: list[EffectBase] = []
        for sub in spec.then or ():
            scaled = sub
            if sub.dice is not None and scale > 1:
                dice = sub.dice
                scaled = sub.model_copy(
                    update={"dice": Dice(count=dice.count * scale, sides=dice.sides)}
                )
            for target in recipients:
                batch += self._then_effect(scaled, target)
        return batch

    def _then_effect(self, spec: EffectSpec, target: UnitState) -> list[EffectBase]:
        """``then`` 的一個效果對 ``target`` 的結算（自動命中、不暴擊、沒有格擋）。"""
        caster = self.caster
        if spec.type == "damage":
            dice, flat, scaled, multiplier, element = damage_parameters(
                self.ctx.state, caster, self.skill, spec, modified=self.modified
            )
            bonus = self._modifier(modifiers.damage_permille, target)
            return [
                DamageEffect(
                    target_id=target.id,
                    source_id=caster.id,
                    cause="attack",
                    element=element,
                    dice=dice,
                    flat=flat,
                    scaled_permille=scaled,
                    min_damage=self.ctx.core.min_damage_on_hit,
                    multiplier_permille=multiplier * bonus // PERMILLE,
                )
            ]
        if spec.type == "heal":
            return [
                HealEffect(
                    target_id=target.id,
                    source_id=caster.id,
                    dice=spec.dice,
                    scaled_permille=self._spell_scaled(),
                )
            ]
        if spec.type == "shield":
            return [
                ShieldEffect(
                    target_id=target.id,
                    source_id=caster.id,
                    dice=spec.dice,
                    scaled_permille=self._spell_scaled(),
                )
            ]
        return self._status_effects(spec, target)

    # -- 數值 ----------------------------------------------------------

    def damage(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        params = damage_parameters(
            self.ctx.state, self.caster, self.skill, spec, modified=self.modified
        )
        dice, flat, scaled, multiplier, element = params
        min_damage = self.ctx.core.min_damage_on_hit
        gamble = self.gamble_mult if effect.spec_index >= 0 else PERMILLE  # 分支自己的傷害不再乘
        overload = overload_bonus(self.ctx.state, self.caster, self.skill)  # 超載層數（3D-7b）
        explode_max = self.ctx.core.explode_max if spec.explode else 0
        batch: list[EffectBase] = []
        units = self.targets(effect.affects, spec.condition)
        healed = self.split_healed(spec)  # 聖光雙效：友方改為治療，與敵方的傷害共用同一次擲骰
        preset = self.split_rolls(spec, bool(units or healed))
        for unit in units:
            roll = self.hits.get(unit.id)
            block = self.blocks.get(unit.id, PERMILLE)
            bonus = PERMILLE + self.caster_bonus + self.target_bonus.get(unit.id, 0)
            bonus += overload + scale_bonus(self.ctx.state, self.caster, unit, spec.scaling)
            bonus = bonus * self._modifier(modifiers.damage_permille, unit) // PERMILLE
            bonus = bonus * gamble // PERMILLE
            batch.append(
                DamageEffect(
                    target_id=unit.id,
                    source_id=self.caster.id,
                    cause="backlash" if effect.affects == "self" else "attack",
                    element=element,
                    dice=dice,
                    flat=flat,
                    scaled_permille=scaled,
                    crit=roll is not None and roll.crit,
                    min_damage=min_damage,
                    explode_max=explode_max,
                    preset_rolls=preset,
                    multiplier_permille=multiplier
                    * block
                    * bonus
                    * self.behind_permille(unit)
                    // (PERMILLE * PERMILLE * PERMILLE),
                )
            )
        batch += [
            HealEffect(
                target_id=unit.id,
                source_id=self.caster.id,
                dice=spec.dice,
                scaled_permille=self._spell_scaled(),
                preset_rolls=preset,
            )
            for unit in healed
        ]
        if effect.affects in _TOUCHING_AFFECTS:
            for xy in (*self.area.tiles, *self.pierced_tiles()):
                obj = self.ctx.state.object_at(*xy)
                if obj is None or obj.hp is None or not self.tile_holds(spec.condition, xy):
                    continue
                if "breakable" not in self.ctx.rules.object_def(obj.kind).tags:
                    continue
                batch.append(
                    DamageObjectEffect(
                        object_id=obj.id,
                        source_id=self.caster.id,
                        cause="attack",
                        element=element,
                        dice=dice,
                        flat=flat,
                        scaled_permille=scaled,
                        min_damage=min_damage,
                        multiplier_permille=multiplier
                        * (PERMILLE + self.caster_bonus)
                        // PERMILLE
                        * self._modifier(modifiers.damage_permille, None, xy)
                        // PERMILLE
                        * gamble
                        // PERMILLE,
                    )
                )
        return batch

    def split_healed(self, spec: EffectSpec) -> list[UnitState]:
        """聖光雙效（``split_heal``，Phase 3D-8a）受治療的友方（含自己，依單位 ID 排序）；不是聖光
        雙效為空。"""
        if not spec.split_heal:
            return []
        alive = (u for u in self.allies if u.alive and self.holds(spec.condition, Subject(u, u.xy)))
        return sorted(alive, key=lambda u: u.id)

    def split_rolls(self, spec: EffectSpec, anyone: bool) -> tuple[int, ...] | None:
        """聖光雙效的骰值：傷害與治療共用的一次擲骰（沒有對象時不擲）；不是聖光雙效為 ``None``。"""
        if not spec.split_heal or spec.dice is None or not anyone:
            return None
        return tuple(self.ctx.rng.roll(spec.dice.sides) for _ in range(spec.dice.count))

    def lifesteal(self, permille: int, start: int) -> None:
        """吸血（Phase 3D-8a）：施放者回復這個傷害效果對敵人實際造成的傷害（扣掉護盾吸收，含溢出）
        × ``permille``‰（無條件捨去）；已滿血或施放者倒下時沒有效果。"""
        caster, state = self.caster, self.ctx.state
        dealt = sum(
            e.amount - e.absorbed
            for e in self.ctx.events[start:]
            if isinstance(e, DamageDealt)
            and e.source_id == caster.id
            and e.cause == "attack"
            and e.target_id in state.units
            and state.units[e.target_id].team is not caster.team
        )
        amount = dealt * permille // PERMILLE
        if amount <= 0 or not caster.alive or caster.hp >= caster.max_hp:
            return
        execute(
            self.ctx,
            [HealEffect(target_id=caster.id, source_id=caster.id, flat=amount, cause="lifesteal")],
        )

    def pierced_tiles(self) -> list[XY]:
        """穿透的單體射線穿過、但不在影響範圍內的 ``penetrable`` 物件所在格（物件受全額傷害）。"""
        return [xy for xy in self.trace.object_tiles if xy not in self.area.tiles]

    def touch_untouched_tiles(self, spec: EffectSpec, start: int) -> None:
        """帶元素的傷害：沒有單位或物件受到傷害的影響格，補上一次元素觸及（每格一次）。"""
        element = damage_parameters(
            self.ctx.state, self.caster, self.skill, spec, modified=self.modified
        ).element
        if element is Element.PHYSICAL:
            return
        touched: set[XY] = set()
        for event in self.ctx.events[start:]:
            if isinstance(event, DamageDealt) and event.source_id == self.caster.id:
                if event.cause == "attack" and event.pos is not None:
                    touched.add((event.pos.x, event.pos.y))
            elif isinstance(event, ObjectDamaged) and event.source_id == self.caster.id:
                touched.add((event.pos.x, event.pos.y))
        remaining = [
            ElementTouchEffect(source_id=self.caster.id, pos=xy, element=element, tile_only=True)
            for xy in self.area.tiles
            if xy not in touched and self.tile_holds(spec.condition, xy)
        ]
        if remaining:
            execute(self.ctx, remaining)

    def _spell_scaled(self) -> int:
        """治療與護盾的屬性加成（‰）：有效縮放屬性 × ``spell_attr_multiplier_permille``。"""
        attr = skill_scaling_value(self.ctx.rules, self.caster, self.skill)
        return attr * self.ctx.core.spell_attr_multiplier_permille

    def heal(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        scaled = self._spell_scaled()
        return [
            HealEffect(
                target_id=unit.id,
                source_id=self.caster.id,
                dice=spec.dice,
                scaled_permille=scaled,
            )
            for unit in self.targets(effect.affects, spec.condition)
        ]

    def shield(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        scaled = self._spell_scaled()
        return [
            ShieldEffect(
                target_id=unit.id,
                source_id=self.caster.id,
                dice=spec.dice,
                scaled_permille=scaled,
            )
            for unit in self.targets(effect.affects, spec.condition)
        ]

    # -- 位移 ----------------------------------------------------------

    def _displace_direction(self, unit: UnitState, *, pull: bool) -> XY | None:
        area = self.area
        if area.direction is not None:
            dx, dy = area.direction
            return (-dx, -dy) if pull else (dx, dy)
        direction = axis_direction(unit.pos.x - area.origin[0], unit.pos.y - area.origin[1])
        if direction is None:
            return None
        return (-direction[0], -direction[1]) if pull else direction

    def displace(self, effect: ResolvedEffect, spec: EffectSpec, *, pull: bool) -> list[EffectBase]:
        assert spec.distance is not None
        batch: list[EffectBase] = [] if pull else self.topple_in_area(spec)
        for unit in self.targets(effect.affects, spec.condition):
            direction = self._displace_direction(unit, pull=pull)
            if direction is None:
                continue
            distance, extra = spec.distance, 0
            if self.modified:
                state, subject = self.ctx.state, Subject(unit, unit.xy)
                distance, extra = modifiers.displace_split(
                    state, self.caster, self.use, subject, distance
                )
            batch.append(
                PushEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    direction=direction,
                    distance=distance,
                    collision_dice=spec.collision_dice,
                    extra_collisions=extra,
                )
            )
        return batch

    # -- 場景物件（Phase 3C-5a）--------------------------------------------

    def _away_from_caster(self, xy: XY) -> XY | None:
        """``xy`` 遠離施放者的方向：方向型形狀為形狀的方向，其他為「施放者 → 該格」的主要軸向。"""
        if self.area.direction is not None:
            return self.area.direction
        return axis_direction(xy[0] - self.caster.pos.x, xy[1] - self.caster.pos.y)

    def _topple_effects(self, xy: XY, condition: ConditionSpec | None) -> list[EffectBase]:
        """``xy`` 上的 ``topplable`` 物件往遠離施放者的方向推倒（以一格推擊結算，見
        :mod:`trpg.engine.effects.world`）。"""
        obj = self.ctx.state.object_at(*xy)
        if obj is None or TOPPLABLE not in self.ctx.rules.object_def(obj.kind).tags:
            return []
        direction = self._away_from_caster(xy)
        if direction is None or not self.tile_holds(condition, xy):
            return []
        return [
            PushEffect(source_id=self.caster.id, object_id=obj.id, direction=direction, distance=1)
        ]

    def topple_in_area(self, spec: EffectSpec) -> list[EffectBase]:
        """技能的推擊（不含拉扯）也會推倒影響範圍內的 ``topplable`` 物件（通用規則）。"""
        batch: list[EffectBase] = []
        for xy in self.area.tiles:
            batch += self._topple_effects(xy, spec.condition)
        return batch

    def topple(self, spec: EffectSpec) -> list[EffectBase]:
        """``topple``：推倒目標物件（形狀 ``single``，選取時已確認是 ``topplable``）。"""
        return self.topple_in_area(spec)

    def hurl_object(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``hurl_object``：落點被命中的單位先受 ``dice`` 物理傷害（暴擊、格擋與修正規則照常；
        ``knock_prone`` 時再以對抗判定擊倒），然後物件落地（:class:`HurlObjectEffect`）。"""
        action = self.action
        assert action is not None and action.target_object_id is not None
        assert action.target_pos is not None and spec.dice is not None
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            roll = self.hits.get(unit.id)
            block = self.blocks.get(unit.id, PERMILLE)
            bonus = self._modifier(modifiers.damage_permille, unit)
            batch.append(
                DamageEffect(
                    target_id=unit.id,
                    source_id=self.caster.id,
                    cause="attack",
                    element=Element.PHYSICAL,
                    dice=spec.dice,
                    crit=roll is not None and roll.crit,
                    min_damage=self.ctx.core.min_damage_on_hit,
                    multiplier_permille=block * bonus // PERMILLE,
                )
            )
        if batch:
            execute(self.ctx, batch)
        if spec.knock_prone:
            prone = self.knock_prone(effect, spec)
            if prone:
                execute(self.ctx, prone)
        dest = (action.target_pos.x, action.target_pos.y)
        return [
            HurlObjectEffect(
                source_id=self.caster.id,
                object_id=action.target_object_id,
                dest=dest,
                ignite=modifiers.skill_is_fiery(self.ctx.state, self.caster, self.skill),
            )
        ]

    def knock_prone(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            batch += self._knock_down(unit)
        return batch

    def _knock_down(self, unit: UnitState) -> list[EffectBase]:
        """對 ``unit`` 擲擊倒的對抗判定（技能的縮放屬性 vs 目標同屬性），成功才倒地。"""
        if unit.has_status(PRONE):
            return []
        if not contest(
            self.ctx,
            "knock_prone",
            self.caster,
            unit,
            self.skill.scaling_attr,
            skill_id=self.skill.id,
            primary=False,
            attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
        ):
            return []
        return [ApplyStatusEffect(source_id=self.caster.id, target_id=unit.id, status_id=PRONE)]

    def teleport(self, spec: EffectSpec) -> list[EffectBase]:
        assert self.action is not None
        pos = self.action.target_pos
        assert pos is not None
        if not self.holds(spec.condition, Subject(self.caster, self.caster.xy)):
            return []
        return [
            MoveUnitEffect(
                source_id=self.caster.id,
                unit_id=self.caster.id,
                dest=(pos.x, pos.y),
                mode="teleport",
            )
        ]

    def summon(self, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``summon``（Phase 3D-4a）：在選取的格子召喚 ``unit``，持續 ``duration`` 輪（直接結算，
        見 :mod:`trpg.engine.summons`）。"""
        action = self.action
        if action is None or action.target_pos is None:
            return []
        if not self.holds(spec.condition, Subject(self.caster, self.caster.xy)):
            return []
        assert spec.unit is not None and spec.duration is not None
        xy = (action.target_pos.x, action.target_pos.y)
        summon_unit(self.ctx, self.caster, spec.unit, xy, spec.duration, self.skill.id)
        return []

    def zone(self, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``zone``（Phase 3D-5）：在影響範圍建立持續區域（直接結算，見
        :mod:`trpg.engine.zones`）。"""
        create_zone(self.ctx, self.caster, self.skill, spec, self.area.tiles, self.area.direction)
        return []

    def leap(self, spec: EffectSpec) -> list[EffectBase]:
        """``leap``（Phase 3D-2）：跳到指定的空格（選取時已檢查落點與路徑）；不觸發藉機攻擊。"""
        assert self.action is not None
        pos = self.action.target_pos
        assert pos is not None
        if not self.holds(spec.condition, Subject(self.caster, self.caster.xy)):
            return []
        return [
            MoveUnitEffect(
                source_id=self.caster.id,
                unit_id=self.caster.id,
                dest=(pos.x, pos.y),
                mode="leap",
            )
        ]

    def charge(self, spec: EffectSpec) -> None:
        """``charge_through``（Phase 3D-2c）：沿直線衝向選取的終點。一格一格走：空格移動
        （``mode: dash``，陷阱、表面與墜落照常結算，被定身、倒地或倒下就停下；不給藉機攻擊的機會）；
        有單位的格子穿過去，敵人在被穿過時各擲一次命中（依路徑順序）。隊友不受影響。"""
        action, caster, ctx = self.action, self.caster, self.ctx
        assert action is not None and action.target_pos is not None
        if not self.holds(spec.condition, Subject(caster, caster.xy)):
            return
        dest = (action.target_pos.x, action.target_pos.y)
        route = charge_route(ctx.state, caster, dest, shape_reach(ctx.state, self.skill, caster))
        if not isinstance(route, ChargeRoute):
            ctx.emit(EffectFizzled, effect_kind=CHARGE_THROUGH, pos=None, reason="charge_no_path")
            return
        start = caster.xy
        ctx.emit(
            UnitCharged,
            unit_id=caster.id,
            target=action.target_pos,
            path=tuple(Pos(x=x, y=y) for x, y in (start, *route.cells)),
        )
        moved = self._charge_walk(spec, route, start)
        if moved and caster.alive:
            collect_move(ctx, caster)  # on_move 被動：衝撞算主動移動
        if self.modified:
            self._update_cooldown_delta()

    def _charge_walk(self, spec: EffectSpec, route: ChargeRoute, start: XY) -> bool:
        """衝撞沿路線前進；回傳施放者有沒有移動過。"""
        caster, state = self.caster, self.ctx.state
        first = route.cells[0]
        travel = (first[0] - start[0], first[1] - start[1])
        moved = False
        for cell in route.cells:
            if not caster.alive:
                break
            occupant = state.unit_at(*cell)
            if occupant is not None and occupant.id != caster.id:
                if occupant.team is not caster.team:
                    self._charge_hit(spec, occupant, travel)
                if state.unit_at(*cell) is not None:
                    continue  # 還站在那裡：穿過去；倒下或被推開了就走進這一格
            before = caster.xy
            execute(
                self.ctx,
                [MoveUnitEffect(source_id=caster.id, unit_id=caster.id, dest=cell, mode="dash")],
            )
            enemy_enters_adjacent_reactions(self.ctx, caster, before)
            enemy_moves_in_range_reactions(self.ctx, caster)
            moved = True
            if not self._dash_continues(cell):
                break
        return moved

    def _charge_hit(self, spec: EffectSpec, unit: UnitState, travel: XY) -> None:
        """衝撞穿過敵人 ``unit``：擲命中；命中受 ``dice`` 物理傷害（暴擊、格擋與修正規則照常），
        還活著時依 ``on_hit`` 擊倒或推到路徑旁。"""
        assert spec.dice is not None
        roll = self._roll_one(unit, force_block=True)
        if not roll.hit:
            return
        block = self.blocks.get(unit.id, PERMILLE)
        bonus = self._modifier(modifiers.damage_permille, unit)
        execute(
            self.ctx,
            [
                DamageEffect(
                    target_id=unit.id,
                    source_id=self.caster.id,
                    cause="attack",
                    element=Element.PHYSICAL,
                    dice=spec.dice,
                    crit=roll.crit,
                    min_damage=self.ctx.core.min_damage_on_hit,
                    multiplier_permille=block * bonus // PERMILLE,
                )
            ],
        )
        if not unit.alive:
            return
        if spec.on_hit == "knock_prone":
            follow = self._knock_down(unit)
        else:
            direction = aside_direction(self.ctx.state, unit, travel)
            follow = [
                PushEffect(
                    source_id=self.caster.id, target_id=unit.id, direction=direction, distance=1
                )
            ]
        if follow:
            execute(self.ctx, follow)

    def displace_check(
        self, kind: Literal["teleport", "swap"], target: UnitState, bonus: int
    ) -> bool:
        """位移的抵抗判定（Phase 3D-2b，``swap``、``swap_any``、``teleport_target`` 共用）：敵方
        目標擲對抗判定（技能的縮放屬性 vs 目標同屬性，目標加 ``bonus``，沿用技巧動作的
        :func:`~trpg.engine.maneuvers.contest`），攻方勝出才位移；友方不檢定。預覽：抵抗判定是
        分歧點（``min`` 視為抵抗成功、``max`` 視為失敗）。"""
        if target.team is self.caster.team:
            return True
        return contest(
            self.ctx,
            kind,
            self.caster,
            target,
            self.skill.scaling_attr,
            skill_id=self.skill.id,
            primary=False,
            attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
            resist_bonus=bonus,
        )

    def swap(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """``swap``（Phase 3D-2）：與目標單位交換位置；對敵人要過一般位移檢定（3D-2b 起，
        不再用命中判定），抵抗成功就不交換。"""
        pool = self.enemies if effect.affects == "enemies" else self.allies
        units = sorted((u for u in pool if u.alive and u.id != self.caster.id), key=lambda u: u.id)
        return [
            SwapUnitsEffect(source_id=self.caster.id, unit_id=self.caster.id, other_id=unit.id)
            for unit in units
            if self.holds(spec.condition, Subject(unit, unit.xy))
            and self.displace_check("swap", unit, 0)
        ]

    def teleport_target(self) -> list[EffectBase]:
        """``teleport_target``（Phase 3D-2b）：把選取的單位傳送到落點（選取時已檢查）。友方一定
        成功；敵方抵抗加成 ``teleport_enemy_resist_bonus``，落點是致命地形時再加
        ``teleport_lethal_resist_bonus``；失敗時目標不移動。"""
        action = self.action
        assert action is not None and action.target_id is not None and action.target_pos is not None
        state, core = self.ctx.state, self.ctx.core
        target = state.units[action.target_id]
        dest = (action.target_pos.x, action.target_pos.y)
        bonus = core.teleport_enemy_resist_bonus
        if is_deadly(state, dest):
            bonus += core.teleport_lethal_resist_bonus
        if not target.alive or not self.displace_check("teleport", target, bonus):
            return []
        return [
            MoveUnitEffect(
                source_id=self.caster.id, unit_id=target.id, dest=dest, mode="teleported"
            )
        ]

    def swap_any(self) -> list[EffectBase]:
        """``swap_any``（Phase 3D-2b）：選取的兩個單位互換位置。每個敵方各自過一般位移檢定
        （依單位 ID 全部擲出），任一個抵抗成功則整個互換失敗；全是友方時不檢定。"""
        action = self.action
        assert action is not None and action.target_id is not None
        assert action.second_target_id is not None
        units = self.ctx.state.units
        first, second = units[action.target_id], units[action.second_target_id]
        if not (first.alive and second.alive):
            return []
        foes = sorted((u for u in (first, second) if u.team is not self.caster.team), key=_unit_id)
        passed = [self.displace_check("swap", unit, 0) for unit in foes]
        if not all(passed):
            return []
        return [SwapUnitsEffect(source_id=self.caster.id, unit_id=first.id, other_id=second.id)]

    def status_duration(self, spec: EffectSpec) -> int | None:
        """此技能施加狀態的持續回合：``mastery: duration`` 生效時在（效果指定的或狀態預設的）
        持續上加 1；永久狀態（沒有持續回合）不變。"""
        bonus = mastery_duration_bonus(self.caster, self.skill)
        if bonus == 0:
            return spec.duration
        assert spec.status is not None
        base = spec.duration
        if base is None:
            base = self.ctx.rules.status_def(spec.status).duration
        return None if base is None else base + bonus

    def apply_status(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """施加狀態：對敵方先轉換（Boss）、再擲抵抗判定（:mod:`trpg.engine.control`）；
        對友方與自己不擲。"""
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            batch += self._status_effects(spec, unit)
        return batch

    def _status_effects(self, spec: EffectSpec, unit: UnitState) -> list[EffectBase]:
        assert spec.status is not None
        planned = status_effect(
            self.ctx,
            caster=self.caster,
            target=unit,
            status_id=spec.status,
            duration=self.status_duration(spec),
            attack_attr=self.skill.scaling_attr,
            attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
            skill_id=self.skill.id,
        )
        return [] if planned is None else [planned]

    # -- 地形 ----------------------------------------------------------

    def tile_effect(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        state = self.ctx.state
        source = self.caster.id
        batch: list[EffectBase] = []
        for xy in self.tiles(effect.affects, spec.condition):
            if effect.type == "create_surface":
                assert spec.surface is not None
                batch.append(
                    CreateSurfaceEffect(
                        source_id=source,
                        pos=xy,
                        surface=spec.surface,
                        duration=spec.duration,
                        team=self.caster.team,
                    )
                )
            elif effect.type == "destroy_object":
                obj = state.object_at(*xy)
                if obj is not None and "breakable" in self.ctx.rules.object_def(obj.kind).tags:
                    batch.append(DestroyObjectEffect(source_id=source, object_id=obj.id))
            elif effect.type == "create_obstacle":
                assert spec.object is not None
                batch.append(
                    CreateObstacleEffect(source_id=source, pos=xy, object_kind=spec.object)
                )
            elif effect.type == "raise_terrain":
                batch.append(RaiseTerrainEffect(source_id=source, pos=xy, amount=spec.amount or 1))
            elif effect.type == "lower_terrain":
                batch.append(LowerTerrainEffect(source_id=source, pos=xy, amount=spec.amount or 1))
        return batch


_Builder = Callable[[_Cast, ResolvedEffect, EffectSpec], list[EffectBase]]
_Cast._SIMPLE = {
    "damage": _Cast.damage,
    "heal": _Cast.heal,
    "shield": _Cast.shield,
    "cleanse": _Cast.cleanse,
    "knock_prone": _Cast.knock_prone,
    "apply_status": _Cast.apply_status,
    CONSUME_STATUS: _Cast.consume_status,
    RESTORE_RESOURCE: _Cast.restore_resource,
    STEAL_BUFF: _Cast.steal_buff,
    DISPEL: _Cast.dispel,
    REVEAL: _Cast.reveal,
    REVIVE: _Cast.revive,
    DELAYED_DAMAGE: _Cast.delayed_damage,
    GRANT_SKILL: _Cast.grant_skill,
    HURL_OBJECT: _Cast.hurl_object,
    SUMMON: _Cast.summon,
    ZONE: _Cast.zone,
    GAMBLE: _Cast.gamble_effect,
}
"""只需要 ``(effect, spec)`` 的原語 → 展開方法。"""


class _TriggeredCast(_Cast):
    """被動技能的施放：沒有 ``UseSkill`` 動作，效果自動命中（Phase 2E 決定 F）。被動、陷阱與
    修正規則的命中後效果都不是持有者的動作，不受修正規則影響（Phase 3C-2）。"""

    modified = False

    def __init__(self, ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
        super().__init__(ctx, caster, skill, None, area)

    def roll_hits(self) -> None:
        """不擲命中：沒有 ``attack_rolled``，也沒有格擋。"""

    def _hit(self, unit: UnitState) -> bool:
        return unit.id != self.caster.id
