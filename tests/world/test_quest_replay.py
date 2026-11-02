"""任務、三選一、聊天、酒館的日誌重播（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.6、16.8）。"""

from __future__ import annotations

import json
from collections.abc import Callable

from tests.world.helpers import NOON, make_world
from tests.world.test_situations import act, at_event, thread
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AcceptQuestAction,
    EventSolveAction,
    FightAction,
    OfferPickAction,
    TalkAction,
    TavernAction,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, dumps_world, loads_char, loads_log
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def test_quest_log_replays_identically(ambush: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    start = make_char().model_copy(
        update={
            "affinity": {"shopkeeper_liu": 25},
            "threads": (thread("missing_went_to_rift", "lantern_patrol"),),
        }
    )
    char = start
    entries: list[WorldLogEntry] = []
    now = NOON

    def act(action: WorldAction) -> None:
        nonlocal char, world, now
        now += 60
        result = world_step(ambush, world, char, action, now)
        char, world = result.char, result.world
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id="alice", action=action)
        )

    act(AcceptQuestAction(quest="starter_ferry"))
    act(AcceptQuestAction(quest="main_mist_rift"))  # 線頭已持有：接了立刻完成第 1 步
    assert char.quest_state("main_mist_rift").steps_done == 1  # type: ignore[union-attr]
    act(TalkAction(npc="shopkeeper_liu"))
    act(AcceptQuestAction(quest="hidden_elixir_cave"))
    act(TavernAction())
    act(TravelAction(to="ferry_steps"))
    assert char.pending_encounter is not None
    act(FightAction(steps=auto_steps(ambush, char)))
    if char.pending_offers:
        act(OfferPickAction(pick=0))

    restored = loads_log(dumps_log(entries))
    first = replay(ambush, make_world(), {"alice": start}, entries)
    second = replay(ambush, make_world(), {"alice": start}, restored)
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert dumps_world(first.world) == dumps_world(second.world)
    assert first.events == second.events
    assert loads_char(dumps_char(char)) == char  # 新欄位存檔往返


def test_old_character_without_quest_fields_loads(make_char: MakeChar) -> None:
    char = make_char()
    text = dumps_char(char)
    for key in ('"quests"', '"affinity"', '"pending_offers"', '"offers_made"', '"story_flags"'):
        assert key in text

    data = json.loads(text)
    for key in ("quests", "affinity", "pending_offers", "offers_made", "story_flags"):
        data.pop(key)
    assert loads_char(json.dumps(data)) == char


def test_5b4b_log_replays_identically(calm: ContentLibrary, make_char: MakeChar) -> None:
    """5B-4b：交涉（人情抵用）→ 移動 → 到期結局 → 聊天解鎖 → 祕密事件判定，重播逐字相同。"""
    world = make_world()
    base = at_event(make_char(), "broken_ferry", "ferry_steps")
    start = base.model_copy(
        update={
            "affinity": {"granny_du": 70},
            "threads": (
                thread("scarface_grudge", "gang_toll", NOON - 259_000),
                thread("peddler_owes_you"),
            ),
        }
    )
    char = start
    entries: list[WorldLogEntry] = []
    now = NOON

    def step(action: WorldAction) -> None:
        nonlocal char, world, now
        now += 300
        result = world_step(calm, world, char, action, now)
        char, world = result.char, result.world
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id="alice", action=action)
        )

    step(EventSolveAction(solution=0, use_thread="peddler_owes_you"))
    step(TravelAction(to="mist_ferry"))
    step(TalkAction(npc="granny_du"))
    assert "scarface_rises" in char.story_flags  # 到期結局
    assert char.unlocked_skeletons == ("granny_past",)
    if char.pending_event is not None and char.pending_event.skeleton == "granny_past":
        step(act("granny_parley", attribute=Attribute.WIL, method="parley"))

    restored = loads_log(dumps_log(entries))
    first = replay(calm, make_world(), {"alice": start}, entries)
    second = replay(calm, make_world(), {"alice": start}, restored)
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert first.events == second.events
    assert loads_char(dumps_char(char)) == char
