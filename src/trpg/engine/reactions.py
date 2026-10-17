"""反應規則與暫停點（``docs/專案計畫.md`` 5.2.1、5.9）。

- 單位帶有反應規則（範本的 ``reactions``，預設為 ``reactions.yaml`` 的 ``default_rules``）。
  條件成立時：``auto`` 自動執行；``prompt`` 暫停結算（:class:`PauseForDecision`），由
  ``resolve`` 回傳 ``pending``，玩家以 ``resume`` 回答。
- 每個單位每輪最多反應 ``reactions_per_round`` 次（每輪開始時重設）。
- 已實作的反應效果：``reduce_damage``（格擋）與 ``basic_attack``（藉機攻擊）。

普攻的結算（:func:`perform_unit_attack`）也放在這裡，因為格擋會在命中後、傷害前介入，
藉機攻擊本身也是一次普攻。
"""

from __future__ import annotations

from trpg.content.battle import ReactionRule
from trpg.content.environment import ReactionDef
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import AttackRolled, ReactionDeclined, ReactionTriggered
from trpg.engine.results import Pending
from trpg.engine.rules.combat import ForcedOutcome, attack_problem, roll_attack
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import UnitState
from trpg.shared.errors import TrpgError

__all__ = [
    "PauseForDecision",
    "block_multiplier",
    "is_melee_attack",
    "opportunity_attacks",
    "perform_unit_attack",
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
    unless = rule.unless
    if (
        unless is not None
        and unless.self_stamina_below is not None
        and unit.stamina < unless.self_stamina_below
    ):
        return None
    if unit.stamina < definition.stamina_cost:
        return None
    if definition.requires_melee_weapon and not is_melee_attack(ctx, unit):
        return None
    return definition


def _decide(ctx: Ctx, unit: UnitState, rule: ReactionRule, trigger: UnitState) -> bool:
    if rule.mode == "auto":
        return True
    if ctx.preview is not None:
        return ctx.preview == "max"
    if ctx.decisions:
        return ctx.decisions.pop(0)
    raise PauseForDecision(
        Pending(
            kind="reaction", unit_id=unit.id, reaction=rule.reaction, trigger_unit_id=trigger.id
        )
    )


def _use(ctx: Ctx, unit: UnitState, definition: ReactionDef, trigger: UnitState) -> None:
    unit.reactions_used += 1
    unit.stamina -= definition.stamina_cost
    ctx.emit(
        ReactionTriggered,
        unit_id=unit.id,
        reaction=definition.id,
        trigger_unit_id=trigger.id,
        stamina_spent=definition.stamina_cost,
    )


def _try(
    ctx: Ctx, unit: UnitState, events: tuple[str, ...], effect: str, trigger: UnitState
) -> ReactionDef | None:
    """找出 ``unit`` 第一條符合事件與效果、目前可用的規則並詢問；使用時回傳反應定義。"""
    for rule in unit.reactions:
        if rule.when.event not in events:
            continue
        definition = _usable(ctx, unit, rule)
        if definition is None or definition.effect != effect:
            continue
        if _decide(ctx, unit, rule, trigger):
            _use(ctx, unit, definition, trigger)
            return definition
        ctx.emit(
            ReactionDeclined, unit_id=unit.id, reaction=definition.id, trigger_unit_id=trigger.id
        )
        return None
    return None


def block_multiplier(ctx: Ctx, attacker: UnitState, target: UnitState) -> int:
    """命中後、傷害前：目標的格擋類反應。回傳傷害倍率（‰，沒有格擋時 1000）。"""
    events: tuple[str, ...] = ("targeted_by_attack",)
    if is_melee_attack(ctx, attacker):
        events = ("targeted_by_melee", "targeted_by_attack")
    definition = _try(ctx, target, events, "reduce_damage", attacker)
    if definition is None:
        return PERMILLE
    return PERMILLE - definition.damage_reduction_permille


def perform_unit_attack(ctx: Ctx, attacker: UnitState, target: UnitState, *, primary: bool) -> None:
    """一次普攻：命中判定 → （命中時）格擋反應 → 傷害。

    ``primary``：是否為動作本身的攻擊（預覽時主要攻擊視為命中，次要攻擊如藉機攻擊在
    ``min`` 模式視為失手、``max`` 模式視為暴擊）。
    """
    forced: ForcedOutcome | None = None
    if ctx.preview is not None:
        if primary:
            forced = "hit" if ctx.preview == "min" else "crit"
        else:
            forced = "miss" if ctx.preview == "min" else "crit"
    roll = roll_attack(ctx.state, ctx.rng, attacker, target, forced)
    ctx.emit(
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
        target_number=roll.target_number,
        hit=roll.hit,
        crit=roll.crit,
    )
    if not roll.hit:
        return
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
                scaled_permille=attacker.attributes[weapon.scaling_attr]
                * ctx.core.basic_attack_attr_multiplier_permille,
                crit=roll.crit,
                min_damage=ctx.core.min_damage_on_hit,
                multiplier_permille=multiplier,
            )
        ],
    )


def opportunity_attacks(ctx: Ctx, mover: UnitState, from_xy: XY, to_xy: XY) -> None:
    """``mover`` 即將從 ``from_xy`` 走到 ``to_xy``：離開相鄰格的敵人可以藉機攻擊（依 ID 順序）。"""
    state = ctx.state
    for reactor in state.living_units():
        if not mover.alive:
            return
        if reactor.team is mover.team:
            continue
        if manhattan(reactor.xy, from_xy) != 1 or manhattan(reactor.xy, to_xy) == 1:
            continue
        if attack_problem(state, reactor, mover) is not None:
            continue
        if _try(ctx, reactor, ("enemy_leaves_adjacent",), "basic_attack", mover) is None:
            continue
        perform_unit_attack(ctx, reactor, mover, primary=False)
