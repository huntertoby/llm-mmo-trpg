"""召喚與放置原語：召喚、獻祭召喚物、持續區域、復活、引爆符文。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.skills import (
    SUMMON_BESIDE,
    EffectSpec,
)
from trpg.engine.effects.models import (
    DamageEffect,
    DetonateRuneEffect,
    EffectBase,
    HealEffect,
)
from trpg.engine.events import EffectFizzled, UnitSummoned
from trpg.engine.gear.summon import gear_sacrifice_permille
from trpg.engine.lifecycle import dismiss_summon
from trpg.engine.reactions import perform_unit_attack
from trpg.engine.rules.combat import PERMILLE, attack_problem
from trpg.engine.rules.footprint import dist_to
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.runes import own_runes
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.skills.revive import revive_unit
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    summon_site_problem,
)
from trpg.engine.summons.core import summon_room, summon_unit
from trpg.engine.summons.variants import second_summon_site
from trpg.engine.zones import create_zone
from trpg.shared.types import Element, Pos

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast
    from trpg.engine.state import BattleState, UnitState


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


def summon_beside(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``summon_beside``（TF-1，#159 伴生、護主）：在施放者旁邊第一個可以召喚的格子（東、西、
    南、北）召出縮小版召喚物（``power_permille``）。同一召喚者的召喚物已達上限、或旁邊沒有空格時
    不召喚（``effect_fizzled``，原因 ``summon_limit``／``summon_blocked``）。``strike_other``：
    召喚物改出現在攻擊者旁邊離施放者最近的空格（同距離照東、西、南、北），召出後立刻對攻擊者
    普攻一次，打得到才打；攻擊者旁邊沒有空格時退回施放者旁邊（多半咬不到）。"""
    ctx, caster = cast.ctx, cast.caster
    if not cast.holds(spec.condition, Subject(caster, caster.xy)):
        return []
    assert spec.unit is not None and spec.duration is not None
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if not summon_room(ctx, caster, cast.skill.id):
        ctx.emit(EffectFizzled, effect_kind=SUMMON_BESIDE, pos=pos, reason="summon_limit")
        return []
    foe = _strike_target(cast) if spec.strike_other else None
    site = None if foe is None else _site_near(ctx.state, foe.xy, caster.xy)
    if site is None:
        site = second_summon_site(ctx.state, caster.xy)
    if site is None:
        ctx.emit(EffectFizzled, effect_kind=SUMMON_BESIDE, pos=pos, reason="summon_blocked")
        return []
    events = summon_unit(ctx, caster, spec.unit, site, spec.duration, cast.skill.id, spec=spec)
    summoned = next((e for e in events if isinstance(e, UnitSummoned)), None)
    if foe is not None and summoned is not None:
        pet = ctx.state.units[summoned.unit_id]
        if pet.alive and foe.alive and attack_problem(ctx.state, pet, foe) is None:
            perform_unit_attack(ctx, pet, foe, primary=False, reaction=True)
    return []


def _strike_target(cast: Cast) -> UnitState | None:
    """護主反咬的對象：影響範圍裡第一個存活的敵人（反應技形狀 ``single`` 的對象＝觸發者）。"""
    state = cast.ctx.state
    for uid in cast.area.units:
        unit = state.units.get(uid)
        if unit is not None and unit.alive and unit.team is not cast.caster.team:
            return unit
    return None


def _site_near(state: BattleState, foe_xy: XY, owner_xy: XY) -> XY | None:
    """攻擊者旁邊可以召喚、離施放者最近的格子（同距離照東、西、南、北）。"""
    sites = [(foe_xy[0] + dx, foe_xy[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    free = [xy for xy in sites if summon_site_problem(state, xy) is None]
    return min(free, key=lambda xy: manhattan(xy, owner_xy), default=None)


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
        (u for u in cast.ctx.state.living_units() if dist_to(u, xy) <= spec.radius),
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
    SUMMON_BESIDE: summon_beside,
    "sacrifice_summon": sacrifice_summon,
    "zone": zone,
    "revive": revive,
    "detonate_runes": detonate_runes,
}
