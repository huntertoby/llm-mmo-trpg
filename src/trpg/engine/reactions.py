"""反應規則與暫停點（``docs/專案計畫.md`` 5.2.1、5.9）。

- 單位帶有反應規則（範本的 ``reactions``，預設為 ``reactions.yaml`` 的 ``default_rules``）。
  條件成立時：``auto`` 自動執行；``prompt`` 暫停結算（:class:`PauseForDecision`），由
  ``resolve`` 回傳 ``pending``，玩家以 ``resume`` 回答。
- 每個單位每輪最多反應 ``reactions_per_round`` 次（每輪開始時重設），內建反應與反應技共用。
- 已實作的反應效果：``reduce_damage``（格擋）與 ``basic_attack``（藉機攻擊）。
- 反應技（Phase 2E-2，``kind: reaction``）：規則的 ``reaction`` 是持有者裝備的技能 ID；事件
  ``hit_by_melee``／``hit_by_attack``（被命中、傷害之後）、``enemy_leaves_adjacent``、
  ``ally_hit_adjacent``（相鄰友方被單體攻擊命中、傷害之前；配 ``intercept`` 原語替他擋下）。
  反應技不花 AP，立刻施放一次技能（:func:`trpg.engine.skills.interpreter.use_reaction_skill`）。

普攻的結算（:func:`perform_unit_attack`）也放在這裡，因為格擋會在命中後、傷害前介入，
藉機攻擊本身也是一次普攻。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.battle import ReactionRule
from trpg.content.environment import ReactionDef
from trpg.content.skills import SkillDef
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    AttackIntercepted,
    AttackRolled,
    ReactionDeclined,
    ReactionTriggered,
)
from trpg.engine.results import Pending
from trpg.engine.rules.combat import ForcedOutcome, attack_problem, roll_attack
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.statuses import effective_attribute, skip_turn_status
from trpg.engine.skill_triggers import check_trigger_depth, holding, redirect_fired
from trpg.engine.skills.conditions import skill_condition_met
from trpg.engine.skills.targeting import reaction_problem, reaction_target_problem
from trpg.engine.state import UnitState
from trpg.shared.errors import TrpgError

__all__ = [
    "PauseForDecision",
    "block_multiplier",
    "hit_reactions",
    "is_melee_attack",
    "opportunity_attacks",
    "perform_unit_attack",
    "try_intercept",
]

PERMILLE = 1000


class PauseForDecision(TrpgError):
    """``prompt`` 反應需要玩家決定：中止結算，由 ``resolve`` 轉成 ``pending``。"""

    def __init__(self, pending: Pending) -> None:
        super().__init__(f"等待 {pending.unit_id} 決定是否使用 {pending.reaction}")
        self.pending = pending


def is_melee_attack(ctx: Ctx, attacker: UnitState) -> bool:
    """近戰攻擊：武器射程 ≤ ``melee_height_limit_max_range``（近戰與長柄）。"""
    return attacker.weapon.range <= ctx.core.melee_height_limit_max_range


def _usable(ctx: Ctx, unit: UnitState, rule: ReactionRule) -> ReactionDef | None:
    definition = ctx.rules.reaction_def(rule.reaction)
    if not unit.alive or unit.reactions_used >= ctx.core.reactions_per_round:
        return None
    if skip_turn_status(ctx.rules, unit) is not None:
        return None  # 暈眩中不能執行反應
    if _unless(unit, rule):
        return None
    if unit.stamina < definition.stamina_cost:
        return None
    if definition.requires_melee_weapon and not is_melee_attack(ctx, unit):
        return None
    return definition


def _unless(unit: UnitState, rule: ReactionRule) -> bool:
    unless = rule.unless
    return (
        unless is not None
        and unless.self_stamina_below is not None
        and unit.stamina < unless.self_stamina_below
    )


def _skill_usable(
    ctx: Ctx, unit: UnitState, skill: SkillDef, rule: ReactionRule, trigger: UnitState
) -> bool:
    """反應技目前能不能施放：每輪次數、狀態與代價、目標（射程、致盲）、技能條件，最後才檢查
    觸發深度（超過上限發出 ``trigger_limit_reached``，不付代價、不計次數）。"""
    state = ctx.state
    if unit.reactions_used >= ctx.core.reactions_per_round or _unless(unit, rule):
        return False
    if reaction_problem(state, unit, skill) is not None:
        return False
    if skill.shape.type == "single" and not trigger.alive:
        return False
    if reaction_target_problem(state, unit, skill, trigger) is not None:
        return False
    subject = trigger if skill.shape.type == "single" else unit
    if not skill_condition_met(state, unit, skill, [subject.xy]):
        return False
    depth = ctx.trigger_depth + 1
    return check_trigger_depth(ctx, unit.id, skill.id, depth)


def _decide(ctx: Ctx, unit: UnitState, rule: ReactionRule, trigger: UnitState) -> bool:
    if rule.mode == "auto":
        return True
    if ctx.preview is not None:
        ctx.mark_branch()
        return ctx.preview == "max"
    if ctx.decisions:
        return ctx.decisions.pop(0)
    raise PauseForDecision(
        Pending(
            kind="reaction", unit_id=unit.id, reaction=rule.reaction, trigger_unit_id=trigger.id
        )
    )


def _use(ctx: Ctx, unit: UnitState, picked: ReactionDef | SkillDef, trigger: UnitState) -> None:
    unit.reactions_used += 1
    cost = picked.stamina_cost if isinstance(picked, ReactionDef) else 0
    unit.stamina -= cost
    ctx.emit(
        ReactionTriggered,
        unit_id=unit.id,
        reaction=picked.id,
        trigger_unit_id=trigger.id,
        stamina_spent=cost,
    )


def _candidate(  # noqa: PLR0917
    ctx: Ctx,
    unit: UnitState,
    rule: ReactionRule,
    trigger: UnitState,
    effect: str | None,
    skills: bool,
) -> ReactionDef | SkillDef | None:
    """``rule`` 目前能不能用：反應技（``skills``）或效果為 ``effect`` 的內建反應。"""
    if rule.reaction in unit.skills:
        if not skills:
            return None
        skill = ctx.rules.skill_def(rule.reaction)
        return skill if _skill_usable(ctx, unit, skill, rule, trigger) else None
    definition = _usable(ctx, unit, rule)
    if definition is None or effect is None or definition.effect != effect:
        return None
    if effect == "basic_attack" and attack_problem(ctx.state, unit, trigger) is not None:
        return None  # 藉機攻擊要能打到觸發者原本的位置
    return definition


def _react(
    ctx: Ctx,
    unit: UnitState,
    events: tuple[str, ...],
    trigger: UnitState,
    *,
    effect: str | None = None,
    skills: bool = False,
) -> ReactionDef | SkillDef | None:
    """找出 ``unit`` 第一條符合事件、目前可用的規則並詢問；使用時回傳反應定義或反應技
    （已扣次數與耐力、發出 ``reaction_triggered``，由呼叫端執行效果）。"""
    for rule in unit.reactions:
        if rule.when.event not in events:
            continue
        picked = _candidate(ctx, unit, rule, trigger, effect, skills)
        if picked is None:
            continue
        if _decide(ctx, unit, rule, trigger):
            _use(ctx, unit, picked, trigger)
            return picked
        ctx.emit(ReactionDeclined, unit_id=unit.id, reaction=picked.id, trigger_unit_id=trigger.id)
        return None
    return None


def _run_skill(
    ctx: Ctx,
    unit: UnitState,
    skill: SkillDef,
    trigger: UnitState,
    on_paid: Callable[[], None] | None = None,
) -> None:
    # 延後匯入：技能解譯器匯入本模組（block_multiplier、try_intercept……）。
    from trpg.engine.skills.interpreter import use_reaction_skill  # noqa: PLC0415

    use_reaction_skill(ctx, unit, skill, trigger, depth=ctx.trigger_depth + 1, on_paid=on_paid)


def block_multiplier(
    ctx: Ctx, attacker: UnitState, target: UnitState, melee: bool | None = None
) -> int:
    """命中後、傷害前：目標的格擋類反應。回傳傷害倍率（‰，沒有格擋時 1000）。

    ``melee``：這次攻擊是否算近戰（技能傳入；省略時看攻擊者的武器）。
    """
    events: tuple[str, ...] = ("targeted_by_attack",)
    if is_melee_attack(ctx, attacker) if melee is None else melee:
        events = ("targeted_by_melee", "targeted_by_attack")
    definition = _react(ctx, target, events, attacker, effect="reduce_damage")
    if not isinstance(definition, ReactionDef):
        return PERMILLE
    return PERMILLE - definition.damage_reduction_permille


def hit_reactions(ctx: Ctx, attacker: UnitState, target: UnitState, *, melee: bool) -> None:
    """``target`` 被 ``attacker`` 的攻擊命中、傷害結算之後（仍存活）：``hit_by_melee``／
    ``hit_by_attack`` 反應技（例如反擊）。``melee``：這次攻擊是否算近戰。"""
    if not target.alive or not attacker.alive:
        return
    events = ("hit_by_melee", "hit_by_attack") if melee else ("hit_by_attack",)
    picked = _react(ctx, target, events, attacker, skills=True)
    if isinstance(picked, SkillDef):
        _run_skill(ctx, target, picked, attacker)


def try_intercept(
    ctx: Ctx, attacker: UnitState, target: UnitState, seq: int, *, skill_id: str | None = None
) -> UnitState | None:
    """``attacker`` 對 ``target`` 的單體攻擊已命中、傷害與其他效果結算之前：與 ``target`` 相鄰的友方
    （依單位 ID，第一個願意且能反應的）用 ``intercept`` 反應技替他擋下。

    成功時先付代價並結算反應技自己的其他效果（例如替守護者加上護衛），發出
    ``attack_intercepted``，回傳守護者——呼叫端把這次攻擊的所有效果改為作用在守護者身上
    （不重擲命中）。``seq`` 是這次命中判定的事件序號（尚未結算的攻擊者被動觸發一併改對守護者）。
    """
    if attacker.team is target.team:
        return None
    for guardian in ctx.state.units_sorted():
        if guardian.id == target.id or guardian.team is not target.team:
            continue
        if not guardian.alive or manhattan(guardian.xy, target.xy) != 1:
            continue
        picked = _react(ctx, guardian, ("ally_hit_adjacent",), attacker, skills=True)
        if not isinstance(picked, SkillDef):
            continue

        def announce(guardian: UnitState = guardian) -> None:
            ctx.emit(
                AttackIntercepted,
                guardian_id=guardian.id,
                attacker_id=attacker.id,
                target_id=target.id,
                skill_id=skill_id,
            )
            redirect_fired(ctx, seq, target.id, guardian.id)

        _run_skill(ctx, guardian, picked, attacker, announce)
        return guardian
    return None


def perform_unit_attack(ctx: Ctx, attacker: UnitState, target: UnitState, *, primary: bool) -> None:
    """一次普攻：命中判定 → （命中時）格擋反應 → 傷害。

    ``primary``：是否為動作本身的攻擊（預覽時主要攻擊視為命中，次要攻擊如藉機攻擊在
    ``min`` 模式視為失手、``max`` 模式視為暴擊）。被動技能的觸發等傷害結算完才處理。
    """
    with holding(ctx):
        _attack_once(ctx, attacker, target, primary=primary)


def _attack_once(ctx: Ctx, attacker: UnitState, target: UnitState, *, primary: bool) -> None:
    forced: ForcedOutcome | None = None
    if ctx.preview is not None:
        ctx.mark_branch()
        if primary:
            forced = "hit" if ctx.preview == "min" else "crit"
        else:
            forced = "miss" if ctx.preview == "min" else "crit"
    roll = roll_attack(ctx.state, ctx.rng, attacker, target, forced)
    rolled_event = ctx.emit(
        AttackRolled,
        attacker_id=attacker.id,
        target_id=target.id,
        rolls=roll.rolls,
        advantage=roll.advantage,
        natural=roll.natural,
        attack_value=roll.attack_value,
        defense_value_permille=roll.defense_value_permille,
        hit_modifier=roll.hit_modifier,
        proficiency=roll.proficiency,
        situational=roll.situational,
        total=roll.total,
        cover=roll.cover,
        cover_object_id=roll.cover_object_id,
        target_number=roll.target_number,
        hit=roll.hit,
        crit=roll.crit,
    )
    if not roll.hit:
        return
    guardian = try_intercept(ctx, attacker, target, rolled_event.seq)
    if guardian is not None:
        target = guardian  # 替隊友擋攻擊：傷害改作用在守護者身上（不重擲命中）
    multiplier = block_multiplier(ctx, attacker, target)
    weapon = attacker.weapon
    execute(
        ctx,
        [
            DamageEffect(
                target_id=target.id,
                source_id=attacker.id,
                cause="attack",
                element=weapon.element,
                dice=weapon.dice,
                flat=weapon.flat,
                scaled_permille=effective_attribute(ctx.rules, attacker, weapon.scaling_attr)
                * ctx.core.basic_attack_attr_multiplier_permille,
                crit=roll.crit,
                min_damage=ctx.core.min_damage_on_hit,
                multiplier_permille=multiplier,
            )
        ],
    )
    hit_reactions(ctx, attacker, target, melee=is_melee_attack(ctx, attacker))


def opportunity_attacks(ctx: Ctx, mover: UnitState, from_xy: XY, to_xy: XY) -> None:
    """``mover`` 即將從 ``from_xy`` 走到 ``to_xy``：離開相鄰格的敵人可以反應（依 ID 順序）——
    藉機攻擊，或 ``enemy_leaves_adjacent`` 的反應技。"""
    state = ctx.state
    for reactor in state.living_units():
        if not mover.alive:
            return
        if reactor.team is mover.team:
            continue
        if manhattan(reactor.xy, from_xy) != 1 or manhattan(reactor.xy, to_xy) == 1:
            continue
        picked = _react(
            ctx, reactor, ("enemy_leaves_adjacent",), mover, effect="basic_attack", skills=True
        )
        if isinstance(picked, SkillDef):
            _run_skill(ctx, reactor, picked, mover)
        elif picked is not None:
            perform_unit_attack(ctx, reactor, mover, primary=False)
