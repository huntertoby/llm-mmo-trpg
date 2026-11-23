"""WM-1：大世界走路不黏腳的伺服器部分（``docs/phases/PhaseWM-1計畫.md``）。

- 第 3 項：主角面板（技能驗證）快取——有快取和沒快取時畫面逐位元相同；換技能、換裝備、升級後重算。
- 守則 14：走路回應的 ``field`` 照舊是依觀看者過濾的 :func:`~trpg.api.world_field_view.field_view`。
- 第 4 項：走路觸發地點事件時（LLM 開著）先回畫面（``story_pending``），
  旁白由 ``event_story`` 補上，
  照舊寫成日誌裡的 ``narrate`` 動作（重播結果不變）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import trpg.api.world_growth_view as growth_view
from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.api import run_presenter
from trpg.api.llm_source import MockLlmProvider
from trpg.api.run_schemas import HeroOut
from trpg.api.world import WorldStore
from trpg.api.world_field_view import field_view
from trpg.api.world_growth_view import clear_hero_panel_cache, hero_panel
from trpg.content.library import ContentLibrary
from trpg.roguelite.state import RunState
from trpg.world.layout import LOG_FILE
from trpg.world.replay import replay
from trpg.world.save import loads_char, loads_log
from trpg.world.state import EventTrigger, FieldEventMark

SKELETON = "wounded_peddler"
START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _walk(client: TestClient, cid: str, cell: list[int]) -> Any:
    url = f"/api/world/characters/{cid}/actions"
    return client.post(url, json={"kind": "walk", "path": [cell]})


def _count_hero_out(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """把 ``hero_out``（技能驗證、技能卡）換成會記次數的版本。"""
    calls: list[str] = []
    real = run_presenter.hero_out

    def counted(lib: ContentLibrary, run: RunState) -> HeroOut:
        calls.append("x")
        return real(lib, run)

    monkeypatch.setattr(growth_view, "hero_out", counted)
    return calls


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def test_cached_view_is_byte_identical(client: TestClient) -> None:
    """走一步之後：快取熱著和清空重算，回傳的畫面逐位元相同。"""
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    walked = _walk(client, cid, [11, 8])
    assert walked.status_code == 200, walked.text
    warm = client.get(f"/api/world/characters/{cid}")
    clear_hero_panel_cache()
    cold = client.get(f"/api/world/characters/{cid}")
    assert warm.status_code == cold.status_code == 200
    assert warm.content == cold.content
    # 走路的回應本身也一樣：同一份狀態重算（清空快取）組出來的英雄面板相同
    assert walked.json()["hero"] == cold.json()["hero"]


def test_walk_reuses_panel(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """連走幾步，技能驗證（``hero_out``）只算第一次。"""
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    calls = _count_hero_out(monkeypatch)
    clear_hero_panel_cache()
    for cell in ([11, 8], [10, 8], [11, 8], [10, 8]):
        _ok(_walk(client, cid, cell))
    assert calls == ["x"]


def test_cache_invalidates_on_skills_gear_level(
    client: TestClient, field_library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    """技能、裝備、等級任何一樣變了就重算，結果和不用快取時相同。"""
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    store = _store(client)
    world, char = store.world(), store.character(cid)
    lib = store.library
    calls = _count_hero_out(monkeypatch)
    clear_hero_panel_cache()
    base = hero_panel(lib, world, char)
    assert hero_panel(lib, world, char) is base  # 同一份狀態：命中
    assert len(calls) == 1

    assert char.generated_skills, "建角就有生成技能"
    item = next(iter(field_library.items.values()))
    first = char.generated_skills[0]
    renamed = (first.model_copy(update={"name_zh": "改過的招"}), *char.generated_skills[1:])
    changed = {
        "skills": char.model_copy(update={"generated_skills": renamed}),
        "gear": char.model_copy(update={"equipment": {item.slot_type: item}}),
        "level": char.model_copy(update={"level": char.level + 2}),
    }
    for name, other in changed.items():
        before = len(calls)
        cached = hero_panel(lib, world, other)
        assert len(calls) == before + 1, f"{name} 變了要重算"
        clear_hero_panel_cache()
        fresh = hero_panel(lib, world, other)
        assert cached == fresh, name
    assert changed["level"] is not char
    clear_hero_panel_cache()
    assert hero_panel(lib, world, changed["skills"]) != base  # 技能變了，面板真的不同


def test_walk_field_still_filtered_for_viewer(client: TestClient) -> None:
    """守則 14：走路回應的 ``field`` 就是依這個角色過濾的視圖（快取不經手 ``field``）。"""
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    view = _ok(_walk(client, cid, [11, 8]))
    store = _store(client)
    expected = field_view(
        store.library,
        store.character(cid),
        world=store.world(),
        now=NOON,
        social=store.field_social(cid),
        inline_tiles=False,
    )
    assert expected is not None
    assert view["field"] == expected.model_dump(mode="json")


# ---------------------------------------------------------------------------
# 第 4 項：地點事件先回畫面，旁白之後補上
# ---------------------------------------------------------------------------


def _calm(field_library: ContentLibrary) -> ContentLibrary:
    return with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})


def _place_mark(client: TestClient, cid: str) -> None:
    """測試用：在霧渡鎮主角入口旁邊放一個事件「！」（略過進地點的機率；城裡沒有敵人，不會遇敵）。"""
    store = _store(client)
    trigger = EventTrigger(
        region="cloud_ridge",
        location="mist_ferry",
        skeleton=SKELETON,
        candidates=(SKELETON,),
        weather="clear",
        day_phase="day",
        at=store.clock(),
    )
    with store.lock:
        char = store.character(cid)
        mark = FieldEventMark(trigger=trigger, map="mist_ferry", x=12, y=8, spot="wm1_test")
        store._save_char(char.model_copy(update={"field_event": mark}))


def _touch_mark(client: TestClient, cid: str) -> dict[str, Any]:
    """走一格碰到「！」（站在它四方向相鄰）：開事件卡。"""
    url = f"/api/world/characters/{cid}/actions"
    view = _ok(client.post(url, json={"kind": "walk", "path": [[11, 8]]}))
    assert view["event"] is not None, view["events"]
    return view


def test_walk_event_story_deferred_with_llm(
    field_library: ContentLibrary, make_client: ClientFactory, tmp_path: Path
) -> None:
    """LLM 開著：走路那一步不呼叫 LLM、先回畫面（占位）；``event_story`` 補上旁白並照舊寫進日誌。"""
    provider = MockLlmProvider(generate=True, story_responses=["不是 JSON"] * 8)
    client = make_client(_calm(field_library), clock=lambda: NOON, llm=provider)
    store = _store(client)
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    _place_mark(client, cid)
    world0, initial = store.world(), store.character(cid)
    calls = len(provider.story.calls)
    event = _touch_mark(client, cid)["event"]
    assert event["story"] is None and event["story_pending"] is True  # 先回畫面
    assert len(provider.story.calls) == calls  # 走路的請求沒有呼叫 LLM

    filled = _ok(client.post(f"/api/world/characters/{cid}/event_story"))
    assert len(provider.story.calls) > calls  # 補旁白時才呼叫
    story = filled["event"]["story"]
    assert story is not None and story["text_zh"]
    assert filled["event"]["story_pending"] is False
    # 再送一次不重寫：已經敘述過
    again = _ok(client.post(f"/api/world/characters/{cid}/event_story"))
    assert again["event"]["story"] == story
    # 重新載入看得到同一段旁白（照舊存在日誌的 narrate 動作）
    assert _ok(client.get(f"/api/world/characters/{cid}"))["event"]["story"] == story

    saves = tmp_path / "saves" / "world"
    log = loads_log((saves / LOG_FILE).read_text(encoding="utf-8"))
    kinds = [e.action.kind for e in log]
    assert kinds == ["walk", "narrate"]  # 和原本同一個請求寫的一樣：走路之後一個 narrate
    replayed = replay(store.library, world0, {cid: initial}, log)
    saved = loads_char((saves / "chars" / f"{cid}.json").read_text(encoding="utf-8"))
    assert replayed.characters[cid] == saved


def test_walk_event_story_inline_without_llm(
    field_library: ContentLibrary, make_client: ClientFactory
) -> None:
    """LLM 關著：模板旁白很快，照舊在走路的請求裡寫好（沒有占位）。"""
    client = make_client(_calm(field_library), clock=lambda: NOON)
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    _place_mark(client, cid)
    event = _touch_mark(client, cid)["event"]
    assert event["story"] is not None
    assert event["story_pending"] is False
