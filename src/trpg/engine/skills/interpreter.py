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

from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
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
)
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ObjectDamaged,
    SkillCooldownChanged,
    SkillUsed,
)
from trpg.engine.maneuvers import contest
from trpg.engine.reactions import block_multiplier
from trpg.engine.rules.combat import PERMILLE, AttackProfile, AttackRoll, ForcedOutcome, roll_attack
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    SkillArea,
    compute_area,
    damage_parameters,
    hp_cost,
    resolve_effects,
    skill_problem,
    skill_profile,
)
from trpg.engine.state import UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos

__all__ = ["use_skill"]

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
    area = compute_area(ctx.state, caster, skill, action)
    _pay_costs(ctx, caster, skill, area)
    _Cast(ctx, caster, skill, action, area).run()


def _pay_costs(ctx: Ctx, caster: UnitState, skill: SkillDef, area: SkillArea) -> None:
    ap = skill.ap_cost or 0
    hp = hp_cost(caster, skill)
    caster.ap -= ap
    caster.mana -= skill.cost.mana
    caster.hp -= hp
    if skill.cost.uses_per_battle is not None:
        caster.skill_uses[skill.id] = caster.skill_uses.get(skill.id, 0) + 1
    cooldown = skill.cost.cooldown
    if cooldown is not None:
        caster.cooldowns[skill.id] = cooldown
    ctx.emit(
        SkillUsed,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        ap=ap,
        mana=skill.cost.mana,
        mana_after=caster.mana,
        hp_spent=hp,
        cooldown=cooldown,
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
    )
    if cooldown is not None:
        ctx.emit(SkillCooldownChanged, unit_id=caster.id, skill_id=skill.id, remaining=cooldown)


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
        self, ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill, area: SkillArea
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
            rolled += self.allies
        for unit in sorted(rolled, key=lambda u: u.id):
            forced: ForcedOutcome | None = None
            if ctx.preview is not None:
                ctx.mark_branch()
                forced = "hit" if ctx.preview == "min" else "crit"
            roll = roll_attack(ctx.state, ctx.rng, self.caster, unit, forced, self.profile)
            ctx.emit(
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
            if roll.hit and self._affected_by_damage(unit):
                self.blocks[unit.id] = block_multiplier(
                    ctx, self.caster, unit, melee=self.profile.height_limited
                )

    # ------------------------------------------------------------------
    # 選出效果的對象
    # ------------------------------------------------------------------

    def _hit(self, unit: UnitState) -> bool:
        roll = self.hits.get(unit.id)
        return roll is not None and roll.hit

    def targets(self, affects: str) -> list[UnitState]:
        """``affects`` 對應的存活單位（敵方與 ``all`` 的友方需命中）。"""
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
        return sorted((u for u in chosen if u.alive), key=lambda u: u.id)

    def tiles(self, affects: str) -> list[XY]:
        """地形類效果的作用格：``tiles`` 為全部影響格；其他為對象單位目前所在的格子。"""
        if affects == "tiles":
            return list(self.area.tiles)
        cells = {u.xy for u in self.targets(affects)}
        return sorted(cells, key=lambda p: (p[1], p[0]))

    # ------------------------------------------------------------------
    # 展開
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.roll_hits()
        for effect in self.effects:
            spec = self.skill.effects[effect.spec_index]
            start = len(self.ctx.events)
            batch = self.build(effect, spec)
            if batch:
                execute(self.ctx, batch)
            if effect.type == "damage" and effect.affects in _TOUCHING_AFFECTS:
                self.touch_untouched_tiles(spec, start)

    def build(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:  # noqa: PLR0911
        kind = effect.type
        if kind == "damage":
            return self.damage(effect, spec)
        if kind == "heal":
            return self.heal(effect, spec)
        if kind in ("push", "pull"):
            return self.displace(effect, spec, pull=kind == "pull")
        if kind == "knock_prone":
            return self.knock_prone(effect)
        if kind == "teleport":
            return self.teleport()
        if kind == "apply_status":
            return self.apply_status(effect, spec)
        return self.tile_effect(effect, spec)

    # -- 數值 ----------------------------------------------------------

    def damage(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        params = damage_parameters(self.ctx.state, self.caster, self.skill, spec)
        dice, flat, scaled, multiplier, element = params
        min_damage = self.ctx.core.min_damage_on_hit
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects):
            roll = self.hits.get(unit.id)
            block = self.blocks.get(unit.id, PERMILLE)
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
                    multiplier_permille=multiplier * block // PERMILLE,
                )
            )
        if effect.affects in _TOUCHING_AFFECTS:
            for xy in self.area.tiles:
                obj = self.ctx.state.object_at(*xy)
                if obj is None or obj.hp is None:
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
                        multiplier_permille=multiplier,
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
            if xy not in touched
        ]
        if remaining:
            execute(self.ctx, remaining)

    def heal(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        scaled = (
            self.caster.attributes[self.skill.scaling_attr]
            * self.ctx.core.spell_attr_multiplier_permille
        )
        return [
            HealEffect(
                target_id=unit.id,
                source_id=self.caster.id,
                dice=spec.dice,
                scaled_permille=scaled,
            )
            for unit in self.targets(effect.affects)
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
        for unit in self.targets(effect.affects):
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

    def knock_prone(self, effect: ResolvedEffect) -> list[EffectBase]:
        batch: list[EffectBase] = []
        for unit in self.targets(effect.affects):
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

    def teleport(self) -> list[EffectBase]:
        pos = self.action.target_pos
        assert pos is not None
        return [
            MoveUnitEffect(
                source_id=self.caster.id,
                unit_id=self.caster.id,
                dest=(pos.x, pos.y),
                mode="teleport",
            )
        ]

    def apply_status(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        assert spec.status is not None
        return [
            ApplyStatusEffect(
                source_id=self.caster.id,
                target_id=unit.id,
                status_id=spec.status,
                duration=spec.duration,
            )
            for unit in self.targets(effect.affects)
        ]

    # -- 地形 ----------------------------------------------------------

    def tile_effect(self, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
        state = self.ctx.state
        source = self.caster.id
        batch: list[EffectBase] = []
        for xy in self.tiles(effect.affects):
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
