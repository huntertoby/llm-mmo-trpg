"""地點留言與足跡（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.7；#105）。

測試裡的密碼一律用 ``secrets`` 當場產生。
"""

from __future__ import annotations

import importlib.util
import io
import secrets
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.account_config import AccountSettings
from trpg.api.accounts import AccountStore
from trpg.api.app import create_app
from trpg.api.first_kills import FirstKill
from trpg.api.notes import (
    FOOTPRINT_MAX,
    LocationNoteStore,
    NoteError,
    clean_note_text,
    footprints,
)
from trpg.api.server_config import ServerSettings
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.world.actions import CampAction, TravelAction
from trpg.world.replay import WorldLogEntry

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _make(library: ContentLibrary, saves: Path, *, dev_mode: bool) -> TestClient:
    app = create_app(
        library,
        save_dir=saves,
        accounts=AccountSettings(dev_mode=dev_mode),
        server=ServerSettings(llm_health_interval_s=0),
    )
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: NOON
    return TestClient(app)


@pytest.fixture
def dev(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(calm, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _create(client: TestClient, name: str = "阿霧", headers: dict[str, str] | None = None) -> str:
    reply = client.post("/api/world/characters", json={**START, "name": name}, headers=headers)
    assert reply.status_code == 201, reply.text
    cid: str = reply.json()["character"]["character_id"]
    return cid


def _note(client: TestClient, cid: str, text: str, headers: dict[str, str] | None = None) -> Any:
    return client.post(f"/api/world/characters/{cid}/notes", json={"text": text}, headers=headers)


def test_clean_note_text_rules() -> None:
    assert clean_note_text("  霧裡有狼  ") == "霧裡有狼"
    assert clean_note_text("字" * 50) == "字" * 50
    for bad in ("", "   ", "字" * 51, "第一行\n第二行", "tab\there"):
        with pytest.raises(NoteError):
            clean_note_text(bad)


def test_post_and_read_notes_at_current_location(dev: TestClient) -> None:
    cid = _create(dev)
    other = _create(dev, "小美")
    reply = _note(dev, cid, "北坡的狼很兇，帶火")
    assert reply.status_code == 200, reply.text
    board = reply.json()
    assert board["max_len"] == 50 and board["location_name_zh"]
    assert [n["text"] for n in board["notes"]] == ["北坡的狼很兇，帶火"]
    assert board["notes"][0]["mine"] is True and board["notes"][0]["name"] == "阿霧"
    seen = dev.get(f"/api/world/characters/{other}/notes").json()  # 同一個小鎮
    assert seen["notes"][0]["mine"] is False
    assert _note(dev, cid, "字" * 51).status_code == 422
    assert _note(dev, cid, "a\nb").status_code == 422


def test_notes_are_per_location_and_newest_first(dev: TestClient) -> None:
    store = _store(dev)
    cid = _create(dev)
    times = iter(range(NOON, NOON + 100))
    store.clock = lambda: next(times)
    for i in range(22):
        _note(dev, cid, f"第 {i} 則")
    board = dev.get(f"/api/world/characters/{cid}/notes").json()
    assert len(board["notes"]) == 20 and board["notes"][0]["text"] == "第 21 則"
    char = store.character(cid)
    elsewhere = LocationNoteStore(store.root).at(char.region, "nowhere")
    assert elsewhere == []


def test_notes_do_not_touch_world_log(dev: TestClient) -> None:
    store = _store(dev)
    cid = _create(dev)
    before = len(store.entries())
    _note(dev, cid, "不進日誌")
    assert len(store.entries()) == before
    log = (store.root / "log.jsonl").read_text(encoding="utf-8") if before else ""
    assert "不進日誌" not in log
    assert (store.root / "notes.json").is_file()


def test_footprints_from_log_and_first_kills(dev: TestClient) -> None:
    store = _store(dev)
    me = _create(dev)
    friend = _create(dev, "小美")
    here = store.character(me)
    store.entries().append(  # 不是 travel，不算足跡
        WorldLogEntry(seq=98, now=NOON + 9, character_id=friend, action=CampAction())
    )
    store.entries().append(
        WorldLogEntry(
            seq=99, now=NOON + 5, character_id=friend, action=TravelAction(to=here.location)
        )
    )
    store.entries().append(
        WorldLogEntry(seq=100, now=NOON + 6, character_id=me, action=TravelAction(to=here.location))
    )
    board = dev.get(f"/api/world/characters/{me}/notes").json()
    assert [f["text_zh"] for f in board["footprints"]] == ["小美 來過這裡"]  # 不含自己


def _kill(cid: str, location: str, at: int) -> FirstKill:
    return FirstKill(
        kind="elite",
        target="wolf",
        target_name_zh="霧狼王",
        character_id=cid,
        name="小美",
        region="r1",
        location=location,
        seq=1,
        at=at,
    )


def test_footprints_function_orders_and_limits() -> None:
    entries = [
        WorldLogEntry(seq=i, now=100 + i, character_id=f"c{i:02d}", action=TravelAction(to="x1"))
        for i in range(15)
    ]
    entries.append(WorldLogEntry(seq=50, now=1, character_id="c00", action=TravelAction(to="x2")))
    kills = [_kill("c99", "x1", 500), _kill("c98", "x2", 600)]
    found = footprints(
        entries,
        {"c99": "小美"},
        kills,
        region="r1",
        location="x1",
        exclude="c03",
        region_of=lambda loc: "r1",
    )
    assert len(found) == FOOTPRINT_MAX
    assert found[0].kind == "first_kill" and found[0].target_name_zh == "霧狼王"
    assert all(f.character_id != "c03" for f in found)
    assert [f.at for f in found] == sorted((f.at for f in found), reverse=True)
    other_region = footprints(
        entries, {}, kills, region="r2", location="x1", exclude="", region_of=lambda loc: "r1"
    )
    assert other_region == []


def _login(client: TestClient, name: str, *, admin: bool = False) -> dict[str, str]:
    accounts = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(accounts, AccountStore)
    pw = secrets.token_urlsafe(12)
    record = accounts.create(name, pw)
    if admin:
        accounts.set_admin(record.account_id, True)
    reply = client.post("/api/auth/login", json={"username": name, "password": pw})
    assert reply.status_code == 200, reply.text
    return {"Authorization": f"Bearer {reply.json()['token']}"}


def test_delete_needs_admin(calm: ContentLibrary, tmp_path: Path) -> None:
    with _make(calm, tmp_path / "saves", dev_mode=False) as client:
        user = _login(client, "player1")
        root = _login(client, "root1", admin=True)
        cid = _create(client, headers=user)
        note_id = _note(client, cid, "刪我", headers=user).json()["notes"][0]["note_id"]
        assert client.delete(f"/api/world/notes/{note_id}").status_code == 401
        denied = client.delete(f"/api/world/notes/{note_id}", headers=user)
        assert denied.status_code == 403 and "刪留言" in denied.json()["detail"]
        assert client.delete(f"/api/world/notes/{note_id}", headers=root).status_code == 204
        assert client.delete(f"/api/world/notes/{note_id}", headers=root).status_code == 404
        assert client.get(f"/api/world/characters/{cid}/notes", headers=user).json()["notes"] == []
        other = _login(client, "player2")
        assert client.get(f"/api/world/characters/{cid}/notes", headers=other).status_code == 404


def test_dev_mode_without_token_can_delete(dev: TestClient) -> None:
    cid = _create(dev)
    note_id = _note(dev, cid, "開發模式").json()["notes"][0]["note_id"]
    assert dev.delete(f"/api/world/notes/{note_id}").status_code == 204


def _script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "location_notes.py"
    spec = importlib.util.spec_from_file_location("location_notes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["location_notes"] = module
    spec.loader.exec_module(module)
    return module


def test_script_list_and_delete(dev: TestClient) -> None:
    store = _store(dev)
    cid = _create(dev)
    note_id = _note(dev, cid, "腳本看得到").json()["notes"][0]["note_id"]
    script = _script()
    world = str(store.root)
    out = io.StringIO()
    assert script.main(["--world-dir", world, "list"], out) == 0
    assert note_id in out.getvalue() and "腳本看得到" in out.getvalue()
    out = io.StringIO()
    assert script.main(["--world-dir", world, "delete", note_id], out) == 0
    err = io.StringIO()
    assert script.main(["--world-dir", world, "delete", note_id], io.StringIO(), err) == 2
    assert "找不到" in err.getvalue()
    board = dev.get(f"/api/world/characters/{cid}/notes").json()  # 伺服器重讀檔案
    assert board["notes"] == []
