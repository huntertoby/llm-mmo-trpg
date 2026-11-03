"""Bot 行為（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.5）。只用假 Discord，不連網。

測試裡的密碼一律由 ``secrets`` 產生（Bot 預設的產生器）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from trpg.api.accounts import AccountDisabledError, AccountStore, AuthError
from trpg.bot.fake import FakeDiscordGateway
from trpg.bot.gateway import CommandEvent, MemberRemoveEvent, MemberUpdateEvent
from trpg.bot.service import (
    ALREADY,
    DM_SENT,
    NEED_ROLE,
    NO_ACCOUNT,
    WRONG_GUILD,
    BotService,
    derive_username,
)

GUILD = "1000"
ROLE = "2000"
OTHER_ROLE = "2001"
PASSWORD_RE = re.compile(r"密碼：(\S+)")


@pytest.fixture
def store(tmp_path: Path) -> AccountStore:
    return AccountStore(tmp_path / "accounts")


@pytest.fixture
def gateway() -> FakeDiscordGateway:
    return FakeDiscordGateway()


@pytest.fixture
def bot(store: AccountStore, gateway: FakeDiscordGateway) -> BotService:
    return BotService(store, gateway, guild_id=GUILD, role_id=ROLE)


def _register(user: str, name: str = "Alice.Wu", username: str | None = None) -> CommandEvent:
    return CommandEvent(GUILD, user, name, "register", username)


def _reset(user: str) -> CommandEvent:
    return CommandEvent(GUILD, user, "x", "reset_password")


def _password(gateway: FakeDiscordGateway, user: str) -> str:
    match = PASSWORD_RE.search(gateway.dms_to(user)[-1])
    assert match is not None
    return match.group(1)


def test_needs_role(bot: BotService, gateway: FakeDiscordGateway, store: AccountStore) -> None:
    gateway.join(GUILD, "u1", OTHER_ROLE)
    bot.handle_command(_register("u1"))
    assert gateway.last_reply() == NEED_ROLE
    bot.handle_command(_register("u9"))  # 不在伺服器
    assert gateway.last_reply() == NEED_ROLE
    assert store.all() == [] and gateway.dms == []


def test_wrong_guild(bot: BotService, gateway: FakeDiscordGateway, store: AccountStore) -> None:
    gateway.join("9999", "u1", ROLE)
    bot.handle_command(CommandEvent("9999", "u1", "alice", "register"))
    assert gateway.last_reply() == WRONG_GUILD
    assert store.all() == []


def test_register_sends_password_only_by_dm(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    gateway.join(GUILD, "u1", ROLE)
    bot.handle_command(_register("u1"))
    record = store.by_discord("u1")
    assert record is not None and record.username == "alice_wu"
    assert gateway.last_reply() == DM_SENT
    assert len(gateway.dms_to("u1")) == 1
    password = _password(gateway, "u1")
    assert all(password not in r.text for r in gateway.replies)  # 回覆不帶密碼
    saved = (store.root / f"{record.account_id}.json").read_text(encoding="utf-8")
    assert password not in saved  # 只存雜湊
    token, _ = store.login("alice_wu", password)
    assert store.authenticate(token).discord_id == "u1"


def test_one_account_per_discord_user(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    gateway.join(GUILD, "u1", ROLE)
    bot.handle_command(_register("u1"))
    bot.handle_command(_register("u1", username="second"))
    assert gateway.last_reply() == ALREADY.format(name="alice_wu")
    assert len(store.all()) == 1
    assert len(gateway.dms_to("u1")) == 1  # 沒有再發密碼


def test_requested_and_derived_usernames(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    for user in ("u1", "u2", "u3", "u4"):
        gateway.join(GUILD, user, ROLE)
    bot.handle_command(_register("u1", username="Hero_1"))
    assert store.by_discord("u1").username == "hero_1"  # type: ignore[union-attr]
    bot.handle_command(_register("u2", username="hero_1"))
    assert "已經有人用了" in gateway.last_reply() and store.by_discord("u2") is None
    bot.handle_command(_register("u2", username="壞名字"))
    assert "3～20 字" in gateway.last_reply() and store.by_discord("u2") is None
    bot.handle_command(_register("u3", name="hero_1"))  # 由 Discord 名稱轉，撞名加尾碼
    derived = store.by_discord("u3").username  # type: ignore[union-attr]
    assert re.fullmatch(r"hero_1_[0-9a-f]{4}", derived)
    bot.handle_command(_register("u4", name="小明"))
    assert store.by_discord("u4").username == "player"  # type: ignore[union-attr]


def test_derive_username_rules() -> None:
    def free(_: str) -> bool:
        return False

    assert derive_username("Some.Long-Name With Spaces", free) == "some_long_name_with_"
    assert derive_username("ab", free) == "player_ab"
    assert derive_username("!!", free) == "player"
    taken = {"x" * 20}
    name = derive_username("x" * 30, lambda n: n in taken, lambda: "beef")
    assert name == "x" * 15 + "_beef" and len(name) == 20


def test_dm_closed_on_register(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    gateway.join(GUILD, "u1", ROLE)
    gateway.dm_closed.add("u1")
    bot.handle_command(_register("u1"))
    assert store.by_discord("u1") is not None
    assert "私訊送不出去" in gateway.last_reply() and "重設密碼" in gateway.last_reply()
    assert gateway.dms == []
    gateway.dm_closed.clear()
    bot.handle_command(_reset("u1"))
    store.login("alice_wu", _password(gateway, "u1"))


def test_reset_password(bot: BotService, gateway: FakeDiscordGateway, store: AccountStore) -> None:
    gateway.join(GUILD, "u1", ROLE)
    bot.handle_command(_reset("u1"))
    assert gateway.last_reply() == NO_ACCOUNT
    bot.handle_command(_register("u1"))
    old = _password(gateway, "u1")
    token, _ = store.login("alice_wu", old)
    bot.handle_command(_reset("u1"))
    new = _password(gateway, "u1")
    assert new != old and gateway.last_reply() == DM_SENT
    with pytest.raises(AuthError):
        store.authenticate(token)  # 重設清掉 session
    with pytest.raises(AuthError):
        store.login("alice_wu", old)
    store.login("alice_wu", new)
    gateway.dm_closed.add("u1")
    bot.handle_command(_reset("u1"))
    assert "私訊送不出去" in gateway.last_reply()
    with pytest.raises(AuthError):
        store.login("alice_wu", new)  # 舊密碼已失效


def test_role_removed_disables_and_readd_does_not_restore(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    gateway.join(GUILD, "u1", ROLE, OTHER_ROLE)
    bot.handle_command(_register("u1"))
    password = _password(gateway, "u1")
    token, _ = store.login("alice_wu", password)
    # 別的身分組變動不影響
    bot.on_member_update(
        MemberUpdateEvent(GUILD, "u1", frozenset({ROLE, OTHER_ROLE}), frozenset({ROLE}))
    )
    assert store.by_discord("u1").disabled is False  # type: ignore[union-attr]
    gateway.set_roles(GUILD, "u1")
    bot.on_member_update(MemberUpdateEvent(GUILD, "u1", frozenset({ROLE}), frozenset()))
    assert store.by_discord("u1").disabled is True  # type: ignore[union-attr]
    with pytest.raises(AuthError):
        store.authenticate(token)
    with pytest.raises(AccountDisabledError):
        store.login("alice_wu", password)
    # 加回身分組：不自動恢復，也不能用重設密碼或再領一個繞過
    gateway.set_roles(GUILD, "u1", ROLE)
    bot.on_member_update(MemberUpdateEvent(GUILD, "u1", frozenset(), frozenset({ROLE})))
    assert store.by_discord("u1").disabled is True  # type: ignore[union-attr]
    bot.handle_command(_reset("u1"))
    assert "已停用" in gateway.last_reply()
    bot.handle_command(_register("u1"))
    assert "已停用" in gateway.last_reply() and len(store.all()) == 1
    assert len(gateway.dms_to("u1")) == 1


def test_member_remove_and_other_guild(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    gateway.join(GUILD, "u1", ROLE)
    bot.handle_command(_register("u1"))
    bot.on_member_remove(MemberRemoveEvent("9999", "u1"))
    bot.on_member_update(MemberUpdateEvent("9999", "u1", frozenset({ROLE}), frozenset()))
    assert store.by_discord("u1").disabled is False  # type: ignore[union-attr]
    bot.on_member_remove(MemberRemoveEvent(GUILD, "u1"))
    assert store.by_discord("u1").disabled is True  # type: ignore[union-attr]
    bot.on_member_remove(MemberRemoveEvent(GUILD, "nobody"))  # 沒帳號：不出錯


def test_reconcile_disables_offline_changes(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    for user, name in (("u1", "alice"), ("u2", "bob"), ("u3", "carol")):
        gateway.join(GUILD, user, ROLE)
        bot.handle_command(_register(user, name=name))
    store.create("devonly", "x" * 12)  # 沒綁 Discord 的帳號不動
    gateway.set_roles(GUILD, "u1", OTHER_ROLE)
    gateway.leave(GUILD, "u3")
    assert bot.reconcile() == ["alice", "carol"]
    assert store.find("bob").disabled is False  # type: ignore[union-attr]
    assert store.find("devonly").disabled is False  # type: ignore[union-attr]
    assert bot.reconcile() == []


def test_server_store_sees_bot_accounts(
    bot: BotService, gateway: FakeDiscordGateway, store: AccountStore
) -> None:
    """Bot 與伺服器是兩個程序：伺服器那邊的 :class:`AccountStore` 立刻看得到（計畫 29.6）。"""
    server = AccountStore(store.root)
    assert server.all() == []
    gateway.join(GUILD, "u1", ROLE)
    bot.handle_command(_register("u1"))
    token, _ = server.login("alice_wu", _password(gateway, "u1"))
    gateway.set_roles(GUILD, "u1")
    bot.on_member_update(MemberUpdateEvent(GUILD, "u1", frozenset({ROLE}), frozenset()))
    with pytest.raises(AuthError):
        server.authenticate(token)
