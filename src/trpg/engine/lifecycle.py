"""單位離開戰場（倒下、撤離）、建立單位與先攻順序維護（效果處理器與回合流程共用）。"""

from __future__ import annotations

from trpg.content.battle import ReactionRule, ReactionWhen, UnitTemplate, WeaponDef
from trpg.content.library import Ruleset
from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, StatusRemoved, UnitDowned, UnitEscaped
from trpg.engine.rules.statuses import is_removed_with_source, stance_status_ids
from trpg.engine.state import UnitState
from trpg.engine.traps import remove_traps_of
from trpg.shared.types import Pos, Team, UnitId

__all__ = ["default_ai_profile", "down_unit", "escape_unit", "make_unit"]


def _remove_from_order(ctx: Ctx, unit: UnitState) -> None:
    """立即移出先攻順序。

    若離開的是目前行動者，``active_unit`` 設為 ``None``，``turn_pos`` 保持不變
    （此時指向順序中的下一位），由回合流程接著開始下一位的回合。
    """
    unit.ap = 0
    unit.move_points = 0
    state = ctx.state
    if unit.id in state.turn_order:
        index = state.turn_order.index(unit.id)
        state.turn_order.pop(index)
        if state.active_unit == unit.id:
            state.active_unit = None
        elif index < state.turn_pos:
            state.turn_pos -= 1


def _release_forced_targets(ctx: Ctx, source: UnitState) -> list[EventBase]:
    """來源離場（倒下或撤離）：以它為來源的嘲諷與恐懼狀態立即移除。"""
    events: list[EventBase] = []
    for other in ctx.state.units_sorted():
        lost = [
            s.status_id
            for s in other.statuses
            if s.source_id == source.id
            and is_removed_with_source(ctx.rules.status_def(s.status_id))
        ]
        if not lost:
            continue
        other.statuses = [s for s in other.statuses if s.status_id not in lost]
        events += [
            ctx.emit(StatusRemoved, target_id=other.id, status_id=status_id, reason="source_lost")
            for status_id in lost
        ]
    return events


def down_unit(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """單位倒下（HP ≤ 0）：標記倒下、立即移出先攻順序，產生 ``unit_downed``；
    以它為來源的嘲諷立即解除。"""
    if unit.downed:
        return []
    unit.downed = True
    unit.hp = 0
    _remove_from_order(ctx, unit)
    events: list[EventBase] = [
        ctx.emit(UnitDowned, unit_id=unit.id),
        *_drop_stances(ctx, unit),
        *_release_forced_targets(ctx, unit),
    ]
    remove_traps_of(ctx, unit.id)  # 放置者離場，陷阱消失（Phase 2E-3）
    return events


def _drop_stances(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """倒下或撤離：移除姿態狀態（2E-2）。"""
    stances = stance_status_ids(ctx.rules, unit)
    if not stances:
        return []
    unit.statuses = [s for s in unit.statuses if s.status_id not in stances]
    return [
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="downed")
        for status_id in stances
    ]


def escape_unit(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """單位抵達出口、離開戰場（撤離勝利條件）：移出先攻順序，產生 ``unit_escaped``。"""
    if not unit.alive:
        return []
    unit.escaped = True
    _remove_from_order(ctx, unit)
    events: list[EventBase] = [
        ctx.emit(UnitEscaped, unit_id=unit.id, pos=unit.pos),
        *_drop_stances(ctx, unit),
        *_release_forced_targets(ctx, unit),
    ]
    remove_traps_of(ctx, unit.id)
    return events


def default_ai_profile(template: UnitTemplate, weapon: WeaponDef) -> str:
    """範本未指定行為模式時：遠程武器 ``archer``，其他 ``brute``。"""
    if template.ai_profile is not None:
        return template.ai_profile
    return "brute" if weapon.is_melee else "archer"


def _auto_reaction_rules(
    template: UnitTemplate, rules: Ruleset, written: tuple[ReactionRule, ...]
) -> list[ReactionRule]:
    """範本裝備了反應技、卻沒有為它寫規則時，自動加一條 ``auto`` 規則（排在其他規則之前，
    依技能 ID 排序；Phase 2E-2 4.1）。"""
    covered = {rule.reaction for rule in written}
    auto: list[ReactionRule] = []
    for skill_id in sorted(template.skills):
        skill = rules.skill_def(skill_id)
        if skill.kind == "reaction" and skill.reaction is not None and skill_id not in covered:
            auto.append(
                ReactionRule(reaction=skill_id, when=ReactionWhen(event=skill.reaction.event))
            )
    return auto


def make_unit(
    uid: UnitId,
    *,
    template: UnitTemplate,
    weapon: WeaponDef,
    team: Team,
    pos: Pos,
    name: str,
    rules: Ruleset,
) -> UnitState:
    """由範本建立戰鬥中的單位（開場與戰鬥中產生的單位共用）。"""
    stamina = template.stamina if template.stamina is not None else rules.core.default_stamina
    reactions = (
        template.reactions if template.reactions is not None else rules.reactions.default_rules
    )
    reactions = (*_auto_reaction_rules(template, rules, reactions), *reactions)
    return UnitState(
        id=uid,
        template_id=template.id,
        name_zh=name,
        team=team,
        pos=pos,
        hp=template.max_hp,
        max_hp=template.max_hp,
        attributes=dict(template.attributes),
        speed=template.speed,
        armor_bonus=template.armor_bonus,
        weapon=weapon,
        resist=dict(template.resist),
        element_mods=dict(template.element_mods),
        tags=template.tags,
        stamina=stamina,
        max_stamina=stamina,
        reactions=tuple(reactions),
        ai_profile=default_ai_profile(template, weapon),
        mana=template.max_mana,
        max_mana=template.max_mana,
        skills=template.skills,
    )
