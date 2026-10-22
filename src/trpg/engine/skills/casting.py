"""施放技能的對外入口（Phase 3E-2b）。

引擎其他模組（延遲段、反應、陷阱、區域、被動觸發、規則改變、灌注、裝備詞條、動作處理器）一律從
這裡呼叫技能的結算，不直接匯入 :mod:`trpg.engine.skills.interpreter`。

為什麼要有這一層：解譯器在結算時要用到這些模組（例如 ``delayed.charge``、``traps.place_trap``、
``reactions.try_intercept``），這些模組在觸發時又要回頭施放技能，彼此循環。本模組執行時不匯入任何
引擎模組（只有型別註記），解譯器在載入時以 :func:`install` 登錄實作；呼叫端在模組頂端匯入本模組
即可，不必再延後匯入。

解譯器由 :mod:`trpg.engine.battle`（動作處理器）匯入，而 ``trpg.engine`` 套件一載入就會匯入
``battle``，所以只要用到引擎，實作就已經登錄；沒有登錄時呼叫會拋出 ``RuntimeError``。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from trpg.content.skills import EffectSpec, SkillDef
    from trpg.engine.actions import UseSkill
    from trpg.engine.context import Ctx
    from trpg.engine.skills.targeting import SkillArea
    from trpg.engine.state import TrapState, UnitState, ZoneState

__all__ = [
    "CastingImpl",
    "install",
    "run_delayed",
    "run_infused",
    "use_gear_effects",
    "use_modifier_effects",
    "use_reaction_skill",
    "use_rule_change_effects",
    "use_skill",
    "use_trap_skill",
    "use_triggered_skill",
    "use_zone_effects",
]


class CastingImpl(Protocol):
    """技能結算的實作（:mod:`trpg.engine.skills.interpreter` 登錄）；各方法的說明見下方同名函式。"""

    def use_skill(self, ctx: Ctx, caster: UnitState, action: UseSkill) -> None: ...

    def use_triggered_skill(
        self, ctx: Ctx, owner: UnitState, skill: SkillDef, other: UnitState | None
    ) -> None: ...

    def use_gear_effects(
        self, ctx: Ctx, owner: UnitState, carrier: SkillDef, subject: UnitState | None
    ) -> None: ...

    def use_modifier_effects(
        self,
        ctx: Ctx,
        owner: UnitState,
        skill: SkillDef,
        effects: tuple[EffectSpec, ...],
        target: UnitState,
    ) -> None: ...

    def use_rule_change_effects(
        self,
        ctx: Ctx,
        owner: UnitState,
        skill: SkillDef,
        effects: tuple[EffectSpec, ...],
        target: UnitState,
        *,
        depth: int,
    ) -> None: ...

    def use_trap_skill(self, ctx: Ctx, trap: TrapState, skill: SkillDef, *, depth: int) -> None: ...

    def use_zone_effects(
        self, ctx: Ctx, zone: ZoneState, unit: UnitState, *, depth: int
    ) -> None: ...

    def use_reaction_skill(
        self,
        ctx: Ctx,
        owner: UnitState,
        skill: SkillDef,
        trigger: UnitState | None,
        *,
        depth: int,
        on_paid: Callable[[], None] | None = None,
    ) -> None: ...

    def run_delayed(
        self, ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
    ) -> None: ...

    def run_infused(
        self, ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
    ) -> None: ...


_INSTALLED: dict[str, CastingImpl] = {}
_KEY = "impl"


def install(impl: CastingImpl) -> None:
    """登錄技能結算的實作（解譯器載入時呼叫一次；重複登錄時以最後一次為準）。"""
    _INSTALLED[_KEY] = impl


def _impl() -> CastingImpl:
    impl = _INSTALLED.get(_KEY)
    if impl is None:
        raise RuntimeError("技能解譯器尚未登錄（trpg.engine.skills.interpreter 沒有被匯入）")
    return impl


def use_skill(ctx: Ctx, caster: UnitState, action: UseSkill) -> None:
    """``UseSkill`` 的動作處理器：檢查、付代價、結算（含複合技能與第二段）。"""
    _impl().use_skill(ctx, caster, action)


def use_triggered_skill(
    ctx: Ctx, owner: UnitState, skill: SkillDef, other: UnitState | None
) -> None:
    """結算被動技能的效果（代價與 ``skill_triggered`` 已由呼叫端處理）。"""
    _impl().use_triggered_skill(ctx, owner, skill, other)


def use_gear_effects(
    ctx: Ctx, owner: UnitState, carrier: SkillDef, subject: UnitState | None
) -> None:
    """結算裝備詞條（第 6、7 類）包成的被動技能的效果。"""
    _impl().use_gear_effects(ctx, owner, carrier, subject)


def use_modifier_effects(
    ctx: Ctx, owner: UnitState, skill: SkillDef, effects: tuple[EffectSpec, ...], target: UnitState
) -> None:
    """結算修正規則的命中後效果（``skill_triggered`` 已由呼叫端發出）。"""
    _impl().use_modifier_effects(ctx, owner, skill, effects, target)


def use_rule_change_effects(
    ctx: Ctx,
    owner: UnitState,
    skill: SkillDef,
    effects: tuple[EffectSpec, ...],
    target: UnitState,
    *,
    depth: int,
) -> None:
    """結算規則改變對 ``target`` 的效果（``rule_change_triggered`` 已由呼叫端發出）。"""
    _impl().use_rule_change_effects(ctx, owner, skill, effects, target, depth=depth)


def use_trap_skill(ctx: Ctx, trap: TrapState, skill: SkillDef, *, depth: int) -> None:
    """結算陷阱觸發的效果（``trap_triggered`` 已由呼叫端發出，陷阱已移除）。"""
    _impl().use_trap_skill(ctx, trap, skill, depth=depth)


def use_zone_effects(ctx: Ctx, zone: ZoneState, unit: UnitState, *, depth: int) -> None:
    """結算持續區域對 ``unit`` 的效果（``zone_triggered`` 已由呼叫端發出）。"""
    _impl().use_zone_effects(ctx, zone, unit, depth=depth)


def use_reaction_skill(
    ctx: Ctx,
    owner: UnitState,
    skill: SkillDef,
    trigger: UnitState | None,
    *,
    depth: int,
    on_paid: Callable[[], None] | None = None,
) -> None:
    """立刻施放反應技（``ReactionTriggered`` 已由呼叫端發出）。"""
    _impl().use_reaction_skill(ctx, owner, skill, trigger, depth=depth, on_paid=on_paid)


def run_delayed(
    ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
) -> None:
    """結算延遲段（:mod:`trpg.engine.delayed`）。"""
    _impl().run_delayed(ctx, caster, skill, pick, area)


def run_infused(
    ctx: Ctx, caster: UnitState, skill: SkillDef, pick: UseSkill, area: SkillArea
) -> None:
    """結算召喚物施放的灌注技能（:mod:`trpg.engine.skill_infusion`）。"""
    _impl().run_infused(ctx, caster, skill, pick, area)
