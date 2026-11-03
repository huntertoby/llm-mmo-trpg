"""測試用的假 Discord（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.4）。不連網。"""

from __future__ import annotations

from dataclasses import dataclass, field

from trpg.bot.gateway import CommandEvent

__all__ = ["FakeDiscordGateway", "SentMessage"]


@dataclass(frozen=True)
class SentMessage:
    user_id: str
    text: str


@dataclass
class FakeDiscordGateway:
    """記憶體裡的伺服器成員與身分組；記錄每則私訊與回覆。"""

    members: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)
    """``(guild_id, user_id)`` → 身分組 ID。"""
    dm_closed: set[str] = field(default_factory=set)
    """關閉私訊的使用者 ID。"""
    dms: list[SentMessage] = field(default_factory=list)
    replies: list[SentMessage] = field(default_factory=list)

    def join(self, guild_id: str, user_id: str, *roles: str) -> None:
        self.members[(guild_id, user_id)] = frozenset(roles)

    def set_roles(self, guild_id: str, user_id: str, *roles: str) -> None:
        self.members[(guild_id, user_id)] = frozenset(roles)

    def leave(self, guild_id: str, user_id: str) -> None:
        self.members.pop((guild_id, user_id), None)

    def member_roles(self, guild_id: str, user_id: str) -> frozenset[str] | None:
        return self.members.get((guild_id, user_id))

    def send_dm(self, user_id: str, text: str) -> bool:
        if user_id in self.dm_closed:
            return False
        self.dms.append(SentMessage(user_id, text))
        return True

    def reply(self, event: CommandEvent, text: str) -> None:
        self.replies.append(SentMessage(event.user_id, text))

    def dms_to(self, user_id: str) -> list[str]:
        return [m.text for m in self.dms if m.user_id == user_id]

    def last_reply(self) -> str:
        return self.replies[-1].text
