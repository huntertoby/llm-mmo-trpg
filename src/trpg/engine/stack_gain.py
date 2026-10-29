"""層數的自動累積（Phase 3-52，``docs/design/06-技能.md`` 6.32；規則寫在 ``content/stacks.yaml`` 的
``gain``）。

做法與被動、裝備觸發一致：事件發生時 **收集**（:func:`collect_attack`、:func:`collect_damage`、
:func:`collect_downed`、:func:`collect_cast`、:func:`collect_turn_end`）記一筆
:class:`~trpg.engine.skill_triggers.Fired`（``event`` 為 ``stack_gain:<時機>``、``skill_id`` 放層數
ID），等整個技能或攻擊結算完才由 :func:`resolve` 累積——所以終結技消耗層數時，不會把「這一招自己
命中」的那一層算進去。

只有 **身上帶有消耗這種層數的技能** 的單位才會自動累積（:func:`consumes`）；沒有人用得到的層數
不會出現在畫面上，舊戰鬥的紀錄也不受影響。裝備已經有這種層數的充能詞條時，不重複累積。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.equipment import ChargeAffix
from trpg.content.form_breath import BREATH_PREFIX
from trpg.content.library import Ruleset
from trpg.content.skills import CONSUME_STACK, SkillDef
from trpg.content.stacks import GainOn, StackDef
from trpg.engine.events import AttackRolled, DamageDealt, UnitDowned
from trpg.engine.state import UnitState
from trpg.shared.types import Element, UnitId

if TYPE_CHECKING:
    from trpg.engine.context import Ctx
    from trpg.engine.skill_triggers import Fired

__all__ = [
    "STACK_GAIN_PREFIX",
    "collect_attack",
    "collect_cast",
    "collect_damage",
    "collect_downed",
    "collect_turn_end",
    "consumes",
    "resolve",
]

STACK_GAIN_PREFIX = "stack_gain:"
"""``Fired.event`` 的前綴（``stack_gain:<時機>``；``Fired.skill_id`` 為層數 ID）。"""


def _event_skill(rules: Ruleset, skill_id: str) -> SkillDef | None:
    """攻擊事件的技能。形態的蓄力吐息技能由形態資料臨時組出、不登錄在規則包（回傳 ``None``，
    它不是武器技也不消耗層數）；其餘 ID 找不到就是資料錯誤，直接拋 ``KeyError``。"""
    if skill_id.startswith(BREATH_PREFIX):
        return None
    return rules.skill_def(skill_id)


def consumes(rules: Ruleset, unit: UnitState, stack_id: str) -> bool:
    """``unit`` 身上有沒有消耗 ``stack_id`` 的技能（``consume_stack``）。"""
    for skill_id in unit.skills:
        skill = rules.skill_def(skill_id)
        if any(e.type == CONSUME_STACK and e.stack == stack_id for e in skill.effects):
            return True
    return False


def _gaining(rules: Ruleset, on: GainOn, element: Element | None = None) -> list[StackDef]:
    return [
        s for s in rules.stacks.stacks if any(g.when == on and g.element == element for g in s.gain)
    ]


def _eligible(rules: Ruleset, unit: UnitState, stack: StackDef) -> bool:
    """自動累積的持有者：消耗這種層數，且裝備沒有同一種層數的充能詞條。"""
    if not consumes(rules, unit, stack.id):
        return False
    return not any(
        isinstance(g.affix, ChargeAffix) and g.affix.stack == stack.id
        for g in unit.gear.active_affixes()
    )


def _collect(  # noqa: PLR0917
    ctx: Ctx,
    seq: int,
    owner_id: UnitId | None,
    on: GainOn,
    other_id: UnitId | None = None,
    element: Element | None = None,
) -> None:
    from trpg.engine.skill_triggers import Fired  # noqa: PLC0415

    owner = None if owner_id is None else ctx.state.units.get(owner_id)
    if owner is None or not owner.alive:
        return
    rules = ctx.rules
    for stack in _gaining(rules, on, element):
        if _eligible(rules, owner, stack):
            ctx.fired.append(
                Fired(
                    seq,
                    owner.id,
                    stack.id,
                    f"{STACK_GAIN_PREFIX}{on}",
                    other_id,
                    ctx.trigger_depth + 1,
                )
            )


def collect_attack(ctx: Ctx, event: AttackRolled) -> None:
    """命中判定：武器技命中（``weapon_skill_hit``）、普攻命中（``basic_attack_hit``）。"""
    if not event.hit:
        return
    if event.skill_id is None:
        _collect(ctx, event.seq, event.attacker_id, "basic_attack_hit", event.target_id)
        return
    skill = _event_skill(ctx.rules, event.skill_id)
    if skill is not None and skill.category == "weapon":
        _collect(ctx, event.seq, event.attacker_id, "weapon_skill_hit", event.target_id)


def collect_damage(ctx: Ctx, event: DamageDealt) -> None:
    """傷害：受傷（``damaged``）、擊倒（``kill``）、元素攻擊命中（``element_hit``，疊在被命中者）。"""
    if event.amount <= 0:
        return
    _collect(ctx, event.seq, event.target_id, "damaged", event.source_id)
    source = event.source_id
    if source is None or source == event.target_id:
        return
    if event.hp_after <= 0:
        _collect(ctx, event.seq, source, "kill", event.target_id)
    if event.cause == "attack":
        _collect(ctx, event.seq, source, "element_hit", event.target_id, event.element)


def collect_downed(ctx: Ctx, event: UnitDowned) -> None:
    """召喚物被打倒（``summon_downed``）：召喚者累積。"""
    unit = ctx.state.units.get(event.unit_id)
    if unit is not None and unit.owner_id is not None:
        _collect(ctx, event.seq, unit.owner_id, "summon_downed", unit.id)


def collect_cast(ctx: Ctx, caster: UnitState, skill: SkillDef) -> None:
    """施放治療（有 ``heal`` 效果）或神聖技能（標籤或傷害元素）之後（``heal_or_holy_cast``）。"""
    holy = (
        "holy" in skill.tags
        or any(e.type == "heal" for e in skill.effects)
        or any(e.type == "damage" and e.element is Element.HOLY for e in skill.effects)
    )
    if holy:
        _collect(ctx, ctx.state.next_event_seq, caster.id, "heal_or_holy_cast")


def collect_turn_end(ctx: Ctx, unit: UnitState) -> None:
    """回合結束且這回合沒有主動移動（``turn_end_still``）。"""
    if not unit.moved_this_turn:
        _collect(ctx, ctx.state.next_event_seq, unit.id, "turn_end_still")


def resolve(ctx: Ctx, fired: Fired) -> None:
    """結算一筆自動累積（層數疊在持有者自己、或疊在被命中的敵人身上）。"""
    from trpg.engine.stacks import add_stacks  # noqa: PLC0415

    state = ctx.state
    owner = state.units.get(fired.owner_id)
    if state.ended or owner is None or not owner.alive:
        return
    stack = ctx.rules.stack_def(fired.skill_id)
    on = fired.event.removeprefix(STACK_GAIN_PREFIX)
    amount = next(g.amount for g in stack.gain if g.when == on)
    unit = owner
    if stack.owner == "target":
        other = None if fired.other_id is None else state.units.get(fired.other_id)
        if other is None or not other.alive:
            return
        unit = other
    add_stacks(ctx, unit, stack.id, amount, source_id=owner.id)
