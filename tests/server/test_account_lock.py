"""帳號檔的跨程序寫入與按賽季的角色上限（Phase 5D-R2）。

兩個 :class:`AccountStore` 開同一個資料夾＝Bot 與遊戲伺服器兩個程序。
"""

from __future__ import annotations

import json
import secrets
import threading
from pathlib import Path

import pytest

import trpg.server.accounts as accounts_module
from trpg.server.accounts import (
    LOCK_FILE,
    AccountDisabledError,
    AccountLimitError,
    AccountRecord,
    AccountStore,
    PasswordHash,
)
from trpg.server.file_lock import FileLock

T0 = 1_800_000_000


def _pw() -> str:
    return secrets.token_urlsafe(12)


def _pair(tmp_path: Path) -> tuple[AccountStore, AccountStore]:
    root = tmp_path / "accounts"
    return AccountStore(root, clock=lambda: T0), AccountStore(root, clock=lambda: T0)


def test_disable_during_login_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """伺服器比對密碼時 Bot 停用帳號：伺服器發 session 前重讀帳號檔，停用不會被蓋回去。"""
    server, bot = _pair(tmp_path)
    pw = _pw()
    account = server.create("alice", pw)
    real = accounts_module.verify_password

    def verify_then_bot_disables(password: str, stored: PasswordHash) -> bool:
        ok = real(password, stored)
        bot.set_disabled(account.account_id, True)
        return ok

    monkeypatch.setattr(accounts_module, "verify_password", verify_then_bot_disables)
    with pytest.raises(AccountDisabledError):
        server.login("alice", pw)
    on_disk = AccountStore(server.root).get(account.account_id)
    assert on_disk.disabled and on_disk.sessions == ()


def test_stale_cache_merges_instead_of_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """快取沒察覺另一個程序的寫入（例如修改時間相同）時，寫入前仍重讀那個帳號檔再合併。"""
    server, bot = _pair(tmp_path)
    account = server.create("alice", _pw())
    server.get(account.account_id)  # 快取住
    monkeypatch.setattr(server, "_current_signature", lambda: server._signature)
    bot.set_disabled(account.account_id, True)
    assert not server.get(account.account_id).disabled  # 快取確實是舊的
    updated = server.set_admin(account.account_id, True)
    assert updated.admin and updated.disabled
    on_disk = AccountStore(server.root).get(account.account_id)
    assert on_disk.admin and on_disk.disabled


def test_interleaved_writers_keep_each_change(tmp_path: Path) -> None:
    """兩個寫入者交錯：伺服器登入、Bot 停用、伺服器登出舊 token；最後仍是停用且沒有 session。"""
    server, bot = _pair(tmp_path)
    pw = _pw()
    account = server.create("alice", pw)
    token, _ = server.login("alice", pw)
    bot.set_disabled(account.account_id, True)
    server.logout(token)
    bot.set_admin(account.account_id, True)
    on_disk = AccountStore(server.root).get(account.account_id)
    assert on_disk.disabled and on_disk.admin and on_disk.sessions == ()


def test_writer_waits_for_the_lock_file(tmp_path: Path) -> None:
    """另一個程序持有鎖檔時寫入會等；放開後才寫。"""
    server, bot = _pair(tmp_path)
    account = server.create("alice", _pw())
    done = threading.Event()
    errors: list[BaseException] = []

    def disable() -> None:
        try:
            bot.set_disabled(account.account_id, True)
        except BaseException as exc:  # pragma: no cover - 失敗時讓斷言看得到
            errors.append(exc)
        finally:
            done.set()

    holder = FileLock(server.root / LOCK_FILE)
    holder.acquire()
    try:
        worker = threading.Thread(target=disable)
        worker.start()
        assert not done.wait(0.3)
        assert not AccountStore(server.root, clock=lambda: T0)._reread(account.account_id).disabled
    finally:
        holder.release()
    worker.join(10)
    assert done.is_set() and not errors
    assert AccountStore(server.root).get(account.account_id).disabled


def test_character_limit_counts_only_this_season(tmp_path: Path) -> None:
    """角色上限按賽季算：季末清掉的角色不佔上限；歸屬紀錄保留（不轉移照舊）。"""
    season = ["s1"]
    store = AccountStore(tmp_path / "accounts", max_characters=2, season=lambda: season[0])
    account = store.create("alice", _pw())
    store.attach_character(account.account_id, "c1")
    store.attach_character(account.account_id, "c2")
    with pytest.raises(AccountLimitError, match="上限"):
        store.check_character_room(account.account_id)
    season[0] = "s2"
    store.check_character_room(account.account_id)
    record = store.attach_character(account.account_id, "c3")
    assert record.characters == ("c1", "c2", "c3")
    assert record.character_seasons == {"c1": "s1", "c2": "s1", "c3": "s2"}
    assert store.season_characters(record) == ("c3",)
    other = store.create("bob", _pw())
    with pytest.raises(AccountLimitError, match="不能轉移"):
        store.attach_character(other.account_id, "c1")


def test_old_account_characters_are_first_season(tmp_path: Path) -> None:
    """舊帳號檔沒有 character_seasons：角色都算第一季。"""
    store = AccountStore(tmp_path / "accounts", max_characters=1, season=lambda: "s1")
    account = store.create("alice", _pw())
    path = store.root / f"{account.account_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["characters"] = ["c1"]
    raw.pop("character_seasons", None)
    path.write_text(json.dumps(raw), encoding="utf-8")
    record = AccountRecord.model_validate(raw)
    assert record.season_of("c1") == "s1"
    with pytest.raises(AccountLimitError):
        AccountStore(store.root, max_characters=1).check_character_room(account.account_id)
    later = AccountStore(store.root, max_characters=1, season=lambda: "s2")
    later.check_character_room(account.account_id)
