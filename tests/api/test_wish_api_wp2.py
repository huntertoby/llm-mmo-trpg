"""許願池的 API、面板資料與等待提示（Phase WP-2；``docs/phases/PhaseWP計畫.md`` 第 4 節）。

全部用 Mock（:class:`~trpg.api.llm_source.MockLlmProvider`）或假的生成函式，不連網路：

- ``POST …/actions`` 收 ``wish``（文字與選單）、都不拿退款；
- ``WorldView.wish``：費用、退款、本週剩幾次、能不能許與原因（和送出被拒的字相同）、LLM 開關、選單；
- ``POST …/pregen/wait`` 的 ``kind: "wish"``；
- **許願在單一佇列插隊**（開發 PM 裁定）：排在所有還沒開始的預測前面，不打斷正在跑的那一筆。
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_offer_prefetch import _at_altar
from tests.api.test_world_api import FixedClock, _ok
from tests.api.test_world_pregen import Recorder, _town_char
from tests.world.helpers import hero, make_world
from trpg.api.app import create_app
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world import WorldStore
from trpg.api.world_pregen import Generators, WorldPregen
from trpg.content.library import ContentLibrary
from trpg.world.generated import WishGen, WishGenRequest
from trpg.world.save import dumps_world, write_atomic
from trpg.world.state import CharacterState
from trpg.world.step import new_character
from trpg.world.wish import WISH_NO_MATCH_ZH, wish_request

WISH = "讓敵人燃燒起來"
"""Mock 對到 ``ignite``，Mock 提議器做得出帶點燃的完整技能（同 ``test_wish_pregen``）。"""
CID = "alice"
"""Mock 提議器的成敗跟技能種子（角色 ID、賽季種子）有關；同 test_wish_pregen 用 alice。"""


# ---------------------------------------------------------------------------
# 佇列插隊
# ---------------------------------------------------------------------------


class _Gated(Recorder):
    """第一筆開始時通知（``started``），之後等 ``gate`` 才回；許願也記下鍵。"""

    def __init__(self, gate: threading.Event) -> None:
        super().__init__(gate)
        self.started = threading.Event()

    def _enter(self, key: str) -> None:
        self.started.set()
        super()._enter(key)

    def wish(self, _library: ContentLibrary, request: WishGenRequest) -> WishGen:
        self._enter(request.key)
        self._leave()
        return WishGen(key=request.key)

    def generators(self) -> Generators:
        return Generators(flash=self.flash, story=self.story, offer=self.offer, wish=self.wish)


def _wish_req(library: ContentLibrary, character_id: str, text: str) -> WishGenRequest:
    char = new_character(library, character_id, hero(library), region="cloud_ridge")
    return wish_request(library, make_world(), char, text)


def test_wish_jumps_the_queue(library: ContentLibrary) -> None:
    """正在跑的那一筆做完，接著先做許願（許願之間照先後），最後才是排在前面的預測。"""
    gate = threading.Event()
    rec = _Gated(gate)
    # wait_seconds=0：等待提示把許願排進佇列後立刻回 timeout，許願留在佇列裡
    pregen = WorldPregen(rec.generators(), enabled=lambda: True, wait_seconds=0.0)
    world = make_world()
    try:
        pregen.prefetch(library, world, _town_char(library))  # 閃現（第一筆會卡在 gate）
        assert rec.started.wait(timeout=30)
        pregen.prefetch(library, world, _at_altar(library, "bob"))  # 機遇
        queued = pregen.pending("alice") + pregen.pending("bob") - 1
        assert queued >= 1  # 至少一筆預測在排隊（沒開始）
        first = _wish_req(library, "carol", "第一個願望")
        second = _wish_req(library, "dave", "第二個願望")
        assert pregen.wait("carol", "wish", first, library=library).status == "timeout"
        assert pregen.wait("dave", "wish", second, library=library).status == "timeout"
        gate.set()
        pregen.drain(timeout=60)
        assert len(rec.calls) == queued + 3
        assert rec.calls[1:3] == [first.key, second.key]  # 不打斷第一筆，許願緊接在後
        assert first.key not in rec.calls[3:] and rec.max_active == 1
    finally:
        gate.set()
        pregen.shutdown()


def test_cancelled_wish_is_skipped(library: ContentLibrary) -> None:
    """排隊中的許願被丟掉（例如伺服器忘了這個角色）：背景執行緒略過它，其餘照做。"""
    gate = threading.Event()
    rec = _Gated(gate)
    pregen = WorldPregen(rec.generators(), enabled=lambda: True, wait_seconds=0.0)
    try:
        pregen.prefetch(library, make_world(), _town_char(library))
        assert rec.started.wait(timeout=30)
        dropped = _wish_req(library, "carol", "丟掉的願望")
        kept = _wish_req(library, "dave", "留著的願望")
        pregen.wait("carol", "wish", dropped, library=library)
        pregen.wait("dave", "wish", kept, library=library)
        pregen.forget("carol")
        gate.set()
        pregen.drain(timeout=60)
        assert dropped.key not in rec.calls and rec.calls[1] == kept.key
    finally:
        gate.set()
        pregen.shutdown()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def _client(library: ContentLibrary, saves: Path) -> TestClient:
    app = create_app(library, save_dir=saves, llm=MockLlmProvider())
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = FixedClock()
    world = make_world()  # 同 test_wish_pregen 的種子：Mock 提議器做得出點燃的完整技能
    write_atomic(saves / "world" / "world.json", dumps_world(world))
    return TestClient(app)


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _put(client: TestClient, **updates: Any) -> CharacterState:
    store = _store(client)
    char = new_character(store.library, CID, hero(store.library), region="cloud_ridge")
    char = char.model_copy(
        update={"region": "capital", "location": "capital", "quest_coins": 10, **updates}
    )
    store._save_char(char)
    return char


@pytest.fixture
def client(content_library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(content_library, tmp_path / "saves") as c:
        _ok(c.post("/api/world/llm", json={"enabled": True}))  # Mock：探測一定成功
        _put(c)
        yield c


def _view(client: TestClient) -> dict[str, Any]:
    return _ok(client.get(f"/api/world/characters/{CID}"))


def _act(client: TestClient, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{CID}/actions", json=action)


def test_wish_view_in_capital(client: TestClient, content_library: ContentLibrary) -> None:
    wish = _view(client)["wish"]
    assert wish is not None
    assert (wish["cost"], wish["refund"], wish["left"], wish["per_week"]) == (4, 2, 2, 2)
    assert (wish["coins"], wish["available"], wish["blocked_zh"]) == (10, True, None)
    assert wish["text_max_chars"] == 60 and wish["max_keywords"] == 2
    assert wish["title_zh"] == "許願池" and wish["speaker"]["name_zh"] == "守池人"
    assert wish["line_zh"]
    ids = [m["id"] for m in wish["menu"]]
    assert "ignite" in ids and "frozen" in ids
    hidden = {k.id for k in content_library.keywords.keywords if k.start_hidden}
    assert not hidden & set(ids)
    assert all(m["name_zh"] and m["description_zh"] for m in wish["menu"])
    assert wish["llm"] is True  # Mock 供應者：預先生成裝上、LLM 開著


def test_wish_view_only_in_capital(client: TestClient) -> None:
    _put(client, region="cloud_ridge", location="mist_ferry")
    assert _view(client)["wish"] is None


def test_wish_view_llm_off(client: TestClient) -> None:
    _ok(client.post("/api/world/llm", json={"enabled": False}))
    assert _view(client)["wish"]["llm"] is False


def test_menu_wish_skip_refund_and_counts(client: TestClient) -> None:
    after = _ok(_act(client, kind="wish", keywords=["ignite", "frozen"]))
    pending = after["pending_offer"]
    assert pending["quest_name_zh"] == "許願池"
    assert (pending["source"], pending["refund"]) == ("wish", 2)
    assert len(pending["offer"]["candidates"]) == 3
    assert after["wish"]["left"] == 1 and after["wish"]["coins"] == 6
    assert after["wish"]["available"] is False  # 三選一還沒選
    assert after["wish"]["blocked_zh"] == "還有任務給的技能三選一沒有選：先選一招，或都不拿"
    skipped = _ok(_act(client, kind="offer_pick"))
    assert skipped["pending_offer"] is None
    assert (skipped["wish"]["coins"], skipped["wish"]["left"]) == (8, 1)  # 退 2、次數照扣
    assert skipped["wish"]["available"] is True


def test_refusal_matches_view(client: TestClient) -> None:
    """畫面說不能許時，送出被拒的字＝``blocked_zh``，任務幣與次數不變。"""
    _put(client, quest_coins=3)
    wish = _view(client)["wish"]
    assert wish["available"] is False
    refused = _act(client, kind="wish", keywords=["ignite"])
    assert refused.status_code == 422 and wish["blocked_zh"] in refused.text
    assert _store(client).character(CID).quest_coins == 3


def test_week_limit_in_view(client: TestClient) -> None:
    for _ in range(2):
        _ok(_act(client, kind="wish", keywords=["ignite"]))
        _ok(_act(client, kind="offer_pick"))  # 都不拿（次數照扣）
    wish = _view(client)["wish"]
    assert (wish["left"], wish["available"]) == (0, False)
    assert wish["blocked_zh"] == "這週已經許了 2 次願，下週再來"


def test_text_wish_wait_then_act(client: TestClient) -> None:
    """等待提示先排（插隊）、做好；接著送出文字許願直接拿那一筆（Mock：點燃、至少一張 LLM 卡）。"""
    url = f"/api/world/characters/{CID}/pregen/wait"
    out = _ok(client.post(url, json={"kind": "wish", "text": WISH}))
    assert out["status"] == "ready"
    pregen = _store(client).pregen
    assert pregen is not None
    calls = pregen.calls
    after = _ok(_act(client, kind="wish", text=WISH))
    assert pregen.calls == calls  # 送出時用等待排好的那一筆，沒有再呼叫
    offer = after["pending_offer"]
    assert offer["source"] == "wish"
    assert any(t["source"] == "llm" for t in offer["offer"]["tags"])
    assert after["wish"]["coins"] == 6


def test_wait_none_cases(client: TestClient) -> None:
    url = f"/api/world/characters/{CID}/pregen/wait"
    # 選單許願不呼叫 LLM、空白願望、超過字數
    assert _ok(client.post(url, json={"kind": "wish", "keywords": ["ignite"]}))["status"] == "none"
    assert _ok(client.post(url, json={"kind": "wish", "text": "  "}))["status"] == "none"
    assert _ok(client.post(url, json={"kind": "wish", "text": "火" * 61}))["status"] == "none"
    _put(client, quest_coins=0)  # 現在不能許：不白打 LLM
    assert _ok(client.post(url, json={"kind": "wish", "text": WISH}))["status"] == "none"
    pregen = _store(client).pregen
    assert pregen is not None and pregen.calls == 0


def test_text_wish_without_match_is_refused(client: TestClient) -> None:
    refused = _act(client, kind="wish", text="隨便")
    assert refused.status_code == 422 and WISH_NO_MATCH_ZH in refused.text
    assert _store(client).character(CID).quest_coins == 10


def test_wish_action_needs_exactly_one_way(client: TestClient) -> None:
    both = _act(client, kind="wish", text=WISH, keywords=["ignite"])
    assert both.status_code == 422
