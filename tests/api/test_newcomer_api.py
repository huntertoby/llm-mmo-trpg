"""主題合併（R2）。

原 ``test_first10_text_6f1.py``：

6F-1：前 10 分鐘的文字修正（靈感點提示不露出原始 ID、提到閃現）。

原 ``test_newcomer_api_6f2.py``：

新手流程的 API（Phase 6F-2；#99 戰鬥短提示、#125 開局在主城、玩法 PM 筆記 U1～U4）。

- 建角：出生在主城中央廣場；``guide`` 有開場兩句與「到霧渡鎮找渡婆婆」。
- 從主城第一次傳送到霧渡鎮（免費）；到了之後指引換成「找渡婆婆」（RT-5b 玩法 PM 改）。
- 主線在新手任務鏈完成前標「建議先完成霧渡新手路」；任務追蹤有方向與出口。
- 戰鬥中 ``battle_hints``：新手任務這一步的 ``teach``，加上通用的四種。

原 ``test_newcomer_api_6f4.py``：

新手前 10 分鐘的 API（Phase 6F-4；#129、#133、6F-2b）。

- 開局預覽多了 ``links``（兩招的觸發關係）、``recommended``／``recommended_zh``（推薦配法）。
- 大世界建角照推薦配法自動配好（不用自己配點）。
- 世界畫面多了 ``hints``（提示紀錄，記在角色身上）與 ``level_up``；三個提示動作走一般的動作端點。
- 6F-2b 的四句定稿文字。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.engine.helpers import library
from tests.world.helpers import NOON, hero, with_rules
from trpg.api.world import START_REGION, spawn_region
from trpg.api.world_growth_view import growth_event_line
from trpg.api.world_newcomer_view import battle_hints, guide_view, with_routes
from trpg.api.world_story_view import quest_log
from trpg.content.fields import CAPITAL_LOCATION, CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.world.actions import InsightGainedEvent
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import new_character

# --- 原 test_first10_text_6f1.py ---


def _line(source: str) -> str:
    line = growth_event_line(library(), InsightGainedEvent(source=source, amount=1, insight=1), {})
    assert line is not None
    return line


def test_quest_insight_uses_the_quest_name_and_mentions_flash() -> None:
    line = _line("quest:starter_ferry")
    assert line.startswith("任務「霧渡新手路」：靈感 ＋1（共 1 點）")
    assert "閃現" in line and "（G）" in line
    assert "starter_ferry" not in line and "quest:" not in line


def test_unknown_insight_sources_do_not_leak_ids() -> None:
    assert "nowhere" not in _line("quest:nowhere")
    assert "mystery" not in _line("mystery:thing")


def test_elite_insight_keeps_the_elite_name() -> None:
    assert _line("elite:mist_wolf").startswith("首次擊敗精英「")


# --- 原 test_newcomer_api_6f2.py ---

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


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


# --- 原 test_newcomer_api_6f4.py ---

START_6F4 = {"name": "阿霧", "weapon": "dagger", "keywords": ["frozen", "concealed"], "seed": 0}


@pytest.fixture
def client_6f4(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _6f4_ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_start_preview_links_and_recommended(client_6f4: TestClient) -> None:
    body = {"weapon": "lightning_staff", "keywords": ["wet", "charged"], "seed": 0}
    preview = _6f4_ok(client_6f4.post("/api/runs/start-preview", json=body))
    assert sum(preview["recommended"].values()) == 4
    assert preview["recommended_zh"]
    for link in preview["links"]:
        assert link["text_zh"] == (
            f"{link['maker_zh']}製造{link['keyword']['name_zh']} → "
            f"{link['user_zh']}利用{link['keyword']['name_zh']}"
        )
    one = _6f4_ok(client_6f4.post("/api/runs/start-preview", json={**body, "keywords": ["wet"]}))
    assert one["links"] == []  # 選滿兩個才有


def test_world_character_is_auto_allocated(client_6f4: TestClient) -> None:
    view = _6f4_ok(client_6f4.post("/api/world/characters", json=START_6F4), 201)
    attrs = view["hero"]["attributes"]
    spent = {a: v - 10 for a, v in attrs.items() if v != 10}
    assert sum(spent.values()) == 4
    assert view["hero"].get("attribute_points", 0) == 0
    assert view["hints"] == {"seen": [], "off": False}
    assert view["level_up"] is None


def test_hint_actions_round_trip(client_6f4: TestClient) -> None:
    view = _6f4_ok(client_6f4.post("/api/world/characters", json=START_6F4), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    seen = _6f4_ok(
        client_6f4.post(url, json={"kind": "hint_seen", "ids": ["opening", "move_attack"]})
    )
    assert seen["hints"] == {"seen": ["move_attack", "opening"], "off": False}
    off = _6f4_ok(client_6f4.post(url, json={"kind": "hints_off"}))
    assert off["hints"]["off"] is True
    reset = _6f4_ok(client_6f4.post(url, json={"kind": "hints_reset"}))
    assert reset["hints"] == {"seen": [], "off": False}


def test_final_texts_6f2b(field_library: ContentLibrary) -> None:
    newcomer = field_library.world_newcomer
    assert newcomer is not None
    assert newcomer.guide_capital_how_zh == "走到中央廣場的傳送陣，或按 M 選雲嶺的霧渡鎮"
    hints = {h.id: h.text_zh for h in newcomer.battle_hints}
    assert hints["ice_surface"] == "冰面很滑：踏上第一格要過敏捷判定，失敗會一路滑出去再倒地"
    assert hints["lethal_terrain"] == ("深淵、岩漿、冰窟是致命地形：被推進去會直接倒下，別背對它站")
    assert newcomer.reflash_lesson[0].text_zh == (
        "閃過的變化不滿意，可以重閃其中一次換成別的變化：要花靈感，但不用先上場"
    )
    assert newcomer.mentor_npc == "gran"
    assert set(newcomer.attribute_notes) == set(Attribute)
