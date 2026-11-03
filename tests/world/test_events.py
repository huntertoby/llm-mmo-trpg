"""事件出現擲骰（Phase 5B-1；``docs/phases/Phase5計畫.md`` 8.6、8.7）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventFrequency, EventSkeletonTable, WorldEventContent
from trpg.world.actions import (
    EventCheckEvent,
    EventLeftEvent,
    EventTriggeredEvent,
    TravelAction,
)
from trpg.world.clock import day_phase
from trpg.world.events import event_candidates, event_chance
from trpg.world.state import CharacterState, EventTrigger, ThreadState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

NIGHT = next(t for t in range(NOON, NOON + 1800) if day_phase(t) == "night")
"""NOON 之後第一個遊戲夜晚的時間。"""


def with_frequency(library: ContentLibrary, per_step: int, cap: int = 1000) -> ContentLibrary:
    content = library.world_event_content
    assert content.rules is not None
    frequency = EventFrequency(per_step_permille=per_step, max_permille=cap)
    rules = content.rules.model_copy(update={"frequency": frequency})
    return dataclasses.replace(
        library, world_event_content=dataclasses.replace(content, rules=rules)
    )


def with_skeleton(library: ContentLibrary, **skeleton: Any) -> ContentLibrary:
    content = library.world_event_content
    table = content.events["cloud_ridge"]
    data = table.model_dump()
    data["skeletons"] = [*data["skeletons"], skeleton]
    events = {**content.events, "cloud_ridge": EventSkeletonTable.model_validate(data)}
    return dataclasses.replace(
        library, world_event_content=dataclasses.replace(content, events=events)
    )


@pytest.fixture(scope="module")
def always(calm: ContentLibrary) -> ContentLibrary:
    """不遇敵、每一步都出事件（有合格骨架時）的內容庫。"""
    return with_frequency(calm, 1000)


@pytest.fixture(scope="module")
def never(calm: ContentLibrary) -> ContentLibrary:
    return with_frequency(calm, 0)


def _of[T](events: tuple[object, ...], kind: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def test_event_chance(library: ContentLibrary) -> None:
    rules = library.world_event_content.rules
    assert rules is not None
    assert [event_chance(rules.frequency, s) for s in range(6)] == [0, 150, 300, 450, 600, 600]


def test_no_event_rules_skips(calm: ContentLibrary, make_char: MakeChar) -> None:
    lib = dataclasses.replace(calm, world_event_content=WorldEventContent())
    result = world_step(lib, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    assert "event" not in result.char.rng_counters
    assert not _of(result.events, EventCheckEvent)
    assert result.char.event_steps == 0


def test_event_triggers(always: ContentLibrary, make_char: MakeChar) -> None:
    result = world_step(always, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    trigger = result.char.pending_event
    assert trigger is not None
    assert trigger.candidates == ("broken_ferry", "wounded_peddler")
    assert trigger.skeleton in trigger.candidates
    assert trigger.location == "ferry_steps"
    assert trigger.region == "cloud_ridge"
    assert trigger.day_phase == "day"
    assert trigger.at == NOON
    assert trigger.follows_thread is None
    assert result.char.event_steps == 0
    assert result.char.rng_counters["event"] == 1
    (check,) = _of(result.events, EventCheckEvent)
    assert check.triggered
    assert check.steps == 1
    assert check.chance_permille == 1000
    assert _of(result.events, EventTriggeredEvent)[0].trigger == trigger


def test_event_order_in_travel(always: ContentLibrary, make_char: MakeChar) -> None:
    result = world_step(always, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    kinds = [e.kind for e in result.events]
    assert kinds[:4] == ["traveled", "encounter_check", "event_check", "event_triggered"]


def test_night_only_skeleton(always: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    day = event_candidates(always, world, "cloud_ridge", "ferry_steps", NOON)
    night = event_candidates(always, world, "cloud_ridge", "ferry_steps", NIGHT)
    assert "lantern_patrol" not in {s.id for s in day}
    assert "lantern_patrol" in {s.id for s in night}
    result = world_step(always, world, make_char(), TravelAction(to="ferry_steps"), NIGHT)
    trigger = result.char.pending_event
    assert trigger is not None
    assert trigger.candidates == ("broken_ferry", "lantern_patrol", "wounded_peddler")
    assert trigger.day_phase == "night"


@pytest.mark.parametrize(("weather", "expected"), [("rain", True), ("fog", False)])
def test_weather_skeleton(always: ContentLibrary, weather: str, expected: bool) -> None:
    lib = with_rules(
        always,
        weather=[{"region": "cloud_ridge", "day": {weather: 1}, "night": {weather: 1}}],
    )
    ids = {
        s.id for s in event_candidates(lib, make_world(), "cloud_ridge", "old_pine_altar", NIGHT)
    }
    assert ("storm_altar" in ids) is expected
    day_ids = {
        s.id for s in event_candidates(lib, make_world(), "cloud_ridge", "old_pine_altar", NOON)
    }
    assert "storm_altar" not in day_ids


def test_no_candidates_no_event(always: ContentLibrary, make_char: MakeChar) -> None:
    # 雲頂觀是 Boss 地點，不設事件
    result = world_step(
        always,
        make_world(),
        make_char(location="crystal_rift"),
        TravelAction(to="cloud_summit"),
        NOON,
    )
    assert result.char.pending_event is None
    (check,) = _of(result.events, EventCheckEvent)
    assert not check.triggered
    assert result.char.event_steps == 1
    assert result.char.rng_counters["event"] == 1


def test_encounter_step_has_no_event(ambush: ContentLibrary, make_char: MakeChar) -> None:
    lib = with_frequency(ambush, 1000)
    result = world_step(lib, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    assert result.char.pending_encounter is not None
    assert result.char.pending_event is None
    (check,) = _of(result.events, EventCheckEvent)
    assert check.chance_permille == 1000
    assert not check.triggered
    assert result.char.rng_counters["event"] == 1
    assert result.char.event_steps == 1


def test_steps_accumulate(never: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    world = make_world()
    for i, to in enumerate(["hunter_hut", "mist_ferry", "ferry_steps"], start=1):
        result = world_step(never, world, char, TravelAction(to=to), NOON + i)
        char = result.char
        (check,) = _of(result.events, EventCheckEvent)
        assert check.steps == i
        assert char.event_steps == i
    assert char.rng_counters["event"] == 3


def test_steps_reset_after_event(always: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="hunter_hut", event_steps=3)
    result = world_step(always, make_world(), char, TravelAction(to="mist_ferry"), NOON)
    (check,) = _of(result.events, EventCheckEvent)
    assert check.steps == 4
    assert result.char.pending_event is not None
    assert result.char.pending_event.skeleton == "tavern_storyteller"
    assert result.char.event_steps == 0


def test_leaving_drops_pending_event(
    always: ContentLibrary, never: ContentLibrary, make_char: MakeChar
) -> None:
    first = world_step(always, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    pending = first.char.pending_event
    assert pending is not None
    # 事件不擋移動；離開地點＝作罷
    second = world_step(never, make_world(), first.char, TravelAction(to="mist_ferry"), NOON + 1)
    assert second.char.pending_event is None
    (left,) = _of(second.events, EventLeftEvent)
    assert left.skeleton == pending.skeleton
    assert left.location == "ferry_steps"


def test_follows_thread_preferred(always: ContentLibrary, make_char: MakeChar) -> None:
    lib = with_skeleton(
        always,
        id="peddler_returns",
        number=99,
        who_zh="回來道謝的行商",
        want_zh="還人情",
        stakes_zh="一份謝禮",
        locations=["ferry_steps"],
        solutions=[{"kind": "parley"}],
        follows=["wolves_driven_down"],
    )
    thread = ThreadState(
        thread="wolves_driven_down",
        skeleton="wounded_peddler",
        region="cloud_ridge",
        created_at=NOON - 10,
        expires_at=NOON + 1000,
    )
    for counter in range(6):
        char = make_char(threads=(thread,), rng_counters={"event": counter})
        result = world_step(lib, make_world(), char, TravelAction(to="ferry_steps"), NOON)
        trigger = result.char.pending_event
        assert trigger is not None
        assert trigger.skeleton == "peddler_returns"
        assert trigger.follows_thread == "wolves_driven_down"
        assert "peddler_returns" in trigger.candidates


def test_world_thread_also_followed(always: ContentLibrary, make_char: MakeChar) -> None:
    lib = with_skeleton(
        always,
        id="fox_returns",
        number=99,
        who_zh="狐火",
        want_zh="引路",
        stakes_zh="線索",
        locations=["ferry_steps"],
        solutions=[{"kind": "abandon"}],
        follows=["foxfire_guide"],
    )
    thread = ThreadState(
        thread="foxfire_guide",
        skeleton="fox_traveler",
        region="cloud_ridge",
        created_at=NOON - 10,
        expires_at=NOON + 1000,
    )
    world = make_world(threads=(thread,))
    result = world_step(lib, world, make_char(), TravelAction(to="ferry_steps"), NOON)
    assert result.char.pending_event is not None
    assert result.char.pending_event.skeleton == "fox_returns"


def test_expired_thread_not_followed(always: ContentLibrary, make_char: MakeChar) -> None:
    lib = with_skeleton(
        always,
        id="peddler_returns",
        number=99,
        who_zh="回來道謝的行商",
        want_zh="還人情",
        stakes_zh="一份謝禮",
        locations=["ferry_steps"],
        solutions=[{"kind": "parley"}],
        follows=["peddler_owes_you"],
    )
    thread = ThreadState(
        thread="peddler_owes_you",
        skeleton="wounded_peddler",
        region="cloud_ridge",
        created_at=NOON - 10,
        expires_at=NOON,
    )
    picks = set()
    for counter in range(12):
        char = make_char(threads=(thread,), rng_counters={"event": counter})
        trigger = world_step(lib, make_world(), char, TravelAction(to="ferry_steps"), NOON)
        assert trigger.char.pending_event is not None
        assert trigger.char.pending_event.follows_thread is None
        picks.add(trigger.char.pending_event.skeleton)
    assert len(picks) > 1


def test_same_input_same_result(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="ferry_steps", event_steps=2)
    a = world_step(library, make_world(), char, TravelAction(to="bamboo_path"), NOON)
    b = world_step(library, make_world(), char, TravelAction(to="bamboo_path"), NOON)
    assert a.char == b.char
    assert a.events == b.events


def test_seed_changes_picks(always: ContentLibrary, make_char: MakeChar) -> None:
    picks = {
        world_step(
            always, make_world(season_seed=seed), make_char(), TravelAction(to="ferry_steps"), NOON
        ).char.pending_event
        for seed in range(12)
    }
    assert len({p.skeleton for p in picks if p is not None}) == 2


def test_trigger_candidates_must_be_sorted() -> None:
    with pytest.raises(ValueError, match="candidates"):
        EventTrigger(
            region="cloud_ridge",
            location="ferry_steps",
            skeleton="a",
            candidates=("b", "a"),
            weather="rain",
            day_phase="day",
            at=0,
        )


@pytest.mark.parametrize(
    ("start", "location", "thread", "expected"),
    [
        ("sword_tomb", "crystal_rift", "scarface_grudge", "shard_convoy"),
        ("sword_tomb", "crystal_rift", "temple_traitor", "shard_convoy"),
        ("sword_tomb", "crystal_rift", "shards_under_den", "shard_convoy"),
        ("bamboo_path", "rain_terraces", "wolves_driven_down", "gang_toll"),
    ],
)
def test_cloud_ridge_follows_picks_following_skeleton(
    always: ContentLibrary,
    *,
    make_char: MakeChar,
    start: str,
    location: str,
    thread: str,
    expected: str,
) -> None:
    """18.4 補充的 follows 對照：持有該線頭時，接它的骨架被優先選中（用雲嶺真實資料）。"""
    held = ThreadState(
        thread=thread,
        skeleton="x",
        region="cloud_ridge",
        created_at=NOON - 10,
        expires_at=NOON + 1000,
    )
    for counter in range(8):
        char = make_char(location=start, threads=(held,), rng_counters={"event": counter})
        result = world_step(always, make_world(), char, TravelAction(to=location), NOON)
        trigger = result.char.pending_event
        assert trigger is not None
        assert trigger.skeleton == expected
        assert trigger.follows_thread == thread
        assert len(trigger.candidates) >= 2  # 沒有線頭時還有別的骨架可選
