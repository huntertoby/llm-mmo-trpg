"""6C-5 收尾（6C-5b；21.10 第 9、13、17 條）：營火點的清空條件、新手固定戰照步驟消失、走路抵達格
的感知。

全部用測試專用的小地圖放在真的地點上（地點種類照正式的地點圖）。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.actions import PerceptionCheckEvent, TravelAction
from trpg.world.battle import with_cleared
from trpg.world.field_actions import UseTeleportStoneAction
from trpg.world.field_enemies import field_enemies
from trpg.world.state import CharacterState, FieldPos, QuestState
from trpg.world.step import camp_problem, new_character, world_step

type XY = tuple[int, int]

FIRE: XY = (2, 2)
OFF: XY = (1, 1)


def _grid(rows: list[str]) -> str:
    return "\n".join(rows) + "\n"


def _small(location: str, **extra: Any) -> FieldMapDef:
    """5×5 的空地，入口 (1, 1)，營火點 (2, 2)。"""
    data: dict[str, Any] = {
        "id": location,
        "region": "cloud_ridge",
        "location": location,
        "size": [5, 5],
        "heights": _grid(["00000"] * 5),
        "terrain": _grid(["....."] * 5),
        "legend": {".": "stone"},
        "entry": list(OFF),
        "campfires": [{"id": f"{location}_fire", "at": list(FIRE)}],
    }
    return FieldMapDef.model_validate({**data, **extra})


def _with_maps(
    base: ContentLibrary, *maps: FieldMapDef, drop: tuple[str, ...] = ()
) -> ContentLibrary:
    calm = with_rules(base, encounter={"base_permille": 0, "per_level_permille": 0})
    kept = {
        k: m.model_copy(update={"spawns": ()})
        for k, m in calm.field_maps.items()
        if m.place not in drop
    }
    return dataclasses.replace(calm, field_maps={**kept, **{m.id: m for m in maps}})


def _char(library: ContentLibrary, location: str, at: XY, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    pos = FieldPos(map=location, x=at[0], y=at[1])
    return char.model_copy(update={"location": location, "field": pos, **updates})


# ---------------------------------------------------------------------------
# ① 營火點：營地、精英巢穴、Boss 要等已清空；其他地點有巡邏也能用（21.10 第 13 條）
# ---------------------------------------------------------------------------

CAMP_CASES = [
    # (地點, 種類, 站在營火上, 已清空, 能紮營)
    ("ferry_steps", "camp", True, False, False),  # 6C-5b 改：營地的營火也要先清空
    ("ferry_steps", "camp", True, True, True),
    ("ferry_steps", "camp", False, False, False),
    ("ferry_steps", "camp", False, True, True),
    ("north_slope", "elite_lair", True, False, False),
    ("north_slope", "elite_lair", True, True, True),
    ("north_slope", "elite_lair", False, True, False),  # 營火點以外照舊不能紮營
    ("cloud_summit", "boss", True, False, False),
    ("cloud_summit", "boss", True, True, True),
    ("cloud_summit", "boss", False, True, False),
    ("hunter_hut", "village", True, False, True),  # 其他地點有巡邏也能用
    ("hunter_hut", "village", False, False, True),
    ("herb_valley", "ruin", True, False, True),
    ("old_pine_altar", "altar", True, False, True),
    ("bamboo_path", "camp", True, False, False),
]


@pytest.mark.parametrize(("location", "kind", "on_fire", "cleared", "ok"), CAMP_CASES)
def test_campfire_needs_clear_only_for_camp_lair_boss(
    field_library: ContentLibrary,
    *,
    location: str,
    kind: str,
    on_fire: bool,
    cleared: bool,
    ok: bool,
) -> None:
    patrol = {"at": [4, 4], "group": "bandit_raiders", "patrol": [[4, 4], [4, 0]]}
    library = _with_maps(field_library, _small(location, spawns=[patrol]))
    place = library.world_maps["cloud_ridge"].location_by_id()[location]
    assert place.kind == kind
    world = make_world()
    if cleared:
        world = with_cleared(world, "cloud_ridge", location, NOON + 600)
    char = _char(library, location, FIRE if on_fire else OFF)
    problem = camp_problem(library, world, char, NOON)
    assert (problem is None) is ok, problem


# ---------------------------------------------------------------------------
# ② 新手固定戰：那一步完成就不再出現（21.10 第 9 條）
# ---------------------------------------------------------------------------

STEP_SPAWNS = [
    {
        "at": [3, 1],
        "group": "bandit_raiders",
        "personal": True,
        "until_quest": "starter_ferry",
        "until_step": "ferry_bandits",
    },
    {
        "at": [3, 3],
        "group": "bandit_raiders",
        "personal": True,
        "until_quest": "starter_ferry",
        "until_step": "bamboo_wolves",
    },
    {"at": [1, 3], "group": "bandit_raiders", "personal": True, "until_quest": "starter_ferry"},
]


@pytest.mark.parametrize(
    ("quest", "shown"),
    [
        (None, [0, 1, 2]),  # 還沒接任務
        (QuestState(quest="starter_ferry", steps_done=0, started_at=NOON), [0, 1, 2]),
        (QuestState(quest="starter_ferry", steps_done=1, started_at=NOON), [1, 2]),  # 第 1 步完成
        (
            QuestState(quest="starter_ferry", steps_done=2, started_at=NOON),
            [2],
        ),  # 沒寫步驟＝整個任務
        (
            QuestState(
                quest="starter_ferry", steps_done=3, done=True, started_at=NOON, completed_at=NOON
            ),
            [],
        ),
    ],
)
def test_starter_fight_gone_after_its_step(
    field_library: ContentLibrary, quest: QuestState | None, shown: list[int]
) -> None:
    found = _small("ferry_steps", campfires=[], spawns=STEP_SPAWNS)
    library = _with_maps(field_library, found)
    char = _char(library, "ferry_steps", OFF, quests=() if quest is None else (quest,))
    assert [e.index for e in field_enemies(library, make_world(), char, NOON)] == shown


def test_until_step_needs_until_quest() -> None:
    with pytest.raises(ValueError, match="until_step"):
        _small("ferry_steps", spawns=[{"at": [3, 1], "group": "g", "until_step": "ferry_bandits"}])


# ---------------------------------------------------------------------------
# ③ 走路抵達的那一格也判定隱藏入口（21.10 第 17 條）；傳送抵達不判
# ---------------------------------------------------------------------------


def _slope(door_at: XY) -> FieldMapDef:
    """北坡獵場：入口 (1, 1)、傳送石 (3, 1)，往鶴歸崖（隱藏地點）的隱藏門在 ``door_at``。"""
    door = {"id": "crack", "at": list(door_at), "to": "crane_cliff", "hidden_until": "reveal"}
    return _small(
        "north_slope",
        campfires=[],
        size=[8, 5],
        heights=_grid(["00000000"] * 5),
        terrain=_grid(["........"] * 5),
        doors=[door],
        teleport_stones=[{"id": "stone_slope", "at": [3, 1]}],
    )


@pytest.mark.parametrize(("door_at", "checked"), [((2, 0), True), ((7, 4), False)])
def test_travel_arrival_cell_senses_hidden_door(
    field_library: ContentLibrary, door_at: XY, checked: bool
) -> None:
    """從沒有實地地圖的冬湖走（``travel``）到北坡獵場：抵達格 3 格內有隱藏入口就判定。"""
    library = _with_maps(field_library, _slope(door_at), drop=("winter_lake",))
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"location": "winter_lake", "field": None})
    result = world_step(library, make_world(), char, TravelAction(to="north_slope"), NOON)
    assert result.char.location == "north_slope"
    checks = [e for e in result.events if isinstance(e, PerceptionCheckEvent)]
    assert [e.location for e in checks] == (["crane_cliff"] if checked else [])


def test_teleport_arrival_does_not_sense(field_library: ContentLibrary) -> None:
    library = _with_maps(field_library, _slope((3, 0)))  # 傳送石 (3, 1) 旁邊就是隱藏入口
    stones = ("stone_mist_ferry", "stone_slope")
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(
        update={"field": FieldPos(map="mist_ferry", x=12, y=8), "teleport_stones": stones}
    )
    action = UseTeleportStoneAction(to="stone_slope")
    result = world_step(library, make_world(), char, action, NOON)
    assert result.char.location == "north_slope"
    assert not any(isinstance(e, PerceptionCheckEvent) for e in result.events)
