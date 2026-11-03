"""真實 Discord adapter 不連線的部分（Phase 5E-2b；``docs/phases/Phase5計畫.md`` 32.4、32.5）。

不需要網路與 token：只測 intents、指令註冊表、事件轉換，以及 :class:`DiscordPyGateway` 對假
client 的行為（事件迴圈在背景執行緒跑，跟真的 Bot 一樣從工作執行緒呼叫）。
"""

from __future__ import annotations

import asyncio
import re
import secrets
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import discord
import pytest
from discord import app_commands

from trpg.api.accounts import AccountStore
from trpg.bot.commands import (
    SLASH_COMMANDS,
    command_event,
    member_remove_event,
    member_update_event,
)
from trpg.bot.config import BotSettings
from trpg.bot.discord_adapter import (
    DiscordPyGateway,
    GatewayError,
    TrpgBotClient,
    build_intents,
    register_commands,
)
from trpg.bot.gateway import CommandEvent
from trpg.bot.service import DM_SENT, BotService

GUILD = 1000
ROLE = 2000
USER = 3000
CHANNEL = 4000


def _http_error(cls: type[discord.HTTPException], status: int) -> discord.HTTPException:
    return cls(SimpleNamespace(status=status, reason="stub"), "stub")


# -- intents 與指令 ---------------------------------------------------------------


def test_intents_only_what_is_needed() -> None:
    intents = build_intents()
    assert intents.guilds and intents.members
    assert not intents.message_content and not intents.presences
    assert not intents.messages and not intents.voice_states


def test_command_registry() -> None:
    assert [spec.name for spec in SLASH_COMMANDS] == ["register", "reset_password"]
    assert [spec.command for spec in SLASH_COMMANDS] == ["register", "reset_password"]
    for spec in SLASH_COMMANDS:
        assert re.fullmatch(r"[a-z_]{1,32}", spec.name)
        assert 1 <= len(spec.description_zh) <= 100
        for option in spec.options:
            assert 1 <= len(option.description_zh) <= 100


async def _noop_handler(*_args: object) -> None:
    return None


def test_commands_registered_only_in_guild() -> None:
    client = discord.Client(intents=build_intents())
    tree: app_commands.CommandTree[discord.Client] = app_commands.CommandTree(client)
    guild = discord.Object(id=GUILD)
    register_commands(tree, guild, _noop_handler)
    commands = {c.name: c for c in tree.get_commands(guild=guild)}
    assert sorted(commands) == ["register", "reset_password"]
    assert tree.get_commands() == []  # 沒有全域指令
    register = commands["register"]
    assert isinstance(register, app_commands.Command)
    params = register.parameters
    assert [(p.name, p.required, p.type) for p in params] == [
        ("username", False, discord.AppCommandOptionType.string)
    ]
    assert params[0].description == SLASH_COMMANDS[0].options[0].description_zh
    reset = commands["reset_password"]
    assert isinstance(reset, app_commands.Command)
    assert reset.parameters == []


def test_bot_client_builds_without_connecting() -> None:
    settings = BotSettings(
        token=secrets.token_urlsafe(24),  # type: ignore[arg-type]
        guild_id=str(GUILD),
        role_id=str(ROLE),
        announce_channel_id=str(CHANNEL),
    )

    def no_service(_gateway: object) -> BotService:
        raise AssertionError("不連線就不該建服務")

    client = TrpgBotClient(settings, no_service, None, lambda: 0)
    try:
        names = sorted(c.name for c in client.tree.get_commands(guild=client.guild_ref))
        assert names == ["register", "reset_password"]
        assert client.intents.members and not client.intents.message_content
        assert settings.token.get_secret_value() not in repr(client.settings)
    finally:
        client._executor.shutdown(wait=False)


# -- 事件轉換 ---------------------------------------------------------------------


def test_command_event_conversion() -> None:
    event = command_event(
        guild_id=GUILD,
        user_id=USER,
        user_name="alice",
        command="register",
        username="  ",
        interaction_id=99,
    )
    assert event == CommandEvent(str(GUILD), str(USER), "alice", "register", None, "99")
    dm = command_event(guild_id=None, user_id=USER, user_name="a", command="reset_password")
    assert dm.guild_id == "" and dm.interaction_id is None
    named = command_event(
        guild_id=GUILD, user_id=USER, user_name="a", command="register", username=" bob "
    )
    assert named.username == "bob"


def test_member_events_drop_everyone_role() -> None:
    roles = [SimpleNamespace(id=GUILD), SimpleNamespace(id=ROLE)]
    event = member_update_event(GUILD, USER, roles, [SimpleNamespace(id=GUILD)])
    assert event.before_roles == frozenset({str(ROLE)})
    assert event.after_roles == frozenset()
    assert event.guild_id == str(GUILD) and event.user_id == str(USER)
    assert member_remove_event(GUILD, USER) == member_remove_event(GUILD, USER)
    assert member_remove_event(GUILD, USER).user_id == str(USER)


# -- Gateway 對假 client -----------------------------------------------------------


@dataclass
class StubChannel(discord.abc.Messageable):
    sent: list[tuple[str, Any]] = field(default_factory=list)

    async def send(self, content: str, **kwargs: Any) -> None:  # type: ignore[override]
        self.sent.append((content, kwargs.get("allowed_mentions")))


@dataclass
class StubClient:
    members: dict[int, list[int]] = field(default_factory=dict)
    """使用者 ID → 身分組 ID（含 @everyone）。"""
    dm_closed: set[int] = field(default_factory=set)
    offline: bool = False
    dms: list[tuple[int, str]] = field(default_factory=list)
    channels: dict[int, StubChannel] = field(default_factory=dict)
    fetches: int = 0

    def get_guild(self, guild_id: int) -> Any:
        client = self

        class Guild:
            async def fetch_member(self, user_id: int) -> Any:
                client.fetches += 1
                if client.offline:
                    raise _http_error(discord.DiscordServerError, 503)
                if user_id not in client.members:
                    raise _http_error(discord.NotFound, 404)
                return SimpleNamespace(
                    roles=[SimpleNamespace(id=r) for r in client.members[user_id]]
                )

        return Guild()

    async def fetch_user(self, user_id: int) -> Any:
        client = self

        class User:
            async def send(self, text: str, **_kwargs: Any) -> None:
                if user_id in client.dm_closed:
                    raise _http_error(discord.Forbidden, 403)
                client.dms.append((user_id, text))

        return User()

    def get_channel(self, channel_id: int) -> Any:
        return self.channels.get(channel_id)

    async def fetch_channel(self, channel_id: int) -> Any:
        raise _http_error(discord.NotFound, 404)


@pytest.fixture
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(5)
    loop.close()


@pytest.fixture
def client() -> StubClient:
    return StubClient(members={USER: [GUILD, ROLE]})


@pytest.fixture
def gateway(client: StubClient, loop: asyncio.AbstractEventLoop) -> DiscordPyGateway:
    return DiscordPyGateway(cast(discord.Client, client), loop, timeout=5)


def test_member_roles_refetched_every_time(client: StubClient, gateway: DiscordPyGateway) -> None:
    assert gateway.member_roles(str(GUILD), str(USER)) == frozenset({str(ROLE)})
    client.members[USER] = [GUILD]
    assert gateway.member_roles(str(GUILD), str(USER)) == frozenset()
    assert gateway.member_roles(str(GUILD), "1") is None  # 不在伺服器
    assert client.fetches == 3


def test_member_roles_network_error_is_not_absence(
    client: StubClient, gateway: DiscordPyGateway
) -> None:
    """斷線時丟 GatewayError，不回 None（不能因為網路問題停用帳號）。"""
    client.offline = True
    with pytest.raises(GatewayError):
        gateway.member_roles(str(GUILD), str(USER))


def test_send_dm(client: StubClient, gateway: DiscordPyGateway) -> None:
    assert gateway.send_dm(str(USER), "hi")
    assert client.dms == [(USER, "hi")]
    client.dm_closed.add(USER)
    assert not gateway.send_dm(str(USER), "again")


def test_reply_finds_tracked_interaction(gateway: DiscordPyGateway) -> None:
    sent: list[tuple[str, bool]] = []

    async def followup_send(text: str, *, ephemeral: bool = False) -> None:
        sent.append((text, ephemeral))

    interaction = SimpleNamespace(followup=SimpleNamespace(send=followup_send))
    event = command_event(
        guild_id=GUILD, user_id=USER, user_name="a", command="register", interaction_id=7
    )
    gateway.track("7", cast(discord.Interaction, interaction))
    gateway.reply(event, "ok")
    assert sent == [("ok", True)]
    gateway.forget("7")
    gateway.reply(event, "gone")  # 找不到就略過，不當掉
    assert sent == [("ok", True)]


def test_send_channel_disables_mentions(client: StubClient, gateway: DiscordPyGateway) -> None:
    channel = StubChannel()
    client.channels[CHANNEL] = channel
    assert gateway.send_channel(str(CHANNEL), "公告")
    text, mentions = channel.sent[0]
    assert text == "公告"
    assert isinstance(mentions, discord.AllowedMentions)
    assert mentions.everyone is False and mentions.users is False and mentions.roles is False
    assert not gateway.send_channel("1", "沒有這個頻道")


def test_bot_service_over_real_gateway(
    tmp_path: Path, client: StubClient, gateway: DiscordPyGateway
) -> None:
    """BotService 經真實 gateway（假 client）領帳號：密碼只在私訊，回覆不含密碼。"""
    replies: list[str] = []

    async def followup_send(text: str, *, ephemeral: bool = False) -> None:
        assert ephemeral
        replies.append(text)

    store = AccountStore(tmp_path / "accounts")
    service = BotService(store, gateway, guild_id=str(GUILD), role_id=str(ROLE))
    event = command_event(
        guild_id=GUILD, user_id=USER, user_name="Alice", command="register", interaction_id=1
    )
    gateway.track(
        "1",
        cast(discord.Interaction, SimpleNamespace(followup=SimpleNamespace(send=followup_send))),
    )
    service.handle_command(event)
    assert replies == [DM_SENT]
    match = re.search(r"密碼：(\S+)", client.dms[0][1])
    assert match is not None
    assert match.group(1) not in replies[0]
    record = store.by_discord(str(USER))
    assert record is not None and record.username == "alice"
