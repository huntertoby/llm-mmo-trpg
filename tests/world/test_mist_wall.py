"""6E-1 霧牆（#122，21.10 第 18 條）：主線 ``main_mist_rift`` 的 ``rift_battle`` 完成前，源晶裂痕
往雲頂觀的山門出口走不過去；有 ``mist_rift_done`` 的角色一直開著；只看自己的主線進度。

用正式的源晶裂痕實地地圖（拿掉看得見的敵人，避免開打），角色站在山門出口 (21, 0) 下面一格。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.world_field_view import field_view
from trpg.api.world_presenter import event_lines
from trpg.content.library import ContentLibrary
from trpg.world.actions import TraveledEvent
from trpg.world.field import FieldCtx, exit_open
from trpg.world.field_actions import ExitBlockedEvent, WalkAction, WalkedEvent
from trpg.world.field_things import object_status
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.state import CharacterState, FieldPos, QuestState, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]

RIFT = "crystal_rift"
BELOW_GATE: XY = (21, 1)
GATE: XY = (21, 0)
QUEST = "main_mist_rift"
RIFT_BATTLE_INDEX = 3
"""``rift_battle`` 是主線的第 4 步（``steps_done`` 超過 3＝這一步完成）。"""
NOTICE = "霧太濃，還過不去。主線：先查清源晶裂痕"


@pytest.fixture(scope="module")
def rift_lib(field_library: ContentLibrary) -> ContentLibrary:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    maps = {
        k: m.model_copy(update={"spawns": ()}) if m.place in (RIFT, "cloud_summit") else m
        for k, m in calm.field_maps.items()
    }
    return dataclasses.replace(calm, field_maps=maps)


def _char(library: ContentLibrary, name: str = "alice", **updates: Any) -> CharacterState:
    char = new_character(library, name, hero(library), region="cloud_ridge")
    pos = FieldPos(map=RIFT, x=BELOW_GATE[0], y=BELOW_GATE[1], facing="n")
    return char.model_copy(update={"location": RIFT, "field": pos, **updates})


def _quest(steps_done: int, *, done: bool = False) -> tuple[QuestState, ...]:
    return (QuestState(quest=QUEST, steps_done=steps_done, done=done, started_at=NOON),)


def _walk(library: ContentLibrary, char: CharacterState, world: WorldState | None = None) -> Any:
    return world_step(library, world or make_world(), char, WalkAction(path=(GATE,)), NOON)


def test_rift_battle_index_matches_content(rift_lib: ContentLibrary) -> None:
    quest = rift_lib.world_quests.quest("cloud_ridge", QUEST)
    assert quest is not None
    assert [s.id for s in quest.steps].index("rift_battle") == RIFT_BATTLE_INDEX
    gate = next(e for e in rift_lib.field_maps[RIFT].exits if e.to == "cloud_summit").gate
    assert gate is not None and gate.notice_zh() == NOTICE


@pytest.mark.parametrize(
    ("updates", "opens"),
    [
        ({}, False),  # 還沒接主線
        ({"quests": _quest(0)}, False),
        ({"quests": _quest(RIFT_BATTLE_INDEX)}, False),  # 停在第 1～3 步之後、第 4 步還沒打
        ({"quests": _quest(RIFT_BATTLE_INDEX + 1)}, True),  # 第 4 步打贏
        ({"quests": _quest(5, done=True)}, True),
        ({"story_flags": ("mist_rift_done",)}, True),  # 打過 Boss、舊存檔
    ],
)
def test_gate_blocks_until_rift_battle(
    rift_lib: ContentLibrary, updates: dict[str, Any], opens: bool
) -> None:
    char = _char(rift_lib, **updates)
    result = _walk(rift_lib, char)
    blocked = [e for e in result.events if isinstance(e, ExitBlockedEvent)]
    if opens:
        assert not blocked
        assert result.char.location == "cloud_summit"
        assert any(isinstance(e, TraveledEvent) for e in result.events)
        return
    # 不換圖、不移動、不算一步（沒有 travel、時間與補給不變）
    assert [(e.exit, e.text_zh) for e in blocked] == [("to_cloud_summit", NOTICE)]
    walked = next(e for e in result.events if isinstance(e, WalkedEvent))
    assert walked.steps == () and (walked.x, walked.y) == BELOW_GATE
    assert not any(isinstance(e, TraveledEvent) for e in result.events)
    assert result.char.location == RIFT
    assert result.char.field is not None
    assert (result.char.field.x, result.char.field.y) == BELOW_GATE
    assert result.char.supplies == char.supplies
    assert result.char.rng_counters == char.rng_counters


def test_longer_path_stops_before_the_gate(rift_lib: ContentLibrary) -> None:
    start = _char(rift_lib).model_copy(update={"field": FieldPos(map=RIFT, x=21, y=3)})
    result = world_step(
        rift_lib, make_world(), start, WalkAction(path=((21, 2), (21, 1), (21, 0))), NOON
    )
    walked = next(e for e in result.events if isinstance(e, WalkedEvent))
    assert walked.steps == ((21, 2), (21, 1)) and walked.stopped == "end"
    assert any(isinstance(e, ExitBlockedEvent) for e in result.events)
    assert result.char.field is not None and (result.char.field.x, result.char.field.y) == (21, 1)


def test_only_own_progress_counts(rift_lib: ContentLibrary) -> None:
    """別人打過、世界旗標有 ``mist_rift_done`` 都不算；只看自己的任務與劇情旗標。"""
    world = make_world().model_copy(update={"flags": ("mist_rift_done",)})
    alice = _char(rift_lib)
    bob = _char(rift_lib, "bob", story_flags=("mist_rift_done",), quests=_quest(5, done=True))
    found = rift_lib.field_maps[RIFT]
    exit_ = next(e for e in found.exits if e.id == "to_cloud_summit")
    assert exit_open(rift_lib, bob, found, exit_)
    assert not exit_open(rift_lib, alice, found, exit_)
    result = _walk(rift_lib, alice, world)
    assert any(isinstance(e, ExitBlockedEvent) for e in result.events)


def test_mist_wall_card_follows_progress(rift_lib: ContentLibrary) -> None:
    found = rift_lib.field_maps[RIFT]
    ctx = FieldCtx(library=rift_lib, world=make_world(), map=found, now=NOON)
    spot = next(o for o in found.situation_objects if o.id == "rift_mist_wall")
    closed = object_status(ctx, _char(rift_lib), spot).note_zh
    opened = object_status(ctx, _char(rift_lib, story_flags=("mist_rift_done",)), spot).note_zh
    assert closed.startswith(spot.note_zh) and NOTICE in closed
    assert NOTICE not in opened and opened == "霧牆散開了，山門後的石階一路通往雲頂觀。"


def test_other_exits_unaffected(rift_lib: ContentLibrary) -> None:
    char = _char(rift_lib).model_copy(update={"field": FieldPos(map=RIFT, x=1, y=12)})
    result = world_step(rift_lib, make_world(), char, WalkAction(path=((0, 12),)), NOON)
    assert result.char.location == "north_slope"
    assert not any(isinstance(e, ExitBlockedEvent) for e in result.events)


def test_blocked_walk_replays(rift_lib: ContentLibrary) -> None:
    world = make_world()
    char = _char(rift_lib)
    cid = char.character_id
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id=cid, action=WalkAction(path=(GATE,))),
        WorldLogEntry(
            seq=2, now=NOON, character_id=cid, action=WalkAction(path=((20, 1), (20, 0)))
        ),
    ]
    first = replay(rift_lib, world, {char.character_id: char}, entries)
    second = replay(rift_lib, world, {char.character_id: char}, entries)
    assert [e.model_dump(mode="json") for _, e in first.events] == [
        e.model_dump(mode="json") for _, e in second.events
    ]
    assert first.characters == second.characters
    assert sum(isinstance(e, ExitBlockedEvent) for _, e in first.events) == 2
    moved = first.characters[char.character_id]
    assert moved.location == RIFT and moved.field is not None
    assert (moved.field.x, moved.field.y) == (20, 1)


def test_view_and_line_show_the_notice(rift_lib: ContentLibrary) -> None:
    """畫面：出口帶 ``blocked_zh``（滑鼠提示、警告框），事件句子＝提示文字。"""

    world = make_world()
    char = _char(rift_lib)
    view = field_view(rift_lib, char, world=world, now=NOON)
    assert view is not None
    exits = {e.id: e.blocked_zh for e in view.exits}
    assert exits["to_cloud_summit"] == NOTICE and exits["to_north_slope"] is None
    result = _walk(rift_lib, char, world)
    assert NOTICE in event_lines(rift_lib, "cloud_ridge", result.events, result.char)
    done = _char(rift_lib, story_flags=("mist_rift_done",))
    opened = field_view(rift_lib, done, world=world, now=NOON)
    assert opened is not None
    assert all(e.blocked_zh is None for e in opened.exits)
