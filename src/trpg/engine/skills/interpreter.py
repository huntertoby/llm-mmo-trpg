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
from typing import ClassVar

from trpg.content.battle import Dice
from trpg.content.skills import (
    ADD_STACK,
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    CONSUME_STACK,
    CONSUME_STATUS,
    COPY_SKILL,
    EXTRA_REACTION,
    GRANT_AP,
    HURL_OBJECT,
    INTERCEPT,
    PLACE_TRAP,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    RESET_COOLDOWN,
    TOPPLE,
    ConditionSpec,
    EffectSpec,
    SkillDef,
    on_hit_carrier,
)
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
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
)
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EffectFizzled,
    ObjectDamaged,
    SkillCooldownChanged,
    SkillCopied,
    SkillUsed,
)
from trpg.engine.maneuvers import contest
from trpg.engine.reactions import (
    PauseForDecision,
    block_multiplier,
    hit_reactions,
    try_intercept,
)
from trpg.engine.results import Pending
from trpg.engine.rewrites import grant_ap, grant_reactions, reset_cooldowns
from trpg.engine.rules.combat import PERMILLE, AttackProfile, AttackRoll, ForcedOutcome, roll_attack
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.skill_triggers import collect_cast, holding
from trpg.engine.skills.conditions import Subject, condition_met
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
    skill_ap_cost,
    skill_problem,
    skill_profile,
)
from trpg.engine.source import spend_source
from trpg.engine.stacks import add_stacks, consume_stacks
from trpg.engine.state import BattleState, LastCast, TrapState, UnitState
from trpg.engine.traps import place_trap
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


def use_skill(ctx: Ctx, caster: UnitState, action: UseSkill) -> None:
    """``UseSkill`` 的動作處理器（``ACTION_HANDLERS["use_skill"]``）。"""
    try:
        skill = ctx.rules.skill_def(action.skill_id)
    except KeyError:
        raise IllegalActionError(f"找不到技能：{action.skill_id}") from None
    if skill.id not in caster.skills:
        raise IllegalActionError(f"{caster.name_zh} 沒有裝備技能：{skill.name_zh}")
    problem = skill_problem(ctx.state, caster, skill)
    if problem is not None:
        raise IllegalActionError(problem)
    area = checked_area(ctx.state, caster, skill, action)
    _check_copy(ctx, caster, skill, action)
    with holding(ctx):  # 被動的觸發等整個技能結算完才處理
        _pay_costs(ctx, caster, skill, area)
        if skill.trap is not None:  # 陷阱技能：施放時只放置陷阱，其餘效果等觸發時結算
            assert action.target_pos is not None
            place_trap(ctx, caster, skill, (action.target_pos.x, action.target_pos.y))
        else:
            _Cast(ctx, caster, skill, action, area).run()
        if skill.kind == "active":  # copy_skill 的複製對象（Phase 3C-4b）
            _record_cast(ctx.state, caster, skill)
        _apply_self_status(ctx, caster, skill)
        collect_cast(ctx, caster, skill)  # on_cast_tag：在該技能結算之後


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
            _Cast(ctx, owner, skill, None, area).run()
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


def _axis_direction(dx: int, dy: int) -> XY | None:
    """向量的主要軸向（四方向）；兩軸相同時取水平；零向量為 ``None``。"""
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


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

    # ------------------------------------------------------------------
    # 命中
    # ------------------------------------------------------------------

    def _affected_by_damage(self, unit: UnitState) -> bool:
        enemy = unit.team is not self.caster.team
        return any(
            e.type == "damage" and (e.affects == "all" or (enemy and e.affects == "enemies"))
            for e in self.effects
        )

    def roll_hits(self) -> None:
        ctx = self.ctx
        rolled: list[UnitState] = []
        if any(e.affects in ("enemies", "all") for e in self.effects):
            rolled += self.enemies
        if any(e.affects == "all" for e in self.effects):
            rolled += [u for u in self.allies if u is not self.caster]  # 敵我不分也不打到自己
        for unit in sorted(rolled, key=lambda u: u.id):
            forced: ForcedOutcome | None = None
            if ctx.preview is not None:
                ctx.mark_branch()
                forced = "hit" if ctx.preview == "min" else "crit"
            bonus = self._modifier(modifiers.hit_bonus, unit)
            roll = roll_attack(
                ctx.state, ctx.rng, self.caster, unit, forced, self.profile, bonus=bonus
            )
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
            )
            self.hits[unit.id] = roll
            if roll.hit and self.skill.shape.type == "single":
                guardian = try_intercept(
                    ctx, self.caster, unit, rolled_event.seq, skill_id=self.skill.id
                )
                if guardian is not None:
                    self._redirect(unit, guardian)
                    unit = guardian  # noqa: PLW2901 - 之後的格擋與傷害都是守護者的
            if roll.hit and self._affected_by_damage(unit):
                self.blocks[unit.id] = block_multiplier(
                    ctx, self.caster, unit, melee=self.profile.height_limited
                )
        if self.modified:
            hit = [Subject(u, u.xy) for u in self.enemies if self._hit(u)]
            state = ctx.state
            self.cooldown_delta = modifiers.cooldown_delta(state, self.caster, self.use, hit)

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
        self.roll_hits()
        self.consume_stacks()
        for effect in self.effects:
            spec = self.skill.effects[effect.spec_index]
            start = len(self.ctx.events)
            batch = self.build(effect, spec)
            if batch:
                execute(self.ctx, batch)
            if effect.type == "damage" and effect.affects in _TOUCHING_AFFECTS:
                self.touch_untouched_tiles(spec, start)
        self.react_to_hits()
        self.shorten_cooldown()

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
        if kind in (INTERCEPT, PLACE_TRAP, CONSUME_STACK):
            return []  # 攔截由反應機制處理；陷阱在 use_skill 放置；消耗層數在 consume_stacks
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
        _Cast(self.ctx, self.caster, copied, pick, area).run()
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
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            roll = self.hits.get(unit.id)
            block = self.blocks.get(unit.id, PERMILLE)
            bonus = PERMILLE + self.caster_bonus + self.target_bonus.get(unit.id, 0)
            bonus = bonus * self._modifier(modifiers.damage_permille, unit) // PERMILLE
            batch.append(
                DamageEffect(
                    target_id=unit.id,
                    source_id=self.caster.id,
                    cause="attack",
                    element=element,
                    dice=dice,
                    flat=flat,
                    scaled_permille=scaled,
                    crit=roll is not None and roll.crit,
                    min_damage=min_damage,
                    multiplier_permille=multiplier * block * bonus // (PERMILLE * PERMILLE),
                )
            )
        if effect.affects in _TOUCHING_AFFECTS:
            for xy in self.area.tiles:
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
                        // PERMILLE,
                    )
                )
        return batch

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
        direction = _axis_direction(unit.pos.x - area.origin[0], unit.pos.y - area.origin[1])
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
        return _axis_direction(xy[0] - self.caster.pos.x, xy[1] - self.caster.pos.y)

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
            HurlObjectEffect(source_id=self.caster.id, object_id=action.target_object_id, dest=dest)
        ]

    def knock_prone(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            if unit.has_status(PRONE):
                continue
            if contest(
                self.ctx,
                "knock_prone",
                self.caster,
                unit,
                self.skill.scaling_attr,
                skill_id=self.skill.id,
                primary=False,
                attack_value=skill_scaling_value(self.ctx.rules, self.caster, self.skill),
            ):
                batch.append(
                    ApplyStatusEffect(source_id=self.caster.id, target_id=unit.id, status_id=PRONE)
                )
        return batch

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
    HURL_OBJECT: _Cast.hurl_object,
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
