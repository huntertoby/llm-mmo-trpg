"""開局在主城與第一次免費傳送（Phase 6F-2；09 9.6.9 #125、21 21.5）。

- 新角色在主城出生：主城實地地圖的 ``entry``（中央廣場）。
- 還沒到過新手區（``newcomer.yaml`` 的 ``start_region``）的小鎮：主城可以直接傳到那一區（區域傳送、
  傳送石都可以），不必先解鎖那邊的傳送石；到過之後照一般規則（#120）。
- 舊存檔（建角時就站在雲嶺小鎮）不受影響；重播一致。
"""

from __future__ import annotations

import dataclasses

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.content.fields import CAPITAL_LOCATION, CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.world.actions import TeleportAction, WorldAction
from trpg.world.atlas import (
    can_teleport_to,
    free_first_teleport,
    region_state,
    unlocked_stones,
)
from trpg.world.errors import WorldActionError
from trpg.world.field import placed
from trpg.world.field_actions import UseTeleportStoneAction
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import WORLD_RULES_VERSION, dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, world_step

START = "cloud_ridge"


@pytest.fixture(scope="module")
def calm(field_library: ContentLibrary) -> ContentLibrary:
    lib = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    maps = {k: m.model_copy(update={"spawns": ()}) for k, m in lib.field_maps.items()}
    return dataclasses.replace(lib, field_maps=maps)


def _fresh(library: ContentLibrary) -> CharacterState:
    """6F-2 的新角色：在主城出生（API 的 ``spawn_region``）。"""
    return new_character(library, "alice", hero(library), region=CAPITAL_REGION)


def _old(library: ContentLibrary) -> CharacterState:
    """6F-2 以前建的角色：站在雲嶺小鎮出生，之後傳到主城。"""
    char = new_character(library, "alice", hero(library), region=START)
    result = world_step(
        library, make_world(), char, UseTeleportStoneAction(to="stone_capital"), NOON
    )
    assert result.char.region == CAPITAL_REGION
    return result.char


def _town_stone(library: ContentLibrary, region: str) -> str:
    world_map = library.location_map(region)
    assert world_map is not None
    town = library.outdoor_map(region, world_map.town)
    assert town is not None
    return town.teleport_stones[0].id


def test_newcomer_content(calm: ContentLibrary) -> None:
    newcomer = calm.world_newcomer
    assert newcomer is not None
    assert newcomer.start_region == START
    assert [line.speaker_zh for line in newcomer.opening] == ["說書人", "守印人"]
    assert "霧渡鎮" in newcomer.guide_capital_zh and "渡婆婆" in newcomer.guide_capital_zh
    assert WORLD_RULES_VERSION >= 8  # 6F-4 升到 9（新手保護 #128）


def test_new_character_spawns_in_capital_plaza(calm: ContentLibrary) -> None:
    char = placed(calm, _fresh(calm))
    assert (char.region, char.location) == (CAPITAL_REGION, CAPITAL_LOCATION)
    capital = calm.field_maps[CAPITAL_LOCATION]
    assert char.field == FieldPos(map=capital.id, x=capital.entry[0], y=capital.entry[1])
    # 中央廣場（11～20, 9～14；capital.yaml 開頭的說明）
    assert 11 <= capital.entry[0] <= 20 and 9 <= capital.entry[1] <= 14
    assert char.visited_towns == (CAPITAL_REGION,)
    assert START not in char.teleport_stones


def test_free_first_teleport_by_region(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    assert free_first_teleport(calm, char, START)
    assert can_teleport_to(calm, char, START)
    assert region_state(calm, make_world(), char, START).status == "open"
    result = world_step(calm, make_world(), char, TeleportAction(region=START), NOON)
    world_map = calm.location_map(START)
    assert world_map is not None
    assert (result.char.region, result.char.location) == (START, world_map.town)
    assert START in result.char.visited_towns
    assert not free_first_teleport(calm, result.char, START)  # 到過了


def test_free_first_teleport_by_stone(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    stone = _town_stone(calm, START)
    assert stone in unlocked_stones(calm, char)
    assert stone not in char.teleport_stones  # 不寫進存檔，只是第一次免費
    result = world_step(calm, make_world(), char, UseTeleportStoneAction(to=stone), NOON)
    assert result.char.region == START
    assert START in result.char.visited_towns


def test_free_teleport_only_to_start_region(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    assert not free_first_teleport(calm, char, "ashen_waste")
    with pytest.raises(WorldActionError):
        world_step(calm, make_world(), char, TeleportAction(region="ashen_waste"), NOON)


def test_after_visiting_normal_rules(calm: ContentLibrary) -> None:
    """到過霧渡鎮、沒有站上那邊的傳送石：回到主城後，那顆傳送石照一般規則還沒解鎖。"""
    world = make_world()
    char = _fresh(calm)
    there = world_step(calm, world, char, TeleportAction(region=START), NOON).char
    back = world_step(calm, world, there, TeleportAction(region=CAPITAL_REGION), NOON + 60).char
    stone = _town_stone(calm, START)
    assert stone not in back.teleport_stones
    assert stone not in unlocked_stones(calm, back)
    with pytest.raises(WorldActionError, match="還沒走到過傳送石"):
        world_step(calm, world, back, UseTeleportStoneAction(to=stone), NOON + 120)
    # 區域傳送照一般規則：亮起的區可以去
    again = world_step(calm, world, back, TeleportAction(region=START), NOON + 180).char
    assert again.region == START


def test_old_character_unaffected(calm: ContentLibrary) -> None:
    char = _old(calm)
    assert START in char.visited_towns
    assert not free_first_teleport(calm, char, START)
    assert _town_stone(calm, START) not in unlocked_stones(calm, char)
    assert loads_char(dumps_char(char)) == char


def test_without_newcomer_content_no_free_teleport(calm: ContentLibrary) -> None:
    lib = dataclasses.replace(calm, world_newcomer=None)
    char = _fresh(lib)
    assert not free_first_teleport(lib, char, START)
    with pytest.raises(WorldActionError):
        world_step(lib, make_world(), char, TeleportAction(region=START), NOON)


def _play(
    library: ContentLibrary, world: WorldState, char: CharacterState, actions: list[WorldAction]
) -> tuple[WorldState, CharacterState, list[WorldLogEntry]]:
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        now = NOON + seq * 60
        result = world_step(library, world, char, action, now)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
    return world, char, entries


@pytest.mark.parametrize("first", ["region", "stone"])
def test_free_teleport_replays(calm: ContentLibrary, first: str) -> None:
    world = make_world()
    start = _fresh(calm)
    go: WorldAction = (
        TeleportAction(region=START)
        if first == "region"
        else UseTeleportStoneAction(to=_town_stone(calm, START))
    )
    actions: list[WorldAction] = [
        go,
        TeleportAction(region=CAPITAL_REGION),
        TeleportAction(region=START),
    ]
    end_world, live, entries = _play(calm, world, start, actions)
    log = read_log(dumps_log(entries))
    one = replay(calm, world, {"alice": start}, log.entries)
    two = replay(calm, world, {"alice": start}, log.entries)
    assert one.characters["alice"] == live == two.characters["alice"]
    assert one.world == end_world == two.world
    assert live.region == START
