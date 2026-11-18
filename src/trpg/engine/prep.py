"""戰前佈置（SK-3，``docs/design/06-技能.md`` 6.38 第 11 點）。

開戰前（雙方都還沒行動），玩家可以在**我方起始區內**免費放 1 個自己的刻印、陷阱或表面；條件是
裝備著會做這件事的主動技能，放了就算這招用過（照常進冷卻、每場次數 +1）。每場 1 個。

- **開窗**：只有 ``BattleSetup.prep_placement``（網頁的戰鬥工作階段才會設；CLI、模擬、AI 代打都
  沒有）而且主角（我方第一個單位，同 API 的主角）有可放的技能時，:func:`open_prep` 在開場把
  :attr:`BattleState.prep` 設成 :class:`PrepWindow`（主角與起始區）。沒有就是 ``None``，既有戰鬥
  逐字不變。
- **佈置**：動作 :class:`~trpg.engine.actions.Prepare`（``skill_id``＋``target_pos``；兩個都省略＝
  跳過）由 :func:`do_prepare` 結算：不看行動順序（敵人先手時也能在第一個行動之前放）、不花 AP
  與法力；
  放 1 個（陷阱 1 格、符文 1 格、表面 1 格，照技能第一個放置類效果的種類與參數）。
- **關窗**：佈置或跳過之後，或任何其他動作結算時（:func:`trpg.engine.battle.resolve_with`），
  ``prep`` 變回 ``None``。

全程不取亂數。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.skills import SkillDef, weapon_problem
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import CreateSurfaceEffect, InscribeEffect
from trpg.engine.effects.world import surface_allowed
from trpg.engine.events import PrepPlaced, PrepSkipped, SkillCooldownChanged
from trpg.engine.gear.core import gear_cooldown
from trpg.engine.gear.summon import gear_summon_cooldown
from trpg.engine.rules.footprint import giant_at
from trpg.engine.rules.forms import held_weapon
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.landing import LandingBlock, landing_problem
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.skills.conditions import unit_held
from trpg.engine.state import BattleState, PrepWindow, UnitState
from trpg.engine.traps import place_trap
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

__all__ = [
    "PrepKind",
    "PrepOption",
    "do_prepare",
    "open_prep",
    "placement_kind",
    "prep_actor",
    "prep_options",
]

type PrepKind = Literal["trap", "rune", "surface"]

_KIND_OF_EFFECT: dict[str, PrepKind] = {
    "place_trap": "trap",
    "inscribe": "rune",
    "create_surface": "surface",
}


@dataclass(frozen=True, slots=True)
class PrepOption:
    """一招可以佈置的東西：``kind``（陷阱、符文、表面）與起始區內放得下的格子（依 (y, x)）。"""

    skill_id: str
    kind: PrepKind
    tiles: tuple[XY, ...]


def placement_kind(skill: SkillDef) -> PrepKind | None:
    """技能第一個放置類效果（``place_trap``、``inscribe``、``create_surface``）的種類；沒有就
    ``None``。只看主動技能。"""
    if skill.kind != "active":
        return None
    for effect in skill.effects:
        kind = _KIND_OF_EFFECT.get(effect.type)
        if kind == "trap" and skill.trap is None:
            continue
        if kind is not None:
            return kind
    return None


def _skill_problem(state: BattleState, unit: UnitState, skill: SkillDef) -> str | None:
    """這招現在能不能拿來佈置（不看 AP、法力：佈置是免費的）。"""
    if skill.id not in unit.skills:
        return f"沒有裝備這招：{skill.name_zh}"
    if placement_kind(skill) is None:
        return f"這招不會放陷阱、刻印或表面：{skill.name_zh}"
    if unit.cooldowns.get(skill.id, 0) > 0:
        return f"冷卻中：{skill.name_zh}"
    limit = skill.cost.uses_per_battle
    if limit is not None and unit.skill_uses.get(skill.id, 0) >= limit:
        return f"這場的使用次數已用完：{skill.name_zh}"
    if skill.id in unit.sealed_skills or skill.id in unit.sealed_until:
        return f"被封住了：{skill.name_zh}"
    problem = weapon_problem(skill, held_weapon(unit).weapon_class, unit_held(unit))
    return problem


def _site_ok(state: BattleState, kind: PrepKind, xy: XY) -> bool:
    if not state.in_bounds(*xy) or giant_at(state, xy) is not None:
        return False
    if kind == "trap":
        block = landing_problem(state, xy)
        if block in (LandingBlock.OUT_OF_BOUNDS, LandingBlock.NOT_STANDABLE, LandingBlock.OCCUPIED):
            return False
        return not is_deadly(state, xy) and state.trap_at(*xy) is None
    if kind == "rune":
        return is_standable(state, xy)
    return surface_allowed(state, xy)


def _options_for(state: BattleState, unit: UnitState, zone: tuple[XY, ...]) -> list[PrepOption]:
    found: list[PrepOption] = []
    for skill_id in sorted(unit.skills):
        skill = state.ruleset.skill_def(skill_id)
        kind = placement_kind(skill)
        if kind is None or _skill_problem(state, unit, skill) is not None:
            continue
        tiles = tuple(xy for xy in zone if _site_ok(state, kind, xy))
        if tiles:
            found.append(PrepOption(skill_id, kind, tiles))
    return found


def prep_options(state: BattleState) -> tuple[PrepOption, ...]:
    """目前可以佈置的技能（依技能 ID）；窗沒開時是空的。"""
    window = state.prep
    if window is None or state.ended:
        return ()
    unit = state.units.get(window.unit_id)
    if unit is None or not unit.alive:
        return ()
    zone = tuple((p.x, p.y) for p in window.zone)
    return tuple(_options_for(state, unit, zone))


def open_prep(state: BattleState, zone: list[XY]) -> None:
    """開場（:func:`trpg.engine.battle.begin_battle`）：主角（我方第一個單位）有可佈置的技能時開窗。"""
    allies = [u for u in state.units_sorted() if u.team is Team.ALLY and not u.is_summon]
    if not allies:
        return
    hero = allies[0]
    cells = tuple(sorted(dict.fromkeys(zone), key=lambda c: (c[1], c[0])))
    if _options_for(state, hero, cells):
        state.prep = PrepWindow(hero.id, tuple(Pos(x=x, y=y) for x, y in cells))


def prep_actor(state: BattleState, unit_id: str) -> UnitState:
    """``Prepare`` 的合法行動者：窗開著、是窗的主角（不看行動順序）。"""
    window = state.prep
    if window is None:
        raise IllegalActionError("現在不能戰前佈置（雙方已經有人行動，或沒有可放的技能）")
    if unit_id != window.unit_id:
        raise IllegalActionError("只有主角可以戰前佈置")
    return state.units[window.unit_id]


def do_prepare(ctx: Ctx, unit: UnitState, skill_id: str | None, target: Pos | None) -> None:
    """結算一次佈置（或跳過）。不合法時拋 :class:`IllegalActionError`。"""
    state = ctx.state
    if skill_id is None:
        if target is not None:
            raise IllegalActionError("跳過戰前佈置時不能指定格子")
        state.prep = None
        ctx.emit(PrepSkipped, unit_id=unit.id)
        return
    if target is None:
        raise IllegalActionError("戰前佈置要選一格")
    option = next((o for o in prep_options(state) if o.skill_id == skill_id), None)
    if option is None:
        skill = state.ruleset.skill_def(skill_id) if skill_id in unit.skills else None
        why = None if skill is None else _skill_problem(state, unit, skill)
        raise IllegalActionError(why or f"這招不能拿來戰前佈置：{skill_id}")
    xy = (target.x, target.y)
    if xy not in option.tiles:
        raise IllegalActionError(f"只能放在我方起始區內放得下的格子：{xy}")
    skill = ctx.rules.skill_def(skill_id)
    state.prep = None
    ctx.emit(PrepPlaced, unit_id=unit.id, skill_id=skill.id, kind=option.kind, pos=target)
    _place(ctx, unit, skill, option.kind, xy)
    _spend(ctx, unit, skill)


def _place(ctx: Ctx, unit: UnitState, skill: SkillDef, kind: PrepKind, xy: XY) -> None:
    """放 1 個：陷阱照技能的 ``trap``；符文、表面照技能第一個同類效果的參數（表面的持續回合照
    原語：智力的常駐加成照算）。"""
    if kind == "trap":
        place_trap(ctx, unit, skill, xy)
        return
    effect_type = "inscribe" if kind == "rune" else "create_surface"
    spec = next(e for e in skill.effects if e.type == effect_type)
    if kind == "rune":
        execute(
            ctx,
            [
                InscribeEffect(
                    source_id=unit.id,
                    pos=xy,
                    team=unit.team,
                    element=spec.element,
                    tag=spec.tag,
                    duration=spec.duration,
                )
            ],
        )
        return
    assert spec.surface is not None
    duration = spec.duration
    bonus = attribute_perk(ctx.rules, unit, "surface_duration")
    if bonus:
        base = duration if duration is not None else ctx.rules.surface_def(spec.surface).duration
        duration = None if base is None else base + bonus
    execute(
        ctx,
        [
            CreateSurfaceEffect(
                source_id=unit.id,
                pos=xy,
                surface=spec.surface,
                duration=duration,
                team=unit.team,
                magnitude_permille=spec.magnitude_permille or 1000,
            )
        ],
    )


def _spend(ctx: Ctx, unit: UnitState, skill: SkillDef) -> None:
    """「算這招用過一次」：照常進冷卻（裝備的冷卻修正照算）、每場次數 +1；不花 AP、法力、耐力。"""
    if skill.cost.uses_per_battle is not None:
        unit.skill_uses[skill.id] = unit.skill_uses.get(skill.id, 0) + 1
    cooldown = gear_summon_cooldown(unit, skill, gear_cooldown(unit, skill.cost.cooldown))
    if cooldown is not None:
        unit.cooldowns[skill.id] = cooldown
        ctx.emit(SkillCooldownChanged, unit_id=unit.id, skill_id=skill.id, remaining=cooldown)
