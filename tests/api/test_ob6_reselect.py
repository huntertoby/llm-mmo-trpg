"""OB-6a 的行為一致測試（``docs/phases/PhaseOB-6計畫.md``「行為一致測試」T1～T3）。

一律打 ``POST /api/world/characters/{id}/actions``：角色照
``tests/world/test_opening_choice.py::_played`` 真的打完新手第 1、2 步（AI 代打），再經 API 正式
選定、選完兩組三選一。每一列同時斷言畫面資料（``opening.reselect`` 的 ``available``／
``window_open``／``blocked_zh``）和送出的結果一致。種子固定（建角種子 7、開局種子 7）。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, hero, make_encounter, with_rules, without_fields
from tests.world.test_gear import _item
from tests.world.test_opening_choice import _played
from trpg.api.opening_gear_note import STARTER_WEAPON_ZH, reselect_weapon_zh
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.opening import HIRE_PANEL_ZH, SHADOW_AI_ZH, opening_limits, range_content
from trpg.world.opening_choice import place_problem
from trpg.world.opening_reselect import starter_item_id
from trpg.world.state import CharacterState
from trpg.world.step import new_character

CONFIRM = {"kind": "opening_confirm", "weapon": "greatsword", "keywords": ["prone", "ignite"]}
RESELECT = {"kind": "opening_reselect", "weapon": "fire_staff", "keywords": ["ignite", "charged"]}
NEW = {"name": "小靶", "seed": 7, "race": "human"}
SHOP = "shop_liu"


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})
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


def _url(cid: str) -> str:
    return f"/api/world/characters/{cid}/actions"


def _view(client: TestClient, cid: str) -> dict[str, Any]:
    return _ok(client.get(f"/api/world/characters/{cid}"))


def _starter_played(client: TestClient) -> str:
    """API 建角 → 換成「真的打完第 1、2 步、人在霧渡鎮、遠程入門期」的角色（同一個 ID）。"""
    cid = str(_ok(client.post("/api/world/characters", json=NEW), 201)["character"]["character_id"])
    store = _store(client)
    library = without_fields(store.library)  # 真的打的那兩場照世界層測試的做法（沒有實地地圖）

    def factory(character_id: str = cid, **updates: Any) -> CharacterState:
        char = new_character(library, character_id, hero(library), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    store._save_char(_played(library, factory, "ranged"))
    return cid


def _chosen(client: TestClient) -> str:
    """正式選定（經 API）並選完兩組延後的三選一：3 級、在霧渡鎮、還能重選。"""
    cid = _starter_played(client)
    _ok(client.post(_url(cid), json=CONFIRM))
    for _ in range(2):
        _ok(client.post(_url(cid), json={"kind": "offer_pick", "pick": 0}))
    char = _store(client).character(cid)
    assert char.level == 3 and not char.pending_offers
    return cid


def _patch(client: TestClient, cid: str, **updates: Any) -> CharacterState:
    store = _store(client)
    char = store.character(cid).model_copy(update=updates)
    store._save_char(char)
    return char


def _refused_matches_view(client: TestClient, cid: str) -> str:
    """畫面資料說不能重選，送出被拒的句子＝``blocked_zh``，角色不變。"""
    reselect = _view(client, cid)["opening"]["reselect"]
    assert reselect["available"] is False and reselect["blocked_zh"]
    before = _store(client).character(cid)
    refused = client.post(_url(cid), json=RESELECT)
    assert refused.status_code == 422
    assert refused.json()["detail"] == reselect["blocked_zh"]
    assert _store(client).character(cid) == before
    return str(reselect["blocked_zh"])


# ---------------------------------------------------------------------------
# T1 重選規則表
# ---------------------------------------------------------------------------


def test_reselect_in_mentor_town(client: TestClient) -> None:
    cid = _chosen(client)
    library = _store(client).library
    arena = range_content(library)
    reselect = _view(client, cid)["opening"]["reselect"]
    assert reselect["available"] and reselect["window_open"] and reselect["blocked_zh"] is None
    assert not reselect["in_capital"] and reselect["here_zh"] == arena.choose_place_zh
    assert reselect["speaker"]["name_zh"] == "葛蘭"
    assert [x["text_zh"] for x in reselect["lines"]] == [x.text_zh for x in arena.reselect]
    assert [x["text_zh"] for x in reselect["done"]] == [x.text_zh for x in arena.reselect_done]
    assert reselect["npc"] == "gran" and reselect["place_zh"] == place_problem(library, "重選")
    after = _ok(client.post(_url(cid), json=RESELECT))
    assert after["opening"]["reselect"]["window_open"] is False  # 小牌消失
    assert after["opening"]["reselect"]["used"] is True
    assert after["pending_offer"] is not None  # 第 1 組三選一重新出
    char = _store(client).character(cid)
    assert char.hero.weapon == "fire_staff" and char.opening is not None
    assert char.opening.reselect_used and char.opening.keywords == ("ignite", "charged")


def test_reselect_in_capital_speaker_is_keeper(
    field_library: ContentLibrary, make_client: ClientFactory
) -> None:
    """守印人的頭像在主城的實地地圖上，所以這一列用有實地地圖的內容庫。"""
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    client = make_client(calm, clock=lambda: NOON)
    cid = _chosen(client)
    arena = range_content(_store(client).library)
    _patch(client, cid, region="capital", location="capital")
    reselect = _view(client, cid)["opening"]["reselect"]
    assert reselect["available"] and reselect["in_capital"]
    assert reselect["speaker"]["name_zh"] == "守印人"
    assert [x["text_zh"] for x in reselect["lines"]] == [x.text_zh for x in arena.reselect_capital]
    assert [x["text_zh"] for x in reselect["done"]] == [
        x.text_zh for x in arena.reselect_capital_done
    ]
    assert reselect["here_zh"].endswith("工坊靶場") and "主城" not in reselect["here_zh"]
    _ok(client.post(_url(cid), json=RESELECT))


def test_reselect_in_the_wild_is_refused_but_badge_stays(client: TestClient) -> None:
    cid = _chosen(client)
    _patch(client, cid, location="ferry_steps")
    reason = _refused_matches_view(client, cid)
    assert reason == place_problem(_store(client).library, "重選")
    assert _view(client, cid)["opening"]["reselect"]["window_open"] is True


def test_second_reselect_is_refused(client: TestClient) -> None:
    cid = _chosen(client)
    _ok(client.post(_url(cid), json=RESELECT))
    _ok(client.post(_url(cid), json={"kind": "offer_pick", "pick": 0}))
    _ok(client.post(_url(cid), json={"kind": "offer_pick", "pick": 0}))
    assert _refused_matches_view(client, cid) == "免費重選只有一次，已經用過了"


def test_reselect_ends_at_before_level(client: TestClient) -> None:
    cid = _chosen(client)
    reselect = _view(client, cid)["opening"]["reselect"]
    assert reselect["before_level"] == OPENING_END_LEVEL
    _patch(client, cid, level=reselect["before_level"])
    assert (
        _refused_matches_view(client, cid) == f"已到 {reselect['before_level']} 級，免費重選已結束"
    )
    assert _view(client, cid)["opening"]["reselect"]["window_open"] is False
    _patch(client, cid, level=reselect["before_level"] - 1)
    assert _view(client, cid)["opening"]["reselect"]["window_open"] is True


def test_no_reselect_in_starter_period(client: TestClient) -> None:
    cid = _starter_played(client)
    view = _view(client, cid)
    assert view["opening"]["stage"] == "starter" and view["opening"]["reselect"] is None
    refused = client.post(_url(cid), json=RESELECT)
    assert refused.status_code == 422 and "還沒正式選定" in refused.json()["detail"]


def test_pending_encounter_blocks_reselect(client: TestClient) -> None:
    cid = _chosen(client)
    _patch(client, cid, pending_encounter=make_encounter("ferry_steps"))
    assert _refused_matches_view(client, cid) == "還有沒處理的遭遇，不能重選"


def test_full_bag_after_swapping_main_hand_is_refused(client: TestClient) -> None:
    """換過主手（起始武器本體進背包，卡片寫會收回）→ 起始武器賣掉、背包塞滿 → 被拒、角色不變。"""
    cid = _chosen(client)
    store = _store(client)
    rules = store.library.world_economy.rules
    assert rules is not None
    own = _item(store.library, "weapon")
    _patch(client, cid, gear=(own,))
    _ok(client.post(_url(cid), json={"kind": "equip", "item": own.id}))
    base_id = starter_item_id(store.library, store.character(cid))
    rows = {r["item"]: r for r in _view(client, cid)["inventory"]["bag"] if r["gear"]}
    assert rows[base_id]["opening_note_zh"] == reselect_weapon_zh()  # 背包裡的起始武器卡
    _patch(client, cid, gear=(), bag={"item_coarse_material": 20 * rules.bag_slots})
    reselect = _view(client, cid)["opening"]["reselect"]
    assert reselect["available"]  # 畫面資料不預先判斷背包（OB-3）；送出時才拒絕
    before = store.character(cid)
    refused = client.post(_url(cid), json=RESELECT)
    assert refused.status_code == 422 and "背包放不下" in refused.json()["detail"]
    after = store.character(cid)
    assert after == before and after.opening is not None and not after.opening.reselect_used


def test_finished_opening_has_no_reselect(client: TestClient) -> None:
    cid = _chosen(client)
    _patch(client, cid, opening=None)
    assert _view(client, cid)["opening"] is None
    refused = client.post(_url(cid), json=RESELECT)
    assert refused.status_code == 422 and "開局已經結束" in refused.json()["detail"]


def test_what_changes_and_what_stays(client: TestClient) -> None:
    cid = _chosen(client)
    store = _store(client)
    helm = _item(store.library, "head")
    _patch(client, cid, gear=(helm,), gold=123)
    before = store.character(cid)
    reselect = _view(client, cid)["opening"]["reselect"]
    after_view = _ok(client.post(_url(cid), json=RESELECT))
    after = store.character(cid)
    assert before.opening is not None and after.opening is not None
    # 變
    assert after.hero.weapon != before.hero.weapon
    assert after.opening.keywords != before.opening.keywords
    assert after.hero.skills[:2] != before.hero.skills[:2]
    assert not set(before.opening.granted_skills) & set(after.hero.skills + after.bench)
    assert after.attribute_spent != before.attribute_spent
    assert after.opening.reselect_used and not before.opening.reselect_used
    assert after.pending_offers
    # 不變
    for name in ("level", "xp", "insight", "gold", "region", "location", "quests"):
        assert getattr(after, name) == getattr(before, name), name
    assert helm in after.gear
    # 確認彈窗列的 = 實際收回的
    assert after_view["opening"]["reselect"]["used"] is True
    returned = reselect["returned_zh"]
    names = {s.id: s.name_zh for s in before.generated_skills}
    gone = [
        names.get(s) or store.library.skills[s].name_zh
        for s in (*before.hero.skills, *before.bench)
        if s in before.opening.granted_skills and s not in after.hero.skills + after.bench
    ]
    assert returned == gone
    item = starter_item_id(store.library, before)
    still_there = any(g.id == item for g in after.gear) or after.hero.weapon == before.hero.weapon
    assert reselect["weapon_returned"] is True and not still_there


# ---------------------------------------------------------------------------
# T2 雇用句、影子打法句
# ---------------------------------------------------------------------------


def test_hire_and_shadow_reasons_in_starter_period(client: TestClient) -> None:
    cid = _starter_played(client)
    view = _view(client, cid)
    limits = opening_limits(_store(client).character(cid))
    hire = client.post(_url(cid), json={"kind": "hire", "mercenaries": []})
    assert hire.status_code == 422
    assert hire.json()["detail"] == HIRE_PANEL_ZH == limits["hire"] == view["limits"]["hire"]
    assert view["party"]["hire_problem_zh"] == HIRE_PANEL_ZH
    shadow = client.post(_url(cid), json={"kind": "shadow_ai", "profile": None})
    assert shadow.status_code == 422 and shadow.json()["detail"] == SHADOW_AI_ZH


# ---------------------------------------------------------------------------
# T3 入門武器卡寫的「不能」與起始武器卡
# ---------------------------------------------------------------------------


def _main_hand(view: dict[str, Any]) -> dict[str, Any]:
    slots = {e["slot"]: e for e in view["inventory"]["equipment"]}
    slot: dict[str, Any] = slots["main_hand"]
    return slot


def test_starter_weapon_card_and_every_cannot_is_refused(client: TestClient) -> None:
    cid = _starter_played(client)
    view = _view(client, cid)
    main = _main_hand(view)
    assert main["opening_note_zh"] == STARTER_WEAPON_ZH
    item = main["item"]["id"]
    before = _store(client).character(cid)
    tries = {
        "賣": {"kind": "sell", "shop": SHOP, "item": item},
        "寄": {"kind": "mail_send", "to": "bob", "gear": [item]},
        "分解": {"kind": "salvage", "station": "smithy_mist_ferry", "item": item},
    }
    for word, action in tries.items():
        assert word in STARTER_WEAPON_ZH
        reply = client.post(_url(cid), json=action)
        assert reply.status_code == 422, (word, reply.text)
        assert _store(client).character(cid) == before


def test_chosen_weapon_card_note_only_while_reselect_is_open(client: TestClient) -> None:
    cid = _chosen(client)
    assert _main_hand(_view(client, cid))["opening_note_zh"] == reselect_weapon_zh()
    assert reselect_weapon_zh() == "4 級前重選的話，這把會被收回。"  # 定稿（before_level＝4）
    _ok(client.post(_url(cid), json=RESELECT))
    assert _main_hand(_view(client, cid))["opening_note_zh"] is None


def test_allocate_lesson_carries_reselect_reminder(client: TestClient) -> None:
    cid = _chosen(client)
    arena = range_content(_store(client).library)
    lesson = _view(client, cid)["lesson"]
    assert lesson is not None and lesson["kind"] == "allocate" and lesson["respec"]
    assert [x["text_zh"] for x in lesson["reselect_reminder"]] == [
        x.text_zh for x in arena.reselect_reminder
    ]
    _patch(client, cid, level=OPENING_END_LEVEL)  # 沒有資格就不提醒
    lesson = _view(client, cid)["lesson"]
    assert lesson is None or lesson["reselect_reminder"] == []
