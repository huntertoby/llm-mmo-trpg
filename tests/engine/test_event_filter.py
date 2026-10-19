"""Phase 3-1 3.2：依陣營過濾事件 ``filter_events``。"""

from __future__ import annotations

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_traps import BEAR, CINDER, end_turns, place, scene, walk
from trpg.cli.battle import default_lineup
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.event_filter import event_visible_to, filter_events, view_of_event
from trpg.engine.events import (
    EventBase,
    SkillUsed,
    TrapExpired,
    TrapPlaced,
    TrapTriggered,
    TriggerLimitReached,
    UnitMoved,
)
from trpg.engine.runner import run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Pos, Team
from trpg.sim.matrix import library_with_builds


def _place_events(skill: str = BEAR, xy: tuple[int, int] = (4, 3)) -> list[EventBase]:
    action = UseSkill(unit_id=U1, skill_id=skill, target_pos=Pos(x=xy[0], y=xy[1]))
    return list(resolve(scene(), action).events)


def test_trap_placed_is_only_visible_to_the_owner_team() -> None:
    state = scene()
    events = _place_events()
    (placed,) = [e for e in events if isinstance(e, TrapPlaced)]
    assert event_visible_to(placed, state, Team.ALLY)
    assert not event_visible_to(placed, state, Team.ENEMY)
    assert placed not in filter_events(events, state, Team.ENEMY)
    assert placed in filter_events(events, state, Team.ALLY)


def test_trap_expired_is_only_visible_to_the_owner_team() -> None:
    state = place(scene(), BEAR, (4, 3))
    _, events = end_turns(state, 12)
    expired = [e for e in events if isinstance(e, TrapExpired)]
    assert expired and expired[0].reason == "timeout"
    assert all(event_visible_to(e, state, Team.ALLY) for e in expired)
    assert not any(event_visible_to(e, state, Team.ENEMY) for e in expired)


def test_the_trap_skill_used_event_hides_the_tiles_from_the_other_team() -> None:
    state = scene()
    events = _place_events()
    (used,) = [e for e in events if isinstance(e, SkillUsed)]
    assert used.tiles  # 原事件含格子
    seen = view_of_event(used, state, Team.ENEMY)
    assert isinstance(seen, SkillUsed)
    assert seen.tiles == () and seen is not used  # 替換後的複本
    assert (seen.unit_id, seen.skill_id, seen.name_zh, seen.seq) == (
        used.unit_id,
        used.skill_id,
        used.name_zh,
        used.seq,
    )
    assert used.tiles  # 原事件沒被修改
    assert view_of_event(used, state, Team.ALLY) is used


def test_a_normal_skill_used_event_is_unchanged_for_everyone() -> None:
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(6, 3)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (2, 3), caster_template(["skill_fire_bolt"])),
                spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=999)),
            ],
        ),
        U1,
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U2))
    (used,) = of(result, SkillUsed)
    assert used.tiles
    assert view_of_event(used, state, Team.ENEMY) is used


def test_trigger_limit_from_a_hidden_trap_is_only_visible_to_the_owner_team() -> None:
    state = place(scene(max_depth=0), BEAR, (4, 3))
    result = walk(state, (6, 3), (5, 3), (4, 3), (3, 3))
    (limit,) = of(result, TriggerLimitReached)
    assert event_visible_to(limit, result.state, Team.ALLY)
    assert not event_visible_to(limit, result.state, Team.ENEMY)


def test_trap_triggered_and_its_effects_are_visible_to_everyone() -> None:
    state = place(scene(), BEAR, (4, 3))
    result = walk(state, (6, 3), (5, 3), (4, 3), (3, 3))
    (triggered,) = of(result, TrapTriggered)
    for team in Team:
        seen = filter_events(result.events, result.state, team)
        assert triggered in seen
        assert [e for e in seen if isinstance(e, UnitMoved)] == of(result, UnitMoved)
        assert seen == list(result.events)  # 這段沒有隱藏的事件


def test_seq_values_are_preserved_so_the_filtered_list_has_gaps() -> None:
    state = scene()
    events = _place_events()
    seen = filter_events(events, state, Team.ENEMY)
    assert len(seen) < len(events)
    original = {e.seq for e in events}
    assert {e.seq for e in seen} <= original
    assert [e.seq for e in seen] == sorted(e.seq for e in seen)


def test_cinder_mine_placement_also_hides_tiles() -> None:
    state = scene()
    events = _place_events(CINDER, (3, 3))
    for e in filter_events(events, state, Team.ENEMY):
        assert not isinstance(e, TrapPlaced)
        if isinstance(e, SkillUsed):
            assert e.tiles == ()
    assert U2 in state.units


def _trapper_battle() -> tuple[list[EventBase], BattleState]:
    lib = library_with_builds(library())
    allies = ["build_trapper", *lib.builds.companions][:3]
    default_allies, default_enemies = default_lineup(lib, "open_plain")
    setup = build_setup(lib, "open_plain", allies or default_allies, default_enemies, max_rounds=30)
    run = run_battle(setup, 1, UtilityAI(lib.ai_profiles))
    return run.events, run.state


def test_a_full_battle_leaks_no_untriggered_trap_to_the_other_team() -> None:
    events, state = _trapper_battle()
    placed = [e for e in events if isinstance(e, TrapPlaced)]
    assert placed, "這個種子的戰鬥應該放過陷阱"
    triggered = {(e.pos, e.skill_id) for e in events if isinstance(e, TrapTriggered)}
    never_triggered = [p for p in placed if (p.pos, p.skill_id) not in triggered]
    # 不論放置者是哪一方，對方的視角都不該看到該陷阱的放置、消失與施放格子
    for viewer in Team:
        seen = filter_events(events, state, viewer)
        for e in seen:
            if isinstance(e, TrapPlaced | TrapExpired):
                owner = state.units[e.owner_id].team
                assert owner is viewer
            if isinstance(e, SkillUsed) and state.units[e.unit_id].team is not viewer:
                assert not (state.ruleset.skill_def(e.skill_id).trap and e.tiles)
        for trap in never_triggered:
            if state.units[trap.owner_id].team is not viewer:
                # 該陷阱的放置與過期事件已被濾掉
                assert not any(
                    isinstance(e, TrapPlaced | TrapExpired)
                    and e.pos == trap.pos
                    and e.skill_id == trap.skill_id
                    for e in seen
                )
    # 放置者自己的視角完整保留
    ally_seen = filter_events(events, state, Team.ALLY)
    assert [e for e in events if isinstance(e, TrapPlaced) and e.team is Team.ALLY] == [
        e for e in ally_seen if isinstance(e, TrapPlaced)
    ]
