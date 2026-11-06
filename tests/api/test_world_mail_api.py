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
from trpg.api.world_field_view import _facility
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary, load_library
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


def _ok_list(reply: Any, status: int = 200) -> list[dict[str, Any]]:
    assert reply.status_code == status, reply.text
    data: list[dict[str, Any]] = reply.json()
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
    assert "自動退回" in panel["footer_zh"]  # 6T-1b：過期的信自動退回
    assert panel["send_note_zh"].startswith("3 天內沒人領，會自動退回給你")
    card = next(b for b in panel["sendable"] if b["gear"])
    assert card["tradable"] and card["origin_zh"] == "最初得自：阿霧（竹林的戰利品）"
    assert card["holder_zh"] == "目前持有：阿霧"

    recipients = _ok_list(client.get(f"/api/world/characters/{alice}/mail/recipients"))
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


def test_refuse_and_expired_auto_return(client: TestClient, library: ContentLibrary) -> None:
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
    # 6T-1b：過期的信自動退回寄件人，和被拒收一樣用「領取」
    assert [m["action"] for m in late["returned"]] == ["claim", "claim"]
    assert [m["status_zh"] for m in late["returned"]] == ["被拒收退回", "過期退回"]
    assert _ok(client.get(f"/api/world/characters/{alice}"))["mail"]["returned"] == 2
    assert _ok(client.get(f"/api/world/characters/{bob}/mail"))["inbox"] == []
    assert client.post(f"/api/world/characters/{alice}/mail/{second}/reclaim").status_code == 404
    done = _ok(client.post(f"/api/world/characters/{alice}/mail/{second}/claim"))
    assert any("過期退回來的信" in line for line in done["events"])
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


def test_postman_and_postbox_on_the_field() -> None:
    """6T-1b：三個城鎮各有郵筒（low_wall 規則、postbox 外觀）與郵差站位；郵差的外觀照人設卡。"""
    library = load_library()  # 正式內容的實地地圖
    rules = library.world_trade
    assert rules is not None
    for postman in rules.mail.postmen:
        field = next(
            f
            for f in library.field_maps.values()
            if f.region == postman.region
            and f.location == postman.card.location
            and not f.is_interior
        )
        posts = [f for f in field.facilities if f.id == "post"]
        stand = [f for f in posts if f.postman]
        boxes = [o for o in field.objects if o.look == "postbox"]
        assert len(stand) == 1 and len(boxes) == 1, field.id
        assert boxes[0].kind == "low_wall"
        assert any(f.at == boxes[0].at for f in posts)  # 走到郵筒旁邊也能開面板
        x, y = stand[0].at
        assert abs(x - boxes[0].at[0]) + abs(y - boxes[0].at[1]) == 1  # 郵差站在郵筒旁
        views = [_facility(library, field.region, f) for f in posts]
        (shown,) = [v for v in views if v.postman is not None]
        assert shown.postman == postman.card.id and shown.name_zh == postman.card.name_zh
        assert shown.figure is not None and shown.figure.portrait == postman.card.portrait
        assert all(v.figure is None for v in views if v.postman is None)  # 郵筒那格沒有人


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
    # 6T-1b：大世界可以換上別大類（換上前前端確認）；換上後那些招暫時不能用，換回就恢復
    assert cards[sword.id]["can_equip"] is True and cards[sword.id]["equip_problem_zh"] is None
    url = f"/api/world/characters/{cid}/actions"
    view = _ok(client.post(url, json={"kind": "equip", "item": sword.id}))["character"]
    assert focus_only.id in view["weapon_blocked"]
    assert view["weapon_blocked_zh"].startswith("主手是近戰武器：")
    assert focus_only.name_zh in view["weapon_blocked_zh"]
    back = _ok(client.post(url, json={"kind": "equip", "item": staff.id}))["character"]
    assert back["weapon_blocked"] == [] and back["weapon_blocked_zh"] is None


def test_tab_lines_6t1c(client: TestClient, library: ContentLibrary) -> None:
    """郵差照分頁換台詞（6T-1c，玩法 PM「郵差內容文字」第 4 節）；沒填的退回打開面板那句。"""
    alice = _ready(client, library, "阿霧")
    tabs = _ok(client.get(f"/api/world/characters/{alice}/mail"))["tab_lines"]
    assert tabs == {
        "send": "「寄給誰？對方進城就能領。金幣抽一成跑腿費，東西不收。」",
        "inbox": "「有你的信。這邊請。」",
        "inbox_empty": "「目前沒有你的信。」",
        "returned": "「沒人來領的，都退回這裡了。」",
    }
    rules = library.world_trade
    assert rules is not None
    huige = rules.mail.postman_of("ashen_waste")
    assert huige is not None and huige.lines.tab_inbox == "「你的。拿去。」"
    # 選填：沒填時退回打開面板那句；空收件匣沒填用「寄東西」那句
    bare = huige.lines.model_copy(
        update={"tab_send": None, "tab_inbox": None, "tab_inbox_empty": None, "tab_returned": None}
    )
    assert bare.tab_lines("「X」") == {
        "send": "「X」",
        "inbox": "「X」",
        "inbox_empty": "「X」",
        "returned": "「X」",
    }
    half = huige.lines.model_copy(update={"tab_inbox_empty": None})
    assert half.tab_lines("「X」")["inbox_empty"] == huige.lines.tab_send


def test_send_stack_count_6t1c(client: TestClient, library: ContentLibrary) -> None:
    """可堆疊的物品寄件時填數量（6T-1c，acfc999f）：quote、send 照個數，上限是背包裡的數量。"""
    store = _store(client)
    alice = _ready(client, library, "阿霧")
    bob = _ready(client, library, "小白")
    url = f"/api/world/characters/{alice}/mail"
    quote = _ok(client.post(f"{url}/quote", json={"to": bob, "items": {ORE: 4}}))
    assert quote["ok"], quote
    over = _ok(client.post(f"{url}/quote", json={"to": bob, "items": {ORE: 6}}))
    assert not over["ok"] and {p["code"] for p in over["problems"]} == {"not_enough"}
    _ok(client.post(f"{url}/send", json={"to": bob, "items": {ORE: 4}}))
    assert store.character(alice).bag.get(ORE, 0) == 1
    letter = _ok(client.get(f"/api/world/characters/{bob}/mail"))["inbox"][0]
    assert [(i["item"], i["count"]) for i in letter["items"]] == [(ORE, 4)]
