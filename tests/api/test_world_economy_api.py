"""``/api/world`` 的貨幣、背包、腰包與商店（Phase 5D-1；``docs/phases/Phase5計畫.md`` 25.5）。

打一場拿金幣 → 回霧渡鎮 → 柳掌櫃的店列商品 → 買一個消耗品 → 背包看到 → 柳掌櫃好感度 +2 → 整理腰包
→ 賣東西。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client, _finish_battle
from tests.world.helpers import with_rules
from trpg.content.library import ContentLibrary


@pytest.fixture(scope="module")
def ambush(library: ContentLibrary) -> ContentLibrary:
    lib = with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})
    economy = lib.world_economy
    assert economy.rules is not None
    # 一場就買得起解毒草（25）：測試把一般戰鬥金幣調成 30
    gold = economy.rules.battle_gold.model_copy(update={"battle": 30})
    rules = economy.rules.model_copy(update={"battle_gold": gold})
    return dataclasses.replace(lib, world_economy=dataclasses.replace(economy, rules=rules))


@pytest.fixture
def client(ambush: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(ambush, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _act(client: TestClient, cid: str, **action: Any) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=action))


def _shop_item(view: dict[str, Any], item: str) -> dict[str, Any]:
    found: dict[str, Any] = next(i for i in view["shop"]["items"] if i["item"] == item)
    return found


def _loot(view: dict[str, Any]) -> list[dict[str, Any]]:
    """背包裡打贏撿到的材料與裝備（5D-2）。"""
    return [b for b in view["inventory"]["bag"] if b["gear"] or b["kind_zh"] == "材料"]


def _shelf(view: dict[str, Any]) -> list[dict[str, Any]]:
    """背包裡掉落以外的東西。"""
    return [b for b in view["inventory"]["bag"] if b not in _loot(view)]


def test_fight_buy_and_pouch(client: TestClient, ambush: ContentLibrary) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    assert view["wallet"] == {"gold": 0, "quest_coins": 0}
    assert view["inventory"]["slots_max"] == 30 and view["inventory"]["pouch_max"] == 3
    shop = view["shop"]
    assert shop["name_zh"] == "柳記雜貨" and shop["npc_name_zh"] == "柳掌櫃"
    pill = _shop_item(view, "item_antidote_herb")
    assert pill["price"] == 25 and pill["can_buy"] is False and "金幣不夠" in pill["problem_zh"]
    mist = _shop_item(view, "item_mist_flask")
    assert mist["locked"] is True and mist["lock_zh"] == "柳掌櫃好感度到友善才賣"
    bamboo = _shop_item(view, "item_green_bamboo")
    assert bamboo["weekly"] is True and bamboo["stock_zh"].startswith("本週剩 ")
    assert "每次消費柳掌櫃好感度 +2" in shop["affinity_zh"]

    for _ in range(10):  # 效用 AI 代打不保證贏：輸了（回霧渡鎮、不給金幣）就再打一場
        _act(client, cid, kind="travel", to="ferry_steps")
        opened = _ok(client.post(f"/api/world/characters/{cid}/battle"))
        _finish_battle(client, opened["battle"], ambush)
        after = _ok(client.get(f"/api/world/characters/{cid}"))
        if after["wallet"]["gold"] > 0:
            break
        assert not any("金幣" in e for e in after["events"])  # 輸了不給
    assert after["wallet"]["gold"] == 30
    assert any("獲得 30 金幣" in e for e in after["events"])
    assert after["shop"] is None  # 野外沒有店

    home = _act(client, cid, kind="travel", to="mist_ferry")
    assert home["shop"] is not None and _shop_item(home, "item_antidote_herb")["can_buy"] is True
    bought = _act(client, cid, kind="buy", shop="shop_liu", item="item_antidote_herb")
    assert bought["wallet"]["gold"] == 5
    looted = len(_loot(home))  # 5D-2：打贏可能撿到材料、裝備
    assert [(b["item"], b["count"]) for b in _shelf(bought)] == [("item_antidote_herb", 1)]
    assert bought["inventory"]["slots_used"] == 1 + looted
    assert any("買了解毒草 ×1" in e for e in bought["events"])
    assert any("柳掌櫃的好感度" in e for e in bought["events"]), bought["events"]
    assert "今天還能 +2" in bought["shop"]["affinity_zh"]

    pouched = _act(client, cid, kind="pouch", items={"item_antidote_herb": 1})
    inventory = pouched["inventory"]
    assert _shelf(pouched) == [] and inventory["pouch_count"] == 1
    assert inventory["pouch"][0]["battle_zh"].startswith("放進腰包")
    assert any("腰包：解毒草 ×1" in e for e in pouched["events"])

    emptied = _act(client, cid, kind="pouch", items={})
    sold = _act(client, cid, kind="sell", shop="shop_liu", item="item_antidote_herb")
    assert emptied["inventory"]["pouch"] == []
    assert sold["wallet"]["gold"] == 17 and _shelf(sold) == []


def test_bad_economy_actions_are_rejected(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    reply = client.post(
        f"/api/world/characters/{cid}/actions",
        json={"kind": "buy", "shop": "shop_liu", "item": "item_hp_potion_small"},
    )
    assert reply.status_code in (400, 409, 422) and "金幣不夠" in reply.text
