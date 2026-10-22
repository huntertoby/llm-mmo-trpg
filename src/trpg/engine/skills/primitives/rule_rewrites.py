"""改寫規則型與資源原語：給 AP、重置冷卻、不死、靈魂連結、複製施放、額外反應、回復資源、
暫時給技能。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.skills import (
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    EffectSpec,
)
from trpg.engine.copying import copy_source
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    EffectBase,
)
from trpg.engine.events import (
    EffectFizzled,
    SkillCopied,
)
from trpg.engine.grants import grant_skill as grant_skill_to
from trpg.engine.resources import (
    restore_cooldowns,
    restore_mana,
)
from trpg.engine.rewrites import (
    grant_ap as grant_ap_to,
)
from trpg.engine.rewrites import (
    grant_reactions,
    reset_cooldowns,
)
from trpg.engine.skill_triggers import collect_cast
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    checked_area,
)
from trpg.engine.state import UnitState
from trpg.shared.types import Pos

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast


def _rewrite_status(
    cast: Cast, kind: str, spec: EffectSpec, targets: list[UnitState]
) -> list[EffectBase]:
    """``cheat_death``（不死）與 ``redirect_damage``（靈魂連結；對象不含施放者自己）。"""
    if kind == CHEAT_DEATH:
        return [
            ApplyStatusEffect(
                source_id=cast.caster.id,
                target_id=unit.id,
                status_id=CHEAT_DEATH_STATUS,
                duration=spec.duration,
            )
            for unit in targets
        ]
    linked = [u for u in targets if u.id != cast.caster.id]
    if not linked:
        cast.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="self_link")
    return [
        ApplyStatusEffect(
            source_id=cast.caster.id,
            target_id=unit.id,
            status_id=REDIRECT_STATUS,
            duration=spec.duration,
            amount=spec.permille,
        )
        for unit in linked
    ]


def _copy_skill(cast: Cast) -> None:
    """``copy_skill``：以施放者的身分立即施放本輪最後施放的技能（不扣法力與 AP、不進冷卻、
    不花源力；``casts`` 在這次施放結束之後才更新，所以這裡看到的仍是被複製的那一次）。
    預覽沒有選取時不結算。"""
    pick = None if cast.action is None else cast.action.copy_cast
    if pick is None:
        return
    state = cast.ctx.state
    found = copy_source(state, cast.caster)
    assert not isinstance(found, str)  # use_skill 開頭已檢查
    copied, origin = found
    area = checked_area(state, cast.caster, copied, pick)
    cast.ctx.emit(
        SkillCopied,
        unit_id=cast.caster.id,
        source_id=origin.id,
        skill_id=copied.id,
        name_zh=copied.name_zh,
        tiles=tuple(Pos(x=x, y=y) for x, y in area.tiles),
    )
    copy = cast.spawn(copied, pick, area)
    copy.pays_miss_cost = False  # 複製的技能不付代價（失手反噬也是代價）
    copy.run()
    collect_cast(cast.ctx, cast.caster, copied)


def restore_resource(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``restore_resource``：對每個對象直接結算（:mod:`trpg.engine.resources`）。"""
    for unit in cast.targets(effect.affects, spec.condition):
        if spec.resource == "mana":
            restore_mana(cast.ctx, cast.caster, unit, spec.amount or 1)
        else:
            restore_cooldowns(cast.ctx, cast.caster, unit, cast.skill, spec)
    return []


def grant_skill(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``grant_skill``（Phase 3D-8c）：每個對象暫時獲得 ``spec.skill``（``engine.grants``）。"""
    assert spec.skill is not None and spec.duration is not None
    for unit in cast.targets(effect.affects, spec.condition):
        grant_skill_to(cast.ctx, cast.caster, unit, spec.skill, spec.duration)
    return []


# -- 改寫規則型（Phase 3C-4a）：grant_ap、reset_cooldown、extra_reaction 直接結算
# （:mod:`trpg.engine.rewrites`）；copy_skill 複製施放；cheat_death 與 redirect_damage 對每個
# 對象施加狀態（不擲抵抗）。


def grant_ap(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    for unit in cast.targets(effect.affects, spec.condition):
        grant_ap_to(cast.ctx, cast.caster, unit, spec.amount or 1)
    return []


def reset_cooldown(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    targets = cast.targets(effect.affects, spec.condition)
    done = [reset_cooldowns(cast.ctx, cast.caster, u, cast.skill, spec) for u in targets]
    if not any(done):
        cast.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_cooldown")
    return []


def extra_reaction(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    for unit in cast.targets(effect.affects, spec.condition):
        grant_reactions(cast.ctx, cast.caster, unit, spec.amount or 1)
    return []


def cheat_death(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    return _rewrite_status(cast, CHEAT_DEATH, spec, cast.targets(effect.affects, spec.condition))


def redirect_damage(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    targets = cast.targets(effect.affects, spec.condition)
    return _rewrite_status(cast, REDIRECT_DAMAGE, spec, targets)


def copy_skill(cast: Cast, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
    _copy_skill(cast)
    return []


HANDLERS: dict[str, Handler] = {
    "grant_ap": grant_ap,
    "reset_cooldown": reset_cooldown,
    "cheat_death": cheat_death,
    "redirect_damage": redirect_damage,
    "copy_skill": copy_skill,
    "extra_reaction": extra_reaction,
    "restore_resource": restore_resource,
    "grant_skill": grant_skill,
}
