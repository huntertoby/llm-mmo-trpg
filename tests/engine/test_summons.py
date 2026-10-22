"""召喚（Phase 3D-4a）：``summon`` 原語、行動順序、到期、召喚者離場、上限、勝負條件、源力。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import SkillDef
from trpg.engine import (
    BattleState,
    EndTurn,
    ResolveResult,
    UseSkill,
    legal_actions,
    project_for,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.context import Ctx
from trpg.engine.event_filter import filter_events
from trpg.engine.events import (
    EventBase,
    SourceChanged,
    SummonExpired,
    TurnStarted,
    UnitDowned,
    UnitEscaped,
    UnitSummoned,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.objectives import check_battle_end, check_round_end
from trpg.engine.source import credit_elite_kill
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
SID = "skill_t_summon"
FLAT = "\n".join(["0000000"] * 7)
SKELETON = "summon_skeleton_warrior"
SPIRIT = "summon_elemental_spirit"


def of[E: EventBase](events: Sequence[EventBase] | ResolveResult, kind: type[E]) -> list[E]:
    items = events.events if isinstance(events, ResolveResult) else events
    return [e for e in items if isinstance(e, kind)]


def summon_skill(unit: str = SKELETON, duration: int = 2, **extra: Any) -> SkillDef:
    effect: dict[str, Any] = {"type": "summon", "unit": unit, "duration": duration, **extra}
    return make_skill(SID, {"type": "ground_tile", "range": 4}, [effect])


def arena(
    skill: SkillDef | None = None,
    *,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    terrain: str | None = None,
    objective: dict[str, object] | None = None,
    foe_hp: int = 200,
    foe_tags: Sequence[str] = (),
) -> BattleState:
    """U1 是施放者（我方法師，裝備 ``skill``，站在 (0, 3)）；之後是 ``foes``（不反應）。"""
    skill = skill or summon_skill()
    m = make_map(FLAT, terrain, ally=[(0, 3)], enemy=list(foes), objective=objective)
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill.id]))]
    for xy in foes:
        spawns.append(spawn(Team.ENEMY, xy, no_reactions(max_hp=foe_hp, tags=list(foe_tags))))
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def cast(state: BattleState, x: int, y: int, unit_id: UnitId = U1) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=unit_id, skill_id=SID, target_pos=Pos(x=x, y=y)))


def end(state: BattleState) -> ResolveResult:
    assert state.active_unit is not None
    return resolve(state, EndTurn(unit_id=state.active_unit))


def summons(state: BattleState) -> list[UnitId]:
    return [u.id for u in state.units_sorted() if u.owner_id is not None and u.alive]


def ready(state: BattleState) -> BattleState:
    """回傳複本：U1 的技能冷卻清空、AP 補滿（同一回合連續施放）。"""
    s = state.clone()
    unit = s.units[U1]
    unit.cooldowns = {}
    unit.ap = s.ruleset.core.ap_per_turn
    return s


# ---------------------------------------------------------------------------
# 召喚與行動順序
# ---------------------------------------------------------------------------


def test_summon_places_an_allied_unit_owned_by_the_caster() -> None:
    result = cast(arena(), 2, 3)
    [event] = of(result, UnitSummoned)
    state = result.state
    summon = state.units[event.unit_id]
    assert (event.owner_id, event.template_id, event.team) == (U1, SKELETON, Team.ALLY)
    assert summon.xy == (2, 3) and summon.team is Team.ALLY and summon.owner_id == U1
    assert (
        summon.name_zh == "骷髏戰士1"
        and summon.max_hp == 23 * state.ruleset.core.summon_role_hp_permille["melee"] // 1000
        and summon.source == 0
    )
    assert summon.ai_profile == "brute" and summon.is_summon
    assert summon.summon_expires_round == state.round + 2 == event.expires_round
    assert state.unit_at(2, 3) is summon


def test_the_summon_acts_right_after_its_owner_without_rolling_initiative() -> None:
    state = cast(arena(foes=((6, 6), (6, 5))), 2, 3).state
    sid = summons(state)[0]
    order = state.turn_order
    assert order[order.index(U1) + 1] == sid
    after = end(state)
    assert after.state.active_unit == sid
    assert of(after, TurnStarted)[0].unit_id == sid


def test_summons_of_the_same_owner_queue_in_summon_order() -> None:
    state = cast(arena(summon_skill(duration=3)), 2, 3).state
    state = cast(ready(state), 2, 4).state
    first, second = summons(state)
    order = state.turn_order
    at = order.index(U1)
    assert order[at + 1 : at + 3] == [first, second]


def test_summon_site_must_be_empty_standable_and_not_deadly() -> None:
    terrain = "\n".join(["......."] * 3 + ["...x..."] + ["......."] * 3)
    state = arena(terrain=terrain, foes=((2, 3),))
    for xy, why in (((2, 3), "已有單位"), ((3, 3), "不可站立")):
        with pytest.raises(IllegalActionError, match=why):
            cast(state, *xy)
    picks = {
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_pos is not None
    }
    assert (1, 3) in picks and (2, 3) not in picks and (3, 3) not in picks


# ---------------------------------------------------------------------------
# 到期、召喚者離場、上限
# ---------------------------------------------------------------------------


def _play_rounds(state: BattleState, rounds: int) -> tuple[BattleState, list[EventBase]]:
    """所有單位直接結束回合，直到經過 ``rounds`` 輪（回傳狀態與事件）。"""
    events: list[EventBase] = []
    target = state.round + rounds
    while state.round < target and not state.ended:
        result = end(state)
        events += result.events
        state = result.state
    return state, events


def test_the_summon_acts_duration_times_and_expires_at_the_owner_turn_end() -> None:
    state = cast(arena(summon_skill(duration=2)), 2, 3).state
    sid = summons(state)[0]
    state, events = _play_rounds(state, 3)
    assert sum(1 for e in of(events, TurnStarted) if e.unit_id == sid) == 2
    [gone] = of(events, SummonExpired)
    assert (gone.unit_id, gone.owner_id, gone.reason) == (sid, U1, "expired")
    # 在召喚者第 2 輪之後那一輪（施放輪 ＋ 2）的回合結束時消失，緊接在 U1 的 turn_ended 之前
    index = events.index(gone)
    assert events[index + 1].type == "turn_ended" and events[index + 1].unit_id == U1  # type: ignore[attr-defined]
    assert gone.round == 1 + 2
    unit = state.units[sid]
    assert unit.dismissed and not unit.alive and sid not in state.turn_order
    assert state.unit_at(2, 3) is None


def test_the_summon_disappears_when_its_owner_goes_down() -> None:
    state = cast(arena(), 2, 3).state
    sid = summons(state)[0]
    ctx = Ctx(state.clone())
    events = down_unit(ctx, ctx.state.units[U1])
    [gone] = of(events, SummonExpired)
    assert (gone.unit_id, gone.reason) == (sid, "owner_gone")
    assert ctx.state.units[sid].dismissed and sid not in ctx.state.turn_order
    assert not of(events, UnitDowned)[1:]  # 召喚物消失不是倒下


def test_the_oldest_summon_disappears_over_the_limit() -> None:
    state = cast(arena(summon_skill(duration=3)), 2, 3).state
    state = cast(ready(state), 2, 4).state
    first, second = summons(state)
    result = cast(ready(state), 2, 2)
    [gone] = of(result, SummonExpired)
    assert (gone.unit_id, gone.reason) == (first, "limit")
    [new] = of(result, UnitSummoned)
    state = result.state
    assert summons(state) == [second, new.unit_id]
    at = state.turn_order.index(U1)
    assert state.turn_order[at + 1 : at + 3] == [second, new.unit_id]
    assert state.turn_order[state.turn_pos] == U1  # 插入與移除後仍指向施放者


def test_the_limit_comes_from_the_core_rules() -> None:
    lib = library()
    assert lib.ruleset.core.summon_limit_per_owner == 2
    skill = summon_skill(duration=3)
    m = make_map(FLAT, ally=[(0, 3)], enemy=[(6, 6)])
    spawns = [
        spawn(Team.ALLY, (0, 3), caster_template([skill.id])),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=200)),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill], summon_limit_per_owner=1), U1)
    state = cast(state, 2, 3).state
    result = cast(ready(state), 2, 4)
    assert [e.reason for e in of(result, SummonExpired)] == ["limit"]
    assert len(summons(result.state)) == 1


# ---------------------------------------------------------------------------
# 勝負條件、撤離、源力
# ---------------------------------------------------------------------------


def _with_enemy_summon(state: BattleState) -> tuple[BattleState, UnitId]:
    """讓敵人 U2 召喚一隻元素之靈（直接用引擎函式，敵人沒有召喚技能）。"""
    from trpg.engine.summons import summon_unit  # noqa: PLC0415

    ctx = Ctx(state.clone())
    [event] = of(summon_unit(ctx, ctx.state.units[U2], SPIRIT, (5, 5), 3, SID), UnitSummoned)
    return ctx.state, event.unit_id


def test_victory_ignores_summons() -> None:
    state, spirit = _with_enemy_summon(arena())
    state.units[U2].downed = True  # 敵方只剩召喚物（不經 down_unit，召喚物不會跟著消失）
    ctx = Ctx(state)
    assert check_battle_end(ctx) and state.winner is Team.ALLY and state.end_reason == "eliminate"
    assert state.units[spirit].alive


def test_an_ally_side_of_only_summons_loses() -> None:
    state = cast(arena(), 2, 3).state
    state.units[U1].downed = True  # 我方只剩召喚物
    assert check_battle_end(Ctx(state)) and state.winner is Team.ENEMY


def test_an_enemy_summon_on_the_defend_point_does_not_take_it() -> None:
    objective = {"kind": "defend", "rounds": 5, "tiles": [[5, 5]]}
    state, _ = _with_enemy_summon(arena(objective=objective))
    assert not check_round_end(Ctx(state)) and not state.ended


def test_a_summon_cannot_escape() -> None:
    objective = {"kind": "escape", "rounds": 5, "tiles": [[2, 3]]}
    result = cast(arena(objective=objective), 2, 3)
    sid = summons(result.state)[0]
    from trpg.engine.effects import MoveUnitEffect, execute  # noqa: PLC0415

    ctx = Ctx(result.state.clone())
    ctx.state.units[sid].pos = Pos(x=1, y=1)
    execute(ctx, [MoveUnitEffect(unit_id=sid, dest=(2, 3), mode="walk")])
    assert not of(ctx.events, UnitEscaped) and ctx.state.units[sid].alive


def test_summons_have_no_source() -> None:
    state = cast(arena(), 2, 3).state
    sid = summons(state)[0]
    ctx = Ctx(state.clone())
    elite = ctx.state.units[U2]
    elite.tags = (*elite.tags, "elite")
    assert credit_elite_kill(ctx, elite, sid) == []
    assert not of(ctx.events, SourceChanged)
    assert credit_elite_kill(ctx, elite, U1) != []  # 召喚者自己擊倒仍照常 +1


def test_summons_do_not_take_source_wells() -> None:
    from trpg.engine.source import take_source_well  # noqa: PLC0415

    state = cast(arena(), 2, 3).state
    sid = summons(state)[0]
    ctx = Ctx(state.clone())
    ctx.state.source_wells = ((2, 3),)
    assert take_source_well(ctx, ctx.state.units[sid]) == []
    assert ctx.state.source_wells == ((2, 3),)


# ---------------------------------------------------------------------------
# 序列化、視圖、事件過濾
# ---------------------------------------------------------------------------


def test_summons_survive_serialization_and_replay_resolution() -> None:
    result = cast(arena(summon_skill(duration=1)), 2, 3)
    state = state_from_json(state_to_json(result.state))
    assert state_to_json(state) == state_to_json(result.state)
    sid = summons(state)[0]
    assert state.units[sid].owner_id == U1 and state.ruleset.summon_def(SKELETON)
    after, _ = _play_rounds(state, 2)
    assert after.units[sid].dismissed
    again = state_from_json(state_to_json(after))
    assert again.units[sid].dismissed and not again.units[sid].alive


def test_views_show_summons_and_dismissal_to_both_teams() -> None:
    result = cast(arena(summon_skill(duration=1)), 2, 3)
    sid = summons(result.state)[0]
    for team in Team:
        view = project_for(result.state, team)
        unit = next(u for u in view.units if u.id == sid)
        assert (unit.owner_id, unit.summon_expires_round, unit.dismissed) == (U1, 2, False)
        assert sid in view.turn_order
        assert of(filter_events(result.events, result.state, team), UnitSummoned)
    after, events = _play_rounds(result.state, 2)
    for team in Team:
        view = project_for(after, team)
        unit = next(u for u in view.units if u.id == sid)
        assert unit.dismissed and sid not in view.turn_order
        assert of(filter_events(events, after, team), SummonExpired)


def test_battle_result_excludes_summons() -> None:
    from trpg.engine import battle_result  # noqa: PLC0415

    state = cast(arena(), 2, 3).state
    assert [a.unit_id for a in battle_result(state).allies] == [U1]
