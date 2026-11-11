"""主城工坊靶場（Phase TR-1，#134；21 21.5、09 9.6.9、06 6.27.3）的 API。

- 建角不含武器與關鍵字＝未完成開局：停在主城、拿佔位武器、沒有技能；畫面拿到 ``opening``。
- 未完成開局時只能確定出發（其他動作 422）；確定出發照 6.27.3 給起始技能，和舊流程（建角就選）
  的結果相同；出發之後不能重選。
- 沙盒試打：不寫世界日誌、不改角色存檔（HP、法力、經驗、背包）、不登記成角色的戰鬥；同一組選擇的
  種子相同（確定性）；示範招是該大類的 2 招，看示範是關鍵字的起始技能。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.world.opening import trial_seed

pytestmark = pytest.mark.capital_spawn  # 正式的出生地：主城（#125）

NEW = {"name": "小靶", "seed": 7, "race": "human"}
PICK = {"weapon": "dagger", "keywords": ["frozen", "concealed"]}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _new(client: TestClient) -> tuple[str, dict[str, Any]]:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    return view["character"]["character_id"], view


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _log_lines(client: TestClient) -> int:
    store = _store(client)
    return len(store.entries())


def test_create_without_weapon_is_pending(client: TestClient) -> None:
    cid, view = _new(client)
    opening = view["opening"]
    assert opening is not None and opening["seed"] == 7
    assert [r["weapon_class"] for r in opening["racks"]] == ["melee", "ranged", "focus"]
    assert all(len(r["skills"]) == 2 for r in opening["racks"])
    assert [d["label_zh"] for d in opening["dummies"]] == [
        "會動的木樁",
        "站在水上的木樁",
        "普通的木樁",
    ]
    assert opening["intro"] and opening["done"]
    assert view["map"]["region"] == "capital"
    store = _store(client)
    char = store.character(cid)
    assert char.opening is not None and char.hero.skills == () and char.generated_skills == ()
    assert char.hero.race == "human" and char.hero.name_zh == "小靶"


def test_create_with_only_weapon_rejected(client: TestClient) -> None:
    reply = client.post("/api/world/characters", json={**NEW, "weapon": "dagger"})
    assert reply.status_code == 422


def test_pending_blocks_other_actions(client: TestClient) -> None:
    cid, _ = _new(client)
    url = f"/api/world/characters/{cid}/actions"
    refused = client.post(url, json={"kind": "teleport", "region": "cloud_ridge"})
    assert refused.status_code == 422 and "確定出發" in refused.text
    # 只記畫面紀錄的動作照樣能做（開場「站起來」）
    _ok(client.post(url, json={"kind": "hint_seen", "ids": ["opening"]}))


def test_confirm_gives_starters_same_as_direct(client: TestClient) -> None:
    cid, _ = _new(client)
    url = f"/api/world/characters/{cid}/actions"
    done = _ok(client.post(url, json={"kind": "opening_confirm", **PICK}))
    assert done["opening"] is None
    assert any("正式選定：" in line for line in done["events"])
    direct = _ok(client.post("/api/world/characters", json={**NEW, **PICK}), 201)
    store = _store(client)
    mine = store.character(cid)
    other = store.character(direct["character"]["character_id"])
    assert mine.opening is None and other.opening is None
    assert mine.hero == other.hero
    assert mine.generated_skills == other.generated_skills
    assert (mine.hp, mine.mana) == (other.hp, other.mana)
    assert len(mine.hero.skills) == len(PICK["keywords"])
    # 出發之後就能傳送（第一次免費，#125）
    moved = _ok(client.post(url, json={"kind": "teleport", "region": "cloud_ridge"}))
    assert moved["map"]["region"] == "cloud_ridge"


def test_confirm_cannot_repeat(client: TestClient) -> None:
    cid, _ = _new(client)
    url = f"/api/world/characters/{cid}/actions"
    _ok(client.post(url, json={"kind": "opening_confirm", **PICK}))
    bow = {"kind": "opening_confirm", "weapon": "bow", "keywords": ["ignite", "charged"]}
    again = client.post(url, json=bow)
    assert again.status_code == 422 and "不能重選" in again.text
    trial = client.post(f"/api/world/characters/{cid}/range/trial", json={"weapon": "bow"})
    assert trial.status_code == 422


def test_confirm_rejects_bad_choice(client: TestClient) -> None:
    cid, _ = _new(client)
    url = f"/api/world/characters/{cid}/actions"
    one = {"kind": "opening_confirm", "weapon": "dagger", "keywords": ["frozen"]}
    bad = client.post(url, json=one)
    assert bad.status_code == 422
    still = _store(client).character(cid)
    assert still.opening is not None


def test_trial_is_sandbox(client: TestClient) -> None:
    cid, _ = _new(client)
    store = _store(client)
    before = store.character(cid)
    lines = _log_lines(client)
    out = _ok(client.post(f"/api/world/characters/{cid}/range/trial", json={"weapon": "dagger"}))
    assert out["demo"] is True and len(out["skills_zh"]) == 2
    assert "單手劍" not in out["title_zh"] and "匕首" in out["title_zh"]
    battle = out["battle"]
    units = battle["view"]["units"]
    assert sum(1 for u in units if u["team"] == "enemy") == 3
    # 打一下（結束回合，木樁回合跑完）：還是不碰角色與日誌
    bid = battle["battle_id"]
    end = {"type": "end_turn", "unit_id": battle["hero_id"]}
    _ok(client.post(f"/api/battles/{bid}/actions", json=end))
    after = store.character(cid)
    assert after == before
    assert _log_lines(client) == lines
    view = _ok(client.get(f"/api/world/characters/{cid}"))
    assert view["battle_id"] is None and view["opening"] is not None


@pytest.mark.parametrize(
    ("weapon", "names"),
    [
        ("dagger", ["瞬步背刺", "狂野之刃"]),
        ("bow", ["淬毒箭", "燧石飛刃"]),
        ("fire_staff", ["火焰箭", "火花連鎖"]),
    ],
)
def test_trial_offers_the_148_demos(client: TestClient, weapon: str, names: list[str]) -> None:
    cid, view = _new(client)
    out = _ok(client.post(f"/api/world/characters/{cid}/range/trial", json={"weapon": weapon}))
    assert out["demo"] is True and out["skills_zh"] == names
    shown = {
        r["weapon_class"]: [s["name_zh"] for s in r["skills"]] for r in view["opening"]["racks"]
    }
    assert names in shown.values()


def test_oil_flint_demo_card_mentions_the_barrel(client: TestClient) -> None:
    """#148：燧石飛刃的示範卡片多一句油桶的說明（資料在 ``range.demo_notes``，技能本體不改）。"""
    _cid, view = _new(client)
    notes = {r["weapon_class"]: r["notes_zh"] for r in view["opening"]["racks"]}
    assert notes == {
        "melee": {},
        "ranged": {"skill_oil_spark_throw": "靶場的油桶打破會流出油"},
        "focus": {},
    }


def test_trial_keyword_demo_and_seed(client: TestClient) -> None:
    cid, _ = _new(client)
    url = f"/api/world/characters/{cid}/range/trial"
    one = _ok(client.post(url, json={"weapon": "dagger", "keywords": ["frozen"]}))
    assert one["demo"] is False and len(one["skills_zh"]) == 1
    again = _ok(client.post(url, json={"weapon": "dagger", "keywords": ["frozen"]}))
    assert one["skills_zh"] == again["skills_zh"]
    assert one["battle"]["view"] == again["battle"]["view"]
    assert trial_seed(7, "dagger", ["frozen"]) == trial_seed(7, "dagger", ("frozen",))
    assert trial_seed(7, "dagger", ["frozen"]) != trial_seed(8, "dagger", ["frozen"])
    bad = client.post(url, json={"weapon": "dagger", "keywords": ["frozen", "frozen"]})
    assert bad.status_code == 422


def test_old_char_without_opening_is_done(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json={**NEW, **PICK}), 201)
    assert view["opening"] is None
