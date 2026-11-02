"""NPC 好感度、聊天內容與酒館傳聞（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.6、16.8）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_narration import narrate, story
from tests.world.test_situations import act, at_event, sure
from trpg.content.library import ContentLibrary
from trpg.content.world_quests import WorldQuestContent
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AffinityChangedEvent,
    RumorsHeardEvent,
    TalkAction,
    TalkedEvent,
    TavernAction,
)
from trpg.world.affinity import (
    DEFAULT_AFFINITY_RULES,
    affinity_of,
    change_affinity,
    rank_of,
    talk_entries,
)
from trpg.world.clock import refresh_day
from trpg.world.errors import WorldActionError
from trpg.world.narration import narration_problems
from trpg.world.social import week_rumors
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

DAY = 86_400


@pytest.mark.parametrize(
    ("value", "rank"),
    [
        (-100, "hostile"),
        (-50, "hostile"),
        (-49, "cold"),
        (-10, "cold"),
        (-9, "neutral"),
        (0, "neutral"),
        (19, "neutral"),
        (20, "friendly"),
        (59, "friendly"),
        (60, "trusted"),
        (100, "trusted"),
    ],
)
def test_rank_thresholds_116(
    library: ContentLibrary, make_char: MakeChar, value: int, rank: str
) -> None:
    assert rank_of(library, make_char(affinity={"granny_du": value}), "granny_du") == rank
    assert DEFAULT_AFFINITY_RULES.rank_of(value) == rank


def test_change_clamps_and_reports(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert affinity_of(char, "granny_du") == 0
    char, event = change_affinity(library, char, "granny_du", 90, "quest:x")
    assert char.affinity == {"granny_du": 90}
    assert (event.from_rank, event.rank, event.delta) == ("neutral", "trusted", 90)
    char, event = change_affinity(library, char, "granny_du", 50, "quest:x")
    assert char.affinity["granny_du"] == 100 and event.delta == 10
    char, event = change_affinity(library, char, "granny_du", -300, "quest:x")
    assert char.affinity["granny_du"] == -100


def test_event_affinity_from_situation(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = sure(library, "acolyte_find_way", "failure")
    char = at_event(make_char(), "lost_acolyte", strong=True)
    action = act("acolyte_find_way", attribute=Attribute.WIS, method="tracking")
    result = world_step(lib, make_world(), char, action, NOON)
    changed = [e for e in result.events if isinstance(e, AffinityChangedEvent)]
    assert [(e.npc, e.delta, e.source) for e in changed] == [
        ("acolyte_xiaolian", -5, "event:lost_acolyte")
    ]
    assert result.char.affinity == {"acolyte_xiaolian": -5}


def test_situation_without_table_row_no_affinity(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    lib = sure(library, "peddler_safe_path", "success")
    char = at_event(make_char(), "wounded_peddler", strong=True)
    action = act("peddler_safe_path", attribute=Attribute.WIS, method="tracking")
    result = world_step(lib, make_world(), char, action, NOON)
    assert not any(isinstance(e, AffinityChangedEvent) for e in result.events)
    assert result.char.affinity == {}


# ---------------------------------------------------------------------------
# 聊天
# ---------------------------------------------------------------------------


def _talk(library: ContentLibrary, char: CharacterState, npc: str) -> TalkedEvent:
    # 今天已經聊過（5B-4b 每天第一次聊天 +3 另測，見 test_affinity_gain.py）
    char = char.model_copy(update={"talk_days": {npc: refresh_day(NOON)}})
    result = world_step(library, make_world(), char, TalkAction(npc=npc), NOON)
    assert result.char == char  # 今天聊過了：聊天不改狀態
    event = result.events[0]
    assert isinstance(event, TalkedEvent)
    return event


@pytest.mark.parametrize(
    ("value", "entries", "available"),
    [
        (-30, (), ()),
        (0, ("liu_rumor",), ()),
        (20, ("liu_rumor", "liu_cave_entry"), ("hidden_elixir_cave",)),
        (60, ("liu_rumor", "liu_cave_entry", "liu_secret"), ("hidden_elixir_cave",)),
    ],
)
def test_talk_filters_by_rank(
    library: ContentLibrary,
    make_char: MakeChar,
    value: int,
    entries: tuple[str, ...],
    available: tuple[str, ...],
) -> None:
    char = make_char(affinity={"shopkeeper_liu": value})
    event = _talk(library, char, "shopkeeper_liu")
    assert event.entries == entries
    assert event.quests_available == available


def test_granny_tells_secret_door_only_when_trusted(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    # 5B-4b：祕密只說到「年輕時是斷崖幫的人」，暗門要由解鎖的事件結果給（18.7.7）
    neutral = talk_entries(library, make_char(), "granny_du")
    assert all(e.kind != "secret" for e in neutral)
    trusted = talk_entries(library, make_char(affinity={"granny_du": 60}), "granny_du")
    secret = next(e for e in trusted if e.kind == "secret")
    assert "斷崖幫" in secret.text_zh and "暗門" not in secret.text_zh
    assert secret.unlocks_skeleton == "granny_past"


def test_talk_rejections(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="不在這裡"):
        world_step(library, make_world(), make_char(), TalkAction(npc="scarface"), NOON)
    with pytest.raises(WorldActionError, match="沒有 NPC"):
        world_step(library, make_world(), make_char(), TalkAction(npc="nobody"), NOON)


def test_trusted_secret_not_forbidden_in_chat(library: ContentLibrary, make_char: MakeChar) -> None:
    secret = "年輕時是斷崖幫的人"
    action = narrate("chat", story(text_zh=f"婆婆說，她{secret}。"), npc="granny_du")
    neutral = make_char()
    assert any(
        secret in p for p in narration_problems(library, make_world(), neutral, action, NOON)
    )
    trusted = make_char(affinity={"granny_du": 60})
    assert narration_problems(library, make_world(), trusted, action, NOON) == []
    other = narrate("chat", story(text_zh="掌櫃說他偷偷收購源晶碎片。"), npc="shopkeeper_liu")
    assert narration_problems(library, make_world(), trusted, other, NOON)  # 別人的祕密仍禁止


def test_without_social_content(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = dataclasses.replace(library, world_quests=WorldQuestContent())
    event = _talk(lib, make_char(), "granny_du")
    assert event.entries == ()
    assert event.rank == "neutral"


# ---------------------------------------------------------------------------
# 酒館
# ---------------------------------------------------------------------------


def test_tavern_rumors_same_for_everyone_this_week(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    a = world_step(library, world, make_char("alice"), TavernAction(), NOON)
    b = world_step(library, world, make_char("bob", wis=18), TavernAction(), NOON + 2 * DAY)
    heard_a, heard_b = a.events[0], b.events[0]
    assert isinstance(heard_a, RumorsHeardEvent) and isinstance(heard_b, RumorsHeardEvent)
    assert heard_a == heard_b
    assert heard_a.week == 0
    assert len(heard_a.rumors) == 3
    assert list(heard_a.rumors) == sorted(heard_a.rumors)
    assert a.char == make_char("alice")  # 不改狀態、不耗角色亂數


def test_tavern_changes_weekly(library: ContentLibrary) -> None:
    world = make_world()
    weeks = {week_rumors(library, world, "cloud_ridge", NOON + w * 7 * DAY) for w in range(6)}
    assert {w for w, _ in weeks} == set(range(6))
    assert len({tuple(r.id for r in rumors) for _, rumors in weeks}) > 1


def test_tavern_only_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="酒館"):
        world_step(library, make_world(), make_char(location="ferry_steps"), TavernAction(), NOON)
