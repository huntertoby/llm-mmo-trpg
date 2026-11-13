"""存檔格式 ``trpg-world/4``、``trpg-char/15``、``trpg-wlog/10``（5A-2；6B-2、6C-1、6C-1b、6C-R2
升版）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import CampAction, TravelAction
from trpg.world.errors import WorldSaveFormatError
from trpg.world.replay import WorldLogEntry
from trpg.world.save import (
    dumps_char,
    dumps_log,
    dumps_log_entry,
    dumps_world,
    loads_char,
    loads_log,
    loads_world,
    read_log,
    write_atomic,
)
from trpg.world.state import (
    CharacterState,
    ClearedLocation,
    DefeatedSpawn,
    LocationRef,
    PerceptionMark,
    WorldState,
)
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _full_char(ambush: ContentLibrary, make_char: MakeChar) -> CharacterState:
    char = make_char(
        revealed=(LocationRef(region="cloud_ridge", location="crane_cliff"),),
        perception_marks=(PerceptionMark(region="cloud_ridge", location="crane_cliff", day=3),),
        camped_at=LocationRef(region="cloud_ridge", location="mist_ferry"),
    )
    return world_step(ambush, make_world(), char, TravelAction(to="ferry_steps"), NOON).char


def test_world_roundtrip() -> None:
    world = make_world(
        flags=("a_flag", "mist_tide_success"),
        cleared=(ClearedLocation(region="cloud_ridge", location="ferry_steps", respawn_at=9),),
    )
    text = dumps_world(world)
    assert json.loads(text)["format"] == "trpg-world/4"
    assert loads_world(text) == world
    assert dumps_world(loads_world(text)) == text


def test_char_roundtrip(ambush: ContentLibrary, make_char: MakeChar) -> None:
    char = _full_char(ambush, make_char)
    assert char.pending_encounter is not None
    text = dumps_char(char)
    assert json.loads(text)["format"] == "trpg-char/15"
    loaded = loads_char(text)
    assert loaded == char
    assert dumps_char(loaded) == text


def test_log_roundtrip() -> None:
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id="alice", action=TravelAction(to="hunter_hut")),
        WorldLogEntry(seq=2, now=NOON + 5, character_id="alice", action=CampAction()),
    ]
    text = dumps_log(entries)
    lines = text.splitlines()
    assert json.loads(lines[0]) == {"format": "trpg-wlog/10"}
    assert len(lines) == 3
    assert loads_log(text) == tuple(entries)


@pytest.mark.parametrize(
    ("loader", "text"),
    [
        (loads_world, '{"format": "trpg-world/9"}'),
        (loads_world, '{"season_id": "s1"}'),
        (loads_char, '{"format": "trpg-world/1"}'),
        (loads_world, "[1, 2]"),
        (loads_world, "not json"),
        (loads_log, ""),
        (loads_log, '{"format": "trpg-wlog/11"}\n'),
        (loads_log, '{"format": "trpg-wlog/9"}\n{"seq": 1}\n'),
        (loads_log, '{"format": "trpg-wlog/9"}\n{oops\n'),
        (loads_log, '{"format": "trpg-wlog/9", "stale_through": -1}\n'),
        (loads_char, '{"format": "trpg-char/15"}'),
    ],
)
def test_bad_format_rejected(loader: Callable[[str], object], text: str) -> None:
    with pytest.raises(WorldSaveFormatError):
        loader(text)


def test_invalid_content_rejected() -> None:
    raw = json.loads(dumps_world(make_world()))
    raw["flags"] = ["b", "a"]  # 沒排序
    with pytest.raises(WorldSaveFormatError, match="WorldState"):
        loads_world(json.dumps(raw))


def test_state_rejects_unsorted_collections(make_char: MakeChar) -> None:
    refs = (
        LocationRef(region="cloud_ridge", location="z"),
        LocationRef(region="cloud_ridge", location="a"),
    )
    data = make_char().model_dump()
    data["revealed"] = [r.model_dump() for r in refs]
    with pytest.raises(ValueError, match="revealed"):
        CharacterState.model_validate(data)
    with pytest.raises(ValueError, match="cleared"):
        WorldState.model_validate(
            {
                "season_id": "s1",
                "season_seed": 1,
                "season_start": 0,
                "cleared": [
                    {"region": "cloud_ridge", "location": "b", "respawn_at": 1},
                    {"region": "cloud_ridge", "location": "a", "respawn_at": 1},
                ],
            }
        )


def test_write_atomic(tmp_path: Path) -> None:
    path = tmp_path / "data" / "world.json"
    write_atomic(path, dumps_world(make_world()))
    write_atomic(path, dumps_world(make_world(season_seed=5)))
    assert loads_world(path.read_text(encoding="utf-8")).season_seed == 5
    assert sorted(p.name for p in path.parent.iterdir()) == ["world.json"]
    assert b"\r\n" not in path.read_bytes()


def test_world_v1_upgrades_and_wlog_v3_is_stale() -> None:
    """6C-1b：``trpg-world/1`` 照讀（只多了 ``defeated_spawns``）；``trpg-wlog/3`` 不能重播。"""
    old = json.loads(dumps_world(make_world()))
    old.pop("defeated_spawns")
    old["format"] = "trpg-world/1"
    loaded = loads_world(json.dumps(old))
    assert loaded.format == "trpg-world/4" and loaded.defeated_spawns == ()
    entry = WorldLogEntry(seq=4, now=NOON, character_id="alice", action=CampAction())
    log = read_log('{"format": "trpg-wlog/3"}\n' + dumps_log_entry(entry) + "\n")
    assert log.stale_through == 4 and log.stale_zh is not None


def test_defeated_spawns_must_be_sorted() -> None:
    a = DefeatedSpawn(region="cloud_ridge", location="ferry_steps", spawn=1, respawn_at=9)
    b = DefeatedSpawn(region="cloud_ridge", location="ferry_steps", spawn=0, respawn_at=9)
    with pytest.raises(ValueError, match="defeated_spawns"):
        make_world(defeated_spawns=(a, b))
    world = make_world(defeated_spawns=(b, a))
    assert world.spawn_defeated("cloud_ridge", "ferry_steps", 1, 8)
    assert not world.spawn_defeated("cloud_ridge", "ferry_steps", 1, 9)
