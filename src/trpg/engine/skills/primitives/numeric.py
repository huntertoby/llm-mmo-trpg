"""數值型原語：傷害（含聖光雙效與破壞物件）、治療、護盾、淨化。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.skills import (
    EffectSpec,
)
from trpg.engine import modifiers
from trpg.engine.effects.models import (
    CleanseEffect,
    DamageObjectEffect,
    EffectBase,
    HealEffect,
    ShieldEffect,
)
from trpg.engine.rules.combat import PERMILLE
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.primitives.base import TOUCHING_AFFECTS, Handler
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    damage_parameters,
)
from trpg.engine.state import UnitState

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast


def damage(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    params = damage_parameters(
        cast.ctx.state, cast.caster, cast.skill, spec, modified=cast.modified
    )
    dice, flat, scaled, multiplier, element = params
    min_damage = cast.ctx.core.min_damage_on_hit
    gamble = cast.gamble_for(effect)
    explode_max = cast.ctx.core.explode_max if spec.explode else 0
    batch: list[EffectBase] = []
    units = cast.targets(effect.affects, spec.condition)
    healed = _split_healed(cast, spec)  # 聖光雙效：友方改為治療，與敵方的傷害共用同一次擲骰
    preset = _split_rolls(cast, spec, bool(units or healed))
    for unit in units:
        batch.append(
            cast.attack_damage(
                unit,
                spec,
                dice=dice,
                flat=flat,
                scaled=scaled,
                multiplier=multiplier,
                element=element,
                gamble=gamble,
                cause="backlash" if effect.affects == "self" else "attack",
                explode_max=explode_max,
                preset=preset,
            )
        )
    batch += [
        HealEffect(
            target_id=unit.id,
            source_id=cast.caster.id,
            dice=spec.dice,
            scaled_permille=cast.spell_scaled(),
            preset_rolls=preset,
            multiplier_permille=cast.heal_multiplier(),
        )
        for unit in healed
    ]
    if effect.affects in TOUCHING_AFFECTS:
        for xy in (*cast.area.tiles, *_pierced_tiles(cast)):
            obj = cast.ctx.state.object_at(*xy)
            if obj is None or obj.hp is None or not cast.tile_holds(spec.condition, xy):
                continue
            if "breakable" not in cast.ctx.rules.object_def(obj.kind).tags:
                continue
            batch.append(
                DamageObjectEffect(
                    object_id=obj.id,
                    source_id=cast.caster.id,
                    cause="attack",
                    element=element,
                    dice=dice,
                    flat=flat,
                    scaled_permille=scaled,
                    min_damage=min_damage,
                    multiplier_permille=multiplier
                    * (PERMILLE + cast.caster_bonus)
                    // PERMILLE
                    * cast.modifier(modifiers.damage_permille, None, xy)
                    // PERMILLE
                    * gamble
                    // PERMILLE,
                )
            )
    return batch


def _split_healed(cast: Cast, spec: EffectSpec) -> list[UnitState]:
    """聖光雙效（``split_heal``，Phase 3D-8a）受治療的友方（含自己，依單位 ID 排序）；不是聖光
    雙效為空。"""
    if not spec.split_heal:
        return []
    alive = (u for u in cast.allies if u.alive and cast.holds(spec.condition, Subject(u, u.xy)))
    return sorted(alive, key=lambda u: u.id)


def _split_rolls(cast: Cast, spec: EffectSpec, anyone: bool) -> tuple[int, ...] | None:
    """聖光雙效的骰值：傷害與治療共用的一次擲骰（沒有對象時不擲）；不是聖光雙效為 ``None``。"""
    if not spec.split_heal or spec.dice is None or not anyone:
        return None
    return tuple(cast.ctx.rng.roll(spec.dice.sides) for _ in range(spec.dice.count))


def _pierced_tiles(cast: Cast) -> list[XY]:
    """穿透的單體射線穿過、但不在影響範圍內的 ``penetrable`` 物件所在格（物件受全額傷害）。"""
    return [xy for xy in cast.trace.object_tiles if xy not in cast.area.tiles]


def heal(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    scaled = cast.spell_scaled()
    return [
        HealEffect(
            target_id=unit.id,
            source_id=cast.caster.id,
            dice=spec.dice,
            scaled_permille=scaled,
            multiplier_permille=cast.heal_multiplier(self_heal=effect.affects == "self", spec=spec),
        )
        for unit in cast.targets(effect.affects, spec.condition)
    ]


def shield(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    scaled = cast.spell_scaled()
    multiplier = cast.shield_multiplier()
    return [
        ShieldEffect(
            target_id=unit.id,
            source_id=cast.caster.id,
            dice=spec.dice,
            scaled_permille=scaled,
            multiplier_permille=multiplier,
            duration=spec.duration,
            status_id=spec.status,
        )
        for unit in cast.targets(effect.affects, spec.condition)
    ]


def cleanse(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    return [
        CleanseEffect(target_id=unit.id, source_id=cast.caster.id)
        for unit in cast.targets(effect.affects, spec.condition)
    ]


HANDLERS: dict[str, Handler] = {
    "damage": damage,
    "heal": heal,
    "shield": shield,
    "cleanse": cleanse,
}
