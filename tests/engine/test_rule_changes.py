"""常駐類傳說的啟動與四類規則改變（Phase 3D-6，``docs/phases/Phase3D計畫.md`` 6）。

- 啟動：1 AP ＋ 源力、啟動前不生效、``timed`` 到期、``battle`` 整場、生效中不能再啟動、每人同時最多
  1 個規則改變、序列化。
- ``element_heals_allies``、``push_any_object``、``pass_through_apply``、``on_downed_spawn``
  的規則與邊界。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3
from trpg.engine import (
    BattleState,
    Interact,
    Move,
    ResolveResult,
    UseSkill,
    legal_actions,
    modifiers,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.activations import activation_problem, active_rule_change, is_active
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.environment import run_environment
from trpg.engine.events import (
    ActivationExpired,
    DamageDealt,
    EffectFizzled,
    EventBase,
    Healed,
    ObjectMoved,
    RuleChangeTriggered,
    SkillActivated,
    SkillUsed,
    SourceChanged,
    StatusApplied,
    StatusResisted,
    SummonExpired,
    UnitSummoned,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import Activation
from trpg.engine.turns import start_turn
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Team, UnitId

AVATAR = "skill_war_avatar"  # 修正型傳說，限時：所有攻擊傷害 +18%
KINDRED = "skill_kindred_flame"  # 規則改變「慈焰」，整場：火焰對友方改為治療
MOVER = "skill_mountain_mover"  # 規則改變「移山」，限時：推動任何擋路物件
STRIDE = "skill_bloodwake_stride"  # 規則改變「血痕」，限時：步行經過的敵人流血
AFTERIMAGE = "skill_afterimage_vow"  # 規則改變「殘影」，整場：倒下時留下 2 輪的分身


def arena(
    skills: Sequence[str],
    *,
    source: int = 3,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    allies: Sequence[tuple[int, int]] = (),
    objects: Sequence[tuple[int, int, str]] = (),
    terrain: str | None = None,
    holder: tuple[int, int] = (3, 3),
) -> BattleState:
    """U1 持有者（我方戰士，``holder``，源力 ``source``）；之後依序是 ``foes``（敵人，不反應，
    HP 200）、``allies``（友方戰士，HP 200）。"""
    m = make_map(FLAT7, terrain, ally=[holder, *allies], enemy=list(foes), objects=list(objects))
    first = spawn(Team.ALLY, holder, caster_template(list(skills), base="hero_fighter"))
    spawns = [first.model_copy(update={"source": source})]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_fighter", max_hp=200)) for xy in allies]
    return give_turn(make_state(m, spawns), U1)


def of[E: EventBase](events: Sequence[EventBase] | ResolveResult, kind: type[E]) -> list[E]:
    items = events.events if isinstance(events, ResolveResult) else events
    return [e for e in items if isinstance(e, kind)]


def activate(state: BattleState, skill_id: str) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id))


def ctx_run(state: BattleState, fn: Any, *args: Any) -> tuple[BattleState, list[EventBase]]:
    ctx = Ctx(state.clone())
    fn(ctx, *args)
    return ctx.state, ctx.events


def at_round(state: BattleState, round_no: int) -> BattleState:
    s = state.clone()
    s.round = round_no
    return s


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------


def test_activation_costs_one_ap_and_source_and_emits_events_in_order() -> None:
    state = arena([AVATAR], source=2)
    result = activate(state, AVATAR)
    (used,) = of(result, SkillUsed)
    (spent,) = of(result, SourceChanged)
    (activated,) = of(result, SkillActivated)
    assert used.seq < spent.seq < activated.seq
    assert (used.ap, used.source) == (1, 1)
    assert (activated.activation, activated.expires_round, activated.rule) == ("timed", 4, None)
    unit = result.state.units[U1]
    assert (unit.ap, unit.source) == (state.units[U1].ap - 1, 1)
    assert unit.activations == (Activation(skill_id=AVATAR, expires_round=4),)


def test_a_modifier_legendary_does_nothing_until_activated() -> None:
    state = arena([AVATAR])
    unit = state.units[U1]
    foe = state.units[U2]
    subject = Subject(foe, foe.xy)
    assert modifiers.damage_permille(state, unit, modifiers.ATTACK, subject) == 1000
    after = activate(state, AVATAR).state
    unit = after.units[U1]
    assert modifiers.damage_permille(after, unit, modifiers.ATTACK, subject) == 1180


def test_the_passive_slot_legendary_is_offered_as_an_action_and_not_twice() -> None:
    state = arena([AVATAR])
    assert UseSkill(unit_id=U1, skill_id=AVATAR) in legal_actions(state)
    after = activate(state, AVATAR).state
    assert not any(isinstance(a, UseSkill) and a.skill_id == AVATAR for a in legal_actions(after))
    with pytest.raises(IllegalActionError, match="「戰神降臨」已經啟動（還剩 3 輪）"):
        activate(after, AVATAR)


def test_activation_needs_source() -> None:
    state = arena([KINDRED])
    state.units[U1].source = 0
    assert not any(isinstance(a, UseSkill) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="源力不足：需要 1，目前 0"):
        activate(state, KINDRED)


def test_timed_activation_lasts_three_rounds_and_expires_at_the_holders_turn_start() -> None:
    state = activate(arena([AVATAR]), AVATAR).state  # 第 1 輪啟動 → 第 4 輪的回合開始時結束
    kept, events = ctx_run(at_round(state, 3), start_turn, U1)
    assert is_active(kept.units[U1], AVATAR) and not of(events, ActivationExpired)
    gone, events = ctx_run(at_round(state, 4), start_turn, U1)
    (expired,) = of(events, ActivationExpired)
    assert (expired.unit_id, expired.skill_id) == (U1, AVATAR)
    assert gone.units[U1].activations == ()
    foe = gone.units[U2]
    subject = Subject(foe, foe.xy)
    assert modifiers.damage_permille(gone, gone.units[U1], modifiers.ATTACK, subject) == 1000


def test_the_timed_rounds_come_from_core_rules() -> None:
    state = arena([AVATAR])
    state.ruleset = state.ruleset.model_copy(
        update={"core": state.ruleset.core.model_copy(update={"legendary_timed_rounds": 1})}
    )
    (activated,) = of(activate(state, AVATAR), SkillActivated)
    assert activated.expires_round == 2


def test_battle_activation_lasts_the_whole_battle() -> None:
    result = activate(arena([KINDRED]), KINDRED)
    (activated,) = of(result, SkillActivated)
    assert (activated.activation, activated.expires_round) == ("battle", None)
    later, events = ctx_run(at_round(result.state, 50), start_turn, U1)
    assert is_active(later.units[U1], KINDRED) and not of(events, ActivationExpired)


def test_at_most_one_rule_change_is_active_per_unit() -> None:
    state = activate(arena([KINDRED]), KINDRED).state
    state.units[U1].skills = (*state.units[U1].skills, MOVER)  # 繞過裝備檢查（每人最多裝 1 個）
    mover = state.ruleset.skill_def(MOVER)
    problem = activation_problem(state, state.units[U1], mover)
    assert problem == "已有生效中的規則改變「慈焰誓約」（每個單位同時最多 1 個）"
    with pytest.raises(IllegalActionError, match="已有生效中的規則改變"):
        activate(state, MOVER)
    # 修正型傳說不受這個限制
    assert activation_problem(state, state.units[U1], state.ruleset.skill_def(AVATAR)) is None


def test_activations_survive_serialization() -> None:
    state = activate(arena([AVATAR]), AVATAR).state
    again = state_from_json(state_to_json(state))
    assert again.units[U1].activations == state.units[U1].activations
    assert state_to_json(again) == state_to_json(state)


# ---------------------------------------------------------------------------
# element_heals_allies（慈焰）
# ---------------------------------------------------------------------------


def _burn(state: BattleState, target: UnitId, element: Element = Element.FIRE) -> list[EventBase]:
    effect = DamageEffect(target_id=target, source_id=U1, element=element, flat=10)
    return ctx_run(state, execute, [effect])[1]


def test_kindred_flame_heals_allies_hit_by_the_holders_fire() -> None:
    state = arena([KINDRED], allies=[(2, 3)])
    state.units[U3].hp = 150
    before = _burn(state, U3)
    assert of(before, DamageDealt) and not of(before, Healed)  # 啟動前照常受傷
    active = activate(state, KINDRED).state
    events = _burn(active, U3)
    assert not of(events, DamageDealt)
    (trig,) = of(events, RuleChangeTriggered)
    (healed,) = of(events, Healed)
    assert (trig.kind, trig.other_id, trig.amount) == ("element_heals_allies", U3, 10)
    assert (healed.target_id, healed.amount, healed.hp_after) == (U3, 10, 160)


def test_kindred_flame_still_burns_enemies_the_holder_and_other_elements() -> None:
    state = activate(arena([KINDRED], allies=[(2, 3)]), KINDRED).state
    assert of(_burn(state, U2), DamageDealt)  # 敵人
    assert of(_burn(state, U1), DamageDealt)  # 自己不算友方
    assert of(_burn(state, U3, Element.ICE), DamageDealt)  # 不是火焰


def test_kindred_flame_only_applies_to_the_holders_fire() -> None:
    state = activate(arena([KINDRED], allies=[(2, 3)]), KINDRED).state
    effect = DamageEffect(target_id=U3, source_id=U2, element=Element.FIRE, flat=10)
    assert of(ctx_run(state, execute, [effect])[1], DamageDealt)


# ---------------------------------------------------------------------------
# push_any_object（移山）
# ---------------------------------------------------------------------------


def _wall_arena(kind: str = "earth_wall") -> BattleState:
    return arena([MOVER], objects=[(4, 3, kind)])


def _push(state: BattleState) -> Interact:
    obj = state.object_at(4, 3)
    assert obj is not None
    return Interact(unit_id=U1, object_id=obj.id)


def test_mountain_mover_pushes_an_earth_wall_only_after_activation() -> None:
    state = _wall_arena()
    assert _push(state) not in legal_actions(state)
    with pytest.raises(IllegalActionError, match="土牆無法推動"):
        resolve(state, _push(state))
    active = activate(state, MOVER).state
    assert _push(active) in legal_actions(active)
    result = resolve(active, _push(active))
    (trig,) = of(result, RuleChangeTriggered)
    (moved,) = of(result, ObjectMoved)
    assert trig.kind == "push_any_object" and trig.object_id == moved.object_id
    assert (moved.from_pos, moved.to_pos) == (Pos(x=4, y=3), Pos(x=5, y=3))


@pytest.mark.parametrize("kind", ["low_wall", "fallen_log", "rubble"])
def test_mountain_mover_pushes_other_blocking_objects(kind: str) -> None:
    active = activate(_wall_arena(kind), MOVER).state
    assert of(resolve(active, _push(active)), ObjectMoved)


def test_mountain_mover_does_not_move_floor_objects_or_other_units_walls() -> None:
    bridge = activate(arena([MOVER], objects=[(4, 3, "wooden_bridge")]), MOVER).state
    assert not any(isinstance(a, Interact) for a in legal_actions(bridge))  # 地面的一部分
    # 別人（沒有這個規則改變）推不動
    other = arena([MOVER], objects=[(5, 6, "earth_wall")])
    assert active_rule_change(other, other.units[U2]) is None
    wall = other.object_at(5, 6)
    assert wall is not None
    ok = give_turn(other, U2)
    with pytest.raises(IllegalActionError, match="土牆無法推動"):
        resolve(ok, Interact(unit_id=U2, object_id=wall.id))


# ---------------------------------------------------------------------------
# pass_through_apply（血痕）
# ---------------------------------------------------------------------------


def _walk(state: BattleState, *path: tuple[int, int]) -> ResolveResult:
    start = state.units[U1].pos
    return resolve(state, Move(unit_id=U1, path=(start, *(Pos(x=x, y=y) for x, y in path))))


def test_bloodwake_marks_each_adjacent_enemy_once_per_move() -> None:
    # 走 (3,3)→(3,2)→(3,1)→(3,0)：(4,2) 的敵人在前兩格都相鄰，只算一次；(6,6) 太遠
    state = arena([STRIDE], foes=[(4, 2), (6, 6)], allies=[(2, 1)])
    assert not of(_walk(state, (3, 2), (3, 1), (3, 0)), RuleChangeTriggered)  # 啟動前沒有
    active = activate(state, STRIDE).state
    result = _walk(active, (3, 2), (3, 1), (3, 0))
    triggered = of(result, RuleChangeTriggered)
    assert [(t.kind, t.other_id) for t in triggered] == [("pass_through_apply", U2)]
    outcome = of(result, StatusApplied) + of(result, StatusResisted)
    assert [e.target_id for e in outcome] == [U2]
    assert all(e.status_id == "bleed" for e in outcome)


def test_bloodwake_counts_again_on_a_new_move_and_ignores_the_start_tile() -> None:
    state = activate(arena([STRIDE], foes=[(4, 3)]), STRIDE).state  # 起點就和敵人相鄰
    first = _walk(state, (3, 2))  # 離開：踏進的 (3,2) 與 (4,3) 不相鄰
    assert not of(first, RuleChangeTriggered)
    second = _walk(first.state, (3, 3))  # 新的移動、踏回相鄰格
    assert [t.other_id for t in of(second, RuleChangeTriggered)] == [U2]


def test_bloodwake_respects_the_trigger_depth_limit() -> None:
    state = activate(arena([STRIDE], foes=[(4, 2)]), STRIDE).state
    state.ruleset = state.ruleset.model_copy(
        update={"core": state.ruleset.core.model_copy(update={"max_trigger_depth": 0})}
    )
    result = _walk(state, (3, 2))
    assert not of(result, RuleChangeTriggered)
    assert not of(result, StatusApplied) and not of(result, StatusResisted)


# ---------------------------------------------------------------------------
# on_downed_spawn（殘影）
# ---------------------------------------------------------------------------


def _down(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    def run(ctx: Ctx) -> None:
        down_unit(ctx, ctx.state.units[U1])

    return ctx_run(state, run)


def test_afterimage_leaves_a_double_in_the_holders_place_and_turn_slot() -> None:
    state = arena([AFTERIMAGE], foes=[(6, 6)], allies=[(0, 0)])
    _, events = _down(state)
    assert not of(events, UnitSummoned)  # 啟動前沒有
    active = activate(state, AFTERIMAGE).state
    slot = active.turn_order.index(U1)
    after, events = _down(active)
    (trig,) = of(events, RuleChangeTriggered)
    (summoned,) = of(events, UnitSummoned)
    assert trig.kind == "on_downed_spawn" and trig.seq < summoned.seq
    double = after.units[summoned.unit_id]
    assert (summoned.owner_id, summoned.pos, summoned.orphan) == (U1, Pos(x=3, y=3), True)
    assert double.template_id == "summon_afterimage" and double.team is Team.ALLY
    assert after.turn_order.index(double.id) == slot  # 排在持有者原本的位置
    assert summoned.expires_round == active.round + 1  # 持續 2 輪（含倒下的這一輪）


def test_the_double_disappears_at_the_environment_turn_of_its_last_round() -> None:
    active = activate(arena([AFTERIMAGE], allies=[(0, 0)]), AFTERIMAGE).state
    after, events = _down(active)
    (summoned,) = of(events, UnitSummoned)
    stays, events = ctx_run(after, run_environment)  # 第 1 輪的環境回合：還在
    assert stays.units[summoned.unit_id].alive and not of(events, SummonExpired)
    gone, events = ctx_run(at_round(after, 2), run_environment)
    (expired,) = of(events, SummonExpired)
    assert (expired.unit_id, expired.reason) == (summoned.unit_id, "expired")
    assert not gone.units[summoned.unit_id].alive


def test_the_double_fizzles_when_the_holder_falls_into_a_chasm() -> None:
    terrain = "\n".join(["......."] * 3 + ["...x..."] + ["......."] * 3)
    active = activate(arena([AFTERIMAGE], terrain=terrain, holder=(3, 2)), AFTERIMAGE).state
    active.units[U1].pos = Pos(x=3, y=3)  # 已經掉進深淵
    _, events = _down(active)
    assert of(events, RuleChangeTriggered) and not of(events, UnitSummoned)
    (fizzled,) = of(events, EffectFizzled)
    assert fizzled.reason == "summon_blocked"


# ---------------------------------------------------------------------------
# AI 與整場戰鬥
# ---------------------------------------------------------------------------


def _run(build: str, map_id: str, seed: int) -> tuple[Any, Any]:
    from tests.engine.test_zone_ai import _run as run_build  # noqa: PLC0415

    return run_build(build, map_id, seed)


def test_the_ai_activates_a_modifier_legendary_on_its_first_turn() -> None:
    _, run = _run("build_charger", "swamp", 0)
    activated = [e for e in of(run.events, SkillActivated) if e.skill_id == AVATAR]
    assert activated and activated[0].round == 1
    assert activated[0].expires_round == 4


def test_the_ai_activates_kindred_flame_and_its_fire_heals_allies() -> None:
    _, run = _run("build_summoner", "oil_depot", 2)
    assert [e.skill_id for e in of(run.events, SkillActivated)] == [KINDRED]
    mended = [e for e in of(run.events, RuleChangeTriggered) if e.kind == "element_heals_allies"]
    assert mended
    heals = of(run.events, Healed)
    assert any(h.seq == mended[0].seq + 1 and h.target_id == mended[0].other_id for h in heals)


def test_an_afterimage_battle_spawns_the_double_and_replays_exactly() -> None:
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run("build_trapper", "swamp", 1)
    summoned = [e for e in of(run.events, UnitSummoned) if e.orphan]
    assert summoned and run.state.units[summoned[0].unit_id].template_id == "summon_afterimage"
    again = replay(setup, 1, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
