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

from trpg.content.skills import (
    ADD_STACK,
    CONSUME_STACK,
    INTERCEPT,
    PLACE_TRAP,
    ConditionSpec,
    EffectSpec,
    SkillDef,
)
from trpg.engine.actions import UseSkill
from trpg.engine.context import Ctx
from trpg.engine.control import status_effect
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
    LowerTerrainEffect,
    MoveUnitEffect,
    PushEffect,
    RaiseTerrainEffect,
    ShieldEffect,
)
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ObjectDamaged,
    SkillCooldownChanged,
    SkillUsed,
)
from trpg.engine.maneuvers import contest
from trpg.engine.reactions import block_multiplier, hit_reactions, try_intercept
from trpg.engine.rules.combat import PERMILLE, AttackProfile, AttackRoll, ForcedOutcome, roll_attack
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skill_triggers import holding
from trpg.engine.skills.conditions import Subject, condition_met
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
from trpg.engine.stacks import add_stacks, consume_stacks
from trpg.engine.state import TrapState, UnitState
from trpg.engine.traps import place_trap
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, UnitId

__all__ = ["use_reaction_skill", "use_skill", "use_trap_skill", "use_triggered_skill"]

PRONE = "prone"
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
    with holding(ctx):  # 被動的觸發等整個技能結算完才處理
        _pay_costs(ctx, caster, skill, area)
        if skill.trap is not None:  # 陷阱技能：施放時只放置陷阱，其餘效果等觸發時結算
            assert action.target_pos is not None
            place_trap(ctx, caster, skill, (action.target_pos.x, action.target_pos.y))
        else:
            _Cast(ctx, caster, skill, action, area).run()
        _apply_self_status(ctx, caster, skill)


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
    finally:
        ctx.trigger_depth = outer


def _pay_costs(ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
    ap = skill_ap_cost(ctx.state, skill)
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
    )
    if paid.cooldown is not None:
        ctx.emit(
            SkillCooldownChanged, unit_id=caster.id, skill_id=skill.id, remaining=paid.cooldown
        )


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
    """一次施放的工作狀態（命中結果、格擋倍率與影響範圍）。"""

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
            roll = roll_attack(ctx.state, ctx.rng, self.caster, unit, forced, self.profile)
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
        if kind == "damage":
            return self.damage(effect, spec)
        if kind == "heal":
            return self.heal(effect, spec)
        if kind == "shield":
            return self.shield(effect, spec)
        if kind == "cleanse":
            return [
                CleanseEffect(target_id=unit.id, source_id=self.caster.id)
                for unit in self.targets(effect.affects, spec.condition)
            ]
        if kind in ("push", "pull"):
            return self.displace(effect, spec, pull=kind == "pull")
        if kind == "knock_prone":
            return self.knock_prone(effect, spec)
        if kind == "teleport":
            return self.teleport(spec)
        if kind in (INTERCEPT, PLACE_TRAP, CONSUME_STACK):
            return []  # 攔截由反應機制處理；陷阱在 use_skill 放置；消耗層數在 consume_stacks
        if kind == ADD_STACK:
            self.add_stack(effect, spec)
            return []
        if kind == "apply_status":
            return self.apply_status(effect, spec)
        return self.tile_effect(effect, spec)

    # -- 數值 ----------------------------------------------------------

    def damage(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        params = damage_parameters(self.ctx.state, self.caster, self.skill, spec)
        dice, flat, scaled, multiplier, element = params
        min_damage = self.ctx.core.min_damage_on_hit
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            roll = self.hits.get(unit.id)
            block = self.blocks.get(unit.id, PERMILLE)
            bonus = PERMILLE + self.caster_bonus + self.target_bonus.get(unit.id, 0)
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
                        multiplier_permille=multiplier * (PERMILLE + self.caster_bonus) // PERMILLE,
                    )
                )
        return batch

    def touch_untouched_tiles(self, spec: EffectSpec, start: int) -> None:
        """帶元素的傷害：沒有單位或物件受到傷害的影響格，補上一次元素觸及（每格一次）。"""
        element = damage_parameters(self.ctx.state, self.caster, self.skill, spec).element
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
        attr = effective_attribute(self.ctx.rules, self.caster, self.skill.scaling_attr)
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
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            direction = self._displace_direction(unit, pull=pull)
            if direction is None:
                continue
            batch.append(
                PushEffect(
                    source_id=self.caster.id,
                    target_id=unit.id,
                    direction=direction,
                    distance=spec.distance,
                )
            )
        return batch

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

    def apply_status(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        """施加狀態：對敵方先轉換（Boss）、再擲抵抗判定（:mod:`trpg.engine.control`）；
        對友方與自己不擲。"""
        assert spec.status is not None
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects, spec.condition):
            planned = status_effect(
                self.ctx,
                caster=self.caster,
                target=unit,
                status_id=spec.status,
                duration=spec.duration,
                attack_attr=self.skill.scaling_attr,
                skill_id=self.skill.id,
            )
            if planned is not None:
                batch.append(planned)
        return batch

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


class _TriggeredCast(_Cast):
    """被動技能的施放：沒有 ``UseSkill`` 動作，效果自動命中（Phase 2E 決定 F）。"""

    def __init__(self, ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
        super().__init__(ctx, caster, skill, None, area)

    def roll_hits(self) -> None:
        """不擲命中：沒有 ``attack_rolled``，也沒有格擋。"""

    def _hit(self, unit: UnitState) -> bool:
        return unit.id != self.caster.id
