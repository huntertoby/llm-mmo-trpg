"""主城開場四格（Phase RT-5；09 9.6.9 #125、21 21.5）的伺服器面。

- ③ 大世界圖的「免費」（``AtlasRegionView.free``）照「角色還沒到過霧渡鎮」：新角色在主城時只有新手區
  （雲嶺）是 ``True``；傳送過去一次之後就是 ``False``（回到主城也一樣），不另加旗標。
- ② 橋頭石碑的小牌照大世界的開放狀態（``atlas.regions``）：
  雲嶺已開放、荒原尚未開放、其他三區之後的賽季。
- ④ 抵達霧渡鎮：主題換雲嶺（``field.region``），渡婆婆頭上有任務「！」。
- 開場文案由內容提供（``world/newcomer.yaml`` 的 ``opening``），全程不會進戰鬥。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.world import START_REGION, WorldStore
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary

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


def _free(view: dict[str, Any]) -> dict[str, bool]:
    atlas = view["atlas"]
    out = {r["region"]: r["free"] for r in atlas["regions"]}
    out[atlas["capital"]["region"]] = atlas["capital"]["free"]
    return out


@pytest.mark.capital_spawn
def test_free_label_only_before_first_visit(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    free = _free(view)
    assert free[START_REGION] is True
    assert [r for r, on in free.items() if on] == [START_REGION]
    cloud = next(r for r in view["atlas"]["regions"] if r["region"] == START_REGION)
    assert cloud["can_teleport"] is True
    there = _act(client, cid, kind="teleport", region=START_REGION)
    assert not any(_free(there).values())
    back = _act(client, cid, kind="teleport", region=CAPITAL_REGION)
    assert back["map"]["region"] == CAPITAL_REGION
    assert not any(_free(back).values())  # 免費只有第一次
    assert back["guide"] is None


@pytest.mark.capital_spawn
def test_stele_plaques_follow_atlas_status(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    status = {r["region"]: r["status"] for r in view["atlas"]["regions"]}
    assert status == {
        "cloud_ridge": "open",
        "ashen_waste": "locked",
        "crystal_crown": "later",
        "arcane_hub": "later",
        "frost_tide": "later",
    }
    steles = {
        o["stele_region"]
        for o in view["field"]["situation_objects"]
        if o.get("stele_region") is not None
    }
    assert steles == set(status)


@pytest.mark.capital_spawn
def test_opening_to_ferry_without_battle(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    assert [line["speaker_zh"] for line in view["guide"]["opening"]] == ["說書人", "守印人"]
    keeper = [o for o in view["field"]["situation_objects"] if o["name_zh"] == "守印人"]
    assert len(keeper) == 1 and keeper[0]["figure"] is not None
    seen = _act(client, cid, kind="hint_seen", ids=["opening"])
    assert "opening" in seen["hints"]["seen"]
    there = _act(client, cid, kind="teleport", region=START_REGION)
    assert there["encounter"] is None
    assert there["field"]["region"] == START_REGION
    alerts = {n["name_zh"]: n["alert"] for n in there["field"]["npcs"]}
    assert alerts["渡婆婆"] == "quest"
