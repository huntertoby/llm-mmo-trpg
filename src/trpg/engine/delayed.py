"""延遲段（Phase 3F-4b，``docs/design/06-技能.md`` 6.23 #5）：跨回合的第二段。

施放 ``followup.when: delayed`` 的技能時，第一段照常結算，接著施放者身上帶上狀態 ``charging``
（``StatusInstance.skill_id`` 是技能、``source_id`` 是施放者自己、``remaining`` 固定為 1——「還要
1 回合」），發出 ``followup_charged``（預計範圍以施放者目前的位置推算）。狀態本身就是等待中的
延遲段，所以可以序列化與重播。

- **釋放**：``release: next_turn`` 在施放者下回合開始時（狀態與表面的回合開始效果之後、被動的
  ``on_turn_start`` 之前）以施放者 **當下** 的位置為中心結算第二段；``release: attacked`` 在
  施放者下回合開始之前被敵人攻擊（``attack_rolled``，不論是否命中）時，等那次攻擊結算完（同被動
  觸發，:mod:`trpg.engine.skill_triggers`）才結算——到下回合開始都沒被攻擊就失效（``expired``）。
- **取消**：施放者倒下（``unit_downed``）、被施加 ``skip_turn`` 的狀態（暈眩、冰凍）時立即取消
  （``followup_cancelled``）；施放另一個延遲段時舊的取消（``replaced``）。
- 第二段的結算由 :func:`trpg.engine.skills.interpreter.run_delayed` 處理（命中、傷害照常；不付
  代價，代價在施放時已付）。
- ``charging`` 是中性、有益的狀態：不會被淨化、驅散或奪取。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.skills import CHARGING, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.context import Ctx
from trpg.engine.effects.models import CancelChargeEffect, EffectBase
from trpg.engine.effects.queue import register_effect
from trpg.engine.events import (
    AttackRolled,
    EffectFizzled,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    StatusApplied,
    UnitDowned,
)
from trpg.engine.rules.statuses import skip_turn_status
from trpg.engine.skills.targeting import SkillArea, checked_area
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.engine.triggers import register_trigger
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos

__all__ = [
    "DELAYED_RELEASE",
    "ChargeInfo",
    "attacked_release",
    "charge",
    "charge_infos",
    "delayed_selection",
    "release_at_turn_start",
    "resolve_attacked_release",
]

DELAYED_RELEASE = "delayed_release"
"""``skill_triggers.Fired.event``：被攻擊才釋放的延遲段（等那次攻擊結算完才結算）。"""


def _second(skill: SkillDef) -> SkillDef:
    follow = skill.followup_skill()
    assert follow is not None
    return follow


def delayed_selection(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> tuple[UseSkill, SkillArea] | None:
    """延遲段以施放者目前的位置為中心的選取與影響範圍；不合法時為 ``None``。"""
    follow = _second(skill)
    pick = UseSkill(unit_id=caster.id, skill_id=skill.id)
    if state.ruleset.shape_def(follow.shape.type).targeting == "tile":
        pick = pick.model_copy(update={"target_pos": Pos(x=caster.xy[0], y=caster.xy[1])})
    try:
        return pick, checked_area(state, caster, follow, pick)
    except IllegalActionError:
        return None


def _tiles(area: SkillArea | None) -> tuple[Pos, ...]:
    return () if area is None else tuple(Pos(x=x, y=y) for x, y in area.tiles)


def charge(ctx: Ctx, caster: UnitState, skill: SkillDef) -> None:
    """第一段結算完：施放者還站著、沒被控制時開始蓄力（取代舊的延遲段）；否則第二段不結算
    （``effect_fizzled``：``followup_caster_down``）。"""
    assert skill.followup is not None and skill.followup.release is not None
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if not caster.alive or skip_turn_status(ctx.rules, caster) is not None:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_caster_down")
        return
    old = caster.get_status(CHARGING)
    if old is not None:
        _drop(ctx, caster, old, "replaced")
    caster.statuses.append(
        StatusInstance(CHARGING, remaining=1, source_id=caster.id, skill_id=skill.id)
    )
    found = delayed_selection(ctx.state, caster, skill)
    ctx.emit(
        FollowupCharged,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        release=skill.followup.release,
        pos=pos,
        tiles=_tiles(None if found is None else found[1]),
    )


def _drop(ctx: Ctx, unit: UnitState, status: StatusInstance, reason: str) -> None:
    unit.statuses = [s for s in unit.statuses if s.status_id != CHARGING]
    skill = ctx.rules.skill_def(status.skill_id or "")
    ctx.emit(
        FollowupCancelled,
        unit_id=unit.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        reason=reason,
    )


def _charged_skill(state: BattleState, unit: UnitState) -> tuple[StatusInstance, SkillDef] | None:
    status = unit.get_status(CHARGING)
    if status is None or status.skill_id is None:
        return None
    skill = state.ruleset.skill_def(status.skill_id)
    if skill.followup is None or skill.followup.release is None:
        return None
    return status, skill


def _release(ctx: Ctx, unit: UnitState, skill: SkillDef) -> None:
    """移除蓄力並結算第二段（以當下位置推算不出選取時 ``followup_no_target``）。"""
    # 延後匯入：技能解譯器匯入本模組（charge）。
    from trpg.engine.skills.interpreter import run_delayed  # noqa: PLC0415

    unit.statuses = [s for s in unit.statuses if s.status_id != CHARGING]
    found = delayed_selection(ctx.state, unit, skill)
    if found is None:
        pos = Pos(x=unit.xy[0], y=unit.xy[1])
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return
    run_delayed(ctx, unit, skill, *found)


def release_at_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """施放者回合開始：``next_turn`` 的延遲段釋放；``attacked`` 的沒被攻擊，失效。"""
    charged = _charged_skill(ctx.state, unit)
    if charged is None:
        return
    status, skill = charged
    assert skill.followup is not None
    if skip_turn_status(ctx.rules, unit) is not None:
        _drop(ctx, unit, status, "controlled")
    elif skill.followup.release == "attacked":
        _drop(ctx, unit, status, "expired")
    else:
        _release(ctx, unit, skill)


def attacked_release(state: BattleState, event: AttackRolled) -> SkillDef | None:
    """``event`` 讓哪個延遲段釋放：目標帶著 ``release: attacked`` 的蓄力、攻擊者是敵人。"""
    target = state.units.get(event.target_id)
    attacker = state.units.get(event.attacker_id)
    if target is None or attacker is None or attacker.team is target.team or not target.alive:
        return None
    charged = _charged_skill(state, target)
    if charged is None:
        return None
    skill = charged[1]
    assert skill.followup is not None
    return skill if skill.followup.release == "attacked" else None


def resolve_attacked_release(ctx: Ctx, unit: UnitState, skill_id: str) -> None:
    """被攻擊、那次攻擊結算完：蓄力還在（同一次攻擊的第二個目標判定、或已經釋放過時不在）而且
    施放者還站著，就釋放。"""
    charged = _charged_skill(ctx.state, unit)
    if charged is None or charged[1].id != skill_id or not unit.alive:
        return
    if skip_turn_status(ctx.rules, unit) is not None:
        _drop(ctx, unit, charged[0], "controlled")
        return
    _release(ctx, unit, charged[1])


@dataclass(frozen=True, slots=True)
class ChargeInfo:
    """等待中的延遲段（網頁、環境預告用）：以施放者目前位置推算的預計範圍。"""

    unit_id: str
    skill_id: str
    name_zh: str
    release: str
    remaining: int
    pos: Pos
    tiles: tuple[Pos, ...]


def charge_infos(state: BattleState) -> tuple[ChargeInfo, ...]:
    """所有帶著蓄力的存活單位（依單位 ID）。"""
    found: list[ChargeInfo] = []
    for unit in state.units_sorted():
        charged = _charged_skill(state, unit) if unit.alive else None
        if charged is None:
            continue
        status, skill = charged
        assert skill.followup is not None and skill.followup.release is not None
        selection = delayed_selection(state, unit, skill)
        found.append(
            ChargeInfo(
                unit_id=unit.id,
                skill_id=skill.id,
                name_zh=skill.name_zh,
                release=skill.followup.release,
                remaining=status.remaining or 1,
                pos=unit.pos,
                tiles=_tiles(None if selection is None else selection[1]),
            )
        )
    return tuple(found)


@register_effect("cancel_charge")
def _cancel_charge(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, CancelChargeEffect)
    unit = ctx.state.units[effect.unit_id]
    status = unit.get_status(CHARGING)
    if status is None or status.skill_id is None:
        return []
    start = len(ctx.events)
    _drop(ctx, unit, status, effect.reason)
    return ctx.events[start:]


@register_trigger("unit_downed")
def _cancel_on_downed(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, UnitDowned)
    if not ctx.state.units[event.unit_id].has_status(CHARGING):
        return []
    return [CancelChargeEffect(depth=depth, unit_id=event.unit_id, reason="downed")]


@register_trigger("status_applied")
def _cancel_on_control(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, StatusApplied)
    unit = ctx.state.units.get(event.target_id)
    if unit is None or not unit.has_status(CHARGING):
        return []
    if not ctx.rules.status_def(event.status_id).skip_turn:
        return []
    return [CancelChargeEffect(depth=depth, unit_id=unit.id, reason="controlled")]
