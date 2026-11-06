"""新手流程的 API（Phase 6F-2；#99 戰鬥短提示、#125 開局在主城、玩法 PM 筆記 U1～U4）。

- 建角：出生在主城中央廣場；``guide`` 有開場兩句與「到霧渡鎮找渡婆婆」。
- 從主城第一次傳送到霧渡鎮（免費）；到了之後指引換成「找渡婆婆」（RT-5b 玩法 PM 改）。
- 主線在新手任務鏈完成前標「建議先完成霧渡新手路」；任務追蹤有方向與出口。
- 戰鬥中 ``battle_hints``：新手任務這一步的 ``teach``，加上通用的四種。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, hero, with_rules
from trpg.api.app import create_app
from trpg.api.world import START_REGION, WorldStore, spawn_region
from trpg.api.world_newcomer_view import battle_hints, guide_view, with_routes
from trpg.api.world_story_view import quest_log
from trpg.content.fields import CAPITAL_LOCATION, CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import new_character

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    app = create_app(calm, save_dir=tmp_path / "saves")
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _act(client: TestClient, cid: str, **action: Any) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=action))


def test_spawn_region(field_library: ContentLibrary) -> None:
    assert spawn_region(field_library) == CAPITAL_REGION


@pytest.mark.capital_spawn
def test_new_character_starts_in_capital_with_opening(
    client: TestClient, field_library: ContentLibrary
) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    assert view["map"]["region"] == CAPITAL_REGION
    capital = field_library.field_maps[CAPITAL_LOCATION]
    assert view["field"]["map_id"] == capital.id
    assert (view["field"]["me"]["x"], view["field"]["me"]["y"]) == capital.entry
    guide = view["guide"]
    assert guide["text_zh"] == "到霧渡鎮找渡婆婆"
    assert [line["speaker_zh"] for line in guide["opening"]] == ["說書人", "守印人"]
    assert guide["opening"][0]["text_zh"].startswith("傳送陣的光暗了下去。")
    assert (
        guide["opening"][1]["text_zh"] == "新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。"
    )
    assert view["quests"] == []
    # 主城的傳送選項：第一次免費，雲嶺可以直接去
    assert START_REGION in [t["region"] for t in view["here"]["teleports"]]
    atlas = {r["region"]: r for r in view["atlas"]["regions"]}
    assert atlas[START_REGION]["status"] == "open"
    # 站上中央廣場的傳送陣：霧渡鎮的傳送石列在可去的地方（還沒走到過也行）
    stone = capital.teleport_stones[0].at
    cid = view["character"]["character_id"]
    on = _act(client, cid, kind="walk", path=[list(stone)])
    targets = [t["id"] for t in on["field"]["stone_targets"]]
    assert targets == ["stone_mist_ferry"]
    moved = _act(client, cid, kind="use_teleport_stone", to="stone_mist_ferry")
    assert moved["map"]["region"] == START_REGION


@pytest.mark.capital_spawn
def test_first_teleport_then_town_guide_and_advice(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    there = _act(client, cid, kind="teleport", region=START_REGION)
    assert there["map"]["region"] == START_REGION
    assert there["guide"] == {
        "text_zh": "找渡婆婆",
        "how_zh": None,
        "opening": [],
    }
    offers = {q["id"]: q for q in there["quests_here"]}
    assert offers["main_mist_rift"]["advice_zh"] == "建議先完成霧渡新手路"
    assert offers["starter_ferry"]["advice_zh"] is None
    accepted = _act(client, cid, kind="accept_quest", quest="starter_ferry")
    assert accepted["guide"] is None
    log = {q["id"]: q for q in accepted["quests"]}
    assert log["starter_ferry"]["route_zh"].startswith("往東邊的出口 → 渡口石階")
    # 回主城：到過霧渡鎮了，沒有開場、沒有指引
    back = _act(client, cid, kind="teleport", region=CAPITAL_REGION)
    assert back["guide"] is None


def _with_starter(library: ContentLibrary, location: str, steps_done: int = 0) -> CharacterState:
    char = new_character(library, "alice", hero(library), region=START_REGION)
    quest = QuestState(quest="starter_ferry", steps_done=steps_done, started_at=NOON)
    return char.model_copy(update={"location": location, "quests": (quest,), "field": None})


def test_battle_hints_follow_current_step(field_library: ContentLibrary) -> None:
    generic = ["ice_surface", "trap_tile", "lethal_terrain", "pushed"]
    first = battle_hints(field_library, _with_starter(field_library, "ferry_steps"))
    assert [h.id for h in first] == ["move_attack", *generic]
    assert first[0].text_zh == "點藍格移動，點紅框攻擊；每回合有 AP"
    lethal = next(h for h in first if h.trigger == "lethal_terrain")
    assert set(lethal.terrains) == {"chasm", "lava", "ice_hole"}
    second = battle_hints(field_library, _with_starter(field_library, "bamboo_path", 1))
    assert [h.id for h in second] == ["water_lightning", "freeze_water", *generic]
    third = battle_hints(field_library, _with_starter(field_library, "rain_terraces", 2))
    assert [h.id for h in third] == ["reaction_auto", *generic]
    # 不在這一步的戰鬥地點：只有通用的
    elsewhere = battle_hints(field_library, _with_starter(field_library, "bamboo_path", 0))
    assert [h.id for h in elsewhere] == generic


def test_guide_and_route_helpers(field_library: ContentLibrary) -> None:
    capital = new_character(field_library, "alice", hero(field_library), region=CAPITAL_REGION)
    guide = guide_view(field_library, capital)
    assert guide is not None and len(guide.opening) == 2
    old = new_character(field_library, "bob", hero(field_library), region=START_REGION)
    town_guide = guide_view(field_library, old)
    assert town_guide is not None and town_guide.opening == ()
    char = _with_starter(field_library, "mist_ferry")
    routes = with_routes(field_library, char, quest_log(field_library, char))
    assert routes[0].route_zh is not None and "渡口石階" in routes[0].route_zh
    at_target = _with_starter(field_library, "ferry_steps")
    routes = with_routes(field_library, at_target, quest_log(field_library, at_target))
    assert routes[0].route_zh is None  # 就在這裡
