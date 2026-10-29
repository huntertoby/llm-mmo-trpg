"""召喚與放置原語：召喚、獻祭召喚物、持續區域、復活、引爆符文。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.skills import (
    EffectSpec,
)
from trpg.engine.effects.models import (
    DamageEffect,
    DetonateRuneEffect,
    EffectBase,
    HealEffect,
)
from trpg.engine.gear.summon import gear_sacrifice_permille
from trpg.engine.lifecycle import dismiss_summon
from trpg.engine.rules.combat import PERMILLE
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.runes import own_runes
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.skills.revive import revive_unit
from trpg.engine.skills.targeting import (
    ResolvedEffect,
)
from trpg.engine.summons.core import summon_unit
from trpg.engine.summons.variants import second_summon_site
from trpg.engine.zones import create_zone
from trpg.shared.types import Element

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast


def summon(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``summon``（Phase 3D-4a）：在選取的格子召喚 ``unit``，持續 ``duration`` 輪（直接結算，
    見 :mod:`trpg.engine.summons.core`）。"""
    action = cast.action
    if action is None or action.target_pos is None:
        return []
    if not cast.holds(spec.condition, Subject(cast.caster, cast.caster.xy)):
        return []
    assert spec.unit is not None and spec.duration is not None
    xy = (action.target_pos.x, action.target_pos.y)
    sites = [xy]
    # 數量型分歧進化（3-33f2）：第二隻放在旁邊第一個合法的空格
    if isinstance(spec.count, int) and spec.count > 1:
        second = second_summon_site(cast.ctx.state, xy)
        sites.append(second if second is not None else xy)  # 沒有空位：第二隻落空（log 有記錄）
    for site in sites:
        summon_unit(
            cast.ctx,
            cast.caster,
            spec.unit,
            site,
            spec.duration,
            cast.skill.id,
            infusion=action.infusion,
            spec=spec,
        )
    return []


def sacrifice_summon(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``sacrifice_summon``（Phase 3-24c）：選取的自己的召喚物消失（原因 ``sacrificed``，不算
    倒下），並在它所在的位置以 ``radius`` 格結算：有 ``element`` 是爆炸（範圍內的敵人自動命中、
    骰值＋縮放屬性 × 法術倍率的傷害），沒有是治療範圍內的友方（含施放者，不含被獻祭者）。"""
    assert spec.dice is not None and spec.radius is not None
    batch: list[EffectBase] = []
    for unit in cast.targets("allies", spec.condition):
        if unit.owner_id != cast.caster.id:  # 只能獻祭自己的召喚物（選取時已檢查）
            continue
        xy = unit.xy
        dismiss_summon(cast.ctx, unit, "sacrificed")
        batch += sacrifice_blast(cast, xy, spec)
    return batch


def sacrifice_blast(cast: Cast, xy: XY, spec: EffectSpec) -> list[EffectBase]:
    assert spec.dice is not None and spec.radius is not None
    caster = cast.caster
    scaled = cast.spell_scaled()
    near = sorted(
        (u for u in cast.ctx.state.living_units() if manhattan(u.xy, xy) <= spec.radius),
        key=lambda u: u.id,
    )
    bonus = PERMILLE + gear_sacrifice_permille(cast.ctx.state, caster)  # 獻祭詞條（3-33f2）
    if spec.element is not None:
        return [
            DamageEffect(
                target_id=u.id,
                source_id=caster.id,
                cause="effect",
                element=spec.element,
                dice=spec.dice,
                scaled_permille=scaled,
                min_damage=cast.ctx.core.min_damage_on_hit,
                multiplier_permille=bonus,
            )
            for u in near
            if u.team is not caster.team
        ]
    return [
        HealEffect(
            target_id=u.id,
            source_id=caster.id,
            dice=spec.dice,
            scaled_permille=scaled,
            multiplier_permille=cast.heal_multiplier() * bonus // PERMILLE,
        )
        for u in near
        if u.team is caster.team
    ]


def zone(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``zone``（Phase 3D-5）：在影響範圍建立持續區域（直接結算，見
    :mod:`trpg.engine.zones`）。"""
    create_zone(cast.ctx, cast.caster, cast.skill, spec, cast.area.tiles, cast.area.direction)
    return []


def revive(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``revive``（Phase 3D-8b）：選定的倒下友方站起來（:mod:`trpg.engine.skills.revive`）。"""
    assert cast.action is not None and cast.action.target_id is not None
    assert spec.hp_permille is not None
    target = cast.ctx.state.units[cast.action.target_id]
    revive_unit(cast.ctx, cast.caster, target, cast.skill.id, spec.hp_permille)
    return []


def detonate_runes(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``detonate_runes``（Phase 3-23）：影響範圍內施放者自己的符文（依編號）每格引爆一次：移除
    符文，並對該格上符合 ``affects`` 的單位自動命中造成一次傷害（骰值＋縮放屬性 × 法術倍率；
    元素取 ``element``、省略時取符文的元素，標籤符文為物理；施放者自己不受 ``all`` 的傷害）。
    ``scope: target_cell``（Phase 3-31，命中後效果與普攻詞條）：只引爆影響範圍的第一格（被命中
    目標所在的那 1 格）。"""
    assert spec.dice is not None
    state, caster = cast.ctx.state, cast.caster
    scaled = cast.spell_scaled()
    batch: list[EffectBase] = []
    tiles = cast.area.tiles[:1] if spec.scope == "target_cell" else cast.area.tiles
    for rune in own_runes(state, caster.id):
        if rune.xy not in tiles or not cast.tile_holds(spec.condition, rune.xy):
            continue
        batch.append(DetonateRuneEffect(source_id=caster.id, pos=rune.xy, rune_id=rune.id))
        unit = state.unit_at(*rune.xy)
        if unit is None or unit.id == caster.id:
            continue
        if effect.affects == "enemies" and unit.team is caster.team:
            continue
        batch.append(
            DamageEffect(
                target_id=unit.id,
                source_id=caster.id,
                cause="effect",
                element=spec.element or rune.element or Element.PHYSICAL,
                dice=spec.dice,
                scaled_permille=scaled,
                min_damage=cast.ctx.core.min_damage_on_hit,
            )
        )
    return batch


HANDLERS: dict[str, Handler] = {
    "summon": summon,
    "sacrifice_summon": sacrifice_summon,
    "zone": zone,
    "revive": revive,
    "detonate_runes": detonate_runes,
}
