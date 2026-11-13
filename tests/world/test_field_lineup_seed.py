"""地圖上一隊敵人的陣容種子（Phase 6C-R2）：改由世界種子＋(區域, 地點, 隊伍)＋重生世代衍生。

- 同一隊、兩個角色（各自這一趟的種子不同）看到的陣容一樣，碰到時的 ``lineup_seed`` 也一樣。
- 巡邏起點與駐守朝向照舊是角色層（這一趟的種子）。
- 打贏一次，重生世代 +1，下一次碰到換一批；只對自己消失的隊伍也記世代，但不會讓它對任何人消失。
- 存檔：``trpg-world/2`` 照讀（``wins`` 當作 1）；``trpg-wlog/6`` 標成規則已變。
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.actions import CampAction
from trpg.world.field_actions import WalkAction
from trpg.world.field_enemies import (
    enemy_lineup,
    field_enemies,
    lineup_seed,
    visit_for,
    with_defeated_spawn,
)
from trpg.world.replay import WorldLogEntry
from trpg.world.rng import STREAM_FIELD, spawn_seed
from trpg.world.save import dumps_log, dumps_log_entry, loads_world, read_log
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]


def _grid(rows: list[str]) -> str:
    return "\n".join(rows) + "\n"


def _steps_map(spawns: list[dict[str, Any]]) -> FieldMapDef:
    """渡口石階（營地）：13×13 空地，西邊 (0, 6) 是往霧渡鎮的出口，入口 (1, 6)。"""
    terrain = ["." * 13 for _ in range(13)]
    return FieldMapDef.model_validate(
        {
            "id": "ferry_steps",
            "region": "cloud_ridge",
            "location": "ferry_steps",
            "size": [13, 13],
            "heights": _grid(["0" * 13] * 13),
            "terrain": _grid(terrain),
            "legend": {".": "stone"},
            "entry": [1, 6],
            "exits": [
                {
                    "id": "to_mist_ferry",
                    "at": [[0, 6]],
                    "to": "mist_ferry",
                    "arrive": "to_ferry_steps",
                }
            ],
            "spawns": spawns,
        }
    )


GUARD = {"at": [8, 6], "group": "bandit_raiders"}


@pytest.fixture(scope="module")
def guard_lib(field_library: ContentLibrary) -> ContentLibrary:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    fields = {k: m.model_copy(update={"spawns": ()}) for k, m in calm.field_maps.items()}
    found = _steps_map([GUARD])
    return dataclasses.replace(calm, field_maps={**fields, found.id: found})


def _char(library: ContentLibrary, name: str, at: XY, **updates: Any) -> CharacterState:
    char = new_character(library, name, hero(library), region="cloud_ridge")
    pos = FieldPos(map="ferry_steps", x=at[0], y=at[1], facing="e")
    return char.model_copy(update={"location": "ferry_steps", "field": pos, **updates})


def test_two_characters_see_the_same_lineup(guard_lib: ContentLibrary) -> None:
    """同一隊、兩個角色：這一趟的種子不同（巡邏起點、駐守朝向各自算），陣容一樣。"""
    world = make_world()
    alice = _char(guard_lib, "alice", (1, 6))
    bob = _char(guard_lib, "bob", (1, 6), rng_counters={STREAM_FIELD: 7})
    va, vb = visit_for(guard_lib, world, alice), visit_for(guard_lib, world, bob)
    assert va is not None and vb is not None and va.seed != vb.seed
    [ea] = field_enemies(guard_lib, world, alice, NOON)
    [eb] = field_enemies(guard_lib, world, bob, NOON)
    la = enemy_lineup(guard_lib, world, alice, ea, NOON)
    lb = enemy_lineup(guard_lib, world, bob, eb, NOON)
    assert la is not None and lb is not None
    assert la == lb
    assert lineup_seed(world, "cloud_ridge", "ferry_steps", 0) == spawn_seed(
        world.season_seed, "cloud_ridge", "ferry_steps", 0, 0
    )


def test_contact_lineup_seed_shared_between_characters(guard_lib: ContentLibrary) -> None:
    """走到駐守旁邊開打：兩個角色記下的 ``lineup_seed`` 一樣（接觸點、先手照各自的位置與朝向）。"""
    world = make_world()
    seeds = []
    for name, counter in (("alice", 0), ("bob", 3)):
        char = _char(guard_lib, name, (1, 6), rng_counters={STREAM_FIELD: counter})
        path = tuple((x, 6) for x in range(2, 8))
        result = world_step(guard_lib, world, char, WalkAction(path=path), NOON)
        encounter = result.char.pending_encounter
        assert encounter is not None and encounter.contact is not None
        seeds.append(encounter.contact.lineup_seed)
    assert seeds[0] == seeds[1]


def _won(world: WorldState, spawn: int = 0) -> WorldState:
    return with_defeated_spawn(world, "cloud_ridge", "ferry_steps", spawn, NOON + 100)


def test_generation_changes_after_a_win() -> None:
    world = make_world()
    first = lineup_seed(world, "cloud_ridge", "ferry_steps", 0)
    once = _won(world)
    assert once.spawn_generation("cloud_ridge", "ferry_steps", 0) == 1
    twice = _won(once)
    assert twice.spawn_generation("cloud_ridge", "ferry_steps", 0) == 2
    seeds = {lineup_seed(w, "cloud_ridge", "ferry_steps", 0) for w in (world, once, twice)}
    assert len(seeds) == 3 and first in seeds
    assert lineup_seed(world, "cloud_ridge", "ferry_steps", 1) != first  # 別隊不同
    other_season = make_world(season_seed=world.season_seed + 1)
    assert lineup_seed(other_season, "cloud_ridge", "ferry_steps", 0) != first
    realigned = with_defeated_spawn(once, "cloud_ridge", "ferry_steps", 0, NOON + 999, win=False)
    assert realigned.spawn_generation("cloud_ridge", "ferry_steps", 0) == 1  # 只對齊時間


def test_old_world_format_reads_wins_as_one() -> None:
    data = json.loads(make_world().model_dump_json())
    data["format"] = "trpg-world/2"
    data["defeated_spawns"] = [
        {"region": "cloud_ridge", "location": "ferry_steps", "spawn": 0, "respawn_at": NOON}
    ]
    world = loads_world(json.dumps(data))
    assert world.format == "trpg-world/4"
    assert world.spawn_generation("cloud_ridge", "ferry_steps", 0) == 1


def test_wlog_6_is_stale() -> None:
    """6C-R2 的陣容種子、6C-5b、21.10 第 20 條都改了規則：``trpg-wlog/6`` 照讀、不能重播。"""
    entry = WorldLogEntry(seq=3, now=NOON, character_id="alice", action=CampAction())
    log = read_log('{"format": "trpg-wlog/6"}\n' + dumps_log_entry(entry) + "\n")
    assert log.stale_through == 3 and log.stale_zh == "規則已變、不能重播"
    assert json.loads(dumps_log((), stale_through=3).splitlines()[0])["format"] == "trpg-wlog/10"
