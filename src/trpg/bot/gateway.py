"""Bot 與 Discord 之間的介面（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.4）。

:class:`DiscordGateway` 是同步介面：真實 adapter（:mod:`trpg.bot.discord_adapter`，5E-2b）在自己的
事件迴圈裡把事件轉成這裡的資料類別，再用工作執行緒呼叫 :class:`~trpg.bot.service.BotService`（scrypt
是 CPU 工作）。測試用 :class:`~trpg.bot.fake.FakeDiscordGateway`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

__all__ = [
    "BotCommand",
    "CommandEvent",
    "DiscordGateway",
    "MemberRemoveEvent",
    "MemberUpdateEvent",
]

BotCommand = Literal["register", "reset_password"]
"""``register``＝領帳號；``reset_password``＝重設密碼。"""


@dataclass(frozen=True)
class CommandEvent:
    """成員下的 Bot 指令（真實 adapter 對應 slash 指令）。"""

    guild_id: str
    user_id: str
    user_name: str
    """Discord 使用者名稱（領帳號沒指定名稱時拿來轉成帳號名稱）。"""
    command: BotCommand
    username: str | None = None
    """``register`` 指定的帳號名稱（選填）。"""
    interaction_id: str | None = None
    """真實 adapter 用來找回要回覆的那次互動（5E-2b）；假介面與測試不用。"""


@dataclass(frozen=True)
class MemberUpdateEvent:
    """成員資料變動（身分組增減）。"""

    guild_id: str
    user_id: str
    before_roles: frozenset[str]
    after_roles: frozenset[str]


@dataclass(frozen=True)
class MemberRemoveEvent:
    """成員離開或被踢出伺服器。"""

    guild_id: str
    user_id: str


class DiscordGateway(Protocol):
    """Bot 對 Discord 的全部需求。"""

    def member_roles(self, guild_id: str, user_id: str) -> frozenset[str] | None:
        """成員目前的身分組 ID；不在伺服器＝``None``。每次指令都重查，不信任事件附帶的資料。"""
        ...

    def send_dm(self, user_id: str, text: str) -> bool:
        """私訊；對方關閉私訊或送不出去 → ``False``。"""
        ...

    def reply(self, event: CommandEvent, text: str) -> None:
        """只有指令發送者看得到的回覆（ephemeral）。**絕不含密碼**。"""
        ...

    def send_channel(self, channel_id: str, text: str) -> bool:
        """貼到頻道（公告，5E-3）；送不出去（沒權限、斷線）→ ``False``，呼叫者下次重試。"""
        ...
