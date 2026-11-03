"""斜線指令註冊表與事件轉換（Phase 5E-2b；``docs/phases/Phase5計畫.md`` 32.4）。

這個模組 **不匯入 discord.py**：指令的名稱、說明、選項是資料，事件轉換是純函式（ID 一律轉字串），
真實 adapter（:mod:`trpg.bot.discord_adapter`）照這裡註冊與轉換，測試不需要網路。

- 指令名稱用英文（代決 5E2b-1），說明用繁中；只註冊在設定的伺服器（代決 5E2b-2）。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Protocol

from trpg.bot.gateway import BotCommand, CommandEvent, MemberRemoveEvent, MemberUpdateEvent

__all__ = [
    "SLASH_COMMANDS",
    "CommandOption",
    "HasRoleId",
    "SlashCommandSpec",
    "command_event",
    "command_spec",
    "member_remove_event",
    "member_update_event",
    "role_ids",
]


@dataclass(frozen=True)
class CommandOption:
    """斜線指令的一個文字選項。"""

    name: str
    description_zh: str
    required: bool = False


@dataclass(frozen=True)
class SlashCommandSpec:
    name: str
    """Discord 上的指令名稱（``/`` 後面那段）。"""
    command: BotCommand
    description_zh: str
    options: tuple[CommandOption, ...] = ()


SLASH_COMMANDS: Final = (
    SlashCommandSpec(
        name="register",
        command="register",
        description_zh="領大世界帳號（密碼用私訊傳給你）",
        options=(
            CommandOption(
                name="username",
                description_zh="帳號名稱（3～20 字的英文字母、數字或底線；不填就用 Discord 名稱）",
            ),
        ),
    ),
    SlashCommandSpec(
        name="reset_password",
        command="reset_password",
        description_zh="重設大世界密碼（新密碼用私訊傳給你）",
    ),
)
"""Bot 註冊的全部斜線指令（依這個順序）。"""


def command_spec(command: BotCommand) -> SlashCommandSpec:
    for spec in SLASH_COMMANDS:
        if spec.command == command:
            return spec
    raise KeyError(command)  # pragma: no cover - BotCommand 只有上面兩種


class HasRoleId(Protocol):
    """discord.py 的 ``Role``（只用到 ``id``）。"""

    @property
    def id(self) -> int: ...


def role_ids(roles: Iterable[HasRoleId], *, guild_id: int | str | None = None) -> frozenset[str]:
    """身分組 → ID 字串；去掉 ``@everyone``（它的 ID 等於伺服器 ID）。"""
    everyone = str(guild_id) if guild_id is not None else None
    return frozenset(str(role.id) for role in roles if str(role.id) != everyone)


def command_event(
    *,
    guild_id: int | None,
    user_id: int,
    user_name: str,
    command: BotCommand,
    username: str | None = None,
    interaction_id: int | None = None,
) -> CommandEvent:
    """斜線指令 → :class:`CommandEvent`。

    不在伺服器裡（私訊）＝``guild_id=""``；空白的名稱＝沒填。"""
    name = username.strip() if username is not None else ""
    return CommandEvent(
        guild_id="" if guild_id is None else str(guild_id),
        user_id=str(user_id),
        user_name=user_name,
        command=command,
        username=name or None,
        interaction_id=None if interaction_id is None else str(interaction_id),
    )


def member_update_event(
    guild_id: int,
    user_id: int,
    before_roles: Iterable[HasRoleId],
    after_roles: Iterable[HasRoleId],
) -> MemberUpdateEvent:
    return MemberUpdateEvent(
        guild_id=str(guild_id),
        user_id=str(user_id),
        before_roles=role_ids(before_roles, guild_id=guild_id),
        after_roles=role_ids(after_roles, guild_id=guild_id),
    )


def member_remove_event(guild_id: int, user_id: int) -> MemberRemoveEvent:
    return MemberRemoveEvent(guild_id=str(guild_id), user_id=str(user_id))
