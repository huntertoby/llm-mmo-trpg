"""真實的 Discord adapter（Phase 5E-2b；``docs/phases/Phase5計畫.md`` 32.5）。

**discord.py 只在這個模組匯入**（``tests/test_architecture.py`` 檢查）。

- :class:`DiscordPyGateway` 實作 :class:`~trpg.bot.gateway.DiscordGateway`：方法在工作執行緒被呼叫，
  用 ``asyncio.run_coroutine_threadsafe`` 回到 Bot 的事件迴圈呼叫 Discord API。
- :class:`TrpgBotClient` 把斜線指令與成員事件轉成 :mod:`trpg.bot.commands` 的事件，交給
  :class:`~trpg.bot.service.BotService`；每 60 秒呼叫一次
  :meth:`~trpg.bot.announcer.Announcer.tick`。全部排進 **同一條** 工作執行緒依序處理（代決
  5E2b-4）：帳號存檔不會被兩個事件同時改，事件迴圈也不會被 scrypt 卡住。
- 身分組每次都向 Discord 重查（``fetch_member``，代決 5E2b-3）。查詢失敗（斷線、逾時）會丟
  :class:`GatewayError`，**不當作「不在伺服器」**：不會因為網路問題停用帳號。
- 密碼只出現在私訊；回覆、log 都不帶。log 不寫訊息內容。
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Final, TypeVar

import discord
from discord import app_commands

from trpg.bot.announcer import Announcer
from trpg.bot.commands import (
    command_event,
    command_spec,
    member_remove_event,
    member_update_event,
    role_ids,
)
from trpg.bot.config import BotConfigError, BotSettings
from trpg.bot.gateway import BotCommand, CommandEvent, DiscordGateway
from trpg.bot.service import BotService

__all__ = [
    "ANNOUNCE_INTERVAL_S",
    "CALL_TIMEOUT_S",
    "GENERIC_ERROR",
    "DiscordPyGateway",
    "GatewayError",
    "TrpgBotClient",
    "build_intents",
    "register_commands",
    "run_bot",
]

log = logging.getLogger(__name__)

T = TypeVar("T")

CALL_TIMEOUT_S: Final = 30.0
"""工作執行緒等一次 Discord API 呼叫的上限（秒）。"""
ANNOUNCE_INTERVAL_S: Final = 60.0
GENERIC_ERROR: Final = "Bot 暫時無法處理（可能是連線問題），請稍後再試。"

CommandHandler = Callable[[discord.Interaction, BotCommand, str | None], Coroutine[Any, Any, None]]


class GatewayError(Exception):
    """跟 Discord 溝通失敗（斷線、逾時、沒權限）；呼叫者不要把它當成「沒有身分組」。"""


def build_intents() -> discord.Intents:
    """只開需要的：``guilds``、``members``（特權 intent，要在 Developer Portal 打開）。"""
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    return intents


# -- 指令註冊 -------------------------------------------------------------------


def register_commands(
    tree: app_commands.CommandTree[Any], guild: discord.abc.Snowflake, handler: CommandHandler
) -> None:
    """照 :data:`~trpg.bot.commands.SLASH_COMMANDS` 把指令加到 ``guild``（只註冊在那個伺服器）。"""
    reg = command_spec("register")
    option = reg.options[0]

    @app_commands.command(name=reg.name, description=reg.description_zh)
    @app_commands.describe(username=option.description_zh)
    async def register(interaction: discord.Interaction, username: str | None = None) -> None:
        await handler(interaction, "register", username)

    reset = command_spec("reset_password")

    @app_commands.command(name=reset.name, description=reset.description_zh)
    async def reset_password(interaction: discord.Interaction) -> None:
        await handler(interaction, "reset_password", None)

    tree.add_command(register, guild=guild)
    tree.add_command(reset_password, guild=guild)


# -- Gateway --------------------------------------------------------------------


class DiscordPyGateway:
    """:class:`~trpg.bot.gateway.DiscordGateway` 的真實版本（在工作執行緒呼叫）。"""

    def __init__(
        self,
        client: discord.Client,
        loop: asyncio.AbstractEventLoop,
        *,
        timeout: float = CALL_TIMEOUT_S,
    ) -> None:
        self.client = client
        self.loop = loop
        self.timeout = timeout
        self._interactions: dict[str, discord.Interaction] = {}
        self._lock = threading.Lock()

    def _call(self, coro: Coroutine[Any, Any, T]) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(self.timeout)
        except TimeoutError:
            future.cancel()
            raise

    # 互動（斜線指令）：reply 要找回是哪一次
    def track(self, interaction_id: str, interaction: discord.Interaction) -> None:
        with self._lock:
            self._interactions[interaction_id] = interaction

    def forget(self, interaction_id: str) -> None:
        with self._lock:
            self._interactions.pop(interaction_id, None)

    async def _guild(self, guild_id: int) -> discord.Guild:
        guild = self.client.get_guild(guild_id)
        return guild if guild is not None else await self.client.fetch_guild(guild_id)

    async def _member_roles(self, guild_id: int, user_id: int) -> frozenset[str] | None:
        guild = await self._guild(guild_id)
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            return None
        return role_ids(member.roles, guild_id=guild_id)

    def member_roles(self, guild_id: str, user_id: str) -> frozenset[str] | None:
        try:
            return self._call(self._member_roles(int(guild_id), int(user_id)))
        except (discord.HTTPException, TimeoutError) as exc:
            raise GatewayError(f"查不到成員的身分組：{type(exc).__name__}") from exc

    async def _send_dm(self, user_id: int, text: str) -> None:
        user = await self.client.fetch_user(user_id)
        await user.send(text, allowed_mentions=discord.AllowedMentions.none())

    def send_dm(self, user_id: str, text: str) -> bool:
        try:
            self._call(self._send_dm(int(user_id), text))
        except (discord.HTTPException, TimeoutError) as exc:
            log.warning("私訊送不出去（使用者 %s）：%s", user_id, type(exc).__name__)
            return False
        return True

    def reply(self, event: CommandEvent, text: str) -> None:
        with self._lock:
            interaction = (
                self._interactions.get(event.interaction_id) if event.interaction_id else None
            )
        if interaction is None:
            log.warning("找不到要回覆的互動（使用者 %s）", event.user_id)
            return
        try:
            self._call(interaction.followup.send(text, ephemeral=True))
        except (discord.HTTPException, TimeoutError) as exc:
            log.warning("回覆送不出去（使用者 %s）：%s", event.user_id, type(exc).__name__)

    async def _send_channel(self, channel_id: int, text: str) -> bool:
        channel = self.client.get_channel(channel_id)
        if channel is None:
            channel = await self.client.fetch_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            log.warning("公告頻道 %s 不能貼文字", channel_id)
            return False
        await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
        return True

    def send_channel(self, channel_id: str, text: str) -> bool:
        try:
            return self._call(self._send_channel(int(channel_id), text))
        except (discord.HTTPException, TimeoutError) as exc:
            log.warning("公告貼不出去（頻道 %s）：%s", channel_id, type(exc).__name__)
            return False


# -- Client ---------------------------------------------------------------------

ServiceFactory = Callable[[DiscordGateway], BotService]
AnnouncerFactory = Callable[[DiscordGateway], Announcer]


class TrpgBotClient(discord.Client):
    """Bot 本體：斜線指令、成員事件、公告迴圈。"""

    def __init__(
        self,
        settings: BotSettings,
        make_service: ServiceFactory,
        make_announcer: AnnouncerFactory | None,
        clock: Callable[[], int],
    ) -> None:
        super().__init__(intents=build_intents(), allowed_mentions=discord.AllowedMentions.none())
        self.settings = settings
        self.guild_ref = discord.Object(id=int(settings.guild_id))
        self.tree: app_commands.CommandTree[TrpgBotClient] = app_commands.CommandTree(self)
        register_commands(self.tree, self.guild_ref, self.on_command)
        self._make_service = make_service
        self._make_announcer = make_announcer
        self._clock = clock
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trpg-bot")
        self.gateway: DiscordPyGateway | None = None
        self.service: BotService | None = None
        self.announcer: Announcer | None = None
        self._started = False
        self._announce_task: asyncio.Task[None] | None = None

    async def _work(self, fn: Callable[..., T], *args: object) -> T:
        """排進 Bot 的工作執行緒（依序處理）。"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args))

    async def setup_hook(self) -> None:
        """登入後、連上 gateway 前：建服務、把指令同步到設定的伺服器。"""
        self.gateway = DiscordPyGateway(self, asyncio.get_running_loop())
        self.service = self._make_service(self.gateway)
        if self._make_announcer is not None:
            self.announcer = self._make_announcer(self.gateway)
        try:
            await self.tree.sync(guild=self.guild_ref)
        except discord.Forbidden as exc:
            raise BotConfigError(
                "無法在伺服器註冊斜線指令：邀請 Bot 時要勾 applications.commands，"
                "並確認 guild_id 是 Bot 已加入的伺服器"
            ) from exc

    async def on_ready(self) -> None:
        if self._started:  # 重連時不重做
            return
        self._started = True
        log.info("Bot 已上線：%s", self.user)
        if self.service is not None:
            try:
                disabled = await self._work(self.service.reconcile)
            except Exception:
                log.exception("啟動時重查身分組失敗（沒有停用任何帳號）")
            else:
                if disabled:
                    log.info("啟動時停用沒有身分組的帳號：%s", "、".join(disabled))
        if self.announcer is not None:
            self._announce_task = asyncio.create_task(self._announce_loop())

    async def _announce_loop(self) -> None:
        announcer = self.announcer
        assert announcer is not None
        while not self.is_closed():
            try:
                posted = await self._work(announcer.tick, self._clock())
            except Exception:
                log.exception("公告失敗（下次再試）")
            else:
                if posted:
                    log.info("貼出 %d 則公告", len(posted))
            await asyncio.sleep(ANNOUNCE_INTERVAL_S)

    async def on_command(
        self, interaction: discord.Interaction, command: BotCommand, username: str | None
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        event = command_event(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            user_name=interaction.user.name,
            command=command,
            username=username,
            interaction_id=interaction.id,
        )
        gateway, service = self.gateway, self.service
        if gateway is None or service is None or event.interaction_id is None:
            await interaction.followup.send(GENERIC_ERROR, ephemeral=True)
            return
        gateway.track(event.interaction_id, interaction)
        try:
            await self._work(service.handle_command, event)
        except Exception:
            log.exception("處理指令 %s 失敗（使用者 %s）", command, event.user_id)
            try:
                await interaction.followup.send(GENERIC_ERROR, ephemeral=True)
            except discord.HTTPException:
                log.warning("錯誤訊息也送不出去（使用者 %s）", event.user_id)
        finally:
            gateway.forget(event.interaction_id)

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if self.service is None:
            return
        event = member_update_event(after.guild.id, after.id, before.roles, after.roles)
        try:
            await self._work(self.service.on_member_update, event)
        except Exception:
            log.exception("處理身分組變更失敗（使用者 %s）", event.user_id)

    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent) -> None:
        if self.service is None:
            return
        event = member_remove_event(payload.guild_id, payload.user.id)
        try:
            await self._work(self.service.on_member_remove, event)
        except Exception:
            log.exception("處理成員離開失敗（使用者 %s）", event.user_id)

    async def close(self) -> None:
        if self._announce_task is not None:
            self._announce_task.cancel()
        await super().close()
        self._executor.shutdown(wait=False)


def run_bot(
    settings: BotSettings,
    make_service: ServiceFactory,
    make_announcer: AnnouncerFactory | None,
    clock: Callable[[], int],
) -> None:
    """連上 Discord 並一直跑到被中斷（Ctrl+C）。

    設定問題 → :class:`BotConfigError`（不含 token）。"""
    client = TrpgBotClient(settings, make_service, make_announcer, clock)
    try:
        client.run(settings.token.get_secret_value())
    except discord.LoginFailure:
        raise BotConfigError(
            "Discord 拒絕這個 token：到 Developer Portal → Bot 按 Reset Token，"
            "把新的 token 填進 .env 的 TRPG_DISCORD_TOKEN"
        ) from None
    except discord.PrivilegedIntentsRequired:
        raise BotConfigError(
            "Bot 需要 Server Members Intent：到 Developer Portal → Bot → "
            "Privileged Gateway Intents 打開「SERVER MEMBERS INTENT」"
        ) from None
