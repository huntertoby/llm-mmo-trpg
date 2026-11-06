"""6C-R3：世界日誌的規則鍵與只 append、足跡索引、留言快取、``prepare_battle`` 快取。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api import world as world_module
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.world import save as save_module
from trpg.world.layout import LOG_FILE
from trpg.world.save import (
    content_digest,
    dumps_log,
    dumps_log_header,
    log_rules_key,
    read_log,
)

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def calm(field_library: ContentLibrary) -> ContentLibrary:
    return with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})


@pytest.fixture
def client(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(calm, save_dir=tmp_path / "saves")
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as c:
        yield c


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient, name: str = "阿霧") -> str:
    view = _ok(client.post("/api/world/characters", json={**START, "name": name}), 201)
    return str(view["character"]["character_id"])


def _walk(client: TestClient, cid: str, *cells: tuple[int, int]) -> dict[str, Any]:
    body = {"kind": "walk", "path": [list(c) for c in cells]}
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=body))


def _log_path(client: TestClient) -> Path:
    return _store(client).root / LOG_FILE


# -- 規則鍵 -------------------------------------------------------------------


def test_content_digest_is_deterministic(
    calm: ContentLibrary, field_library: ContentLibrary
) -> None:
    """同樣的內容＝同樣的 digest；換掉大世界規則或一張實地地圖就不同。"""
    assert content_digest(calm) == content_digest(calm)
    assert content_digest(calm) != content_digest(field_library)
    key = log_rules_key(calm)
    battle_format, version, ruleset, digest = key.split("|")
    assert battle_format.startswith("trpg-battle-log/")
    assert version == f"w{save_module.WORLD_RULES_VERSION}"  # 6D-R1
    assert len(ruleset) == 64 and digest == content_digest(calm)[:16]


def test_world_rules_version_bump_marks_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """世界規則程式版號加一（6D-R1，內容沒變）：舊紀錄到最後一筆都標成規則已變、不能重播。"""
    cid = _create(client)
    _walk(client, cid, (12, 9))
    _walk(client, cid, (13, 9))
    before = _store(client).rules_key()
    monkeypatch.setattr(save_module, "WORLD_RULES_VERSION", save_module.WORLD_RULES_VERSION + 1)
    world_module._RULES_KEYS.clear()  # 規則鍵依內容庫快取；版號是程式常數，真實情況要重啟
    store = _store(client)
    store._forget()  # 同伺服器重啟
    assert store.rules_key() != before
    _walk(client, cid, (12, 9))
    log = read_log(_log_path(client).read_text(encoding="utf-8"))
    assert log.stale_through == 2 and log.rules_key == store.rules_key()
    world_module._RULES_KEYS.clear()


def test_header_records_rules_key(client: TestClient) -> None:
    cid = _create(client)
    _walk(client, cid, (12, 9))
    log = read_log(_log_path(client).read_text(encoding="utf-8"))
    assert log.rules_key == _store(client).rules_key()
    assert log.stale_through is None


@pytest.mark.parametrize("header", [{"rules_key": "other|key|0"}, {}])
def test_rules_key_mismatch_marks_stale(client: TestClient, header: dict[str, str]) -> None:
    """標頭的規則鍵和目前的不同（或沒記）＝規則已變：到最後一筆都不能重播，標頭重寫成新的鍵。"""
    cid = _create(client)
    _walk(client, cid, (12, 9))
    _walk(client, cid, (13, 9))
    path = _log_path(client)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(
        "\n".join([json.dumps({"format": "trpg-wlog/7", **header}), *lines[1:]]) + "\n",
        encoding="utf-8",
    )
    store = _store(client)
    store._forget()  # 同伺服器重啟
    _walk(client, cid, (12, 9))
    log = read_log(path.read_text(encoding="utf-8"))
    assert log.stale_through == 2
    assert log.rules_key == store.rules_key()
    assert [e.seq for e in log.entries] == [1, 2, 3]


def test_matching_key_keeps_replayable(client: TestClient) -> None:
    cid = _create(client)
    _walk(client, cid, (12, 9))
    _store(client)._forget()
    _walk(client, cid, (13, 9))
    assert read_log(_log_path(client).read_text(encoding="utf-8")).stale_through is None


# -- 只 append ----------------------------------------------------------------


def test_append_equals_full_rewrite(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """append 寫出的檔和整份重寫（:func:`dumps_log`）逐字相同；標頭沒變時不整份重寫。"""
    cid = _create(client)
    _walk(client, cid, (12, 9))  # 第一筆：沒有檔，整份寫
    rewrites: list[Path] = []
    real = save_module.write_atomic

    def spy(path: Path, text: str) -> None:
        if path.name == LOG_FILE:
            rewrites.append(path)
        real(path, text)

    monkeypatch.setattr(world_module, "write_atomic", spy)
    for cell in ((13, 9), (12, 9), (13, 9)):
        _walk(client, cid, cell)
    assert rewrites == []
    store = _store(client)
    text = _log_path(client).read_text(encoding="utf-8")
    assert text == dumps_log(store.entries(), rules_key=store.rules_key())
    assert text.splitlines()[0] == dumps_log_header(rules_key=store.rules_key())


def test_header_rewritten_once_when_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _create(client)
    _walk(client, cid, (12, 9))
    path = _log_path(client)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(['{"format": "trpg-wlog/6"}', *lines[1:]]) + "\n", encoding="utf-8")
    store = _store(client)
    store._forget()
    rewrites: list[str] = []
    real = save_module.write_atomic

    def spy(target: Path, text: str) -> None:
        if target.name == LOG_FILE:
            rewrites.append(text)
        real(target, text)

    monkeypatch.setattr(world_module, "write_atomic", spy)
    for cell in ((13, 9), (12, 9), (13, 9)):
        _walk(client, cid, cell)
    assert len(rewrites) == 1  # 只有第一次（標頭換成 /7＋規則鍵＋stale）
    text = path.read_text(encoding="utf-8")
    assert text == dumps_log(store.entries(), stale_through=1, rules_key=store.rules_key())


def test_torn_last_line_is_dropped(client: TestClient) -> None:
    """append 寫到一半中斷（最後一行沒有換行）：讀檔時略過那一行，下一次寫入整份重寫。"""
    cid = _create(client)
    _walk(client, cid, (12, 9))
    path = _log_path(client)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"seq": 2, "now"')
    store = _store(client)
    store._forget()
    _walk(client, cid, (13, 9))
    log = read_log(path.read_text(encoding="utf-8"))
    assert [e.seq for e in log.entries] == [1, 2]


def test_read_log_drops_a_torn_last_line() -> None:
    """殘行處理在 ``read_log`` 裡（6D-R1，所有讀者共用）：最後一行沒有換行結尾就略過。"""
    whole = dumps_log([])
    assert not read_log(whole).torn
    torn = read_log(whole + '{"seq": 1, "no')
    assert torn.torn and torn.entries == () and torn.header == whole.strip()
    empty = read_log('{"format": "trpg-w')
    assert empty.torn and empty.entries == () and empty.header == ""


# -- 足跡索引、留言快取 -------------------------------------------------------


def test_visit_index_updates_on_save(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """第一次用到時掃一次角色資料夾；之後別人存檔就更新索引，不再掃資料夾。"""
    alice = _create(client, "甲")
    bob = _create(client, "乙")
    store = _store(client)
    store._forget()  # 同伺服器重啟：索引第一次用到時重建
    assert [v.name_zh for v in store.field_social(alice).visitors_at("cloud_ridge", "mist_ferry")]
    calls: list[str] = []
    real = WorldStore.character_ids

    def counted(self: WorldStore) -> list[str]:
        calls.append("glob")
        return real(self)

    monkeypatch.setattr(WorldStore, "character_ids", counted)
    char = store.character(bob)
    moved = char.model_copy(update={"location": "ferry_steps"})
    store._save_char(moved)
    social = store.field_social(alice)
    assert [v.character_id for v in social.visitors_at("cloud_ridge", "ferry_steps")] == [bob]
    assert calls == []


def test_notes_cache_follows_writes_and_outside_edits(client: TestClient) -> None:
    cid = _create(client)
    store = _store(client)
    assert store.notes.all() == ()
    note = store.notes.add(store.character(cid), "你好", NOON)
    assert store.notes.all() == (note,)
    store.notes.path.write_text(
        json.dumps({"format": "trpg-notes/1", "notes": []}), encoding="utf-8"
    )  # 管理腳本從外面改檔
    assert store.notes.all() == ()


def test_prepared_battle_cached_per_char_object(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _create(client)
    store = _store(client)
    calls: list[str] = []

    def fake(_library: ContentLibrary, char: Any) -> Any:
        calls.append(char.character_id)
        return object()

    monkeypatch.setattr(world_module, "prepare_battle", fake)
    char = store.character(cid)
    first = store.prepared_battle(char)
    assert store.prepared_battle(char) is first
    assert calls == [cid]
    store._save_char(char.model_copy(update={"location": "ferry_steps"}))
    assert store.prepared_battle(store.character(cid)) is not first
    assert calls == [cid, cid]
