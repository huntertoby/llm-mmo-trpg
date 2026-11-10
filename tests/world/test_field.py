"""實地地圖上的位置與走路（Phase 6B-2；``docs/phases/Phase6計畫.md`` 3.6）。

霧渡鎮（24×18，``entry`` (11, 9)）與渡口石階（20×12）是 6B-1 的草稿；隱藏門、高低差、跨區傳送石用
測試自己的小地圖（藥師谷、丹爐洞、餘燼集）。
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.world_field_schemas import FieldView
from trpg.api.world_field_view import _walk_max_steps, field_view
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.world_rules import WALK_PATH_FORMAT_MAX, FieldRules
from trpg.world.actions import (
    EncounterCheckEvent,
    RetreatAction,
    TeleportAction,
    TravelAction,
    TraveledEvent,
    WorldAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.field import placed
from trpg.world.field_actions import (
    FieldEnteredEvent,
    TeleportStoneUnlockedEvent,
    TeleportStoneUsedEvent,
    UseTeleportStoneAction,
    WalkAction,
    WalkedEvent,
)
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, reveal_location, world_step

ENTRY = (11, 9)
"""霧渡鎮的 ``entry``。"""
MIST_STONE = "stone_mist_ferry"


def _grid(rows: list[str]) -> str:
    return "\n".join(rows) + "\n"


def _test_maps() -> dict[str, FieldMapDef]:
    """藥師谷（隱藏門往丹爐洞、傳送石、2 層高的台子）、丹爐洞、餘燼集（另一區的傳送石）。"""
    herb: dict[str, Any] = {
        "id": "herb_valley",
        "region": "cloud_ridge",
        "location": "herb_valley",
        "size": [6, 5],
        "heights": _grid(["000000", "000000", "000020", "000000", "000000"]),
        "terrain": _grid(["......"] * 5),
        "legend": {".": "stone"},
        "entry": [1, 2],
        "doors": [{"id": "herb_door", "at": [3, 0], "to": "elixir_cave", "hidden_until": "reveal"}],
        "teleport_stones": [{"id": "stone_herb", "at": [1, 1]}],
        "npcs": [{"id": "granny_du", "at": [5, 4]}],
    }
    cave: dict[str, Any] = {
        "id": "elixir_cave",
        "region": "cloud_ridge",
        "location": "elixir_cave",
        "size": [5, 4],
        "heights": _grid(["00000"] * 4),
        "terrain": _grid(["....."] * 4),
        "legend": {".": "stone"},
        "entry": [2, 1],
        "exits": [
            {"id": "to_herb_valley", "at": [[2, 3]], "to": "herb_valley", "arrive": "herb_door"}
        ],
    }
    ember: dict[str, Any] = {
        "id": "ember_market",
        "region": "ashen_waste",
        "location": "ember_market",
        "size": [5, 4],
        "heights": _grid(["00000"] * 4),
        "terrain": _grid(["....."] * 4),
        "legend": {".": "stone"},
        "entry": [2, 2],
        "teleport_stones": [{"id": "stone_ember", "at": [1, 1]}],
    }
    return {m["id"]: FieldMapDef.model_validate(m) for m in (herb, cave, ember)}


NO_MAP = "hunter_hut"
"""測試內容庫裡拿掉實地地圖的地點（「沒有地圖照舊 travel」用；不管正式內容有沒有畫）。"""


def _no_spawns(maps: dict[str, FieldMapDef]) -> dict[str, FieldMapDef]:
    """拿掉看得見的敵人（6C-1）：這裡測的是 6B-2 的走路，不讓巡邏擋路。"""
    return {k: m.model_copy(update={"spawns": ()}) for k, m in maps.items()}


@pytest.fixture(scope="module")
def calm_field(field_library: ContentLibrary) -> ContentLibrary:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    kept = {k: m for k, m in calm.field_maps.items() if m.place != NO_MAP}
    return dataclasses.replace(calm, field_maps=_no_spawns({**kept, **_test_maps()}))


AMBUSH_NO_MAP = "ferry_steps"
"""遇敵測試拿掉實地地圖的地點：6C-1 起有實地地圖的地點不再擲遇敵，所以渡口石階改成沒有地圖、
照舊每步遇敵。"""


@pytest.fixture(scope="module")
def ambush_field(field_library: ContentLibrary) -> ContentLibrary:
    ambush = with_rules(field_library, encounter={"base_permille": 1000, "max_permille": 1000})
    kept = {k: m for k, m in ambush.field_maps.items() if m.place != AMBUSH_NO_MAP}
    return dataclasses.replace(ambush, field_maps=_no_spawns(kept))


def _char(library: ContentLibrary, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    return char.model_copy(update=updates) if updates else char


def _at(x: int, y: int, map_id: str = "mist_ferry") -> FieldPos:
    return FieldPos(map=map_id, x=x, y=y)


def _walk(*cells: tuple[int, int]) -> WalkAction:
    return WalkAction(path=cells)


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    world: WorldState | None = None,
) -> tuple[CharacterState, list[object]]:
    result = world_step(library, world or make_world(), char, action, NOON)
    return result.char, list(result.events)


def _of[T](kind: type[T], events: list[object]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 位置與舊存檔
# ---------------------------------------------------------------------------


def test_new_character_has_no_field_until_needed(calm_field: ContentLibrary) -> None:
    char = _char(calm_field)
    assert char.field is None
    assert placed(calm_field, char).field == _at(*ENTRY)


def test_old_save_loads_and_is_placed_at_entry(calm_field: ContentLibrary) -> None:
    """``trpg-char/1`` 的舊存檔照讀；第一次走路時放到 ``entry``（不另寫日誌）。"""
    data = json.loads(dumps_char(_char(calm_field)))
    data["format"] = "trpg-char/1"
    del data["field"], data["teleport_stones"]
    old = loads_char(json.dumps(data, ensure_ascii=False))
    assert old.format == "trpg-char/13"
    assert old.field is None
    char, events = _step(calm_field, old, _walk((12, 9)))
    assert char.field == FieldPos(map="mist_ferry", x=12, y=9, facing="e")
    assert _of(WalkedEvent, events)[0].steps == ((12, 9),)


def test_no_field_map_means_no_field(calm_field: ContentLibrary) -> None:
    char = _char(calm_field, location="hunter_hut")
    assert placed(calm_field, char).field is None
    with pytest.raises(WorldActionError, match="還沒有實地地圖"):
        _step(calm_field, char, _walk((1, 1)))


# ---------------------------------------------------------------------------
# 走路
# ---------------------------------------------------------------------------


def test_walk_costs_nothing(calm_field: ContentLibrary) -> None:
    char = _char(calm_field)
    moved, events = _step(calm_field, char, _walk((12, 9), (13, 9), (14, 9)))
    assert moved.field == FieldPos(map="mist_ferry", x=14, y=9, facing="e")
    assert moved.rng_counters == char.rng_counters
    assert moved.supplies == char.supplies
    assert moved.event_steps == char.event_steps
    walked = _of(WalkedEvent, events)
    assert [w.stopped for w in walked] == ["end"]
    assert not _of(EncounterCheckEvent, events)


@pytest.mark.parametrize(
    ("start", "path", "message"),
    [
        (ENTRY, [(13, 9)], "不相鄰"),  # 跳格
        (ENTRY, [(11, 9)], "不相鄰"),  # 原地
        ((2, 6), [(2, 5)], "走不過去"),  # 牆
        ((8, 8), [(8, 7)], "走不過去"),  # 石柱（懸賞板）
        ((0, 0), [(-1, 0)], "走不過去"),  # 地圖外
        ((3, 14), [(3, 15), (3, 16), (2, 16)], "走不過去"),  # 木棧橋旁邊是霧河（深淵）
    ],
)
def test_illegal_walk(
    calm_field: ContentLibrary,
    start: tuple[int, int],
    path: list[tuple[int, int]],
    message: str,
) -> None:
    char = _char(calm_field, field=_at(*start))
    with pytest.raises(WorldActionError, match=message):
        _step(calm_field, char, WalkAction(path=tuple(path)))


def test_npc_blocks_walk(calm_field: ContentLibrary) -> None:
    """NPC 站的格子不能走（測試的藥師谷 (5, 4) 站著 NPC）。"""
    char = _char(calm_field, location="herb_valley", field=_at(4, 4, "herb_valley"))
    with pytest.raises(WorldActionError, match="走不過去"):
        _step(calm_field, char, _walk((5, 4)))


def test_height_limit(calm_field: ContentLibrary) -> None:
    """一步最多往上 1 層（照戰鬥規則）；藥師谷 (4, 2) 高 2 層。"""
    char = _char(calm_field, location="herb_valley", field=_at(3, 2, "herb_valley"))
    with pytest.raises(WorldActionError, match="走不過去"):
        _step(calm_field, char, _walk((4, 2)))


def _zigzag(cells: int) -> tuple[tuple[int, int], ...]:
    """從 ``ENTRY`` 往下一格、回來，來回走 ``cells`` 格。"""
    return tuple((ENTRY[0], ENTRY[1] + (k % 2)) for k in range(1, cells + 1))


def test_walk_limit_is_30_cells(calm_field: ContentLibrary) -> None:
    """一次最多 30 格（規則 ``field.walk_max_steps``，由 ``walk`` 檢查；6P-2）。"""
    with pytest.raises(ValidationError):
        WalkAction(path=())
    char = _char(calm_field, field=_at(*ENTRY))
    assert _step(calm_field, char, WalkAction(path=_zigzag(30)))[0].field is not None
    with pytest.raises(WorldActionError, match=r"一次最多走 30 格（這次送了 31 格；請分段送）"):
        _step(calm_field, char, WalkAction(path=_zigzag(31)))
    short = with_rules(calm_field, field={"walk_max_steps": 2})
    with pytest.raises(WorldActionError, match="最多走 2 格"):
        _step(short, char, _walk(*_zigzag(3)))
    assert _step(short, char, _walk(*_zigzag(2)))[0].field is not None


def test_walk_limit_follows_rules(calm_field: ContentLibrary) -> None:
    """6P-2：規則改大，一次能走的格數跟著變（不再被程式的 30 格限制）；世界畫面帶同一個值。"""
    char = _char(calm_field, field=_at(*ENTRY))
    long = with_rules(calm_field, field={"walk_max_steps": 45})
    walked, _ = _step(long, char, WalkAction(path=_zigzag(45)))
    assert walked.field is not None and (walked.field.x, walked.field.y) == _zigzag(45)[-1]
    with pytest.raises(WorldActionError, match="一次最多走 45 格"):
        _step(long, char, WalkAction(path=_zigzag(46)))
    view = field_view(long, char)
    assert view is not None and view.walk_max_steps == 45
    base = field_view(calm_field, char)
    assert base is not None and base.walk_max_steps == 30


def test_walk_limit_default_has_one_source(calm_field: ContentLibrary) -> None:
    """6R-P：沒有世界規則時的預設值與 ``FieldView`` 的預設值都取 ``FieldRules()``。"""
    default = FieldRules().walk_max_steps
    assert FieldView.model_fields["walk_max_steps"].default == default
    assert _walk_max_steps(dataclasses.replace(calm_field, world_rules=None)) == default


def test_walk_request_format_cap(calm_field: ContentLibrary) -> None:
    """請求格式只防過大的請求（``WALK_PATH_FORMAT_MAX``）；規則值不得超過它。"""
    WalkAction(path=((0, 0),) * WALK_PATH_FORMAT_MAX)
    with pytest.raises(ValidationError):
        WalkAction(path=((0, 0),) * (WALK_PATH_FORMAT_MAX + 1))
    with_rules(calm_field, field={"walk_max_steps": WALK_PATH_FORMAT_MAX})
    with pytest.raises(ValidationError):
        with_rules(calm_field, field={"walk_max_steps": WALK_PATH_FORMAT_MAX + 1})


def test_pending_encounter_blocks_walk(ambush_field: ContentLibrary) -> None:
    char, _ = _step(ambush_field, _char(ambush_field, field=_at(22, 8)), _walk((23, 8)))
    assert char.pending_encounter is not None
    with pytest.raises(WorldActionError, match="遭遇"):
        _step(ambush_field, char, _walk((2, 8)))


def test_travel_rejected_where_field_map_exists(calm_field: ContentLibrary) -> None:
    with pytest.raises(WorldActionError, match="請走到出口"):
        _step(calm_field, _char(calm_field), TravelAction(to="hunter_hut"))
    inside = _char(calm_field, field=_at(4, 6, "mist_ferry_tavern"))
    with pytest.raises(WorldActionError, match="請走到出口"):
        _step(calm_field, inside, TravelAction(to="hunter_hut"))
    # 沒有實地地圖的地點照舊 travel；回到霧渡鎮時位置作廢、之後放到 entry
    hut = _char(calm_field, location="hunter_hut", field=_at(20, 8))
    back, _ = _step(calm_field, hut, TravelAction(to="mist_ferry"))
    assert back.location == "mist_ferry"
    assert back.field is None
    assert placed(calm_field, back).field == _at(*ENTRY)


# ---------------------------------------------------------------------------
# 出口
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "exit_cell", "arrive"),
    [
        ((22, 8), (23, 8), (1, 8)),  # 出口第 1 格 → 對面出口第 1 格往內一格
        ((22, 9), (23, 9), (1, 9)),
    ],
)
def test_exit_changes_map(
    calm_field: ContentLibrary,
    start: tuple[int, int],
    exit_cell: tuple[int, int],
    arrive: tuple[int, int],
) -> None:
    char = _char(calm_field, field=_at(*start))
    moved, events = _step(calm_field, char, _walk(exit_cell, (exit_cell[0], exit_cell[1] - 1)))
    assert moved.location == "ferry_steps"
    assert moved.field == FieldPos(map="ferry_steps", x=arrive[0], y=arrive[1], facing="e")
    assert _of(WalkedEvent, events)[0].stopped == "exit"
    assert _of(WalkedEvent, events)[0].steps == (exit_cell,)  # 出口之後的路徑不走
    assert _of(TraveledEvent, events)[0].to == "ferry_steps"
    assert len(_of(EncounterCheckEvent, events)) == 1  # 進入一張地圖＝一步：照舊擲遇敵
    assert moved.rng_counters["travel"] == 1
    entered = _of(FieldEnteredEvent, events)
    assert [(e.map, e.via) for e in entered] == [("ferry_steps", "exit")]


def test_exit_back_to_town(calm_field: ContentLibrary) -> None:
    char = _char(calm_field, location="ferry_steps", field=_at(1, 9, "ferry_steps"))
    moved, _ = _step(calm_field, char, _walk((0, 9)))
    assert moved.location == "mist_ferry"
    assert moved.field == FieldPos(map="mist_ferry", x=22, y=9, facing="w")
    assert moved.visited_towns == ("cloud_ridge",)


def test_exit_to_place_without_map(calm_field: ContentLibrary) -> None:
    path = tuple((11, y) for y in range(8, -1, -1))
    moved, events = _step(calm_field, _char(calm_field), WalkAction(path=path))
    assert moved.location == "hunter_hut"
    assert moved.field is None
    assert _of(FieldEnteredEvent, events)[0].map is None


def test_exit_checks_unlock_flag(calm_field: ContentLibrary) -> None:
    """往灰燼荒原的渡口還沒開放：沿用 travel 的檢查，整個動作不成立。"""
    char = _char(calm_field, field=_at(3, 16))
    with pytest.raises(WorldActionError, match="還沒開放"):
        _step(calm_field, char, _walk((3, 17)))


# ---------------------------------------------------------------------------
# 門與室內
# ---------------------------------------------------------------------------


def test_door_into_interior_rolls_nothing(calm_field: ContentLibrary) -> None:
    char = _char(calm_field, field=_at(3, 6))
    inside, events = _step(calm_field, char, _walk((3, 5)))
    assert inside.location == "mist_ferry"
    assert inside.field == FieldPos(map="mist_ferry_tavern", x=4, y=6, facing="n")
    assert inside.rng_counters == char.rng_counters  # 室內不算進入一張地圖（Q6）
    assert inside.event_steps == char.event_steps
    assert not _of(TraveledEvent, events)
    assert not _of(EncounterCheckEvent, events)
    out, events = _step(calm_field, inside, _walk((4, 7)))
    assert out.field == FieldPos(map="mist_ferry", x=3, y=6, facing="s")  # 門外一格
    assert out.rng_counters == char.rng_counters
    assert not _of(TraveledEvent, events)


def test_hidden_door(calm_field: ContentLibrary) -> None:
    char = _char(calm_field, location="herb_valley", field=_at(3, 1, "herb_valley"))
    with pytest.raises(WorldActionError, match="走不過去"):  # 還沒發現：不可站
        _step(calm_field, char, _walk((3, 0)))
    view = field_view(calm_field, char)
    assert view is not None and view.doors == ()  # 未發現的隱藏門不顯示
    found = reveal_location(char, "cloud_ridge", "elixir_cave")
    shown = field_view(calm_field, found)
    assert shown is not None and [d.to_name_zh for d in shown.doors] == ["丹爐洞"]
    cave, events = _step(calm_field, found, _walk((3, 0)))
    assert cave.location == "elixir_cave"
    assert cave.field == FieldPos(map="elixir_cave", x=2, y=2, facing="n")
    assert _of(TraveledEvent, events)[0].to == "elixir_cave"  # 進隱藏地點算一步
    assert _of(WalkedEvent, events)[0].stopped == "door"
    back, _ = _step(calm_field, cave, _walk((2, 3)))
    assert back.location == "herb_valley"
    assert back.field == FieldPos(map="herb_valley", x=3, y=1, facing="s")  # 門外一格


# ---------------------------------------------------------------------------
# 傳送石
# ---------------------------------------------------------------------------


def test_stone_unlocks_once(calm_field: ContentLibrary) -> None:
    char, events = _step(calm_field, _char(calm_field), _walk((11, 8), (12, 8), (13, 8)))
    assert char.field == FieldPos(map="mist_ferry", x=12, y=8, facing="e")  # 踩上就停
    assert char.teleport_stones == (MIST_STONE,)
    assert _of(TeleportStoneUnlockedEvent, events) == [TeleportStoneUnlockedEvent(stone=MIST_STONE)]
    assert char.location == "mist_ferry"  # 不自動傳送
    char = char.model_copy(update={"field": _at(*ENTRY)})
    again, events = _step(calm_field, char, _walk((11, 8), (12, 8)))
    assert again.teleport_stones == (MIST_STONE,)
    assert not _of(TeleportStoneUnlockedEvent, events)


def test_use_teleport_stone(calm_field: ContentLibrary) -> None:
    stones = (MIST_STONE, "stone_herb")
    char = _char(calm_field, field=_at(12, 8), teleport_stones=stones)
    moved, events = _step(calm_field, char, UseTeleportStoneAction(to="stone_herb"))
    assert (moved.region, moved.location) == ("cloud_ridge", "herb_valley")
    assert moved.field == _at(1, 1, "herb_valley")
    assert moved.rng_counters == char.rng_counters
    used = _of(TeleportStoneUsedEvent, events)
    assert [(u.from_stone, u.to_stone) for u in used] == [(MIST_STONE, "stone_herb")]
    back, _ = _step(calm_field, moved, UseTeleportStoneAction(to=MIST_STONE))
    assert back.location == "mist_ferry"
    assert back.field == _at(12, 8)


@pytest.mark.parametrize(
    ("updates", "to", "message"),
    [
        # 6C-6 起在城鎮裡（沒站在傳送石上）也能傳送：tests/world/test_region_teleport.py
        ({"field": _at(12, 8), "teleport_stones": (MIST_STONE,)}, "stone_herb", "還沒走到過"),
        ({"field": _at(12, 8), "teleport_stones": (MIST_STONE,)}, MIST_STONE, "已經在"),
        (
            {"field": _at(12, 8), "teleport_stones": (MIST_STONE, "stone_ember")},
            "stone_ember",
            "還沒去過",
        ),
        ({"location": "hunter_hut", "teleport_stones": (MIST_STONE,)}, MIST_STONE, "站在"),
    ],
)
def test_illegal_teleport_stone(
    calm_field: ContentLibrary, updates: dict[str, Any], to: str, message: str
) -> None:
    with pytest.raises(WorldActionError, match=message):
        _step(calm_field, _char(calm_field, **updates), UseTeleportStoneAction(to=to))


def test_cross_region_stone_needs_visited_town(calm_field: ContentLibrary) -> None:
    char = _char(
        calm_field,
        field=_at(12, 8),
        teleport_stones=(MIST_STONE, "stone_ember"),
        visited_towns=("ashen_waste", "cloud_ridge"),
    )
    moved, _ = _step(calm_field, char, UseTeleportStoneAction(to="stone_ember"))
    assert (moved.region, moved.location) == ("ashen_waste", "ember_market")
    assert moved.field == _at(1, 1, "ember_market")


# ---------------------------------------------------------------------------
# 其他動作換地點：位置作廢
# ---------------------------------------------------------------------------


def test_retreat_and_teleport_drop_stale_field(ambush_field: ContentLibrary) -> None:
    char, _ = _step(ambush_field, _char(ambush_field, field=_at(22, 8)), _walk((23, 8)))
    assert char.location == "ferry_steps" and char.field is None
    assert char.pending_encounter is not None
    back, _ = _step(ambush_field, char, RetreatAction())
    assert back.location == "mist_ferry"
    assert back.field is None
    assert placed(ambush_field, back).field == _at(*ENTRY)
    town = back.model_copy(
        update={"field": _at(5, 8), "visited_towns": ("ashen_waste", "cloud_ridge")}
    )
    away, _ = _step(ambush_field, town, TeleportAction(region="ashen_waste"))
    assert away.field is None


# ---------------------------------------------------------------------------
# 世界日誌重播
# ---------------------------------------------------------------------------

_LOOP_CALM: tuple[WorldAction, ...] = (
    _walk((11, 8), (12, 8)),  # 傳送石
    _walk((13, 8), (14, 8), (15, 8), (16, 8), (17, 8), (18, 8), (19, 8), (20, 8), (21, 8)),
    _walk((22, 8), (23, 8)),  # 出口 → 渡口石階
    _walk((2, 8), (3, 8), (4, 8), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9)),  # 走一圈回霧渡鎮
    _walk((21, 9), (21, 8), (20, 8), (20, 7)),
)
_LOOP_AMBUSH: tuple[WorldAction, ...] = (
    _walk((12, 9), (13, 9), (14, 9), (15, 9), (16, 9), (17, 9), (18, 9), (19, 9), (20, 9)),
    _walk((21, 9), (22, 9), (23, 9)),  # 出口 → 渡口石階：遇敵
    RetreatAction(),  # 撤退回霧渡鎮（位置作廢 → entry）
    _walk((10, 9), (9, 9), (8, 9), (7, 9), (6, 9), (5, 9), (4, 9), (3, 9), (3, 8), (3, 7), (3, 6)),
    _walk((3, 5)),  # 進酒館
    _walk((4, 7)),  # 出酒館
)


def _play(
    library: ContentLibrary, actions: tuple[WorldAction, ...]
) -> tuple[WorldState, CharacterState, CharacterState, list[WorldLogEntry]]:
    world = make_world()
    start = _char(library)
    char = start
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        now = NOON + seq * 60
        result = world_step(library, world, char, action, now)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
    return world, start, char, entries


@pytest.mark.parametrize("loop", ["calm", "ambush"])
def test_walk_log_replays(
    calm_field: ContentLibrary, ambush_field: ContentLibrary, loop: str
) -> None:
    library, actions = (calm_field, _LOOP_CALM) if loop == "calm" else (ambush_field, _LOOP_AMBUSH)
    world, start, live, entries = _play(library, actions)
    if loop == "calm":
        assert live.field == FieldPos(map="mist_ferry", x=20, y=7, facing="n")
        assert live.teleport_stones == (MIST_STONE,)
        assert live.rng_counters["travel"] == 2
    else:
        assert live.field == FieldPos(map="mist_ferry", x=3, y=6, facing="s")
        assert live.rng_counters["travel"] == 1
    log = read_log(dumps_log(entries))
    assert log.stale_through is None
    first = replay(library, make_world(), {"alice": start}, log.entries)
    second = replay(library, make_world(), {"alice": start}, log.entries)
    assert first.characters["alice"] == live == second.characters["alice"]
    assert first.world == world == second.world
    assert first.events == second.events
    if loop == "ambush":
        assert any(e.kind == "encounter" for _, e in first.events)


def test_old_world_log_is_stale() -> None:
    """``trpg-wlog/1`` 照讀，但規則已變、不能重播；寫回時標頭記下到哪一筆。"""
    old = (
        '{"format": "trpg-wlog/1"}\n'
        + dumps_log(
            [
                WorldLogEntry(
                    seq=3, now=NOON, character_id="alice", action=TravelAction(to="hunter_hut")
                )
            ]
        ).splitlines()[1]
        + "\n"  # 6D-R1：沒有換行結尾的最後一行算寫到一半，會被略過
    )
    log = read_log(old)
    assert log.stale_through == 3
    assert log.stale_zh == "規則已變、不能重播"
    again = read_log(dumps_log(log.entries, stale_through=log.stale_through))
    assert again == log
    assert json.loads(dumps_log((), stale_through=3).splitlines()[0])["format"] == "trpg-wlog/9"
    assert read_log('{"format": "trpg-wlog/1"}\n').stale_through is None
