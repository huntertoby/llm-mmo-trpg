"""#150 正式選定的 API（Phase OB-2）：``opening_confirm`` 在入門期是正式選定、``RangeView`` 帶推薦的
關鍵字。規則的表格測試在 ``tests/world/test_opening_choice.py``。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.api.world import WorldStore
from trpg.content.equipment import ItemDef
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world import opening
from trpg.world.opening import recommended_keywords
from trpg.world.opening_reselect import starter_item_id
from trpg.world.state import DeferredOffer, GearMod, QuestState

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


# ---------------------------------------------------------------------------
# 帶武器的推薦查詢（OB-3）
# ---------------------------------------------------------------------------

RECOMMEND_WEAPONS = ("one_handed_sword", "greatsword", "dagger", "bow", "pistol", "fire_staff")


@pytest.mark.parametrize("weapon_class", ["melee", "ranged", "focus"])
def test_recommend_follows_the_weapon_in_hand(client: TestClient, weapon_class: str) -> None:
    """照玩家當下選的武器算（不是手上的入門武器）；結果和純函式相同、0～2 個、重複查詢一樣。"""
    cid, _url = _starter(client, weapon_class)
    _after_two_steps(client, cid)
    store = _store(client)
    char = store.character(cid)
    url = f"/api/world/characters/{cid}/range/recommend"
    for weapon in RECOMMEND_WEAPONS:
        out = _ok(client.get(url, params={"weapon": weapon}))
        expected = list(recommended_keywords(store.library, char, weapon))
        assert out == {"weapon": weapon, "keywords": expected}
        assert 1 <= len(expected) <= 2 and len(set(expected)) == len(expected)
        assert _ok(client.get(url, params={"weapon": weapon})) == out
    view = _ok(client.get(f"/api/world/characters/{cid}"))  # 既有欄位照舊：手上的入門武器
    held = _ok(client.get(url, params={"weapon": char.hero.weapon}))
    assert view["opening"]["recommended_keywords"] == held["keywords"]


def test_recommend_is_cached(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """同一個角色、同一把武器只算一次（一把武器要試十幾個關鍵字的起始技能）。"""
    cid, _url = _starter(client, "melee")
    _after_two_steps(client, cid)
    calls: list[str] = []
    real = opening._recommend

    def counted(library: ContentLibrary, seed: int, weapon: str, candidates: Any) -> Any:
        calls.append(weapon)
        return real(library, seed, weapon, candidates)

    monkeypatch.setattr(opening, "_recommend", counted)
    opening._recommended.clear()
    url = f"/api/world/characters/{cid}/range/recommend"
    first = _ok(client.get(url, params={"weapon": "spear"}))
    for _ in range(3):
        assert _ok(client.get(url, params={"weapon": "spear"})) == first
    assert calls == ["spear"]


def test_recommend_only_when_choice_is_open(client: TestClient) -> None:
    """只在可以正式選定時回應：還沒打完第 2 步、不在霧渡鎮或主城、已經選定、武器不在靶場都 422。"""
    cid, url = _starter(client, "melee")
    recommend = f"/api/world/characters/{cid}/range/recommend"
    early = client.get(recommend, params={"weapon": "bow"})
    assert early.status_code == 422 and "還不能正式選定" in early.text
    _after_two_steps(client, cid)
    unknown = client.get(recommend, params={"weapon": "no_such_weapon"})
    assert unknown.status_code == 422 and "靶場沒有這把武器" in unknown.text
    assert client.get(recommend).status_code == 422  # 沒帶武器
    store = _store(client)
    away = store.character(cid).model_copy(
        update={"region": "cloud_ridge", "location": "bamboo_path"}
    )
    store._save_char(away)
    far = client.get(recommend, params={"weapon": "bow"})
    assert far.status_code == 422 and "霧渡鎮找葛蘭" in far.text
    store._save_char(away.model_copy(update={"region": "capital", "location": "capital"}))
    assert _ok(client.get(recommend, params={"weapon": "bow"}))["keywords"]
    _ok(client.post(url, json=CONFIRM))
    for _ in range(2):
        _ok(client.post(url, json={"kind": "offer_pick", "pick": 0}))
    # 可以重選時也回應；入門招的使用紀錄已經收回，算不出推薦＝空
    assert _ok(client.get(recommend, params={"weapon": "bow"})) == {"weapon": "bow", "keywords": []}


# ---------------------------------------------------------------------------
# 4 級前的免費重選（OB-3）
# ---------------------------------------------------------------------------

RESELECT = {"kind": "opening_reselect", "weapon": "bow", "keywords": ["ignite", "frozen"]}


def _chosen(client: TestClient) -> tuple[str, str]:
    cid, url = _starter(client, "focus")
    _after_two_steps(client, cid)
    _ok(client.post(url, json=CONFIRM))
    for _ in range(2):
        _ok(client.post(url, json={"kind": "offer_pick", "pick": 0}))
    return cid, url


def test_reselect_view_and_action(client: TestClient) -> None:
    cid, url = _chosen(client)
    view = _ok(client.get(f"/api/world/characters/{cid}"))
    info = view["opening"]["reselect"]
    assert info["available"] is True and info["blocked_zh"] is None and info["used"] is False
    assert info["before_level"] == 4
    assert (info["weapon"], info["keywords"]) == ("greatsword", ["prone", "ignite"])
    assert len(info["returned_zh"]) == 4 and all(info["returned_zh"])
    assert info["weapon_returned"] is True and info["lost_zh"] == []
    after = _ok(client.post(url, json=RESELECT))
    assert any("重選完成：改拿弓" in line and "收回：" in line for line in after["events"])
    again = after["opening"]["reselect"]
    assert again["available"] is False and again["used"] is True
    assert again["blocked_zh"] == "免費重選只有一次，已經用過了"
    assert (again["weapon"], again["keywords"]) == ("bow", ["ignite", "frozen"])
    assert after["pending_offer"] is not None
    char = _store(client).character(cid)
    assert char.hero.weapon == "bow" and len(char.pending_offers) == 1
    for _ in range(2):
        after = _ok(client.post(url, json={"kind": "offer_pick", "pick": 0}))
    refused = client.post(url, json=RESELECT)
    assert refused.status_code == 422 and "只有一次" in refused.text
    recommend = client.get(f"/api/world/characters/{cid}/range/recommend", params={"weapon": "bow"})
    assert recommend.status_code == 422 and "只有一次" in recommend.text


def test_reselect_view_lists_lost_enhancement(client: TestClient) -> None:
    """確認畫面要列的損失：起始武器本體上的強化（材料不退）。"""
    cid, _url = _chosen(client)
    store = _store(client)
    char = store.character(cid)
    base_id = starter_item_id(store.library, char)
    assert base_id is not None
    own = generate_item(store.library, Rng(7), "weapon", "rare", 3, weapon_class="melee")
    base = ItemDef(
        id=base_id, name_zh="雙手劍", slot_type="weapon", weapon="greatsword", rarity="common"
    )
    mod = GearMod(fingerprint="0" * 64, enhance=3)
    store._save_char(
        char.model_copy(
            update={
                "hero": char.hero.model_copy(update={"weapon": own.weapon}),
                "equipment": {"main_hand": own},
                "gear": (base,),
                "gear_mods": {base_id: mod},
            }
        )
    )
    info = _ok(client.get(f"/api/world/characters/{cid}"))["opening"]["reselect"]
    assert info["weapon_returned"] is True
    assert info["lost_zh"] == ["雙手劍的強化 +3（材料不退）"]


def test_reselect_refused_before_choice_and_for_old_characters(client: TestClient) -> None:
    cid, url = _starter(client, "melee")
    early = client.post(url, json=RESELECT)
    assert early.status_code == 422 and "還沒正式選定" in early.text
    assert _ok(client.get(f"/api/world/characters/{cid}"))["opening"]["reselect"] is None
    legacy = {**NEW, "name": "老手", "weapon": "dagger", "keywords": ["frozen", "concealed"]}
    old = _ok(client.post("/api/world/characters", json=legacy), 201)
    assert old["opening"] is None
    old_url = f"/api/world/characters/{old['character']['character_id']}/actions"
    done = client.post(old_url, json=RESELECT)
    assert done.status_code == 422 and "開局已經結束" in done.text
