"""帳號服務層（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28.3～28.5）。

測試裡的密碼一律用 ``secrets`` 當場產生，不寫死真實密碼。
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

import pytest

from trpg.api.account_config import AccountConfigError, load_account_settings
from trpg.api.accounts import (
    ACCOUNT_FORMAT,
    MAX_SESSIONS,
    AccountDisabledError,
    AccountError,
    AccountLimitError,
    AccountStore,
    AuthError,
    hash_password,
    loads_account,
    verify_password,
)

T0 = 1_800_000_000


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> int:
        return self.now


def _pw() -> str:
    return secrets.token_urlsafe(12)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(tmp_path: Path, clock: Clock) -> AccountStore:
    return AccountStore(tmp_path / "accounts", max_characters=3, session_ttl_s=3600, clock=clock)


def test_hash_is_salted_and_has_no_plaintext() -> None:
    pw = _pw()
    a, b = hash_password(pw), hash_password(pw)
    assert a.salt != b.salt and a.hash != b.hash
    assert pw not in a.model_dump_json()
    assert verify_password(pw, a) and verify_password(pw, b)
    assert not verify_password(pw + "x", a)


def test_create_saves_only_hash(store: AccountStore) -> None:
    pw = _pw()
    record = store.create("Alice_1", pw, discord_id="123")
    assert record.username == "alice_1"
    assert record.account_id.startswith("a") and len(record.account_id) == 9
    text = (store.root / f"{record.account_id}.json").read_text(encoding="utf-8")
    assert pw not in text
    assert json.loads(text)["format"] == ACCOUNT_FORMAT
    # 新的服務讀同一資料夾得到相同帳號
    again = AccountStore(store.root)
    assert again.get(record.account_id) == record
    assert again.find("ALICE_1") == record
    assert again.by_discord("123") == record


@pytest.mark.parametrize("name", ["ab", "x" * 21, "有中文", "a b", "a-b"])
def test_bad_username(store: AccountStore, name: str) -> None:
    with pytest.raises(AccountError):
        store.create(name, _pw())


@pytest.mark.parametrize("length", [7, 129])
def test_bad_password_length(store: AccountStore, length: int) -> None:
    with pytest.raises(AccountError):
        store.create("bob", "p" * length)


def test_unique_username_and_discord(store: AccountStore) -> None:
    store.create("bob", _pw(), discord_id="42")
    with pytest.raises(AccountError):
        store.create("BOB", _pw())
    with pytest.raises(AccountError):
        store.create("carol", _pw(), discord_id="42")


def test_login_and_authenticate(store: AccountStore) -> None:
    pw = _pw()
    record = store.create("bob", pw)
    token, logged = store.login("Bob", pw)
    assert logged.account_id == record.account_id
    assert store.authenticate(token).account_id == record.account_id
    text = (store.root / f"{record.account_id}.json").read_text(encoding="utf-8")
    assert token not in text  # 只存 token 的雜湊
    with pytest.raises(AuthError) as wrong:
        store.login("bob", pw + "x")
    with pytest.raises(AuthError) as missing:
        store.login("nobody", pw)
    assert str(wrong.value) == str(missing.value)  # 不透露帳號是否存在
    assert pw not in str(wrong.value)
    with pytest.raises(AuthError):
        store.authenticate("not-a-token")


def test_session_expires(store: AccountStore, clock: Clock) -> None:
    pw = _pw()
    store.create("bob", pw)
    token, _ = store.login("bob", pw)
    clock.now += 3600
    with pytest.raises(AuthError):
        store.authenticate(token)
    assert store.find("bob") is not None
    assert store.find("bob").sessions == ()  # type: ignore[union-attr]


def test_logout(store: AccountStore) -> None:
    pw = _pw()
    store.create("bob", pw)
    token, _ = store.login("bob", pw)
    other, _ = store.login("bob", pw)
    store.logout(token)
    with pytest.raises(AuthError):
        store.authenticate(token)
    assert store.authenticate(other).username == "bob"


def test_session_cap(store: AccountStore) -> None:
    pw = _pw()
    store.create("bob", pw)
    tokens = [store.login("bob", pw)[0] for _ in range(MAX_SESSIONS + 1)]
    with pytest.raises(AuthError):
        store.authenticate(tokens[0])
    for token in tokens[1:]:
        store.authenticate(token)


def test_disable_blocks_login_and_drops_sessions(store: AccountStore) -> None:
    pw = _pw()
    record = store.create("bob", pw)
    token, _ = store.login("bob", pw)
    store.set_disabled(record.account_id, True)
    with pytest.raises(AuthError):
        store.authenticate(token)
    with pytest.raises(AccountDisabledError):
        store.login("bob", pw)
    store.set_disabled(record.account_id, False)
    store.authenticate(store.login("bob", pw)[0])


def test_reset_password_drops_sessions(store: AccountStore) -> None:
    old, new = _pw(), _pw()
    record = store.create("bob", old)
    token, _ = store.login("bob", old)
    store.reset_password(record.account_id, new)
    with pytest.raises(AuthError):
        store.authenticate(token)
    with pytest.raises(AuthError):
        store.login("bob", old)
    store.login("bob", new)


def test_character_limit_and_no_transfer(store: AccountStore) -> None:
    a = store.create("alice", _pw())
    b = store.create("bob", _pw())
    for i in range(3):
        store.attach_character(a.account_id, f"c0000000{i}")
    assert not store.can_add_character(a.account_id)
    with pytest.raises(AccountLimitError):
        store.attach_character(a.account_id, "c00000009")
    with pytest.raises(AccountLimitError):  # 角色不轉移（#100）
        store.attach_character(b.account_id, "c00000000")
    assert store.owner_of("c00000001") == a.account_id
    assert store.owner_of("c00000009") is None
    assert store.get(a.account_id).characters == ("c00000000", "c00000001", "c00000002")


def test_unknown_format_is_rejected(store: AccountStore) -> None:
    record = store.create("bob", _pw())
    raw = json.loads(record.model_dump_json())
    raw["format"] = "trpg-account/99"
    with pytest.raises(AccountError):
        loads_account(json.dumps(raw))


def test_settings_file_and_env(tmp_path: Path) -> None:
    path = tmp_path / "server.toml"
    path.write_text(
        '[accounts]\ndev_mode = false\nmax_characters = 2\nsession_ttl_hours = 1\ndir = "x"\n',
        encoding="utf-8",
    )
    settings = load_account_settings(path, env={})
    assert (settings.dev_mode, settings.max_characters, settings.session_ttl_s) == (False, 2, 3600)
    assert settings.accounts_dir(tmp_path) == Path("x")
    env = {"TRPG_DEV_MODE": "true", "TRPG_ACCOUNTS_DIR": str(tmp_path / "acc")}
    over = load_account_settings(path, env=env)
    assert over.dev_mode is True
    assert over.accounts_dir(tmp_path) == tmp_path / "acc"
    with pytest.raises(AccountConfigError):
        load_account_settings(path, env={"TRPG_DEV_MODE": "maybe"})
    with pytest.raises(AccountConfigError):
        load_account_settings(tmp_path / "missing.toml", env={})


def test_default_settings_keep_dev_mode() -> None:
    settings = load_account_settings(env={})
    assert settings.dev_mode is True
    assert settings.max_characters == 3
    assert settings.accounts_dir(Path("saves")) == Path("saves") / "accounts"
