"""反應規則與暫停點（``docs/專案計畫.md`` 5.2.1、5.9）。

- 單位帶有反應規則（範本的 ``reactions``，預設為 ``reactions.yaml`` 的 ``default_rules``）。
  條件成立時：``auto`` 自動執行；``prompt`` 暫停結算（:class:`PauseForDecision`），由
  ``resolve`` 回傳 ``pending``，玩家以 ``resume`` 回答。
- 每個單位每輪最多反應 ``reactions_per_round`` 次（每輪開始時重設），內建反應與反應技共用。
- 已實作的反應效果：``reduce_damage``（格擋）與 ``basic_attack``（藉機攻擊）。
- 反應技（Phase 2E-2，``kind: reaction``）：規則的 ``reaction`` 是持有者裝備的技能 ID；事件
  ``hit_by_melee``／``hit_by_attack``（被命中、傷害之後）、``enemy_leaves_adjacent``、
  ``ally_hit_adjacent``（相鄰友方被單體攻擊命中、傷害之前；配 ``intercept`` 原語替他擋下）。
  Phase 3D-3 新增四個事件：``hit_by_spell``（被法術技命中、傷害之前）、``ally_downed``（視野內的
  友方倒下之後，等效果佇列清空才處理，見 :func:`ally_downed_reactions`）、``enemy_enters_adjacent``
  （敵人主動移動進入相鄰格之後）、``ally_targeted``（相鄰友方被敵人單體技能或普攻瞄準、命中判定
  之前）。
  Phase 3D-8c 新增內建反應事件 ``enemy_moves_in_range``（監視射擊 ``overwatch_shot``，需要狀態
  ``overwatch``：敵人主動移動的一步結束後位在持有者的武器射程與視線內，自動普攻一次並移除
  ``overwatch``，見 :func:`enemy_moves_in_range_reactions`）。
  Phase 3I-1 新增內建反應 ``counter_attack``（反擊，拳套的武器特性 ``counter``）：事件
  ``hit_by_melee``，相鄰敵人的近戰攻擊命中、傷害之後，對攻擊者普攻一次（見 :func:`hit_reactions`）。
  反應技不花 AP，立刻施放一次技能（:func:`trpg.engine.skills.casting.use_reaction_skill`）。

普攻的結算（:func:`perform_unit_attack`）也放在這裡，因為格擋會在命中後、傷害前介入，
藉機攻擊本身也是一次普攻。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from trpg.content.battle import ReactionRule
from trpg.content.environment import ReactionDef
from trpg.content.skills import SkillDef
from trpg.engine import modifiers
from trpg.engine.basics import guard_covers
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect, RemoveStatusEffect
from trpg.engine.events import (
    AttackIntercepted,
    AttackRolled,
    DamageDealt,
    EventBase,
    ReactionDeclined,
    ReactionTriggered,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.gear_reactions import (
    extra_uses_left,
    reaction_available,
    redirect_affix,
    spend_reaction,
)
from trpg.engine.ids import CONCEALED
from trpg.engine.results import Pending
from trpg.engine.rules.combat import ForcedOutcome, attack_problem, roll_attack
from trpg.engine.rules.facing import face_toward
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.rules.statuses import (
    effective_attribute,
    skip_turn_status,
    weapon_attribute,
    weapon_scale_attr,
)
from trpg.engine.rules.weapons import range_damage_permille
from trpg.engine.skill_triggers import check_trigger_depth, holding, redirect_fired
from trpg.engine.skills.casting import use_reaction_skill
from trpg.engine.skills.conditions import Subject, skill_condition_met
from trpg.engine.skills.targeting import reaction_problem, reaction_target_problem
from trpg.engine.state import UnitState
from trpg.engine.strikes import after_attack_hit
from trpg.engine.weapon_traits import (
    apply_hit_traits,
    attack_dice,
    gunshot_reveals,
    height_permille,
    pierce_line_targets,
    reveal_after_gunshot,
    spend_ammo,
)
from trpg.shared.errors import TrpgError

__all__ = [
    "PauseForDecision",
    "after_attack",
    "ally_downed_reactions",
    "ally_targeted_reactions",
    "block_multiplier",
    "enemy_enters_adjacent_reactions",
    "enemy_moves_in_range_reactions",
    "hit_reactions",
    "is_melee_attack",
    "opportunity_attacks",
    "perform_unit_attack",
    "spell_hit_reactions",
    "try_intercept",
]

PERMILLE = 1000
BLOCK_REACTION = "block"
"""格擋反應的 ID（圓盾的格擋強化只作用在它身上，Phase 3I-2）。"""


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
    if not unit.alive or not reaction_available(ctx.core, unit, rule.reaction):
        return None
    if skip_turn_status(ctx.rules, unit) is not None:
        return None  # 暈眩中不能執行反應
    if _unless(unit, rule):
        return None
    status = definition.requires_status
    if unit.stamina < definition.stamina_cost or (
        status is not None and not unit.has_status(status)
    ):
        return None
    if not _weapon_allows(ctx, unit, definition):
        return None
    return definition


def _weapon_allows(ctx: Ctx, unit: UnitState, definition: ReactionDef) -> bool:
    """內建反應對手上武器的要求：近戰武器（藉機攻擊），或有 ``counter``（反擊，拳套，3I-1）。"""
    if definition.requires_melee_weapon and not is_melee_attack(ctx, unit):
        return False
    return not definition.requires_counter_weapon or unit.weapon.counter


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
    if not reaction_available(ctx.core, unit, rule.reaction) or _unless(unit, rule):
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


_TRIGGER_EVENT_MATCHERS: dict[str, Callable[[EventBase, UnitState, UnitState], bool]] = {
    "targeted_by_melee": lambda e, u, t: (
        isinstance(e, AttackRolled) and e.target_id == u.id and e.attacker_id == t.id
    ),
    "targeted_by_attack": lambda e, u, t: (
        isinstance(e, AttackRolled) and e.target_id == u.id and e.attacker_id == t.id
    ),
    "hit_by_melee": lambda e, u, t: (
        isinstance(e, DamageDealt) and e.target_id == u.id and e.source_id == t.id
    ),
    "hit_by_attack": lambda e, u, t: (
        isinstance(e, DamageDealt) and e.target_id == u.id and e.source_id == t.id
    ),
    "ally_hit_adjacent": lambda e, _u, t: isinstance(e, AttackRolled) and e.attacker_id == t.id,
    "hit_by_spell": lambda e, u, t: (
        isinstance(e, AttackRolled) and e.target_id == u.id and e.attacker_id == t.id
    ),
    "ally_targeted": lambda e, _u, t: isinstance(e, AttackRolled) and e.attacker_id == t.id,
    "ally_hit_in_range": lambda e, _u, t: isinstance(e, AttackRolled) and e.attacker_id == t.id,
    "ally_downed": lambda e, _u, t: isinstance(e, UnitDowned) and e.unit_id == t.id,
    "enemy_enters_adjacent": lambda e, _u, t: isinstance(e, UnitMoved) and e.unit_id == t.id,
    "enemy_moves_in_range": lambda e, _u, t: isinstance(e, UnitMoved) and e.unit_id == t.id,
}


def _trigger_event_seq(ctx: Ctx, unit: UnitState, event: str, trigger: UnitState) -> int | None:
    """引發詢問的事件 ``seq``：本次結算中最近一個符合的事件；找不到時為 ``None``
    （例如 ``enemy_leaves_adjacent`` 的移動事件尚未發出）。"""
    matches = _TRIGGER_EVENT_MATCHERS.get(event)
    if matches is None:
        return None
    for e in reversed(ctx.events):
        if matches(e, unit, trigger):
            return e.seq
    return None


def _pending(
    ctx: Ctx,
    unit: UnitState,
    rule: ReactionRule,
    picked: ReactionDef | SkillDef,
    trigger: UnitState,
) -> Pending:
    """暫停詢問的公開資料：誰、什麼反應、接受要付出什麼。"""
    if isinstance(picked, SkillDef):
        return Pending(
            kind="reaction",
            unit_id=unit.id,
            reaction=rule.reaction,
            trigger_unit_id=trigger.id,
            skill_id=picked.id,
            trigger_event_seq=_trigger_event_seq(ctx, unit, rule.when.event, trigger),
            mana_cost=picked.cost.mana,
            stamina_cost=picked.cost.stamina,
            hp_cost_permille=picked.cost.hp_percent or 0,
        )
    return Pending(
        kind="reaction",
        unit_id=unit.id,
        reaction=rule.reaction,
        trigger_unit_id=trigger.id,
        trigger_event_seq=_trigger_event_seq(ctx, unit, rule.when.event, trigger),
        stamina_cost=picked.stamina_cost,
    )


def _decide(
    ctx: Ctx,
    unit: UnitState,
    rule: ReactionRule,
    picked: ReactionDef | SkillDef,
    trigger: UnitState,
) -> bool:
    if rule.mode == "auto":
        return True
    if ctx.preview is not None:
        ctx.mark_branch()
        return ctx.preview == "max"
    if ctx.decisions:
        return ctx.decisions.pop(0)
    raise PauseForDecision(_pending(ctx, unit, rule, picked, trigger))


def _use(ctx: Ctx, unit: UnitState, picked: ReactionDef | SkillDef, trigger: UnitState) -> None:
    spend_reaction(ctx.core, unit, picked.id)  # 一般反應次數；用完才用裝備給的額外次數（3G-G3b）
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
        if rule.mode == "off" or rule.when.event not in events:
            continue
        picked = _candidate(ctx, unit, rule, trigger, effect, skills)
        if picked is None:
            continue
        if _decide(ctx, unit, rule, picked, trigger):
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
    reduction = definition.damage_reduction_permille
    offhand = target.gear.offhand
    if definition.id == BLOCK_REACTION and offhand is not None:  # 圓盾的格擋強化（3I-2）
        rules = ctx.state.ruleset
        reduction += offhand.block_extra_permille(lambda a: effective_attribute(rules, target, a))
    return max(0, PERMILLE - reduction)


def hit_reactions(ctx: Ctx, attacker: UnitState, target: UnitState, *, melee: bool) -> None:
    """``target`` 被 ``attacker`` 的攻擊命中、傷害結算之後（仍存活）：``hit_by_melee``／
    ``hit_by_attack`` 反應技（例如反擊技），或內建的反擊 ``counter_attack``（Phase 3I-1，拳套：
    只對相鄰攻擊者的近戰攻擊，普攻一次）。``melee``：這次攻擊是否算近戰。"""
    if not target.alive or not attacker.alive:
        return
    events = ("hit_by_melee", "hit_by_attack") if melee else ("hit_by_attack",)
    adjacent = melee and manhattan(target.xy, attacker.xy) == 1
    effect = "basic_attack" if adjacent else None
    picked = _react(ctx, target, events, attacker, effect=effect, skills=True)
    if isinstance(picked, SkillDef):
        _run_skill(ctx, target, picked, attacker)
    elif picked is not None:
        perform_unit_attack(ctx, target, attacker, primary=False, reaction=True)


def _guard_transfer(
    ctx: Ctx, attacker: UnitState, target: UnitState, seq: int, skill_id: str | None
) -> UnitState | None:
    """「守護」動作（Phase 3-21a）：守著 ``target`` 的相鄰隊友（依單位 ID，第一個本輪還能轉移的）
    替他承受這次單體攻擊；不花反應。"""
    for guardian in ctx.state.units_sorted():
        if guardian.team is not target.team or not guard_covers(ctx, guardian, target):
            continue
        guardian.guard_transfers += 1
        ctx.emit(
            AttackIntercepted,
            guardian_id=guardian.id,
            attacker_id=attacker.id,
            target_id=target.id,
            skill_id=skill_id,
            guard=True,
        )
        redirect_fired(ctx, seq, target.id, guardian.id)
        return guardian
    return None


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
    guarded = _guard_transfer(ctx, attacker, target, seq, skill_id)
    if guarded is not None:
        return guarded
    skill_guardian = _intercept_by_skill(ctx, attacker, target, seq, skill_id)
    if skill_guardian is not None:
        return skill_guardian
    return _gear_redirect(ctx, attacker, target, seq, skill_id)


def _gear_redirect(
    ctx: Ctx, attacker: UnitState, target: UnitState, seq: int, skill_id: str | None
) -> UnitState | None:
    """裝備授予的 ``redirect_damage`` 反應（Phase 3G-G3b，``affix_react_guard_ally``）：``target``
    的友方（依單位 ID，第一個願意且能反應的）在詞條的 ``range`` 格內，且這個詞條本輪還沒用過
    （``limit: per_round``）時，替他承受這次攻擊（同 ``intercept``：不重擲命中）。"""
    for guardian in ctx.state.units_sorted():
        if guardian.id == target.id or guardian.team is not target.team or not guardian.alive:
            continue
        affix = redirect_affix(guardian)
        if affix is None or manhattan(guardian.xy, target.xy) > (affix.range or 1):
            continue
        if affix.limit == "per_round" and guardian.gear_round_counts.get(affix.id, 0) >= 1:
            continue
        picked = _react(ctx, guardian, ("ally_hit_in_range",), attacker, effect="redirect_damage")
        if not isinstance(picked, ReactionDef):
            continue
        counts = guardian.gear_round_counts
        counts[affix.id] = counts.get(affix.id, 0) + 1
        ctx.emit(
            AttackIntercepted,
            guardian_id=guardian.id,
            attacker_id=attacker.id,
            target_id=target.id,
            skill_id=skill_id,
        )
        redirect_fired(ctx, seq, target.id, guardian.id)
        return guardian
    return None


def _intercept_by_skill(
    ctx: Ctx, attacker: UnitState, target: UnitState, seq: int, skill_id: str | None
) -> UnitState | None:
    """相鄰友方用 ``intercept`` 反應技替 ``target`` 擋下（見 :func:`try_intercept`）。"""
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


def spell_hit_reactions(ctx: Ctx, caster: UnitState, target: UnitState) -> None:
    """``caster`` 的法術技命中 ``target``、傷害結算之前（Phase 3D-3）：``target`` 的
    ``hit_by_spell`` 反應技（例如法術反射、護符）。"""
    if not target.alive or not caster.alive:
        return
    picked = _react(ctx, target, ("hit_by_spell",), caster, skills=True)
    if isinstance(picked, SkillDef):
        _run_skill(ctx, target, picked, caster)


def ally_targeted_reactions(ctx: Ctx, attacker: UnitState, target: UnitState) -> None:
    """``attacker`` 選了 ``target`` 當單體攻擊的目標、命中判定之前（Phase 3D-3）：與 ``target``
    相鄰的友方（依單位 ID）各自可以用 ``ally_targeted`` 反應技反應（例如對攻擊者還擊、替隊友
    加護盾）。攻擊者或目標倒下就停止。"""
    if attacker.team is target.team:
        return
    for reactor in ctx.state.units_sorted():
        if not attacker.alive or not target.alive:
            return
        if reactor.id == target.id or reactor.team is not target.team or not reactor.alive:
            continue
        if manhattan(reactor.xy, target.xy) != 1:
            continue
        picked = _react(ctx, reactor, ("ally_targeted",), attacker, skills=True)
        if isinstance(picked, SkillDef):
            _run_skill(ctx, reactor, picked, attacker)


def ally_downed_reactions(ctx: Ctx, downed: UnitState) -> None:
    """``downed`` 倒下之後（Phase 3D-3）：視野內的友方（依單位 ID）可以用 ``ally_downed`` 反應技
    反應；另一方是倒下的友方（形狀固定為 ``self``）。"""
    state = ctx.state
    for reactor in state.units_sorted():
        if state.ended:
            return
        if reactor.id == downed.id or reactor.team is not downed.team or not reactor.alive:
            continue
        if not has_line_of_sight(state, reactor.xy, downed.xy):
            continue
        picked = _react(ctx, reactor, ("ally_downed",), downed, skills=True)
        if isinstance(picked, SkillDef):
            _run_skill(ctx, reactor, picked, downed)


def enemy_enters_adjacent_reactions(ctx: Ctx, mover: UnitState, from_xy: XY) -> None:
    """``mover`` 剛主動移動（步行、衝鋒、直線衝撞）離開 ``from_xy``、到了現在的位置（Phase 3D-3）：
    因此進入相鄰格（原本不相鄰）的敵人（依 ID 順序）可以用 ``enemy_enters_adjacent`` 反應技反應。
    強制位移不呼叫這裡。"""
    state = ctx.state
    for reactor in state.living_units():
        if not mover.alive:
            return
        if reactor.team is mover.team or manhattan(reactor.xy, mover.xy) != 1:
            continue
        if manhattan(reactor.xy, from_xy) == 1:
            continue
        picked = _react(ctx, reactor, ("enemy_enters_adjacent",), mover, skills=True)
        if isinstance(picked, SkillDef):
            _run_skill(ctx, reactor, picked, mover)


def enemy_moves_in_range_reactions(ctx: Ctx, mover: UnitState) -> None:
    """``mover`` 剛主動移動（步行、衝鋒、直線衝撞）完成一步（Phase 3D-8c）：帶有 ``overwatch``
    的敵人（依 ID 順序）若能以武器攻擊到 ``mover`` 現在的位置（射程、視線、隱蔽、致盲都照一般普攻
    的規則），就用內建的 ``enemy_moves_in_range`` 反應（監視射擊）普攻一次；佔本輪的反應次數，
    用掉之後移除該狀態。拒絕（``prompt`` 模式選不用）時狀態保留，下一步再問。強制位移、傳送、
    跳躍、互換不呼叫這裡。"""
    for reactor in ctx.state.living_units():
        if not mover.alive:
            return
        if reactor.team is mover.team or reactor.is_summon:
            continue
        picked = _react(ctx, reactor, ("enemy_moves_in_range",), mover, effect="basic_attack")
        if not isinstance(picked, ReactionDef):
            continue
        perform_unit_attack(ctx, reactor, mover, primary=False, reaction=True)
        status_id = picked.requires_status
        if extra_uses_left(reactor, picked.id) > 0:
            continue  # 裝備給了額外次數（3G-G3b）：還能再觸發一次，監視狀態保留到最後一次
        if status_id is not None and reactor.alive and reactor.has_status(status_id):
            execute(
                ctx,
                [RemoveStatusEffect(target_id=reactor.id, status_id=status_id, reason="fired")],
            )


def perform_unit_attack(
    ctx: Ctx,
    attacker: UnitState,
    target: UnitState,
    *,
    primary: bool,
    reaction: bool = False,
) -> None:
    """一次普攻：命中判定 → （命中時）格擋反應 → 傷害。

    ``primary``：是否為動作本身的攻擊（預覽時主要攻擊視為命中，次要攻擊如藉機攻擊在
    ``min`` 模式視為失手、``max`` 模式視為暴擊）。被動技能的觸發等傷害結算完才處理。
    ``reaction``：這是反應攻擊（藉機攻擊、監視射擊）——命中加上感知的常駐數值（Phase 3H-1）。
    """
    with holding(ctx):
        target_xy, attacker_xy = target.xy, attacker.xy
        if attacker.weapon.magazine > 0 and attacker.ammo <= 0:
            return  # 空膛（Phase 3-24a2）：合法性已在 attack_problem 檢查，這裡只是保險
        reveal = gunshot_reveals(ctx.state, attacker)
        behind = pierce_line_targets(ctx.state, attacker, target)  # 開火前的直線（弩，3-24a2）
        spend_ammo(attacker)
        ambushed, rolled, victim = _attack_once(
            ctx, attacker, target, primary=primary, reaction=reaction
        )
        for extra in behind:  # 穿透：各自擲命中與傷害
            if attacker.alive and extra.alive:
                _attack_once(ctx, attacker, extra, primary=False, reaction=reaction)
        for _ in range(attacker.weapon.strikes - 1):  # 連擊武器（雙匕首，3I-4）：每一下各自結算
            if not (attacker.alive and target.alive):
                break
            _attack_once(ctx, attacker, target, primary=False, reaction=reaction)
        turns = [(victim, attacker_xy)] if rolled and attacker.weapon.is_melee else []
        after_attack(ctx, attacker, target_xy, ambushed=ambushed, turns=turns)
        if reveal:
            reveal_after_gunshot(ctx, attacker)  # 槍聲（3-24a2）


def after_attack(
    ctx: Ctx,
    attacker: UnitState,
    target_xy: XY | None,
    *,
    ambushed: bool,
    turns: Iterable[tuple[UnitState, XY]] = (),
) -> None:
    """一次攻擊（普攻）或施放（主動技能、反應技）結算完（Phase 3D-8d）：面向主要目標
    （``target_xy``；``None`` 為沒有單位或物件目標，朝向不變）；隱蔽中擲過命中（潛行偷襲）時移除
    攻擊者的 ``concealed``（原因 ``ambushed``）。

    ``turns``（Phase 3C-6a，``05-戰鬥.md`` 5.1）：被近戰攻擊（不論命中與否）的單位與當時攻擊者的
    位置——結算完才轉身面向攻擊者（所以同一次攻擊裡的背刺判定與 ``from_behind`` 效果仍以擲骰當下
    的朝向為準）；倒下的單位不轉。"""
    for victim, from_xy in turns:
        if victim.alive:
            face_toward(victim, from_xy)
    if not attacker.alive:
        return
    if target_xy is not None:
        face_toward(attacker, target_xy)
    if ambushed and attacker.has_status(CONCEALED):
        execute(
            ctx,
            [RemoveStatusEffect(target_id=attacker.id, status_id=CONCEALED, reason="ambushed")],
        )


def _attack_once(
    ctx: Ctx,
    attacker: UnitState,
    target: UnitState,
    *,
    primary: bool,
    extra_permille: int | None = None,
    reaction: bool = False,
) -> tuple[bool, bool, UnitState]:
    """回傳（這次攻擊是不是在隱蔽中發動——潛行偷襲，結算完要移除隱蔽；有沒有擲命中；承受這次
    攻擊的單位——被守護者擋下時是守護者，3C-6b：轉身的是它）。

    ``extra_permille``：這是普攻連擊多出來的一下（Phase 3-32a），傷害再乘上這個倍率；它不會再
    觸發連擊與分裂。"""
    ally_targeted_reactions(ctx, attacker, target)  # 相鄰友方被瞄準：命中判定之前（3D-3）
    if not attacker.alive or not target.alive:
        return False, False, target
    forced: ForcedOutcome | None = None
    if ctx.preview is not None:
        ctx.mark_branch()
        if primary:
            forced = "hit" if ctx.preview == "min" else "crit"
        else:
            forced = "miss" if ctx.preview == "min" else "crit"
    state = ctx.state
    bonus = modifiers.hit_bonus(state, attacker, modifiers.ATTACK, Subject(target, target.xy))
    if reaction:  # 感知的常駐數值（Phase 3H-1）
        bonus += attribute_perk(ctx.rules, attacker, "reaction_hit")
    if attacker.aimed:  # 瞄準（Phase 3-21a）：下一次需要擲命中的攻擊，用掉即失效
        bonus += ctx.core.aim_hit_bonus
        attacker.aimed = False
    roll = roll_attack(state, ctx.rng, attacker, target, forced, bonus=bonus)
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
        modifier_bonus=roll.modifier_bonus,
        backstab=roll.backstab,
        ambush=roll.ambush,
    )
    if not roll.hit:
        return roll.ambush > 0, True, target
    guardian = try_intercept(ctx, attacker, target, rolled_event.seq)
    if guardian is not None:
        target = guardian  # 替隊友擋攻擊：傷害改作用在守護者身上（不重擲命中）
    use = modifiers.ATTACK
    subject = Subject(target, target.xy)
    bonus_permille = modifiers.damage_permille(state, attacker, use, subject)
    modifiers.spend_attack_limits(state, attacker, use, subject)  # 每回合 1 次的加傷（3-31）
    block = block_multiplier(ctx, attacker, target)
    multiplier = block * bonus_permille // PERMILLE
    multiplier = (
        multiplier * range_damage_permille(attacker, manhattan(attacker.xy, target.xy)) // PERMILLE
    )
    if extra_permille is not None:
        multiplier = multiplier * extra_permille // PERMILLE
    if attacker.is_summon:  # 高處灌注（3-33e1）：比目標高時普攻傷害加成
        multiplier = multiplier * (PERMILLE + height_permille(state, attacker, target)) // PERMILLE
    weapon = attacker.weapon
    execute(
        ctx,
        [
            DamageEffect(
                target_id=target.id,
                source_id=attacker.id,
                cause="attack",
                element=modifiers.damage_element(state, attacker, use, weapon.element),
                dice=attack_dice(state, attacker, backstab=roll.backstab > 0),
                flat=weapon.flat,
                scaled_permille=weapon_attribute(ctx.rules, attacker)
                * ctx.core.basic_attack_attr_multiplier_permille,
                scale_attr=weapon_scale_attr(attacker),
                crit=roll.crit,
                min_damage=ctx.core.min_damage_on_hit,
                multiplier_permille=multiplier,
                block_permille=block,
            )
        ],
    )
    apply_hit_traits(ctx, attacker, target)  # 武器小特性：破甲、震退、祝禱（3-24a1）
    hit_reactions(ctx, attacker, target, melee=is_melee_attack(ctx, attacker))
    if extra_permille is None and attacker.alive:  # 普攻流：分裂與連擊（3-32a）

        def again(permille: int) -> None:
            _attack_once(ctx, attacker, target, primary=False, extra_permille=permille)

        after_attack_hit(ctx, attacker, target, again)
    return roll.ambush > 0, True, target


def opportunity_attacks(ctx: Ctx, mover: UnitState, from_xy: XY, to_xy: XY) -> None:
    """``mover`` 即將從 ``from_xy`` 走到 ``to_xy``：離開相鄰格的敵人可以反應（依 ID 順序）——
    藉機攻擊，或 ``enemy_leaves_adjacent`` 的反應技。

    藉機攻擊的範圍是武器的 ``reach``（Phase 3-24a1，矛為 2）：``mover`` 從 ``reach`` 格內走到
    ``reach`` 格外時才觸發（``reach`` 為 1 時就是離開相鄰格）；反應技仍然只看相鄰。"""
    state = ctx.state
    for reactor in state.living_units():
        if not mover.alive:
            return
        if reactor.team is mover.team:
            continue
        before, after = manhattan(reactor.xy, from_xy), manhattan(reactor.xy, to_xy)
        reach = reactor.weapon.reach
        leaves_reach = before <= reach < after
        leaves_adjacent = before == 1 and after != 1
        if not (leaves_reach or leaves_adjacent):
            continue
        picked = _react(
            ctx,
            reactor,
            ("enemy_leaves_adjacent",),
            mover,
            effect="basic_attack" if leaves_reach else None,
            skills=leaves_adjacent,
        )
        if isinstance(picked, SkillDef):
            _run_skill(ctx, reactor, picked, mover)
        elif picked is not None:
            perform_unit_attack(ctx, reactor, mover, primary=False, reaction=True)
