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
  （``followup_cancelled``）；**法術型**（``category: spell``）的蓄力被沉默（``blocks_spells``）也
  取消（``silenced``，Phase 5A-M1b；武器技型與定向蓄力不吃沉默）；施放另一個延遲段時舊的取消
  （``replaced``）。
- **落在選定格**（BAL-21a）：``followup.anchor: cast_tile`` 時，施放時第一段選的格子
  （``UseSkill.target_pos``）記在蓄力狀態的 ``StatusInstance.anchor``；預告、釋放都以那格為中心
  （:func:`~trpg.engine.skills.targeting.anchored_area`：不重驗射程與視線，只取地圖內的格子與技能
  條件），施放者移動也不跟著走。命中、抵抗仍以施放者本人計。
- **瞄準預告**（RG-1，#162，``lock_on``）：施放＝瞄準（:func:`charge_lock_on`）——蓄力狀態的
  ``lock_target`` 記住目標，預計範圍是目標當下的格子（跟著目標走）；下回合開始時先照
  :func:`trpg.engine.lock_on.lock_problem` 檢查（倒下、出射程、斷視線、照一般規則選不到的隱蔽
  時落空），再以技能本身結算；目標的隊友擋在中間時改打擋住的人（AF-1，:func:`~trpg.engine.lock_on.lock_victim`，
  先發 ``lock_intercepted``）。瞄準中被近戰命中時取消（``interrupted``）。
- 第二段的結算由 :func:`trpg.engine.skills.casting.run_delayed` 處理（命中、傷害照常；不付
  代價，代價在施放時已付）。
- ``charging`` 是中性、有益的狀態：不會被淨化、驅散或奪取。

**定向蓄力**（Phase 3J-2，6.30 龍的蓄力吐息）：形態的天生武器帶 ``charge`` 時，普攻（``Attack``
的 ``direction``）＝ :func:`start_directed_charge`——``charging`` 狀態的 ``direction`` 記著方向、
``skill_id`` 是 ``form_<形態 id>``；下一個自己的回合開始時，由形態資料組出的吐息技能
（:func:`trpg.content.form_breath.breath_skill`）朝該方向以施放者 **當下** 的位置結算（同延遲段，
:func:`trpg.engine.skills.casting.run_delayed`）。倒下、暈眩、冰凍照樣取消；形態解除時取消
（``form_left``，見 :mod:`trpg.engine.forms`）。預告格（``charge_infos``）與延遲段共用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.skills import CHARGING, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.charge_queries import (
    DELAYED_RELEASE,
    attacked_release,
    charged_skill,
    release_of,
)
from trpg.engine.context import Ctx
from trpg.engine.effects.models import CancelChargeEffect, EffectBase
from trpg.engine.effects.queue import register_effect
from trpg.engine.events import (
    EffectFizzled,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    LockIntercepted,
    StatusApplied,
    UnitDowned,
)
from trpg.engine.lock_on import LOCK_BLOCKED, lock_pick, lock_problem, lock_victim
from trpg.engine.rules.facing import face_toward
from trpg.engine.rules.forms import breath_of, is_spell_for_silence
from trpg.engine.rules.statuses import skip_turn_status
from trpg.engine.skill_triggers import register_fired_resolver
from trpg.engine.skills.casting import run_delayed
from trpg.engine.skills.targeting import SkillArea, anchored_area, checked_area
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.engine.trigger_types import Fired
from trpg.engine.triggers import register_trigger
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, UnitId

__all__ = [
    "DELAYED_RELEASE",
    "ChargeInfo",
    "anchor_of",
    "attacked_release",
    "charge",
    "charge_infos",
    "charge_lock_on",
    "delayed_selection",
    "release_at_turn_start",
    "resolve_attacked_release",
    "start_directed_charge",
]


def _second(skill: SkillDef) -> SkillDef:
    """第二段的技能：複合技能的第二段；定向蓄力的吐息技能本身就是第二段。"""
    return skill if skill.followup is None else (skill.followup_skill() or skill)


def anchor_of(skill: SkillDef, action: UseSkill) -> Pos | None:
    """施放 ``skill``（``action``）時要記住的落點：``followup.anchor: cast_tile`` 時是第一段選的格子
    （BAL-21a），其他為 ``None``。"""
    follow = skill.followup
    if follow is None or follow.anchor is None:
        return None
    assert action.target_pos is not None  # ANCHOR_FIRST_SHAPES 都要選格，合法性已驗過
    return action.target_pos


def delayed_selection(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    direction: str | None = None,
    anchor: Pos | None = None,
) -> tuple[UseSkill, SkillArea] | None:
    """延遲段以施放者目前的位置為中心的選取與影響範圍（定向蓄力再加方向）；``anchor``（BAL-21a）
    有值時改以那格為中心（:func:`~trpg.engine.skills.targeting.anchored_area`：不重驗射程與視線）。
    不合法時為 ``None``。"""
    follow = _second(skill)
    pick = UseSkill(unit_id=caster.id, skill_id=skill.id)
    targeting = state.ruleset.shape_def(follow.shape.type).targeting
    if anchor is not None:
        if targeting == "tile":
            pick = pick.model_copy(update={"target_pos": anchor})
        try:
            return pick, anchored_area(state, caster, follow, (anchor.x, anchor.y))
        except IllegalActionError:
            return None
    if targeting == "tile":
        pick = pick.model_copy(update={"target_pos": Pos(x=caster.xy[0], y=caster.xy[1])})
    elif targeting == "direction" and direction is not None:
        pick = pick.model_copy(update={"direction": direction})
    try:
        return pick, checked_area(state, caster, follow, pick)
    except IllegalActionError:
        return None


def _tiles(area: SkillArea | None) -> tuple[Pos, ...]:
    return () if area is None else tuple(Pos(x=x, y=y) for x, y in area.tiles)


def charge(ctx: Ctx, caster: UnitState, skill: SkillDef, action: UseSkill) -> None:
    """第一段結算完：施放者還站著、沒被控制時開始蓄力（取代舊的延遲段）；否則第二段不結算
    （``effect_fizzled``：``followup_caster_down``）。``followup.anchor: cast_tile``（BAL-21a）時
    把 ``action.target_pos`` 記在蓄力狀態上，預計範圍以那格為中心。"""
    assert skill.followup is not None and skill.followup.release is not None
    pos = Pos(x=caster.xy[0], y=caster.xy[1])
    if not caster.alive or skip_turn_status(ctx.rules, caster) is not None:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_caster_down")
        return
    old = caster.get_status(CHARGING)
    if old is not None:
        _drop(ctx, caster, old, "replaced")
    anchor = anchor_of(skill, action)
    caster.statuses.append(
        StatusInstance(CHARGING, remaining=1, source_id=caster.id, skill_id=skill.id, anchor=anchor)
    )
    found = delayed_selection(ctx.state, caster, skill, anchor=anchor)
    ctx.emit(
        FollowupCharged,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        release=skill.followup.release,
        pos=pos if anchor is None else anchor,
        tiles=_tiles(None if found is None else found[1]),
        anchored=anchor is not None,
    )


def charge_lock_on(ctx: Ctx, caster: UnitState, skill: SkillDef, target: UnitState) -> None:
    """瞄準預告（RG-1）：``caster`` 以 ``skill`` 瞄準 ``target``（合法性與代價由呼叫端先處理）。
    已經在蓄力時取代舊的（``replaced``）；施放者面向目標。"""
    old = charged_skill(ctx.state, caster)
    if old is not None:
        _drop(ctx, caster, old[0], "replaced", old[1])
    caster.statuses = [s for s in caster.statuses if s.status_id != CHARGING]
    caster.statuses.append(
        StatusInstance(
            CHARGING, remaining=1, source_id=caster.id, skill_id=skill.id, lock_target=target.id
        )
    )
    face_toward(caster, target.xy)
    ctx.emit(
        FollowupCharged,
        unit_id=caster.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        release="next_turn",
        pos=target.pos,
        tiles=(target.pos,),
        lock_target_id=target.id,
    )


def start_directed_charge(ctx: Ctx, unit: UnitState, direction: str) -> None:
    """定向蓄力：``unit`` 朝 ``direction`` 開始蓄力吐息（形態天生武器帶 ``charge``，合法性與 AP 由
    呼叫端先檢查）。已經在蓄力時取代舊的（``replaced``）。"""
    skill = breath_of(ctx.rules, unit)
    assert skill is not None and unit.form is not None
    old = charged_skill(ctx.state, unit)
    if old is not None:
        _drop(ctx, unit, old[0], "replaced", old[1])
    unit.statuses = [s for s in unit.statuses if s.status_id != CHARGING]
    unit.statuses.append(
        StatusInstance(
            CHARGING,
            remaining=1,
            source_id=unit.id,
            skill_id=f"form_{unit.form.form_id}",
            direction=direction,
        )
    )
    found = delayed_selection(ctx.state, unit, skill, direction)
    ctx.emit(
        FollowupCharged,
        unit_id=unit.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        release="next_turn",
        pos=Pos(x=unit.xy[0], y=unit.xy[1]),
        tiles=_tiles(None if found is None else found[1]),
        direction=direction,
    )


def _drop(
    ctx: Ctx,
    unit: UnitState,
    status: StatusInstance,
    reason: Literal[
        "downed",
        "controlled",
        "silenced",
        "expired",
        "replaced",
        "form_left",
        "part_broken",
        "interrupted",
    ],
    skill: SkillDef | None = None,
) -> None:
    unit.statuses = [s for s in unit.statuses if s.status_id != CHARGING]
    skill = skill or ctx.rules.skill_def(status.skill_id or "")
    ctx.emit(
        FollowupCancelled,
        unit_id=unit.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        reason=reason,
    )


def _release(ctx: Ctx, unit: UnitState, skill: SkillDef, status: StatusInstance) -> None:
    """移除蓄力並結算第二段（以當下位置、或記住的落點推算不出選取時 ``followup_no_target``）。"""
    unit.statuses = [s for s in unit.statuses if s.status_id != CHARGING]
    if status.lock_target is not None:
        _release_lock(ctx, unit, skill, status.lock_target)
        return
    found = delayed_selection(ctx.state, unit, skill, status.direction, status.anchor)
    if found is None:
        pos = Pos(x=unit.xy[0], y=unit.xy[1]) if status.anchor is None else status.anchor
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason="followup_no_target")
        return
    run_delayed(ctx, unit, skill, *found)


def _release_lock(ctx: Ctx, unit: UnitState, skill: SkillDef, target_id: str) -> None:
    """瞄準預告射出（RG-1）：:func:`~trpg.engine.lock_on.lock_problem` 不成立時落空
    （``effect_fizzled``，原因是落空的種類，``pos`` 是目標的格子；目標不在場上時是施放者的格子）；
    否則以技能本身結算（同延遲段，不再付代價）。目標的隊友擋在中間時改打擋住的人（AF-1，先發
    ``lock_intercepted``）；擋住的人本身選不到時落空（``lock_on_blocked``）。"""
    target = ctx.state.units.get(UnitId(target_id))
    problem = lock_problem(ctx.state, unit, skill, target)
    if problem is not None:
        pos = unit.pos if target is None else target.pos
        ctx.emit(EffectFizzled, effect_kind="followup", pos=pos, reason=problem)
        return
    assert target is not None
    victim = lock_victim(ctx.state, unit, skill, target)
    if victim is None:
        ctx.emit(EffectFizzled, effect_kind="followup", pos=target.pos, reason=LOCK_BLOCKED)
        return
    if victim is not target:
        ctx.emit(
            LockIntercepted,
            unit_id=unit.id,
            skill_id=skill.id,
            name_zh=skill.name_zh,
            target_id=target.id,
            blocker_id=victim.id,
        )
    found = lock_pick(ctx.state, unit, skill, victim)
    assert found is not None  # lock_problem／lock_victim 已檢查過
    run_delayed(ctx, unit, skill, *found)


def release_at_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """施放者回合開始：``next_turn`` 的延遲段釋放；``attacked`` 的沒被攻擊，失效。"""
    charged = charged_skill(ctx.state, unit)
    if charged is None:
        return
    status, skill = charged
    if skip_turn_status(ctx.rules, unit) is not None:
        _drop(ctx, unit, status, "controlled", skill)
    elif release_of(skill) == "attacked":
        _drop(ctx, unit, status, "expired", skill)
    else:
        _release(ctx, unit, skill, status)


def resolve_attacked_release(ctx: Ctx, unit: UnitState, skill_id: str) -> None:
    """被攻擊、那次攻擊結算完：蓄力還在（同一次攻擊的第二個目標判定、或已經釋放過時不在）而且
    施放者還站著，就釋放。"""
    charged = charged_skill(ctx.state, unit)
    if charged is None or charged[1].id != skill_id or not unit.alive:
        return
    if skip_turn_status(ctx.rules, unit) is not None:
        _drop(ctx, unit, charged[0], "controlled", charged[1])
        return
    _release(ctx, unit, charged[1], charged[0])


@dataclass(frozen=True, slots=True)
class ChargeInfo:
    """等待中的延遲段（網頁、環境預告用）：以施放者目前位置推算的預計範圍；``anchored``（BAL-21a）
    時 ``pos`` 是施放時選的格子、範圍以它為中心。"""

    unit_id: str
    skill_id: str
    name_zh: str
    release: str
    remaining: int
    pos: Pos
    tiles: tuple[Pos, ...]
    direction: str | None = None
    anchored: bool = False
    lock_target_id: UnitId | None = None
    """瞄準預告（RG-1）瞄準的單位：``pos``／``tiles`` 是他目前的格子。"""


def _lock_info(
    state: BattleState, unit: UnitState, status: StatusInstance, skill: SkillDef
) -> ChargeInfo:
    """瞄準中的單位的預告：預計範圍是目標目前的格子（目標已經不在場上時是空的）。"""
    assert status.lock_target is not None
    target = state.units.get(status.lock_target)
    alive = target is not None and target.alive
    return ChargeInfo(
        unit_id=unit.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        release=release_of(skill),
        remaining=status.remaining or 1,
        pos=target.pos if target is not None and alive else unit.pos,
        tiles=(target.pos,) if target is not None and alive else (),
        lock_target_id=status.lock_target,
    )


def charge_infos(state: BattleState) -> tuple[ChargeInfo, ...]:
    """所有帶著蓄力的存活單位（依單位 ID）。"""
    found: list[ChargeInfo] = []
    for unit in state.units_sorted():
        charged = charged_skill(state, unit) if unit.alive else None
        if charged is None:
            continue
        status, skill = charged
        if status.lock_target is not None:
            found.append(_lock_info(state, unit, status, skill))
            continue
        selection = delayed_selection(state, unit, skill, status.direction, status.anchor)
        found.append(
            ChargeInfo(
                unit_id=unit.id,
                skill_id=skill.id,
                name_zh=skill.name_zh,
                release=release_of(skill),
                remaining=status.remaining or 1,
                pos=unit.pos if status.anchor is None else status.anchor,
                tiles=_tiles(None if selection is None else selection[1]),
                direction=status.direction,
                anchored=status.anchor is not None,
            )
        )
    return tuple(found)


def silence_breaks_charge(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 正在蓄力的是法術型招式（沉默會打斷）；武器技型與定向蓄力（吐息）不吃沉默。"""
    charged = charged_skill(state, unit)
    if charged is None or charged[0].direction is not None:
        return False
    return is_spell_for_silence(state.ruleset, charged[1])


@register_effect("cancel_charge")
def _cancel_charge(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, CancelChargeEffect)
    unit = ctx.state.units[effect.unit_id]
    charged = charged_skill(ctx.state, unit)
    if charged is None:
        return []
    start = len(ctx.events)
    _drop(ctx, unit, charged[0], effect.reason, charged[1])
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
    definition = ctx.rules.status_def(event.status_id)
    if definition.skip_turn:
        return [CancelChargeEffect(depth=depth, unit_id=unit.id, reason="controlled")]
    if definition.blocks_spells and silence_breaks_charge(ctx.state, unit):
        return [CancelChargeEffect(depth=depth, unit_id=unit.id, reason="silenced")]
    return []


@register_fired_resolver(DELAYED_RELEASE)
def _release_fired(ctx: Ctx, fired: Fired) -> None:
    """被動觸發結算到 ``delayed_release``（持有者存在、深度檢查由 ``skill_triggers`` 先做）。"""
    resolve_attacked_release(ctx, ctx.state.units[fired.owner_id], fired.skill_id)
