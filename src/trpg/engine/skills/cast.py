"""一次施放的工作狀態與流程（Phase 3E-2b 自 ``interpreter.py`` 拆出）。

:class:`Cast` 負責命中判定、對象的選取、效果的順序與施放前後的處理（衝鋒與瞬步先結算、消耗層數、
賭注擲骰、吸血、擊殺時效果、失手反噬、命中後反應、冷卻修正）；每個效果原語的展開交給
:mod:`trpg.engine.skills.primitives` 的登錄表（:meth:`Cast.build`）。
:class:`TriggeredCast`（被動、陷阱、區域、修正規則的命中後效果）與 :class:`GearCast`
（裝備詞條）是不擲命中的變體。施放的入口在 :mod:`trpg.engine.skills.interpreter`。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Literal

from trpg.content.battle import Dice
from trpg.content.skills import (
    CONSUME_STACK,
    DAMAGE_MULTIPLIER,
    DASH,
    DETONATE_RUNES,
    GAMBLE,
    GRANT_AP,
    REFUND_AP,
    REFUND_COOLDOWN,
    REVEAL,
    SACRIFICE_SUMMON,
    SELF_DAMAGE_OF_HIT,
    SHADOWSTEP,
    SWAP,
    SWAP_ANY,
    TELEPORT_TARGET,
    ZONE,
    ConditionSpec,
    EffectSpec,
    SkillDef,
    default_affects,
)
from trpg.content.stacks import auto_consumed
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.context import Ctx
from trpg.engine.control import status_effect
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    ElementTouchEffect,
    HealEffect,
    MoveUnitEffect,
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
    UnitDashed,
    UnitDowned,
)
from trpg.engine.ids import PRONE
from trpg.engine.maneuvers import contest
from trpg.engine.pierce import NO_PIERCE, PierceTrace, pierce_trace
from trpg.engine.reactions import (
    ally_targeted_reactions,
    block_multiplier,
    enemy_enters_adjacent_reactions,
    enemy_moves_in_range_reactions,
    hit_reactions,
    opportunity_attacks,
    spell_hit_reactions,
    take_decoy,
    try_intercept,
)
from trpg.engine.refunds import refund_ap, refund_cooldown
from trpg.engine.rewrites import (
    gear_grant_ap,
)
from trpg.engine.rules.combat import PERMILLE, AttackProfile, AttackRoll, ForcedOutcome, roll_attack
from trpg.engine.rules.facing import face_toward
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.statuses import is_rooted, skip_turn_status
from trpg.engine.rules.weapons import range_damage_permille
from trpg.engine.skill_levels import level_multiplier
from trpg.engine.skill_triggers import collect_move
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.skills.mobility import dash_route, shadowstep_behind
from trpg.engine.skills.primitives import primitive_handler
from trpg.engine.skills.primitives.base import TOUCHING_AFFECTS
from trpg.engine.skills.primitives.summoning import sacrifice_blast
from trpg.engine.skills.scaling import (
    mastery_duration_bonus,
    skill_scale_attr,
    skill_scaling_attr,
    skill_scaling_value,
)
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    SkillArea,
    damage_parameters,
    fires_gun,
    form_bonus_permille,
    resolve_effects,
    shape_reach,
    skill_profile,
)
from trpg.engine.skills.variance import overload_bonus, scale_bonus
from trpg.engine.stacks import consume_stacks
from trpg.engine.state import BattleState, UnitState
from trpg.engine.wind import spread_wind
from trpg.shared.types import Element, Pos, UnitId

_OWN_CHECK = (SWAP, SWAP_ANY, TELEPORT_TARGET, ZONE, REVEAL, DETONATE_RUNES)
"""位移類原語自己擲抵抗判定（Phase 3D-2b），不另外擲命中；揭露（Phase 3D-8a）自動命中範圍內的
敵人；引爆符文（Phase 3-23）也自動命中。"""


_NO_ALLY_ROLL = "shockwave"
"""震波（Phase 3-54d，06 6.33 #64）：對敵方先擲命中，對友方（``affects: all`` 也一樣）不擲命中。"""


def _decoy_miss() -> AttackRoll:
    """狐火誘餌（3R-2b）攔下的單體攻擊：沒有擲命中，結果就是落空。"""
    return AttackRoll(
        rolls=(),
        advantage="none",
        natural=0,
        attack_value=0,
        defense_value_permille=0,
        hit_modifier=0,
        proficiency=0,
        situational=0,
        cover=0,
        cover_object_id=None,
        total=0,
        target_number=0,
        hit=False,
        crit=False,
    )


class Cast:
    """一次施放的工作狀態（命中結果、格擋倍率與影響範圍）。

    ``modified``：這次施放受施放者的修正規則影響（主動、姿態、反應技；Phase 3C-2）。

    原語 handler（:mod:`trpg.engine.skills.primitives`）以這個物件為第一個參數，可以用的公開
    方法：對象（``targets``、``tiles``、``holds``、``tile_holds``、``is_hit``）、命中
    （``roll_one``、``update_cooldown_delta``）、數值（``attack_damage``、``physical_element``、
    ``gamble_for``、``spell_scaled``、``level_permille``、``heal_multiplier``、``modifier``）、
    狀態與擊倒（``status_effects``、``status_duration``、``knock_down``）、衝鋒的每一步
    （``dash_continues``）、另起施放（``spawn``）與分支（``resolve_branch``）。
    """

    modified = True

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
        self.gun = self.modified and fires_gun(caster, skill)
        """火器開火的武器技（Phase 3-24c）：傷害套用武器的距離修正（遠距加成、貼臉與距離衰減）。"""
        self.trace: PierceTrace = NO_PIERCE
        """穿透的射線（Phase 3C-5b；沒有穿透或被動、陷阱的施放為 ``NO_PIERCE``）。"""
        if self.modified and self.profile.pierce:
            self.trace = pierce_trace(ctx.state, caster, skill.shape.type, area)
        units = [ctx.state.units[uid] for uid in area.units]
        self.enemies = [u for u in units if u.team is not caster.team]
        self.allies = [u for u in units if u.team is caster.team]
        self.aim_bonus = ctx.core.aim_hit_bonus if self.modified and caster.aimed else 0
        """瞄準（Phase 3-21a）：這次施放每一次命中判定的加值；第一次擲命中時用掉施放者的瞄準。"""
        self.hits: dict[str, AttackRoll] = {}
        self.blocks: dict[str, int] = {}
        self.caster_bonus = 0
        """消耗施放者層數得到的傷害加成（‰，所有目標共用；``consume_stack`` 的結果）。"""
        self.target_bonus: dict[str, int] = {}
        """消耗目標層數得到的傷害加成（‰），單位 ID → 加成。"""
        self.heal_bonus = 0
        """消耗施放者層數得到的治療加成（‰；層數的 ``consumer.boosts`` 含 ``heal``；3-52）。"""
        self.heal_self_only = False
        """治療加成只算治療施放者自己的效果（層數的 ``consumer.heal_self_only``；3-52b）。"""
        self.shield_bonus = 0
        """消耗施放者層數得到的護盾加成（‰；``boosts`` 含 ``shield``，Phase 3-52）。"""
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
        if any(
            e.affects == "all" and not self._splits(e) and e.type != _NO_ALLY_ROLL for e in rolling
        ):
            rolled += [u for u in self.allies if u is not self.caster]  # 敵我不分也不打到自己
        for unit in sorted(rolled, key=lambda u: u.id):
            self.roll_one(unit)
        # 形態的進入獎勵（3J-1a、3J-1b）：這次施放所有目標的命中擲骰都吃到，擲完才用掉
        self.caster.next_attack_hit = self.caster.next_attack_crit = 0
        if self.modified:
            self.update_cooldown_delta()

    def _splits(self, effect: ResolvedEffect) -> bool:
        """這個效果是聖光雙效（``split_heal``，Phase 3D-8a）：友方改為治療、不擲命中。"""
        return effect.spec_index >= 0 and bool(self.skill.effects[effect.spec_index].split_heal)

    def update_cooldown_delta(self) -> None:
        """修正規則的命中後冷卻修正：以目前已命中的敵人計算（命中判定之後呼叫）。"""
        hit = [Subject(u, u.xy) for u in self.enemies if self.is_hit(u)]
        self.cooldown_delta = modifiers.cooldown_delta(self.ctx.state, self.caster, self.use, hit)

    def roll_one(self, unit: UnitState, *, force_block: bool = False) -> AttackRoll:
        """對 ``unit`` 擲一次命中（發出 ``attack_rolled``、記錄結果；單體命中時給守護者攔截的機會，
        命中且受傷害效果影響——或 ``force_block``（直線衝撞自己結算傷害）——時決定格擋倍率）。"""
        ctx = self.ctx
        forced: ForcedOutcome | None = None
        if ctx.preview is not None:
            ctx.mark_branch()
            forced = "hit" if ctx.preview == "min" else "crit"
        single = ctx.preview is None and self.skill.shape.type == "single"
        if single and take_decoy(ctx, self.caster, unit, skill_id=self.skill.id) is not None:
            missed = _decoy_miss()  # 狐火誘餌（3R-2b）：擲命中之前轉向誘餌，這次攻擊落空
            self.hits[unit.id] = missed
            return missed
        bonus = self.modifier(modifiers.hit_bonus, unit) + self.aim_bonus
        self.caster.aimed = self.caster.aimed and not self.aim_bonus  # 用掉瞄準
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
                if self.profile.melee and self.melee_victims:
                    # 3C-6b：守護者擋下近戰，轉身的是守護者（不是原本被瞄準的人）
                    self.melee_victims[-1] = (guardian, self.caster.xy)
                unit = guardian
        if roll.hit and self.skill.category == "spell" and unit.team is not self.caster.team:
            spell_hit_reactions(ctx, self.caster, unit)  # 被法術命中、傷害之前（3D-3）
        if roll.hit and (force_block or self._affected_by_damage(unit)):
            self.blocks[unit.id] = block_multiplier(
                ctx, self.caster, unit, melee=self.profile.height_limited
            )
        return roll

    def modifier(
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

    def is_hit(self, unit: UnitState) -> bool:
        roll = self.hits.get(unit.id)
        return roll is not None and roll.hit

    def targets(self, affects: str, condition: ConditionSpec | None = None) -> list[UnitState]:
        """``affects`` 對應的存活單位（敵方與 ``all`` 的友方需命中），再套用效果層級的條件。"""
        if affects == "enemies":
            chosen = [u for u in self.enemies if self.is_hit(u)]
        elif affects == "allies":
            chosen = list(self.allies)
        elif affects == "all":
            chosen = [u for u in self.enemies if self.is_hit(u)]
            chosen += [u for u in self.allies if self.is_hit(u)]
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
                if effect.affects in TOUCHING_AFFECTS:
                    self.touch_untouched_tiles(spec, start)
                    self.spread_wind(spec)
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
        if any(e.hostile for e in self.effects) and not any(self.is_hit(u) for u in self.enemies):
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
            if not self.dash_continues(step):
                break
        if len(path) > 1 and caster.alive:
            collect_move(ctx, caster)  # on_move 被動：衝鋒算主動移動
        return caster.alive

    def dash_continues(self, step: XY) -> bool:
        """衝鋒走完這一步之後能不能繼續：還在預期的格子上，沒有被定身、擊倒、暈眩。"""
        caster, rules = self.caster, self.ctx.rules
        if not caster.alive or caster.xy != step or caster.has_status(PRONE):
            return False
        return not is_rooted(rules, caster) and skip_turn_status(rules, caster) is None

    def _dash_failed(self, reason: str) -> bool:
        self.ctx.emit(EffectFizzled, effect_kind=DASH, pos=None, reason=f"dash_{reason}")
        return False

    def announce_pierce(self) -> None:
        """穿透的射線穿過了物件：發出 ``shot_pierced``（Phase 3C-5b）。``behind`` 只列「命中」的
        後方單位（失手時沒有人受傷，紀錄不該說「後方只受 70%」；Phase 3C-6a）。"""
        trace = self.trace
        if not trace.objects:
            return
        hit_behind = tuple(uid for uid in trace.behind if (r := self.hits.get(uid)) and r.hit)
        self.ctx.emit(
            ShotPierced,
            unit_id=self.caster.id,
            skill_id=self.skill.id,
            objects=trace.objects,
            object_tiles=tuple(Pos(x=x, y=y) for x, y in trace.object_tiles),
            behind=hit_behind,
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
            definition = rules.stack_def(spec.stack)
            if definition.owner == "self":
                spent = consume_stacks(self.ctx, self.caster, spec.stack, source_id=self.caster.id)
                bonus = spent * spec.per_stack_permille
                boosts = ("damage",) if definition.consumer is None else definition.consumer.boosts
                if "damage" in boosts:
                    self.caster_bonus += bonus
                if "heal" in boosts:
                    self.heal_bonus += bonus
                    if definition.consumer is not None and definition.consumer.heal_self_only:
                        self.heal_self_only = True
                if "shield" in boosts:
                    self.shield_bonus += bonus
                continue
            for unit in self.targets(effect.affects, spec.condition):
                spent = consume_stacks(self.ctx, unit, spec.stack, source_id=self.caster.id)
                self.target_bonus[unit.id] = (
                    self.target_bonus.get(unit.id, 0) + spent * spec.per_stack_permille
                )
        self.auto_consume_stacks()

    def auto_consume_stacks(self) -> None:
        """自動消耗（3-52b，專注）：施放者的主動技能造成傷害時，吃掉全部該層數、每層加成傷害；
        不造成傷害的技能不吃（層數留給下一個傷害技能）。"""
        for stack in auto_consumed(self.skill, self.ctx.rules.stacks.stacks):
            assert stack.auto_consume is not None
            spent = consume_stacks(self.ctx, self.caster, stack.id, source_id=self.caster.id)
            self.caster_bonus += spent * stack.auto_consume.per_stack_permille

    def react_to_hits(self) -> None:
        """全部效果結算之後：每個被命中的單位（依單位 ID）各自可以用 ``hit_by_*`` 反應技反應。"""
        melee = self.profile.height_limited
        for uid in sorted(self.hits):
            roll = self.hits[uid]
            unit = self.ctx.state.units[UnitId(uid)]
            if roll.hit and unit.team is not self.caster.team:
                hit_reactions(self.ctx, self.caster, unit, melee=melee)

    def build(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """把一個效果原語展開成效果模型（「原語 → handler」登錄表，見
        :mod:`trpg.engine.skills.primitives`）；有些原語自己直接結算、回傳空列表。"""
        return primitive_handler(effect.type)(self, effect, spec)

    def spawn(self, skill: SkillDef, action: UseSkill, area: SkillArea) -> Cast:
        """以同一個施放者另起一次一般的施放（``copy_skill`` 複製施放用）。"""
        return Cast(self.ctx, self.caster, skill, action, area)

    # -- 數值 ----------------------------------------------------------

    def gamble_for(self, effect: ResolvedEffect) -> int:
        """賭注成功分支的傷害倍率（‰）；賭注分支自己的傷害（``spec_index < 0``）不再乘。"""
        return self.gamble_mult if effect.spec_index >= 0 else PERMILLE

    def attack_damage(
        self,
        unit: UnitState,
        spec: EffectSpec,
        *,
        dice: Dice | None,
        flat: int = 0,
        scaled: int = 0,
        multiplier: int = PERMILLE,
        element: Element,
        gamble: int,
        cause: Literal["attack", "backlash"] = "attack",
        explode_max: int = 0,
        preset: tuple[int, ...] | None = None,
    ) -> DamageEffect:
        """對 ``unit`` 的一次攻擊傷害（``damage``、``hurl_object``、``charge_through`` 共用）：
        命中的暴擊與格擋倍率、消耗層數的加成（``consume_stack``）、超載、``scaling``、修正規則的傷害‰、
        賭注倍率與穿透後方的折扣。元素由呼叫端決定（已含修正規則的 ``add_element``）。"""
        roll = self.hits.get(unit.id)
        block = self.blocks.get(unit.id, PERMILLE)
        bonus = PERMILLE + self.caster_bonus + self.target_bonus.get(unit.id, 0)
        bonus += overload_bonus(self.ctx.state, self.caster, self.skill)  # 超載層數（3D-7b）
        bonus += scale_bonus(self.ctx.state, self.caster, unit, spec.scaling)
        bonus = bonus * self.modifier(modifiers.damage_permille, unit) // PERMILLE
        bonus = bonus * gamble // PERMILLE
        if self.gun:  # 火器：站在這個距離的傷害修正（火槍遠距 +25%、貼臉 −50%、霰彈槍衰減）
            bonus = bonus * range_damage_permille(self.caster, manhattan(self.caster.xy, unit.xy))
            bonus //= PERMILLE
        behind = self.behind_permille(unit)
        return DamageEffect(
            target_id=unit.id,
            source_id=self.caster.id,
            cause=cause,
            element=element,
            dice=dice,
            flat=flat,
            scaled_permille=scaled,
            scale_attr=skill_scale_attr(self.caster, self.skill),
            crit=roll is not None and roll.crit,
            min_damage=self.ctx.core.min_damage_on_hit,
            explode_max=explode_max,
            preset_rolls=preset,
            multiplier_permille=multiplier
            * block
            * bonus
            * behind
            // (PERMILLE * PERMILLE * PERMILLE),
            pierce_permille=behind,
            block_permille=block,
        )

    def physical_element(self) -> Element:
        """沒有自己元素的傷害（投擲、衝撞）：物理，受修正規則的 ``add_element`` 影響。"""
        if not self.modified:
            return Element.PHYSICAL
        return modifiers.damage_element(self.ctx.state, self.caster, self.use, Element.PHYSICAL)

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

    def spread_wind(self, spec: EffectSpec) -> None:
        """元素擴散（Phase 3-54a，06 6.33）：``element: wind`` 的傷害效果吹到影響格的表面與區域時，
        往風向擴大（:func:`trpg.engine.wind.spread_wind`；只看效果自己寫的元素）。"""
        if spec.element is not Element.WIND:
            return
        tiles = [xy for xy in self.area.tiles if self.tile_holds(spec.condition, xy)]
        caster = self.caster
        spread_wind(self.ctx, self.area, caster.xy, tiles, caster.id, distance=spec.spread)

    def spell_scaled(self) -> int:
        """治療與護盾的屬性加成（‰）：有效縮放屬性 × ``spell_attr_multiplier_permille``。"""
        attr = skill_scaling_value(self.ctx.rules, self.caster, self.skill)
        return attr * self.ctx.core.spell_attr_multiplier_permille

    def level_permille(self) -> int:
        """技能等級的效果倍率（‰；Phase 3-26a，傷害由 ``damage_parameters`` 處理）。"""
        return level_multiplier(self.ctx.rules, self.caster, self.skill)

    def heal_multiplier(self, *, self_heal: bool = False, spec: EffectSpec | None = None) -> int:
        """施放者的治療量倍率（‰；修正規則 ``heal_permille``，3-24b1；再乘技能等級的倍率與消耗
        層數的治療加成；加成只算治療自己時，``self_heal``（效果的對象是 ``self``）才加，3-52b；
        ``spec`` 有 ``form_bonus_permille`` 且施放者在形態中時再乘 ``1000 ＋ n``，3J-4b）。"""
        base = PERMILLE
        if self.modified:
            base = modifiers.heal_permille(self.ctx.state, self.caster, self.use)
        bonus = self.heal_bonus
        if self.heal_self_only and not self_heal:
            bonus = 0
        total = base * self.level_permille() // PERMILLE * (PERMILLE + bonus) // PERMILLE
        if spec is None:
            return total
        return total * form_bonus_permille(self.ctx.state, self.caster, spec) // PERMILLE

    def shield_multiplier(self) -> int:
        """護盾量倍率（‰）：技能等級的倍率，再乘消耗層數的加成（Phase 3-52）。"""
        return self.level_permille() * (PERMILLE + self.shield_bonus) // PERMILLE

    def knock_down(self, unit: UnitState) -> list[EffectBase]:
        """對 ``unit`` 擲擊倒的對抗判定（技能的縮放屬性 vs 目標同屬性），成功才倒地。"""
        if unit.has_status(PRONE):
            return []
        if not contest(
            self.ctx,
            "knock_prone",
            self.caster,
            unit,
            skill_scaling_attr(self.caster, self.skill),
            skill_id=self.skill.id,
            primary=False,
            attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
        ):
            return []
        return [ApplyStatusEffect(source_id=self.caster.id, target_id=unit.id, status_id=PRONE)]

    def status_duration(self, spec: EffectSpec) -> int | None:
        """此技能施加狀態的持續回合：``mastery: duration`` 生效時在（效果指定的或狀態預設的）
        持續上加 1；永久狀態（沒有持續回合）不變。"""
        bonus = mastery_duration_bonus(self.caster, self.skill)
        assert spec.status is not None
        if self.modified:  # 裝備的技能強化：你施加的某狀態 +N 回合（3G-G2）
            bonus += modifiers.status_duration_bonus(
                self.ctx.state, self.caster, self.use, spec.status
            )
        if bonus == 0:
            return spec.duration
        base = spec.duration
        if base is None:
            base = self.ctx.rules.status_def(spec.status).duration
        return None if base is None else base + bonus

    def status_effects(self, spec: EffectSpec, unit: UnitState) -> list[EffectBase]:
        assert spec.status is not None
        planned = status_effect(
            self.ctx,
            caster=self.caster,
            target=unit,
            status_id=spec.status,
            duration=self.status_duration(spec),
            attack_attr=skill_scaling_attr(self.caster, self.skill),
            attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
            skill_id=self.skill.id,
        )
        return [] if planned is None else [planned]


class TriggeredCast(Cast):
    """被動技能的施放：沒有 ``UseSkill`` 動作，效果自動命中（Phase 2E 決定 F）。被動、陷阱與
    修正規則的命中後效果都不是持有者的動作，不受修正規則影響（Phase 3C-2）。"""

    modified = False

    def __init__(self, ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
        super().__init__(ctx, caster, skill, None, area)

    def roll_hits(self) -> None:
        """不擲命中：沒有 ``attack_rolled``，也沒有格擋。"""

    def is_hit(self, unit: UnitState) -> bool:
        return unit.id != self.caster.id


class GearCast(TriggeredCast):
    """裝備詞條的施放（Phase 3G-G3a）：同被動技能，但 ``grant_ap`` 受裝備的每回合 AP 回復上限
    （+1，所有來源合計）約束，且不吃「每輪最多被給一次」的限制。"""

    def build(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        if effect.type == SACRIFICE_SUMMON:
            # 召喚物倒下時（3-33f2）：不獻祭任何召喚物，直接以倒下的那一格為中心爆炸或治療
            return sacrifice_blast(self, self.area.tiles[0], spec)
        if effect.type == GRANT_AP:
            for unit in self.targets(effect.affects, spec.condition):
                gear_grant_ap(self.ctx, self.caster, unit, spec.amount or 1)
            return []
        return super().build(effect, spec)
