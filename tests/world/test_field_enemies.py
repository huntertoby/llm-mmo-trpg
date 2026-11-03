"""實地地圖上看得見的敵人（Phase 6C-1；``docs/phases/Phase6計畫.md`` 0.4 Q4、Q5、Q8）。

用測試自己的小地圖放在真的地點上（渡口石階＝營地、獵戶小屋＝村落），遭遇表照正式內容。
駐守的朝向、巡邏的起點照「這一趟」的種子：測試直接寫好角色的 ``field_visit``，從固定的種子範圍裡
挑出想要的朝向（結果確定）。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_world, with_rules
from trpg.api.world_field_view import field_view
from trpg.content.fields import FieldMapDef, FieldSpawn
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    BattleEndedEvent,
    BattleStartedEvent,
    EncounterCheckEvent,
    EncounterEvent,
    FightAction,
    RetreatAction,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps, first_team, prepare_battle, with_cleared
from trpg.world.field_actions import WalkAction, WalkedEvent
from trpg.world.field_enemies import (
    FieldEnemy,
    after_fight,
    contact_of,
    field_enemies,
    sight_cells,
    spawn_place,
    spawn_route,
    visit_for,
)
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.rng import STREAM_FIELD
from trpg.world.save import dumps_char, dumps_log, read_log
from trpg.world.state import CharacterState, Facing, FieldPos, FieldVisit, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]


def _grid(rows: list[str]) -> str:
    return "\n".join(rows) + "\n"


_OPEN = ["#" * 13, *("#" + "." * 11 + "#" for _ in range(11)), "#" * 13]


def _steps_map(spawns: list[dict[str, Any]], rows: list[str] | None = None) -> FieldMapDef:
    """渡口石階（營地）：13×13，四周是牆，西邊 (0, 6) 是往霧渡鎮的出口，入口 (1, 6)。"""
    terrain = list(rows or _OPEN)
    terrain[6] = "." + terrain[6][1:]
    return FieldMapDef.model_validate(
        {
            "id": "ferry_steps",
            "region": "cloud_ridge",
            "location": "ferry_steps",
            "size": [13, 13],
            "heights": _grid(["0" * 13] * 13),
            "terrain": _grid(terrain),
            "legend": {".": "stone", "#": "wall"},
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


GUARD = {"at": [6, 6], "group": "bandit_raiders"}
PATROL = {"at": [2, 2], "group": "bandit_shield_line", "patrol": [[2, 2], [10, 2]]}


def _library(base: ContentLibrary, *maps: FieldMapDef) -> ContentLibrary:
    calm = with_rules(base, encounter={"base_permille": 0, "per_level_permille": 0})
    fields = {k: m.model_copy(update={"spawns": ()}) for k, m in calm.field_maps.items()}
    return dataclasses.replace(calm, field_maps={**fields, **{m.id: m for m in maps}})


@pytest.fixture(scope="module")
def guard_lib(field_library: ContentLibrary) -> ContentLibrary:
    return _library(field_library, _steps_map([GUARD]))


@pytest.fixture(scope="module")
def patrol_lib(field_library: ContentLibrary) -> ContentLibrary:
    return _library(field_library, _steps_map([PATROL]))


def _char(
    library: ContentLibrary, at: XY, *, location: str = "ferry_steps", **updates: Any
) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    pos = FieldPos(map=location, x=at[0], y=at[1], facing="e")
    return char.model_copy(update={"location": location, "field": pos, **updates})


def _visit(seed: int, **updates: Any) -> FieldVisit:
    data: dict[str, Any] = {
        "region": "cloud_ridge",
        "location": "ferry_steps",
        "seed": seed,
        "arrived": FieldPos(map="ferry_steps", x=1, y=6, facing="e"),
    }
    return FieldVisit.model_validate({**data, **updates})


def _seed_facing(spawn: dict[str, Any], facing: Facing, index: int = 0) -> int:
    """第一個讓駐守的那一隊面向 ``facing`` 的種子。"""
    model = FieldSpawn.model_validate(spawn)
    return next(s for s in range(200) if spawn_place(_visit(s), index, model, 0)[1] == facing)


def _seed_start(spawn: dict[str, Any], start: XY, facing: Facing) -> int:
    """第一個讓巡邏從 ``start``、面向 ``facing`` 出發的種子。"""
    model = FieldSpawn.model_validate(spawn)
    return next(s for s in range(500) if spawn_place(_visit(s), 0, model, 0) == (start, facing))


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    world: WorldState | None = None,
) -> tuple[CharacterState, list[object]]:
    result = world_step(library, world or make_world(), char, action, NOON)
    return result.char, list(result.events)


def _walk(*cells: XY) -> WalkAction:
    return WalkAction(path=cells)


def _of[T](kind: type[T], events: list[object]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 視野：扇形邊界與遮擋
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cell", "seen"),
    [
        ((6, 5), True),  # 正前方 1 格
        ((5, 5), True),  # 前方 1 格、橫 1（45° 邊上）
        ((4, 5), False),  # 前方 1 格、橫 2：超出 90° 扇形
        ((4, 4), True),  # 前方 2 格、橫 2（邊上，距離 4）
        ((6, 2), True),  # 正前方 4 格
        ((6, 1), False),  # 正前方 5 格：超出距離
        ((5, 3), True),  # 前方 3 格、橫 1（距離 4）
        ((4, 3), False),  # 前方 3 格、橫 2（距離 5）
        ((5, 2), False),  # 前方 4 格、橫 1（距離 5）
        ((5, 6), False),  # 側面（往前 0）
        ((6, 7), False),  # 背後
        ((6, 6), False),  # 自己那一格
    ],
)
def test_sight_fan_boundary(guard_lib: ContentLibrary, cell: XY, seen: bool) -> None:
    found = guard_lib.field_maps["ferry_steps"]
    char = _char(guard_lib, (1, 6))
    assert (cell in sight_cells(guard_lib, char, found, (6, 6), "n")) is seen


def test_sight_fan_has_twelve_cells_in_the_open(guard_lib: ContentLibrary) -> None:
    found = guard_lib.field_maps["ferry_steps"]
    cells = sight_cells(guard_lib, _char(guard_lib, (1, 6)), found, (6, 6), "e")
    assert len(cells) == 12
    assert cells == tuple(sorted(cells, key=lambda c: (c[1], c[0])))


def _blocked_map(kind: str) -> FieldMapDef:
    """(6, 6) 往北的視線上 (6, 4) 擺東西：牆、石柱（擋視線物件）、高 2 的台子、草叢（不擋）。"""
    rows = list(_OPEN)
    heights = ["0" * 13] * 13
    objects: list[dict[str, Any]] = []
    if kind == "wall":
        rows[4] = rows[4][:6] + "#" + rows[4][7:]
    elif kind == "height":
        heights = list(heights)
        heights[4] = "0" * 6 + "2" + "0" * 6
    else:
        objects = [{"at": [6, 4], "kind": kind}]
    terrain = list(rows)
    terrain[6] = "." + terrain[6][1:]
    return FieldMapDef.model_validate(
        {
            "id": "ferry_steps",
            "region": "cloud_ridge",
            "location": "ferry_steps",
            "size": [13, 13],
            "heights": _grid(heights),
            "terrain": _grid(terrain),
            "legend": {".": "stone", "#": "wall"},
            "objects": objects,
            "entry": [1, 6],
            "exits": [
                {
                    "id": "to_mist_ferry",
                    "at": [[0, 6]],
                    "to": "mist_ferry",
                    "arrive": "to_ferry_steps",
                }
            ],
        }
    )


@pytest.mark.parametrize(
    ("kind", "hidden"),
    [("wall", True), ("stone_pillar", True), ("height", True), ("grass", False)],
)
def test_sight_blocked_by_walls_and_sight_blockers(
    field_library: ContentLibrary, kind: str, hidden: bool
) -> None:
    found = _blocked_map(kind)
    library = _library(field_library, found)
    cells = sight_cells(library, _char(library, (1, 6)), found, (6, 6), "n")
    assert ((6, 3) not in cells) is hidden  # 擋住的東西後面
    assert ((6, 2) not in cells) is hidden
    assert (6, 5) in cells  # 擋住的東西前面照樣看得到


# ---------------------------------------------------------------------------
# 接觸與先手（21.10 第 4 條）
# ---------------------------------------------------------------------------


def _enemy(guard_lib: ContentLibrary, facing: Facing) -> FieldEnemy:
    found = guard_lib.field_maps["ferry_steps"]
    sight = sight_cells(guard_lib, _char(guard_lib, (1, 6)), found, (6, 6), facing)
    return FieldEnemy(index=0, spawn=found.spawns[0], x=6, y=6, facing=facing, sight=sight)


@pytest.mark.parametrize(
    ("cell", "touched", "first"),
    [
        ((6, 3), True, "enemy"),  # 走進視野：被看到
        ((6, 5), True, "enemy"),  # 正前方相鄰
        ((6, 7), True, "ally"),  # 背後相鄰：我方先手
        ((5, 6), True, None),  # 側面相鄰：照現行先攻
        ((7, 6), True, None),
        ((6, 8), False, None),  # 背後 2 格：沒碰到
        ((4, 6), False, None),  # 側面 2 格：沒碰到
    ],
)
def test_contact_and_first_strike(
    guard_lib: ContentLibrary, cell: XY, touched: bool, first: str | None
) -> None:
    assert contact_of(_enemy(guard_lib, "n"), cell) == (touched, first)


def test_walk_into_sight_starts_enemy_first_encounter(guard_lib: ContentLibrary) -> None:
    seed = _seed_facing(GUARD, "w")
    char = _char(guard_lib, (1, 6), field_visit=_visit(seed))
    char, events = _step(guard_lib, char, _walk((2, 6), (3, 6), (4, 6), (5, 6)))
    walked = _of(WalkedEvent, events)[0]
    assert walked.stopped == "enemy"
    assert walked.steps == ((2, 6),)  # (2, 6) 在 (6, 6) 往西 4 格：一進視野就停下
    encounter = char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.first == "enemy"
    assert (encounter.contact.x, encounter.contact.y) == (2, 6)
    assert encounter.contact.group == "bandit_raiders"
    assert encounter.from_location == "ferry_steps"
    assert first_team(guard_lib, char, encounter, enemy_first=False) is not None
    assert prepare_battle(guard_lib, char).first_team is not None
    assert _of(EncounterEvent, events)


def test_sneak_from_behind_gives_ally_first(guard_lib: ContentLibrary) -> None:
    seed = _seed_facing(GUARD, "e")  # 面向東：從西邊靠過去就是背後
    char = _char(guard_lib, (1, 6), field_visit=_visit(seed))
    char, _ = _step(guard_lib, char, _walk((2, 6), (3, 6), (4, 6), (5, 6), (5, 7)))
    encounter = char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.first == "ally"
    assert (encounter.contact.x, encounter.contact.y) == (5, 6)
    assert prepare_battle(guard_lib, char).first_team is not None
    assert prepare_battle(guard_lib, char).first_team.value == "ally"  # type: ignore[union-attr]


def test_map_lineup_is_battle_lineup(guard_lib: ContentLibrary) -> None:
    seed = _seed_facing(GUARD, "w")
    char = _char(guard_lib, (1, 6), field_visit=_visit(seed))
    view = field_view(guard_lib, char, world=make_world(), now=NOON)
    assert view is not None and len(view.enemies) == 1
    shown = view.enemies[0]
    assert (shown.x, shown.y, shown.facing, shown.patrol) == (6, 6, "w", False)
    assert shown.group == "bandit_raiders" and (2, 6) in shown.sight
    fought, _ = _step(guard_lib, char, _walk((2, 6)))
    lineup = prepare_battle(guard_lib, fought).lineup
    assert tuple(u.unit for u in shown.units if not u.third) == tuple(
        m.unit for m in lineup.members
    )


def test_retreat_returns_to_map_entrance(guard_lib: ContentLibrary) -> None:
    seed = _seed_facing(GUARD, "w")
    char = _char(guard_lib, (1, 6), field_visit=_visit(seed))
    char, _ = _step(guard_lib, char, _walk((1, 7), (2, 7), (2, 6)))
    assert char.pending_encounter is not None
    back, _ = _step(guard_lib, char, RetreatAction())
    assert back.pending_encounter is None
    assert back.location == "ferry_steps"
    assert back.field == FieldPos(map="ferry_steps", x=1, y=6, facing="e")


# ---------------------------------------------------------------------------
# 清空、重生、打贏的那一隊
# ---------------------------------------------------------------------------


def test_cleared_location_hides_enemies_until_respawn(guard_lib: ContentLibrary) -> None:
    char = _char(guard_lib, (1, 6), field_visit=_visit(_seed_facing(GUARD, "w")))
    world = with_cleared(make_world(), "cloud_ridge", "ferry_steps", NOON + 100)
    assert field_enemies(guard_lib, world, char, NOON) == ()
    walked, _ = _step(guard_lib, char, _walk((2, 6), (3, 6), (4, 6)), world)
    assert walked.pending_encounter is None  # 清空了：走進原本的視野也不開打
    assert len(field_enemies(guard_lib, world, char, NOON + 100)) == 1  # 重生


def test_won_group_stays_gone_for_this_visit(field_library: ContentLibrary) -> None:
    """不寫「已清空」的地點（村落）：打贏的那一隊到離開這個地點前不再出現。"""
    hut = _steps_map([{"at": [6, 6], "group": "hunter_beasts"}]).model_copy(
        update={"id": "hunter_hut", "location": "hunter_hut", "exits": ()}
    )
    library = _library(field_library, hut)
    visit = _visit(1).model_copy(update={"location": "hunter_hut"})
    char = _char(library, (6, 5), location="hunter_hut", field_visit=visit)
    assert len(field_enemies(library, make_world(), char, NOON)) == 1
    contact = char.model_copy(update={"pending_encounter": _encounter_on(library, char)})
    world = make_world()
    fight = FightAction(steps=())
    after, won, _ = after_fight(
        library, world, contact, char, action=fight, events=(_ended(won=True),), now=NOON
    )
    assert after == world  # 村落不共享：不寫世界
    assert won.field_visit is not None and won.field_visit.defeated == (0,)
    assert field_enemies(library, make_world(), won, NOON) == ()
    _, lost, _ = after_fight(
        library, world, contact, char, action=fight, events=(_ended(won=False),), now=NOON
    )
    assert lost.field_visit == visit


def _encounter_on(library: ContentLibrary, char: CharacterState) -> Any:
    walked, _ = _step(
        library,
        char.model_copy(update={"field": FieldPos(map="hunter_hut", x=6, y=4)}),
        _walk((6, 5)),
    )
    assert walked.pending_encounter is not None
    return walked.pending_encounter


def _ended(*, won: bool) -> BattleEndedEvent:
    return BattleEndedEvent(won=won, end_reason=None, rounds=1, hp=1, mana=0, xp_gained=0, level=1)


def test_new_visit_after_changing_location(guard_lib: ContentLibrary) -> None:
    char = _char(guard_lib, (1, 6))
    visit = visit_for(guard_lib, make_world(), char)
    assert visit is not None and visit.ticks == 0 and visit.arrived.x == 1
    walked, _ = _step(guard_lib, char, _walk((1, 7)))
    assert walked.field_visit is not None and walked.field_visit.seed == visit.seed
    assert walked.rng_counters[STREAM_FIELD] == 1
    town, _ = _step(guard_lib, walked, _walk((1, 6), (0, 6)))
    assert town.location == "mist_ferry" and town.field_visit is None  # 霧渡鎮沒有敵人


# ---------------------------------------------------------------------------
# 巡邏
# ---------------------------------------------------------------------------


def test_patrol_route_and_bounce(patrol_lib: ContentLibrary) -> None:
    spawn = patrol_lib.field_maps["ferry_steps"].spawns[0]
    route = spawn_route(spawn)
    assert route == tuple((x, 2) for x in range(2, 11))
    seed = _seed_start(PATROL, (2, 2), "e")
    places = [spawn_place(_visit(seed), 0, spawn, t) for t in range(18)]
    assert [p[0][0] for p in places] == [*range(2, 11), *range(9, 1, -1), 3]
    assert places[7][1] == "e" and places[8] == ((10, 2), "w") and places[16] == ((2, 2), "e")


def test_patrol_moves_one_step_per_player_step(patrol_lib: ContentLibrary) -> None:
    seed = _seed_start(PATROL, (2, 2), "e")
    char = _char(patrol_lib, (1, 10), field_visit=_visit(seed))
    char, _ = _step(patrol_lib, char, _walk((2, 10), (3, 10), (4, 10)))
    assert char.pending_encounter is None
    assert char.field_visit is not None and char.field_visit.ticks == 3
    (enemy,) = field_enemies(patrol_lib, make_world(), char, NOON)
    assert (enemy.xy, enemy.facing) == ((5, 2), "e")


def test_patrol_walks_into_you(patrol_lib: ContentLibrary) -> None:
    """站在路線前方：巡邏走過來看到你就開打（敵方先手；不追擊，只看視野與相鄰）。"""
    seed = _seed_start(PATROL, (2, 2), "e")
    char = _char(patrol_lib, (8, 4), field_visit=_visit(seed))
    char, events = _step(patrol_lib, char, _walk((8, 5), (8, 4), (8, 5), (8, 4)))
    walked = _of(WalkedEvent, events)[0]
    assert walked.stopped == "enemy"
    encounter = char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.first == "enemy"
    assert encounter.contact.group == "bandit_shield_line"


# ---------------------------------------------------------------------------
# 沒有實地地圖的地點照舊擲遇敵；有地圖的不擲
# ---------------------------------------------------------------------------


def test_exit_into_field_map_does_not_roll_encounter(field_library: ContentLibrary) -> None:
    ambush = with_rules(field_library, encounter={"base_permille": 1000, "max_permille": 1000})
    library = dataclasses.replace(
        ambush,
        field_maps={k: m.model_copy(update={"spawns": ()}) for k, m in ambush.field_maps.items()},
    )
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    start = char.model_copy(update={"field": FieldPos(map="mist_ferry", x=22, y=8)})
    moved, events = _step(library, start, _walk((23, 8)))
    check = _of(EncounterCheckEvent, events)[0]
    assert moved.location == "ferry_steps"
    assert check.chance_permille == 0 and not check.encountered
    assert moved.pending_encounter is None
    # 沒有實地地圖的地點照舊擲（拿掉渡口石階的地圖）
    bare = dataclasses.replace(
        library,
        field_maps={k: m for k, m in library.field_maps.items() if m.place != "ferry_steps"},
    )
    moved, events = _step(bare, start, _walk((23, 8)))
    assert _of(EncounterCheckEvent, events)[0].encountered
    assert moved.pending_encounter is not None and moved.pending_encounter.contact is None


def test_travel_into_field_map_location_does_not_roll(guard_lib: ContentLibrary) -> None:
    bare = dataclasses.replace(
        with_rules(guard_lib, encounter={"base_permille": 1000, "max_permille": 1000}),
        field_maps={"ferry_steps": guard_lib.field_maps["ferry_steps"]},
    )
    char = new_character(bare, "alice", hero(bare), region="cloud_ridge")
    moved, events = _step(bare, char, TravelAction(to="ferry_steps"))
    assert _of(EncounterCheckEvent, events)[0].chance_permille == 0
    assert moved.pending_encounter is None
    assert moved.field_visit is not None and moved.field_visit.arrived == FieldPos(
        map="ferry_steps", x=1, y=6
    )


# ---------------------------------------------------------------------------
# 世界日誌重播
# ---------------------------------------------------------------------------


def _play(
    library: ContentLibrary, start: CharacterState, actions: list[WorldAction], world: WorldState
) -> tuple[WorldState, CharacterState, list[WorldLogEntry]]:
    char = start
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        result = world_step(library, world, char, action, NOON + seq)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=NOON + seq, character_id="alice", action=action))
    return world, char, entries


def _replays(
    library: ContentLibrary,
    start: CharacterState,
    entries: list[WorldLogEntry],
    world: WorldState,
    live: CharacterState,
) -> None:
    log = read_log(dumps_log(entries))
    first = replay(library, world, {"alice": start}, log.entries)
    second = replay(library, world, {"alice": start}, log.entries)
    assert dumps_char(first.characters["alice"]) == dumps_char(live)
    assert dumps_char(second.characters["alice"]) == dumps_char(live)
    assert first.events == second.events


def test_replay_walk_into_patrol_sight(patrol_lib: ContentLibrary) -> None:
    seed = _seed_start(PATROL, (2, 2), "e")
    start = _char(patrol_lib, (8, 4), field_visit=_visit(seed))
    world = make_world()
    actions: list[WorldAction] = [
        _walk((8, 5), (8, 4)),
        _walk((8, 5), (8, 4), (8, 5), (8, 4)),
        RetreatAction(),
    ]
    world, live, entries = _play(patrol_lib, start, actions, world)
    assert live.field == FieldPos(map="ferry_steps", x=1, y=6, facing="e")
    _replays(patrol_lib, start, entries, make_world(), live)


def test_replay_sneak_and_clear(guard_lib: ContentLibrary) -> None:
    """繞背先手開打、打贏（營地寫「已清空」）、敵人消失，重播一致。"""
    seed = _seed_facing(GUARD, "e")
    start = _char(guard_lib, (1, 6), field_visit=_visit(seed), mercenaries=PARTY)
    world, live, entries = _play(
        guard_lib, start, [_walk((2, 6), (3, 6), (4, 6), (5, 6))], make_world()
    )
    assert live.pending_encounter is not None and live.pending_encounter.contact is not None
    assert live.pending_encounter.contact.first == "ally"
    fight = FightAction(steps=auto_steps(guard_lib, live))
    result = world_step(guard_lib, world, live, fight, NOON + 2)
    started = next(e for e in result.events if isinstance(e, BattleStartedEvent))
    assert started.first_team is not None and started.first_team.value == "ally"
    won = next(e for e in result.events if isinstance(e, BattleEndedEvent)).won
    assert won
    entries.append(WorldLogEntry(seq=2, now=NOON + 2, character_id="alice", action=fight))
    after = result.char
    assert after.field == FieldPos(map="ferry_steps", x=5, y=6, facing="e")  # 打贏回接觸點
    assert result.world.is_cleared("cloud_ridge", "ferry_steps", NOON + 2)
    assert field_enemies(guard_lib, result.world, after, NOON + 2) == ()
    log = read_log(dumps_log(entries))
    first = replay(guard_lib, make_world(), {"alice": start}, log.entries)
    second = replay(guard_lib, make_world(), {"alice": start}, log.entries)
    assert (
        dumps_char(first.characters["alice"])
        == dumps_char(after)
        == dumps_char(second.characters["alice"])
    )
    assert first.world == result.world == second.world
