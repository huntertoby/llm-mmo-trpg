"""``/api/world/characters/{id}/mail``（Phase 6T-1a 郵寄，08 8.16）：面板、收件人、寄件前檢查、
寄、領、拒收、取回過期、日誌的兩角色紀錄、「✉」、裝備卡的交易資料、稽核報表。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client
from tests.world.helpers import NOON
from trpg.api.world import WorldStore
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.replay import replay
from trpg.world.state import GearOrigin

DAY = 86_400
ORE = "item_coarse_material"


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(library, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _ready(client: TestClient, library: ContentLibrary, name: str, **extra: Any) -> str:
    """建一個角色，直接改成 3 級、在主城（白鷺那裡）、有金幣與材料。"""
    view = _ok(client.post("/api/world/characters", json={**START, "name": name}), 201)
    cid: str = view["character"]["character_id"]
    store = _store(client)
    char = store.character(cid)
    update: dict[str, Any] = {
        "level": 3,
        "gold": 100,
        "bag": {ORE: 5},
        "region": "capital",
        "location": "capital",
    }
    update.update(extra)
    store._save_char(char.model_copy(update=update))
    return cid


def test_mail_flow(client: TestClient, library: ContentLibrary) -> None:
    store = _store(client)
    body = generate_item(library, Rng(7), "body", "rare", 3)
    origin = GearOrigin(owner="x", owner_name="阿霧", source="drop", source_zh="竹林的戰利品", at=0)
    alice = _ready(client, library, "阿霧", gear=(body,))
    char = store.character(alice)
    store._save_char(char.model_copy(update={"gear_origin": {body.id: origin}}))
    bob = _ready(client, library, "小白")

    panel = _ok(client.get(f"/api/world/characters/{alice}/mail"))
    assert panel["postman"]["name_zh"] == "白鷺" and panel["here"] and panel["level_ok"]
    assert panel["line_zh"].startswith("「寄給誰？") and panel["mailbox_max"] == 20
    assert panel["footer_zh"].startswith("信只能在城鎮的郵差這裡領；3 天")
    card = next(b for b in panel["sendable"] if b["gear"])
    assert card["tradable"] and card["origin_zh"] == "最初得自：阿霧（竹林的戰利品）"
    assert card["holder_zh"] == "目前持有：阿霧"

    recipients = _ok(client.get(f"/api/world/characters/{alice}/mail/recipients"))
    assert [r["character_id"] for r in recipients] == [bob]  # 開發模式：每個角色算各自的帳號

    send = {"to": bob, "items": {ORE: 2}, "gear": [body.id], "gold": 55, "note": "加油"}
    quote = _ok(client.post(f"/api/world/characters/{alice}/mail/quote", json=send))
    assert quote["ok"] and quote["tax"] == 6 and quote["received"] == 49
    assert quote["tax_zh"] == "跑腿費 10%：−6　對方實收 49"
    sent = _ok(client.post(f"/api/world/characters/{alice}/mail/send", json=send))
    assert (
        sent["line_zh"] == "「送到了。」" and sent["mail"]["outgoing"][0]["status_zh"] == "寄出中"
    )
    assert store.character(alice).gold == 45

    entry = store.entries()[-1]
    assert entry.character_id == alice and entry.counterpart == bob

    world = _ok(client.get(f"/api/world/characters/{bob}"))
    assert world["mail"]["bubble"] == "✉" and world["mail"]["unread"] == 1
    inbox = _ok(client.get(f"/api/world/characters/{bob}/mail"))
    assert inbox["line_zh"] == "「有你的信。這邊請。」"
    (letter,) = inbox["inbox"]
    assert letter["gold"] == 49 and letter["days_left"] == 3 and letter["can_act"]
    assert letter["gear"][0]["origin_zh"] == "最初得自：阿霧（竹林的戰利品）"
    got = _ok(client.post(f"/api/world/characters/{bob}/mail/{letter['id']}/claim"))
    assert got["mail"]["inbox"] == [] and got["events"][0].startswith("領了阿霧的信")
    claimed = store.character(bob)
    assert claimed.gold == 100 + 49 and claimed.bag == {ORE: 7} and claimed.gear[0].id == body.id
    assert claimed.gear_origin[body.id].owner == "x"


def test_quote_problems_and_lines(client: TestClient, library: ContentLibrary) -> None:
    alice = _ready(client, library, "阿霧", level=2)
    bob = _ready(client, library, "小白")
    quote = _ok(
        client.post(f"/api/world/characters/{alice}/mail/quote", json={"to": bob, "gold": 10})
    )
    assert not quote["ok"] and quote["line_zh"] == "「等你站穩了再來。」"
    assert {p["code"] for p in quote["problems"]} == {"low_level"}
    reply = client.post(f"/api/world/characters/{alice}/mail/send", json={"to": bob, "gold": 10})
    assert reply.status_code == 422
    missing = client.post(
        f"/api/world/characters/{bob}/mail/quote", json={"to": "cnobody00", "gold": 10}
    )
    assert {p["code"] for p in _ok(missing)["problems"]} == {"no_recipient"}
    assert client.post(f"/api/world/characters/{bob}/mail/oops/claim").status_code == 422


def test_refuse_and_reclaim(client: TestClient, library: ContentLibrary) -> None:
    store = _store(client)
    alice = _ready(client, library, "阿霧")
    bob = _ready(client, library, "小白")
    for _ in range(2):
        _ok(client.post(f"/api/world/characters/{alice}/mail/send", json={"to": bob, "gold": 20}))
    first, second = (m["id"] for m in _ok(client.get(f"/api/world/characters/{bob}/mail"))["inbox"])
    _ok(client.post(f"/api/world/characters/{bob}/mail/{first}/refuse"))
    back = _ok(client.get(f"/api/world/characters/{alice}/mail"))
    assert [m["status_zh"] for m in back["returned"]] == ["被拒收退回"]
    store.clock.now = NOON + 3 * DAY  # type: ignore[attr-defined]
    late = _ok(client.get(f"/api/world/characters/{alice}/mail"))
    assert [m["action"] for m in late["returned"]] == ["claim", "reclaim"]
    assert _ok(client.get(f"/api/world/characters/{alice}"))["mail"]["returned"] == 2
    assert _ok(client.get(f"/api/world/characters/{bob}/mail"))["inbox"] == []
    done = _ok(client.post(f"/api/world/characters/{alice}/mail/{second}/reclaim"))
    assert done["line_zh"] == "「沒人來領，退回來了。」"
    _ok(client.post(f"/api/world/characters/{alice}/mail/{first}/claim"))
    assert store.character(alice).gold == 100 - 40 + 18 + 18  # 稅不退
    assert store.character(bob).mailbox == ()
    audit = _ok(client.get("/api/world/trades/audit"))
    assert audit["trades"] == 2 and audit["flags"] == []
    statuses = [t.status for t in store.world().trades]
    assert statuses == ["refused", "reclaimed"]


def test_log_replays_pair_entries(client: TestClient, library: ContentLibrary) -> None:
    store = _store(client)
    alice = _ready(client, library, "阿霧")
    bob = _ready(client, library, "小白")
    start_world = store.world()
    start = {cid: store.character(cid) for cid in (alice, bob)}
    _ok(client.post(f"/api/world/characters/{alice}/mail/send", json={"to": bob, "gold": 30}))
    (letter,) = _ok(client.get(f"/api/world/characters/{bob}/mail"))["inbox"]
    _ok(client.post(f"/api/world/characters/{bob}/mail/{letter['id']}/refuse"))
    done = replay(store.library, start_world, start, store.entries())
    assert done.characters[alice] == store.character(alice)
    assert done.characters[bob] == store.character(bob)
    assert done.world.trades == store.world().trades


def test_cross_class_card(client: TestClient, library: ContentLibrary) -> None:
    """#135：別大類的主手卡片寫「別大類：可交易・可分解・可賣」與換上後不能用的招。"""
    store = _store(client)
    sword = generate_item(library, Rng(3), "weapon", "rare", 3, weapon_class="melee")
    staff = generate_item(library, Rng(4), "weapon", "rare", 3, weapon_class="focus")
    cid = _ready(client, library, "阿霧", gear=(sword, staff))
    char = store.character(cid)
    origins = {g.id: char.gear_origin.get(g.id) for g in (sword, staff)}
    assert all(o is None for o in origins.values())  # 直接擺進去的：沒有紀錄＝當作綁定
    focus_only = next(s for s in library.skills.values() if s.weapon_req == "focus")
    hero = char.hero.model_copy(update={"skills": (*char.hero.skills, focus_only.id)})
    store._save_char(char.model_copy(update={"hero": hero}))
    bag = _ok(client.get(f"/api/world/characters/{cid}"))["inventory"]["bag"]
    cards = {b["item"]: b for b in bag if b["gear"]}
    assert cards[sword.id]["cross_class_zh"] == "別大類：可交易・可分解・可賣"
    assert focus_only.name_zh in cards[sword.id]["cross_class_lost_zh"]
    assert cards[sword.id]["cross_class_lost_zh"].startswith("換上後不能用：")
    assert cards[staff.id]["cross_class_zh"] is None
    assert cards[sword.id]["bound_zh"] == "穿過" and not cards[sword.id]["tradable"]
