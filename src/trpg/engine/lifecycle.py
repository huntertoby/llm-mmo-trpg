"""單位離開戰場（倒下、撤離、召喚物消失）、建立單位與先攻順序維護（效果處理器與回合流程共用）。"""

from __future__ import annotations

from trpg.content.battle import ReactionRule, ReactionWhen, UnitTemplate, WeaponDef
from trpg.content.equipment import Loadout
from trpg.content.library import Ruleset
from trpg.content.skills import GRANT_SKILL
from trpg.engine.context import Ctx
from trpg.engine.events import (
    EventBase,
    StatusRemoved,
    SummonExpired,
    SummonExpiryReason,
    SummonModeSet,
    UnitDowned,
    UnitEscaped,
)
from trpg.engine.gear import build_gear, geared_template
from trpg.engine.gear_enhance import geared_weapon
from trpg.engine.gear_reactions import gear_reaction_rules
from trpg.engine.rules.facing import default_facing
from trpg.engine.rules.statuses import is_removed_with_source, stance_status_ids
from trpg.engine.state import Facing, UnitState
from trpg.engine.traps import remove_traps_of
from trpg.engine.zones import remove_caster_zones_of
from trpg.shared.types import Pos, Team, UnitId

__all__ = [
    "default_ai_profile",
    "dismiss_summon",
    "dismiss_summons_of",
    "down_unit",
    "escape_unit",
    "make_unit",
    "retire_focus",
    "summons_of",
]


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
    以它為來源的嘲諷立即解除。生效中的規則改變 ``on_downed_spawn`` 在原地留下分身（3D-6）。"""
    if unit.downed:
        return []
    unit.downed = True
    unit.hp = 0
    order = ctx.state.turn_order
    order_index = order.index(unit.id) if unit.id in order else None
    _remove_from_order(ctx, unit)
    events: list[EventBase] = [
        ctx.emit(UnitDowned, unit_id=unit.id),
        *_drop_stances(ctx, unit),
        *_release_forced_targets(ctx, unit),
        *remove_traps_of(ctx, unit.id),  # 放置者離場，陷阱消失（Phase 2E-3）
        *remove_caster_zones_of(ctx, unit.id),  # 施放者離場，跟隨型區域消失（Phase 3D-5）
        *dismiss_summons_of(ctx, unit, "owner_gone"),  # 召喚者倒下：召喚物一併消失（3D-4a）
        *retire_focus(ctx, unit),  # 集火的目標倒下：召喚物退回跟隨（3-33c）
    ]
    if unit.is_summon:  # 爆裂傀儡被打倒時自爆（Phase 3-33e2a）；延後匯入：召喚匯入本模組
        from trpg.engine.summons import detonate_on_downed  # noqa: PLC0415

        detonate_on_downed(ctx, unit)
    if unit.activations or unit.gear.affixes:  # 規則改變「殘影」：倒下時留下分身（Phase 3D-6）
        # 延後匯入：規則改變模組匯入召喚（召喚匯入本模組）
        from trpg.engine.rule_changes import spawn_on_downed  # noqa: PLC0415

        events += spawn_on_downed(ctx, unit, order_index)
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
        *remove_traps_of(ctx, unit.id),
        *remove_caster_zones_of(ctx, unit.id),
        *dismiss_summons_of(ctx, unit, "owner_gone"),
        *retire_focus(ctx, unit),
    ]
    return events


def summons_of(ctx: Ctx, owner_id: UnitId) -> list[UnitState]:
    """``owner_id`` 仍在戰場上的召喚物，依召喚順序（單位 ID 依建立順序分配）。"""
    return [u for u in ctx.state.units_sorted() if u.owner_id == owner_id and u.alive]


def dismiss_summon(ctx: Ctx, unit: UnitState, reason: SummonExpiryReason) -> list[EventBase]:
    """召喚物消失（Phase 3D-4a）：離開戰場與先攻順序（同倒下：是目前行動者時 ``active_unit``
    變成 ``None``），姿態、以它為來源的嘲諷與恐懼、它的陷阱一併移除。不算倒下（沒有
    ``unit_downed``，不觸發倒下相關的反應與被動）。"""
    if not unit.alive or unit.owner_id is None:
        return []
    unit.dismissed = True
    _remove_from_order(ctx, unit)
    return [
        ctx.emit(
            SummonExpired, unit_id=unit.id, owner_id=unit.owner_id, reason=reason, pos=unit.pos
        ),
        *_drop_stances(ctx, unit),
        *_release_forced_targets(ctx, unit),
        *remove_traps_of(ctx, unit.id),
        *remove_caster_zones_of(ctx, unit.id),
        *retire_focus(ctx, unit),
    ]


def retire_focus(ctx: Ctx, gone: UnitState) -> list[EventBase]:
    """``gone`` 離開戰場（倒下、撤離、消失）：以牠為集火目標的召喚物退回跟隨（Phase 3-33c）。"""
    events: list[EventBase] = []
    for summon in ctx.state.units_sorted():
        if summon.alive and summon.summon_mode == "focus" and summon.summon_target_id == gone.id:
            assert summon.owner_id is not None
            summon.summon_mode = "follow"
            summon.summon_target_id = None
            events.append(
                ctx.emit(
                    SummonModeSet,
                    unit_id=summon.id,
                    owner_id=summon.owner_id,
                    mode="follow",
                    target_id=gone.id,
                    reason="target_gone",
                )
            )
    return events


def dismiss_summons_of(ctx: Ctx, owner: UnitState, reason: SummonExpiryReason) -> list[EventBase]:
    """``owner`` 的全部召喚物消失（依召喚順序）。"""
    events: list[EventBase] = []
    for summon in summons_of(ctx, owner.id):
        events += dismiss_summon(ctx, summon, reason)
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
    auto += _status_reaction_rules(template, rules, covered)
    return auto


def _applies_status(rules: Ruleset, skill_id: str, status_id: str, depth: int = 0) -> bool:
    """技能（或它暫時給出的技能）會施加 ``status_id``（內建反應的 ``requires_status``）。"""
    skill = rules.skill_def(skill_id)
    for effect in skill.effects:
        if effect.type == "apply_status" and effect.status == status_id:
            return True
        granted = effect.skill if effect.type == GRANT_SKILL and depth < 1 else None
        if granted is not None and _applies_status(rules, granted, status_id, depth + 1):
            return True
    return False


def _status_reaction_rules(
    template: UnitTemplate, rules: Ruleset, covered: set[str]
) -> list[ReactionRule]:
    """範本裝備了會施加某狀態的技能，而內建反應需要該狀態（``requires_status``，例如監視射擊
    ``overwatch_shot`` 需要 ``overwatch``；Phase 3D-8c）時，自動加上一條 ``auto`` 規則。"""
    auto: list[ReactionRule] = []
    for definition in rules.reactions.reactions:
        status_id = definition.requires_status
        if status_id is None or definition.id in covered:
            continue
        if any(_applies_status(rules, sid, status_id) for sid in sorted(template.skills)):
            auto.append(
                ReactionRule(reaction=definition.id, when=ReactionWhen(event=definition.events[0]))
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
    facing: Facing | None = None,
    equipment: Loadout | None = None,
) -> UnitState:
    """由範本建立戰鬥中的單位（開場與戰鬥中產生的單位共用）。``facing`` 省略時我方朝東、敵方
    朝西（Phase 3D-8d）。``equipment``（Phase 3G-G1）：裝備快照；數值類詞條併進範本的屬性、
    最大 HP、抗性與速度（:func:`~trpg.engine.gear.geared_template`）。"""
    gear = build_gear(equipment if equipment is not None else Loadout(), rules.equipment)
    template = geared_template(template, gear, rules)
    weapon = geared_weapon(weapon, gear, rules.equipment)  # 武器特性強化（3G-G2）
    stamina = template.stamina if template.stamina is not None else rules.core.default_stamina
    reactions = (
        template.reactions if template.reactions is not None else rules.reactions.default_rules
    )
    reactions = (*_auto_reaction_rules(template, rules, reactions), *reactions)
    reactions = (*reactions, *gear_reaction_rules(gear, rules, tuple(reactions)))  # 3G-G3b
    max_hp = rules.core.template_max_hp(template)
    return UnitState(
        id=uid,
        template_id=template.id,
        name_zh=name,
        team=team,
        pos=pos,
        hp=max_hp,
        max_hp=max_hp,
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
        level=template.level,
        skill_levels=dict(template.skill_levels),
        ammo=weapon.magazine,
        facing=default_facing(team) if facing is None else facing,
        gear=gear,
    )
