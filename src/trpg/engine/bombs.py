"""定時炸彈（Phase 3D-8b，``docs/design/06-技能.md`` 6.18 H）。

``delayed_damage`` 讓命中的敵人帶上狀態 ``time_bomb``（``StatusInstance.remaining`` 是倒數、
``source_id`` 是施放者、``skill_id`` 是技能；炸彈的骰子、元素與半徑取自技能的 ``delayed_damage``
效果）：

- **倒數**：每次環境回合（:func:`tick_bombs`）剩餘 −1，歸零時在攜帶者 **當下的位置** 爆炸。
- **倒下**：攜帶者倒下時（``unit_downed`` 的觸發函式）在倒下的位置立即爆炸（攜帶者已倒下，不算
  受傷者）。
- **移除**：可被淨化；驅散只移除增益（``time_bomb`` 是減益），所以不移除。狀態一旦被移除，炸彈就
  拆除了（沒有別處的紀錄）。
- **爆炸**：``bomb_blast`` 效果發出 ``bomb_exploded``，其觸發函式對半徑（曼哈頓距離）內的所有
  存活單位（敵我不分，含施放者）各結算一次 ``dice ＋ 縮放屬性 × 0.5`` 的傷害（自動命中、不暴擊、沒有
  格擋；縮放屬性取施放者的基礎屬性，不含狀態），並讓每一格被元素觸及一次（表面、物件互動）。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.skills import DELAYED_DAMAGE, TIME_BOMB, EffectSpec
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    BombBlastEffect,
    DamageEffect,
    EffectBase,
    RemoveStatusEffect,
)
from trpg.engine.effects.queue import execute, register_effect
from trpg.engine.events import BombExploded, BombTicked, EventBase, UnitDowned
from trpg.engine.interactions import TILE_CATEGORIES, touch_outcomes
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.scaling import skill_scaling_value
from trpg.engine.skills.shapes import radius_tiles
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.engine.triggers import register_trigger
from trpg.shared.types import Element, Pos

__all__ = ["blast_tiles", "bomb_carriers", "bomb_spec", "tick_bombs"]


def bomb_spec(state: BattleState, skill_id: str) -> EffectSpec:
    """技能的 ``delayed_damage`` 效果（炸彈的骰子、元素、倒數與半徑）。"""
    skill = state.ruleset.skill_def(skill_id)
    return next(e for e in skill.effects if e.type == DELAYED_DAMAGE)


def blast_tiles(state: BattleState, center: Pos, radius: int) -> tuple[XY, ...]:
    """爆炸影響的格子：與 ``center`` 曼哈頓距離不超過 ``radius`` 的格子（依 ``(y, x)`` 排序）。"""
    return radius_tiles(state, (center.x, center.y), radius)


def bomb_carriers(state: BattleState) -> list[tuple[UnitState, StatusInstance]]:
    """身上有定時炸彈的存活單位與炸彈（依單位 ID）。"""
    found: list[tuple[UnitState, StatusInstance]] = []
    for unit in state.living_units():
        status = unit.get_status(TIME_BOMB)
        if status is not None and status.skill_id is not None:
            found.append((unit, status))
    return found


def _detonate(ctx: Ctx, unit: UnitState, status: StatusInstance) -> None:
    """倒數歸零：拆下炸彈（原因 ``expired``）並爆炸。"""
    assert status.skill_id is not None and status.source_id is not None
    execute(
        ctx,
        [
            RemoveStatusEffect(target_id=unit.id, status_id=TIME_BOMB, reason="expired"),
            BombBlastEffect(
                source_id=status.source_id,
                unit_id=unit.id,
                skill_id=status.skill_id,
                cause="timer",
            ),
        ],
    )


def tick_bombs(ctx: Ctx) -> None:
    """環境回合的炸彈倒數（Phase 3D-8b）：每個帶炸彈的存活單位（依單位 ID）剩餘 −1，歸零就爆炸。
    先爆炸的炸彈可能炸倒後面的攜帶者（它在倒下時已經爆炸，之後略過）。"""
    state = ctx.state
    for unit, _ in bomb_carriers(state):
        current = unit.get_status(TIME_BOMB)
        if not unit.alive or current is None or current.remaining is None:
            continue
        remaining = current.remaining - 1
        if remaining <= 0:
            _detonate(ctx, unit, current)
            continue
        unit.statuses = [
            replace(s, remaining=remaining) if s.status_id == TIME_BOMB else s
            for s in unit.statuses
        ]
        spec = bomb_spec(state, current.skill_id or "")
        ctx.emit(
            BombTicked, unit_id=unit.id, remaining=remaining, pos=unit.pos, radius=spec.radius or 0
        )


@register_effect("bomb_blast")
def _bomb_blast(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, BombBlastEffect)
    state = ctx.state
    unit = state.units[effect.unit_id]
    spec = bomb_spec(state, effect.skill_id)
    assert spec.element is not None
    radius = spec.radius or 0
    tiles = blast_tiles(state, unit.pos, radius)
    return [
        ctx.emit(
            BombExploded,
            unit_id=unit.id,
            source_id=effect.source_id or unit.id,
            skill_id=effect.skill_id,
            pos=unit.pos,
            radius=radius,
            element=spec.element,
            cause=effect.cause,
            tiles=tuple(Pos(x=x, y=y) for x, y in tiles),
        )
    ]


@register_trigger("bomb_exploded")
def _bomb_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """爆炸範圍內每個存活單位受傷（依單位 ID），每一格被元素觸及一次（依 ``(y, x)``）。"""
    assert isinstance(event, BombExploded)
    state = ctx.state
    spec = bomb_spec(state, event.skill_id)
    skill = state.ruleset.skill_def(event.skill_id)
    owner = state.units[event.source_id].clone()
    owner.statuses = []  # 縮放屬性取基礎屬性，不含狀態加值
    attr = skill_scaling_value(state.ruleset, owner, skill)
    scaled = attr * ctx.core.spell_attr_multiplier_permille
    tiles = {(p.x, p.y) for p in event.tiles}
    effects: list[EffectBase] = [
        DamageEffect(
            depth=depth,
            source_id=event.source_id,
            target_id=unit.id,
            cause="explosion",
            element=event.element,
            dice=spec.dice,
            scaled_permille=scaled,
            min_damage=ctx.core.min_damage_on_hit,
        )
        for unit in state.units_sorted()
        if unit.alive and unit.xy in tiles
    ]
    if event.element is not Element.PHYSICAL:
        for xy in sorted(tiles, key=lambda p: (p[1], p[0])):
            effects.extend(
                touch_outcomes(
                    ctx,
                    event.element,
                    xy,
                    depth,
                    source_id=event.source_id,
                    categories=TILE_CATEGORIES,
                )
            )
    return effects


@register_trigger("unit_downed")
def _bomb_on_downed(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """攜帶炸彈的單位倒下：在倒下的位置立即爆炸（先拆下狀態，原因 ``downed``）。"""
    assert isinstance(event, UnitDowned)
    unit = ctx.state.units[event.unit_id]
    status = unit.get_status(TIME_BOMB)
    if status is None or status.skill_id is None or status.source_id is None:
        return []
    return [
        RemoveStatusEffect(depth=depth, target_id=unit.id, status_id=TIME_BOMB, reason="downed"),
        BombBlastEffect(
            depth=depth,
            source_id=status.source_id,
            unit_id=unit.id,
            skill_id=status.skill_id,
            cause="downed",
        ),
    ]
