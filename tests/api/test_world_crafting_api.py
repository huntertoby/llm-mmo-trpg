"""``/api/world`` 的鐵匠與附魔台（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.5）。

霧渡鎮看得到鐵匠 → 在柳掌櫃買粗料 → 打造（首位發現者）→ 同配方再打一件（配方碼）→ 強化 → 分解一件
拿精華 → 附魔台重骰。開局金幣用測試內容庫調高。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client
from trpg.content.library import ContentLibrary

SMITHY = "smithy_mist_ferry"
ENCHANTER = "enchanter_mist_ferry"
COARSE = "item_coarse_material"


@pytest.fixture(scope="module")
def rich(library: ContentLibrary) -> ContentLibrary:
    economy = library.world_economy
    assert economy.rules is not None
    rules = economy.rules.model_copy(update={"start_gold": 1000})
    return dataclasses.replace(library, world_economy=dataclasses.replace(economy, rules=rules))


@pytest.fixture
def client(rich: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(rich, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _act(client: TestClient, cid: str, **action: Any) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=action))


def test_craft_enhance_salvage_reroll(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    crafting = view["crafting"]
    assert crafting is not None and crafting["smithy"] == SMITHY
    assert crafting["enchanter"] == ENCHANTER and crafting["can_use"]
    neck = next(s for s in crafting["slots"] if s["slot_type"] == "neck")
    affix = neck["affixes"][0]["id"]
    assert {r["rarity"] for r in crafting["rarities"]} == {"rare", "epic"}

    for _ in range(4):
        view = _act(client, cid, kind="buy", shop="shop_liu", item=COARSE, count=1)
    assert any(m["item"] == COARSE and m["grade"] for m in view["crafting"]["materials"])

    craft = {"kind": "craft", "station": SMITHY, "slot_type": "neck", "rarity": "rare"}
    view = _act(client, cid, **craft, affix=affix, grade=COARSE)
    assert any("首位發現者" in e for e in view["events"])
    recipe = view["crafting"]["recipes"][0]
    assert recipe["mine"] and recipe["can_craft"]
    view = _act(client, cid, kind="craft", station=SMITHY, code=recipe["code"])
    gear = view["crafting"]["gear"]
    assert len(gear) == 2 and gear[0]["code"] == recipe["code"]
    first, second = gear[0]["item"], gear[1]["item"]
    assert first != second

    assert gear[0]["can_enhance"], gear[0]["enhance_zh"]
    view = _act(client, cid, kind="enhance", station=SMITHY, item=first)
    assert any("強化到 +1" in e for e in view["events"])

    view = _act(client, cid, kind="salvage", station=SMITHY, item=second)
    assert view["crafting"]["essence"] == 2
    assert any("精華 ×2" in e for e in view["events"])

    item = next(g for g in view["crafting"]["gear"] if g["item"] == first)
    assert item["affixes"][0]["can_change"]
    view = _act(client, cid, kind="reroll", station=ENCHANTER, item=first, index=0)
    assert any("重骰成" in e for e in view["events"])
    assert view["crafting"]["essence"] == 1
    # 5D-3b：重骰後這件有帶序列的新配方碼，配方表列出它（重骰 1 次）
    assert any("新的配方碼" in e and "首位發現者" in e for e in view["events"])
    item = next(g for g in view["crafting"]["gear"] if g["item"] == first)
    assert item["code"] != recipe["code"]
    variant = next(r for r in view["crafting"]["recipes"] if r["code"] == item["code"])
    assert "重骰 1 次" in variant["summary_zh"] and recipe["code"] in variant["summary_zh"]
    assert variant["can_craft"], variant["problem_zh"]  # 剩 1 精華，夠付 1 次重骰
    # 5D-4：配方表每件裝備只列最新一筆（基礎碼不列，但照樣能打）
    assert [r["code"] for r in view["crafting"]["recipes"]] == [item["code"]]
    view = _act(client, cid, kind="craft", station=SMITHY, code=variant["code"])
    copy = view["crafting"]["gear"][-1]
    assert copy["code"] == item["code"] and copy["description_zh"] == item["description_zh"]
    assert view["crafting"]["essence"] == 0


def test_crafting_hidden_away_from_town(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    moved = _act(client, cid, kind="travel", to="ferry_steps")
    if moved["encounter"] is None:
        assert moved["crafting"] is None
    bad = client.post(
        f"/api/world/characters/{cid}/actions",
        json={"kind": "craft", "station": SMITHY, "code": "ABCDEF0123"},
    )
    assert bad.status_code in {400, 409, 422}
