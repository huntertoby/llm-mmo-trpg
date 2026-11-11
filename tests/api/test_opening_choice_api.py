"""#150 正式選定的 API（Phase OB-2）：``opening_confirm`` 在入門期是正式選定、``RangeView`` 帶推薦的
關鍵字。規則的表格測試在 ``tests/world/test_opening_choice.py``。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.api.world import WorldStore
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.opening import recommended_keywords
from trpg.world.state import DeferredOffer, QuestState

pytestmark = pytest.mark.capital_spawn

NEW = {"name": "小靶", "seed": 7, "race": "human"}
QUEST = "starter_ferry"
CONFIRM = {"kind": "opening_confirm", "weapon": "greatsword", "keywords": ["prone", "ignite"]}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> WorldStore:
    app: Any = client.app
    store = app.state.world
    assert isinstance(store, WorldStore)
    return store


def _starter(client: TestClient, weapon_class: str) -> tuple[str, str]:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    after = _ok(client.post(url, json={"kind": "opening_class", "weapon_class": weapon_class}))
    assert after["opening"]["recommended_keywords"] == []  # 還沒打完第 2 步：不算推薦
    return cid, url


def _after_two_steps(client: TestClient, cid: str) -> None:
    """把角色擺成「入門期、新手第 1、2 步打完、三選一保留」（規則本身在世界層的測試真的打）。"""
    store = _store(client)
    char = store.character(cid)
    assert char.opening is not None
    deferred = tuple(DeferredOffer(quest=QUEST, step=i) for i in range(2))
    opening = char.opening.model_copy(update={"deferred_offers": deferred})
    quests = (QuestState(quest=QUEST, steps_done=2, started_at=NOON),)
    store._save_char(char.model_copy(update={"opening": opening, "quests": quests}))


def test_confirm_before_two_steps_is_refused(client: TestClient) -> None:
    _cid, url = _starter(client, "melee")
    refused = client.post(url, json=CONFIRM)
    assert refused.status_code == 422 and "還不能正式選定" in refused.text


@pytest.mark.parametrize("weapon_class", ["melee", "ranged", "focus"])
def test_range_view_recommends_keywords_when_choice_is_open(
    client: TestClient, weapon_class: str
) -> None:
    cid, _url = _starter(client, weapon_class)
    _after_two_steps(client, cid)
    store = _store(client)
    char = store.character(cid)
    expected = list(recommended_keywords(store.library, char, char.hero.weapon))
    assert expected  # 目前三大類的入門招都至少有一個專屬關鍵字
    view = _ok(client.get(f"/api/world/characters/{cid}"))
    assert view["opening"]["stage"] == "starter"
    assert view["opening"]["recommended_keywords"] == expected


def test_formal_choice_through_api(client: TestClient) -> None:
    cid, url = _starter(client, "focus")
    _after_two_steps(client, cid)
    after = _ok(client.post(url, json=CONFIRM))  # 人在主城：工坊靶場也能選
    assert after["opening"]["stage"] == "chosen"
    assert after["opening"]["weapon_class"] == "melee"
    assert after["opening"]["recommended_keywords"] == []
    assert after["pending_offer"] is not None
    char = _store(client).character(cid)
    assert char.hero.weapon == "greatsword" and len(char.pending_offers) == 1
    assert char.attribute_points == 0 and sum(char.attribute_spent.values()) == 4
    for _ in range(2):
        after = _ok(client.post(url, json={"kind": "offer_pick", "pick": 0}))
    assert after["pending_offer"] is None
    char = _store(client).character(cid)
    assert char.opening is not None and len(char.opening.granted_skills) == 4
    again = client.post(url, json=CONFIRM)
    assert again.status_code == 422 and "已經正式選定" in again.text


def test_full_bag_refusal_reaches_the_player(client: TestClient) -> None:
    """背包放不下副手時，API 的 422 帶玩家看得懂的原因（OB-3 第 3 項）。"""
    cid, url = _starter(client, "melee")
    _after_two_steps(client, cid)
    store = _store(client)
    rules = store.library.world_economy.rules
    assert rules is not None
    shield = generate_item(store.library, Rng(7), "offhand", "rare", 3, weapon_class="focus")
    char = store.character(cid)
    store._save_char(
        char.model_copy(
            update={
                "equipment": {"off_hand": shield},
                "bag": {"item_coarse_material": 20 * rules.bag_slots},
            }
        )
    )
    refused = client.post(url, json=CONFIRM)
    assert refused.status_code == 422
    detail = refused.json()["detail"]
    assert "占用副手" in detail and "背包放不下" in detail and "雙手劍" in detail
    assert store.character(cid).opening.stage == "starter"  # type: ignore[union-attr]
