"""放棄、交涉、戰鬥解法的結算（Phase 5B-4b；``docs/phases/Phase5計畫.md`` 19.6）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_quests import _won
from tests.world.test_situations import at_event, thread
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    AffinityChangedEvent,
    EncounterEvent,
    EventResolvedEvent,
    EventSolveAction,
    EventSolvedEvent,
    FightAction,
    RetreatAction,
    ThreadAddedEvent,
    ThreadSpentEvent,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.quests import advance_quests
from trpg.world.solutions import settle_event_combat
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _resolved(events: Sequence[object]) -> EventResolvedEvent:
    return next(e for e in events if isinstance(e, EventResolvedEvent))


def _added(events: Sequence[object]) -> list[str]:
    return [e.thread for e in events if isinstance(e, ThreadAddedEvent)]


def test_abandon_clears_event_without_penalty(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "wounded_peddler")
    result = world_step(library, make_world(), char, EventSolveAction(solution=2), NOON)
    assert result.char.pending_event is None
    assert result.char.supplies == char.supplies and result.char.hp == char.hp
    solved = next(e for e in result.events if isinstance(e, EventSolvedEvent))
    assert solved.solution_kind == "abandon"
    assert _resolved(result.events).outcome == "abandoned"


def test_parley_pays_supplies(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "gang_toll")
    result = world_step(library, make_world(), char, EventSolveAction(solution=2), NOON)
    assert result.char.supplies == char.supplies - 1
    assert _resolved(result.events).outcome == "success"
    assert _added(result.events) == []  # 付錢了事，不留線頭
    broke = char.model_copy(update={"supplies": 0})
    with pytest.raises(WorldActionError, match="補給不足"):
        world_step(library, make_world(), broke, EventSolveAction(solution=2), NOON)


def test_parley_leaves_threads(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "fox_traveler")
    result = world_step(library, make_world(), char, EventSolveAction(solution=0), NOON)
    assert _added(result.events) == ["foxfire_guide"]
    assert result.char.supplies == char.supplies - 1


def test_ferry_favor_replaces_bamboo(library: ContentLibrary, make_char: MakeChar) -> None:
    """骨架 9：持有「商人欠你人情」可以代替青竹節（補給），線頭用掉。"""
    base = at_event(make_char(), "broken_ferry", "ferry_steps")
    char = base.model_copy(update={"threads": (thread("peddler_owes_you"),)})
    action = EventSolveAction(solution=0, use_thread="peddler_owes_you")
    result = world_step(library, make_world(), char, action, NOON)
    assert result.char.supplies == char.supplies
    assert [t.thread for t in result.char.threads] == ["ferryman_daughter"]
    assert any(isinstance(e, ThreadSpentEvent) for e in result.events)
    solved = next(e for e in result.events if isinstance(e, EventSolvedEvent))
    assert (solved.thread_spent, solved.supplies_spent) == ("peddler_owes_you", 0)
    paid = world_step(library, make_world(), char, EventSolveAction(solution=0), NOON)
    assert paid.char.supplies == char.supplies - 2  # 不用人情就付補給
    assert [t.thread for t in paid.char.threads] == ["peddler_owes_you", "ferryman_daughter"]
    with pytest.raises(WorldActionError, match="沒有持有"):
        world_step(library, make_world(), base, action, NOON)
    with pytest.raises(WorldActionError, match="不能用線頭"):
        world_step(
            library,
            make_world(),
            char,
            EventSolveAction(solution=0, use_thread="temple_pass"),
            NOON,
        )


@pytest.mark.parametrize(
    ("skeleton", "solution", "message"),
    [
        ("wounded_peddler", 1, "situation"),
        ("storm_altar", 0, "機遇"),
        ("wounded_peddler", 9, "沒有第 9 個解法"),
    ],
)
def test_rejected_solutions(
    library: ContentLibrary, make_char: MakeChar, skeleton: str, solution: int, message: str
) -> None:
    char = at_event(make_char(), skeleton, "old_pine_altar" if skeleton == "storm_altar" else None)
    with pytest.raises(WorldActionError, match=message):
        world_step(library, make_world(), char, EventSolveAction(solution=solution), NOON)


def test_no_event_rejected(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="沒有事件"):
        world_step(library, make_world(), make_char(), EventSolveAction(solution=0), NOON)


def test_combat_opens_encounter_here(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "wounded_peddler")
    result = world_step(library, make_world(), char, EventSolveAction(solution=0), NOON)
    encounter = result.char.pending_encounter
    assert encounter is not None
    assert (encounter.location, encounter.from_location) == ("ferry_steps", "ferry_steps")
    assert result.char.pending_event is not None
    assert result.char.pending_event.combat_solution == 0
    assert any(isinstance(e, EncounterEvent) for e in result.events)
    assert not any(isinstance(e, EventResolvedEvent) for e in result.events)
    with pytest.raises(WorldActionError):  # 遭遇中不能走
        world_step(library, make_world(), result.char, TravelAction(to="bamboo_path"), NOON)


def test_combat_in_town_rejected(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "wounded_peddler", "mist_ferry")
    with pytest.raises(WorldActionError, match="打不起來"):
        world_step(library, make_world(), char, EventSolveAction(solution=0), NOON)


def test_combat_fight_settles_event(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "wounded_peddler", strong=True)
    world = make_world()
    opened = world_step(library, world, char, EventSolveAction(solution=0), NOON)
    steps = auto_steps(library, opened.char)
    fought = world_step(library, world, opened.char, FightAction(steps=steps), NOON + 60)
    assert fought.char.pending_event is None
    resolved = _resolved(fought.events)
    won = fought.char.last_battle is not None and fought.char.last_battle.won
    assert resolved.outcome == ("success" if won else "failure")
    if won:
        assert _added(fought.events) == ["peddler_owes_you", "wolves_driven_down"]


def test_retreat_is_failure_and_stays(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "wounded_peddler")
    opened = world_step(library, make_world(), char, EventSolveAction(solution=0), NOON)
    result = world_step(library, make_world(), opened.char, RetreatAction(), NOON + 60)
    assert result.char.location == "ferry_steps"
    assert result.char.pending_event is None
    assert _resolved(result.events).outcome == "failure"
    assert _added(result.events) == []


def test_settle_with_win_gives_threads(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(make_char(), "lost_acolyte")
    world = make_world()
    opened = world_step(library, world, char, EventSolveAction(solution=1), NOON)
    after = opened.char.model_copy(update={"pending_encounter": None})
    world, settled, events = settle_event_combat(
        library, world, opened.char, after, _won("rain_terraces"), now=NOON
    )
    assert settled.pending_event is None
    assert _added(events) == ["temple_quarrel"]
    assert _resolved(events).outcome == "success"


def test_event_affinity_follows_event_resolved(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """事件好感度看 ``event_resolved``：護送戰（戰鬥解法）成功，小蓮 +10。"""
    resolved = EventResolvedEvent(
        skeleton="lost_acolyte", location="rain_terraces", solution=1, outcome="success"
    )
    _, events = advance_quests(library, make_world(), make_char(), (resolved,), NOON)
    changed = [e for e in events if isinstance(e, AffinityChangedEvent)]
    assert [(e.npc, e.delta) for e in changed] == [("acolyte_xiaolian", 10)]
    abandoned = resolved.model_copy(update={"outcome": "abandoned"})
    _, none = advance_quests(library, make_world(), make_char(), (abandoned,), NOON)
    assert none == []


# ---------------------------------------------------------------------------
# 戰鬥解法的勝利條件（Phase 5B-4c；Phase5計畫 21.5）
# ---------------------------------------------------------------------------


def _combat_index(library: ContentLibrary, skeleton: str) -> int:
    table = library.world_event_content.events["cloud_ridge"].skeleton_by_id()[skeleton]
    return next(i for i, s in enumerate(table.solutions) if s.kind == "combat")


@pytest.mark.parametrize(
    ("skeleton", "location", "kind"),
    [
        ("lost_acolyte", "rain_terraces", "escape"),  # 骨架 2 護送＝撤離
        ("lost_acolyte", "old_pine_altar", "escape"),  # 沒有固定地圖：從地圖池挑支援撤離的
        ("gang_deserter", "cliff_gang_fort", "defend"),  # 骨架 7 擋追兵＝守點
        ("gang_deserter", "herb_valley", "defend"),
        ("possessed_hunter", "crystal_rift", "defend"),  # 骨架 8 不殺獵人＝守點（代決 5B4c-7）
        ("possessed_hunter", "north_slope", "defend"),
        ("shard_convoy", "crystal_rift", "escape"),  # 骨架 14 押送隊＝撤離
        ("shard_convoy", "sword_tomb", "eliminate"),  # 劍冢的地圖沒有撤離資料 → 全滅（代決 5B4c-8）
        ("wounded_peddler", "ferry_steps", "eliminate"),  # 沒指定：地圖預設
    ],
)
def test_combat_solution_objective(
    library: ContentLibrary, make_char: MakeChar, skeleton: str, location: str, kind: str
) -> None:
    char = at_event(make_char(), skeleton, location)
    action = EventSolveAction(solution=_combat_index(library, skeleton))
    result = world_step(library, make_world(), char, action, NOON)
    encounter = result.char.pending_encounter
    assert encounter is not None
    solution = library.world_event_content.events["cloud_ridge"].skeleton_by_id()[skeleton]
    assert encounter.objective == solution.solutions[action.solution].objective
    setup = prepare_battle(library, result.char).setup
    assert setup.effective_objective.kind == kind


def test_escape_solution_fight_settles(library: ContentLibrary, make_char: MakeChar) -> None:
    """撤離的戰鬥解法照常打完並結算（勝＝我方全員撤離或敵人全倒）。"""
    char = at_event(make_char(), "lost_acolyte", strong=True)
    world = make_world()
    action = EventSolveAction(solution=_combat_index(library, "lost_acolyte"))
    opened = world_step(library, world, char, action, NOON)
    steps = auto_steps(library, opened.char)
    fought = world_step(library, world, opened.char, FightAction(steps=steps), NOON + 60)
    assert fought.char.pending_event is None
    won = fought.char.last_battle is not None and fought.char.last_battle.won
    assert _resolved(fought.events).outcome == ("success" if won else "failure")
