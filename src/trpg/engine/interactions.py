"""元素 × 標籤／表面互動（讀 ``content/interactions.yaml``）與表面的進入效果。

所有互動都是「事件觸發效果」（``docs/專案計畫.md`` 5.9）：

- ``damage_dealt``（攻擊或效果造成的元素傷害）→ 元素觸及目標所在的格子。
- ``object_damaged`` → 元素觸及物件所在的格子；HP ≤ 0 的 ``breakable`` 物件摧毀。
- ``object_exploded`` → 範圍內的單位受到爆炸傷害，每一格被爆炸的元素觸及。
- ``object_destroyed``（被傷害打破、投擲摔破）→ 物件的 ``spill``：該格與四方向相鄰格漏出表面。
- ``element_touched``（``element_touch`` 效果、產生帶元素的表面）→ 元素觸及該格。
- ``surface_entered``／``check_rolled`` → 表面的進入效果（燃燒、冰面滑倒）。

「元素觸及一格」時，依互動表對該格的 **表面**、**物件**、**單位** 三類對象各套用第一條符合的規則
（:func:`touch_outcomes`）。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Literal

from trpg.content.environment import InteractionOutcome, InteractionRule
from trpg.content.library import Ruleset
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CreateSurfaceEffect,
    DamageEffect,
    DestroyObjectEffect,
    EffectBase,
    ExplodeEffect,
    IgniteObjectEffect,
    PushEffect,
)
from trpg.engine.events import (
    CheckRolled,
    DamageDealt,
    ElementTouched,
    EventBase,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExploded,
    SurfaceEntered,
)
from trpg.engine.rules.geometry import XY, chebyshev
from trpg.engine.rules.movement import is_flying
from trpg.engine.state import BattleState
from trpg.engine.triggers import register_trigger
from trpg.shared.types import Element, Surface, UnitId

__all__ = ["Category", "conducting_tiles", "element_capable", "matching_rules", "touch_outcomes"]

type Category = Literal["surface", "object", "unit"]

ALL_CATEGORIES: tuple[Category, ...] = ("surface", "object", "unit")
TILE_CATEGORIES: tuple[Category, ...] = ("surface", "object")
_INTERACTING_CAUSES = ("attack", "effect")


def element_capable(
    rules: Ruleset, element: Element, effect_kind: str, surface: Surface | None = None
) -> bool:
    """``element`` 是否能產生 ``effect_kind`` 效果（互動表的 ``capabilities``）。

    例如 ``element_capable(rules, Element.SHADOW, "create_surface", Surface.DARKNESS)``。
    Phase 2 的技能驗證以此檢查帶元素的效果是否合理。
    """
    return any(
        cap.element is element
        and cap.effect == effect_kind
        and (cap.surface is None or cap.surface is surface)
        for cap in rules.interactions.capabilities
    )


def matching_rules(
    state: BattleState, element: Element, xy: XY, categories: Sequence[Category] = ALL_CATEGORIES
) -> list[InteractionRule]:
    """``element`` 觸及 ``xy`` 時套用的規則（每類對象第一條符合者，依類別順序）。"""
    tile = state.tile(*xy)
    obj = state.object_at(*xy)
    tags = state.ruleset.object_def(obj.kind).tags if obj is not None else ()
    unit = state.unit_at(*xy)
    chosen: list[InteractionRule] = []
    for category in categories:
        for rule in state.ruleset.interactions.rules:
            if rule.trigger != "element" or rule.element is not element or rule.target != category:
                continue
            if category == "surface" and rule.surface is tile.surface:
                chosen.append(rule)
                break
            if category == "object" and rule.object_tag in tags:
                chosen.append(rule)
                break
            if (
                category == "unit"
                and unit is not None
                and (rule.unit_tag is None or unit.has_tag(rule.unit_tag))
                and (rule.unit_surface is None or rule.unit_surface is tile.surface)
                and not (
                    rule.unit_surface is not None and is_flying(unit)
                )  # 會飛的不受地面表面影響
            ):
                chosen.append(rule)
                break
    return chosen


def conducting_tiles(state: BattleState, start: XY) -> list[XY]:
    """從 ``start`` 出發、四方向相連的導電格（water 表面或 ``conductive`` 物件）。

    依 (y, x) 排序。
    """

    def conducts(xy: XY) -> bool:
        if state.tile(*xy).surface is Surface.WATER:
            return True
        return state.object_has_tag(*xy, "conductive")

    if not conducts(start):
        return []
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nxt in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)):
            if nxt not in seen and state.in_bounds(*nxt) and conducts(nxt):
                seen.add(nxt)
                queue.append(nxt)
    return sorted(seen, key=lambda p: (p[1], p[0]))


def touch_outcomes(
    ctx: Ctx,
    element: Element,
    xy: XY,
    depth: int,
    *,
    source_id: UnitId | None,
    categories: Sequence[Category] = ALL_CATEGORIES,
    direction: tuple[int, int] | None = None,
    push_distance: int = 0,
    damage: int = 0,
    exclude_unit: UnitId | None = None,
) -> list[EffectBase]:
    """``element`` 觸及 ``xy`` 時，依互動表產生的後續效果（``depth`` 為這些效果的深度）。"""
    state = ctx.state
    effects: list[EffectBase] = []
    for rule in matching_rules(state, element, xy, categories):
        for outcome in rule.then:
            effects.extend(
                _outcome_effects(
                    ctx,
                    rule,
                    outcome,
                    element=element,
                    xy=xy,
                    depth=depth,
                    source_id=source_id,
                    direction=direction,
                    push_distance=push_distance,
                    damage=damage,
                    exclude_unit=exclude_unit,
                )
            )
    return effects


def _outcome_effects(  # noqa: PLR0911
    ctx: Ctx,
    rule: InteractionRule,
    outcome: InteractionOutcome,
    *,
    element: Element,
    xy: XY,
    depth: int,
    source_id: UnitId | None,
    direction: tuple[int, int] | None,
    push_distance: int,
    damage: int,
    exclude_unit: UnitId | None,
) -> list[EffectBase]:
    state = ctx.state
    obj = state.object_at(*xy)
    cause = f"interaction:{rule.id}"
    op = outcome.op
    if op == "set_surface":
        assert outcome.surface is not None
        return [
            CreateSurfaceEffect(
                depth=depth,
                source_id=source_id,
                pos=xy,
                surface=outcome.surface,
                react=False,
                cause=cause,
            )
        ]
    if op == "ignite_object" and obj is not None:
        return [
            IgniteObjectEffect(depth=depth, source_id=source_id, object_id=obj.id),
            CreateSurfaceEffect(
                depth=depth,
                source_id=source_id,
                pos=xy,
                surface=Surface.FIRE,
                react=False,
                cause=cause,
            ),
        ]
    if op == "explode" and obj is not None:
        return [ExplodeEffect(depth=depth, source_id=source_id, object_id=obj.id)]
    if op in ("destroy_object", "fill_chasm") and obj is not None:
        return [
            DestroyObjectEffect(
                depth=depth,
                source_id=source_id,
                object_id=obj.id,
                cause="filled" if op == "fill_chasm" else "effect",
                set_terrain=outcome.terrain if op == "fill_chasm" else None,
            )
        ]
    if op == "conduct":
        amount = max(damage * outcome.damage_permille // 1000, outcome.min_damage)
        targets = [
            unit
            for tile in conducting_tiles(state, xy)
            if (unit := state.unit_at(*tile)) is not None and unit.id != exclude_unit
        ]
        return [
            DamageEffect(
                depth=depth,
                source_id=source_id,
                target_id=unit.id,
                cause="conduct",
                element=element,
                flat=amount,
                apply_weather=False,  # 基準傷害已含天氣修正；元素修正由每個單位各自套用
            )
            for unit in targets
        ]
    if op == "push" and direction is not None and push_distance > 0:
        if rule.target == "object" and obj is not None:
            return [
                PushEffect(
                    depth=depth,
                    source_id=source_id,
                    object_id=obj.id,
                    direction=direction,
                    distance=push_distance,
                )
            ]
        unit = state.unit_at(*xy)
        if rule.target == "unit" and unit is not None:
            return [
                PushEffect(
                    depth=depth,
                    source_id=source_id,
                    target_id=unit.id,
                    direction=direction,
                    distance=push_distance,
                )
            ]
    if op == "apply_status" and outcome.status is not None:
        unit = state.unit_at(*xy)
        if rule.target == "unit" and unit is not None:
            return [
                ApplyStatusEffect(
                    depth=depth,
                    source_id=source_id,
                    target_id=unit.id,
                    status_id=outcome.status,
                    duration=outcome.duration,
                )
            ]
    if op == "spread_surface" and direction is not None:
        assert outcome.surface is not None
        nxt = (xy[0] + direction[0], xy[1] + direction[1])
        if state.in_bounds(*nxt):
            return [
                CreateSurfaceEffect(
                    depth=depth, source_id=source_id, pos=nxt, surface=outcome.surface, cause=cause
                )
            ]
    return []


# ---------------------------------------------------------------------------
# 觸發
# ---------------------------------------------------------------------------


@register_trigger("damage_dealt")
def _on_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, DamageDealt)
    if event.cause not in _INTERACTING_CAUSES or event.pos is None:
        return []
    return touch_outcomes(
        ctx,
        event.element,
        (event.pos.x, event.pos.y),
        depth,
        source_id=event.source_id,
        # 單位類規則（冰霜凍住水上的單位，2H-1）也要看；風推單位需要方向與距離，
        # 傷害事件沒有，不會觸發
        categories=ALL_CATEGORIES,
        # 雷電擴散的基準：主要目標套用自身抗性與格擋之前的傷害（Phase 1C 決定 #3）
        damage=event.amount if event.base_amount is None else event.base_amount,
        exclude_unit=event.target_id,
    )


@register_trigger("object_damaged")
def _on_object_damaged(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ObjectDamaged)
    effects: list[EffectBase] = []
    xy = (event.pos.x, event.pos.y)
    if event.cause in _INTERACTING_CAUSES:
        effects.extend(
            touch_outcomes(
                ctx,
                event.element,
                xy,
                depth,
                source_id=event.source_id,
                categories=TILE_CATEGORIES,
                damage=event.amount,
            )
        )
    obj = ctx.state.objects[event.object_id]
    breakable = "breakable" in ctx.rules.object_def(obj.kind).tags
    if event.hp_after <= 0 and breakable and not obj.destroyed:
        effects.append(
            DestroyObjectEffect(
                depth=depth, source_id=event.source_id, object_id=obj.id, cause="damage"
            )
        )
    return effects


@register_trigger("object_destroyed")
def _on_object_destroyed(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """被傷害打破或被丟出去摔破（不是被引爆）的物件若定義了 ``spill``，在該格與四方向相鄰格產生
    表面（漏油）。"""
    assert isinstance(event, ObjectDestroyed)
    if event.cause not in ("damage", "hurled"):
        return []
    spill = ctx.rules.object_def(event.kind).spill
    if spill is None:
        return []
    x, y = event.pos.x, event.pos.y
    tiles = [(x, y), (x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]
    return [
        CreateSurfaceEffect(
            depth=depth, pos=xy, surface=spill.surface, cause=f"spill:{event.object_id}"
        )
        for xy in tiles
        if ctx.state.in_bounds(*xy)
    ]


@register_trigger("object_exploded")
def _on_explosion(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ObjectExploded)
    state = ctx.state
    obj = state.objects[event.object_id]
    explosion = ctx.rules.object_def(obj.kind).explosion
    assert explosion is not None
    center = (event.pos.x, event.pos.y)
    tiles = sorted(
        (
            (x, y)
            for y in range(center[1] - event.radius, center[1] + event.radius + 1)
            for x in range(center[0] - event.radius, center[0] + event.radius + 1)
            if state.in_bounds(x, y) and chebyshev(center, (x, y)) <= event.radius
        ),
        key=lambda p: (p[1], p[0]),
    )
    effects: list[EffectBase] = []
    for xy in tiles:
        unit = state.unit_at(*xy)
        if unit is not None:
            effects.append(
                DamageEffect(
                    depth=depth,
                    source_id=event.source_id,
                    target_id=unit.id,
                    cause="explosion",
                    element=explosion.element,
                    dice=explosion.dice,
                    flat=explosion.flat,
                )
            )
        effects.extend(
            touch_outcomes(
                ctx,
                explosion.element,
                xy,
                depth,
                source_id=event.source_id,
                categories=TILE_CATEGORIES,
            )
        )
    return effects


@register_trigger("element_touched")
def _on_touch(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ElementTouched)
    categories: tuple[Category, ...] = ALL_CATEGORIES
    if event.objects_only:
        categories = ("object",)
    elif event.tile_only:
        categories = TILE_CATEGORIES
    return touch_outcomes(
        ctx,
        event.element,
        (event.pos.x, event.pos.y),
        depth,
        source_id=event.source_id,
        categories=categories,
        direction=event.direction,
        push_distance=event.push_distance,
        damage=event.damage,
    )


@register_trigger("surface_entered")
def _on_surface_entered(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, SurfaceEntered)
    on_enter = ctx.rules.surface_def(event.surface).on_enter
    if on_enter is None or on_enter.apply_status is None:
        return []
    return [
        ApplyStatusEffect(depth=depth, target_id=event.unit_id, status_id=on_enter.apply_status)
    ]


@register_trigger("check_rolled")
def _on_check(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, CheckRolled)
    if event.success or event.fail_status is None:
        return []
    return [ApplyStatusEffect(depth=depth, target_id=event.unit_id, status_id=event.fail_status)]
