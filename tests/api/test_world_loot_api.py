"""``/api/world`` 的掉落與裝備（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.5）。

打贏 → ``last_loot_zh`` 與背包裡的材料、裝備 → 回霧渡鎮裝上 → 再打一場 → 賣掉撿到的裝備。
掉落率用測試內容庫拉到 100%（數值本身在 ``tests/world/test_loot.py`` 測）。
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
from trpg.content.world_loot import MainHandMix


@pytest.fixture(scope="module")
def lucky(library: ContentLibrary) -> ContentLibrary:
    ambush = with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})
    loot = library.world_loot
    assert loot is not None
    # 主手固定同大類（#135 的 50% 別大類另有 test_weapon_mix）：這裡驗的是穿上與賣出的流程。
    # 6T-1b 起別大類也換得上（tests/world/test_cross_class.py），所以「城鎮與營火才能換」的
    # 斷言對兩種主手都成立；固定同大類只是讓後面「換上」不用處理換裝確認與武器技暫停。
    main_hand = MainHandMix(same_permille=1000, elite_same_permille=1000)
    gear = loot.gear.model_copy(update={"battle_permille": 1000, "main_hand": main_hand})
    rules = loot.model_copy(update={"material_permille": 1000, "gear": gear})
    return dataclasses.replace(ambush, world_loot=rules)


@pytest.fixture
def client(lucky: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(lucky, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _act(client: TestClient, cid: str, **action: Any) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=action))


def _win(
    client: TestClient, cid: str, library: ContentLibrary, route: tuple[str, ...]
) -> dict[str, Any]:
    """從霧渡鎮走 ``route`` 到遇敵，打到贏一場（效用 AI 代打不保證贏；打贏的地點會清空）。"""
    before = _materials(_ok(client.get(f"/api/world/characters/{cid}")))
    for _ in range(6):
        for to in route:
            _act(client, cid, kind="travel", to=to)
        opened = _ok(client.post(f"/api/world/characters/{cid}/battle"))
        _finish_battle(client, opened["battle"], library)
        after = _ok(client.get(f"/api/world/characters/{cid}"))
        if _materials(after) > before:  # 打贏才有掉落（測試內容庫必掉材料）
            return after
    raise AssertionError("6 場都沒有打贏")


def _materials(view: dict[str, Any]) -> int:
    return sum(b["count"] for b in view["inventory"]["bag"] if b["kind_zh"] == "材料")


def _gear(view: dict[str, Any]) -> list[dict[str, Any]]:
    return [b for b in view["inventory"]["bag"] if b["gear"]]


def test_loot_equip_and_sell(client: TestClient, lucky: ContentLibrary) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    assert view["last_loot_zh"] is None

    won = _win(client, cid, lucky, ("ferry_steps",))
    assert won["last_loot_zh"].startswith("掉落：")
    assert any(e.startswith("掉落：") for e in won["events"])
    materials = [b for b in won["inventory"]["bag"] if b["kind_zh"] == "材料"]
    assert materials and all(not b["sellable"] for b in materials)  # 材料不能賣（20.1）
    pieces = _gear(won)
    assert len(pieces) == 1 and pieces[0]["kind_zh"] == "裝備"
    assert pieces[0]["can_equip"] is False and "城鎮與營火" in pieces[0]["equip_problem_zh"]
    assert "1 級" in pieces[0]["name_zh"] and pieces[0]["sell_price"] > 0

    home = _act(client, cid, kind="travel", to="mist_ferry")
    piece = _gear(home)[0]
    assert piece["can_equip"] is True
    equipped = _act(client, cid, kind="equip", item=piece["item"])
    assert any(piece["name_zh"] in line for line in equipped["inventory"]["equipped_zh"])
    assert any("換上" in e for e in equipped["events"])
    assert piece["item"] not in [b["item"] for b in _gear(equipped)]

    again = _win(client, cid, lucky, ("ferry_steps", "bamboo_path"))
    loot = [b for b in _gear(again) if b["sellable"]]
    assert loot
    _act(client, cid, kind="travel", to="ferry_steps")
    back = _act(client, cid, kind="travel", to="mist_ferry")
    gold = back["wallet"]["gold"]
    sold = _act(client, cid, kind="sell", shop="shop_liu", item=loot[-1]["item"])
    assert sold["wallet"]["gold"] == gold + loot[-1]["sell_price"]
    assert any(f"賣掉{loot[-1]['name_zh'].split('（')[0]}" in e for e in sold["events"])


def test_full_bag_choice_flow(lucky: ContentLibrary, tmp_path: Path) -> None:
    """5D-2b（玩法 PM 2026-11-03 代決）：背包滿了 → ``pending_loot`` → ``loot_choose`` 丟掉一件。"""
    economy = lucky.world_economy
    assert economy.rules is not None
    tiny = dataclasses.replace(
        lucky,
        world_economy=dataclasses.replace(
            economy, rules=economy.rules.model_copy(update={"bag_slots": 1})
        ),
    )
    with _client(tiny, tmp_path / "saves") as client:
        view = _ok(client.post("/api/world/characters", json=START), 201)
        cid = view["character"]["character_id"]
        assert view["pending_loot"] is None
        for _ in range(6):
            _act(client, cid, kind="travel", to="ferry_steps")
            opened = _ok(client.post(f"/api/world/characters/{cid}/battle"))
            _finish_battle(client, opened["battle"], tiny)
            view = _ok(client.get(f"/api/world/characters/{cid}"))
            if view["pending_loot"] is not None:
                break
        else:
            raise AssertionError("6 場都沒有背包滿")
        pending = view["pending_loot"]
        assert pending["over_slots"] >= 1 and pending["items"]
        assert "背包滿了" in pending["hint_zh"]
        bad = client.post(f"/api/world/characters/{cid}/actions", json={"kind": "loot_choose"})
        assert bad.status_code in (400, 409, 422) and "還差" in bad.text
        drop_items = {r["item"]: r["count"] for r in pending["items"] if not r["gear"]}
        drop_gear = [r["item"] for r in pending["items"] if r["gear"]]
        done = _act(client, cid, kind="loot_choose", drop_items=drop_items, drop_gear=drop_gear)
        assert done["pending_loot"] is None
        assert any(e.startswith("丟掉了") for e in done["events"])
