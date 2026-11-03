"""Bot 行為：領帳號、重設密碼、身分組被拔時停用（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.5）。

- 有指定身分組才能領；一個 Discord 使用者 ID 只能有一個帳號（``discord_id`` 綁定）。
- 密碼由 Bot 產生，**只在私訊出現一次**；回覆、log、錯誤訊息都不帶。伺服器只存雜湊（5E-1）。
- 身分組被拔、或離開伺服器 → 停用帳號（清 session）。加回 **不自動恢復**（代決 5E2-2）。
- 私訊失敗：帳號照建立／密碼照換，但密碼沒送出（只在記憶體，丟掉＝沒人知道）（代決 5E2-3）。
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from typing import Final

from trpg.bot.config import BotSettings
from trpg.bot.gateway import CommandEvent, DiscordGateway, MemberRemoveEvent, MemberUpdateEvent
from trpg.server.accounts import (
    USERNAME_RE,
    AccountError,
    AccountRecord,
    AccountStore,
    normalize_username,
)

__all__ = ["BotService", "derive_username"]

PASSWORD_BYTES: Final = 12
USERNAME_MIN: Final = 3
USERNAME_MAX: Final = 20
SUFFIX_LEN: Final = 5
"""撞名時加的 ``_`` ＋ 4 個十六進位字元。"""
_MAX_TRIES: Final = 50

WRONG_GUILD: Final = "請在指定的 Discord 伺服器使用這個指令。"
NEED_ROLE: Final = "需要指定的身分組才能使用（領帳號、重設密碼）。"
DM_SENT: Final = "已用私訊傳給你，請查看私訊。密碼只會顯示這一次。"
DM_FAILED_REGISTER: Final = (
    "帳號 {name} 已建立，但私訊送不出去（可能關閉了私訊），密碼沒有送出。"
    "請開啟「允許伺服器成員私訊」後使用「重設密碼」。"
)
DM_FAILED_RESET: Final = (
    "私訊送不出去（可能關閉了私訊），新密碼沒有送出，舊密碼已失效。"
    "請開啟「允許伺服器成員私訊」後再重設一次。"
)
ALREADY: Final = "你已經有帳號了：{name}。忘了密碼請用「重設密碼」。"
ALREADY_DISABLED: Final = "你的帳號 {name} 已停用（身分組曾被移除或由管理者停用），請找管理者恢復。"
NO_ACCOUNT: Final = "你還沒有帳號，請先「領帳號」。"
DISABLED: Final = "你的帳號 {name} 已停用，不能重設密碼，請找管理者恢復。"


def _new_password() -> str:
    return secrets.token_urlsafe(PASSWORD_BYTES)


def _new_suffix() -> str:
    return secrets.token_hex(2)


def derive_username(
    user_name: str, taken: Callable[[str], bool], suffix: Callable[[], str] = _new_suffix
) -> str:
    """Discord 名稱 → 合法的帳號名稱（代決 5E1-8 的規則）；撞名加 ``_`` ＋ 4 個十六進位字元。"""
    base = re.sub(r"[.\-\s]", "_", user_name.strip().lower())
    base = re.sub(r"[^a-z0-9_]", "", base)[:USERNAME_MAX]
    if len(base) < USERNAME_MIN:
        base = ("player_" + base if base else "player")[:USERNAME_MAX]
    if not taken(base):
        return base
    stem = base[: USERNAME_MAX - SUFFIX_LEN]
    for _ in range(_MAX_TRIES):
        candidate = f"{stem}_{suffix()}"
        if not taken(candidate):
            return candidate
    raise AccountError("找不到可用的帳號名稱，請指定一個")  # pragma: no cover - 機率極低


def _register_dm(name: str, password: str) -> str:
    return (
        "大世界帳號已建立。\n"
        f"帳號：{name}\n"
        f"密碼：{password}\n"
        "密碼只會顯示這一次，請自己記好；忘了可以用「重設密碼」。"
    )


def _reset_dm(name: str, password: str) -> str:
    return (
        f"帳號 {name} 的密碼已重設，之前的登入都已登出。\n"
        f"新密碼：{password}\n"
        "密碼只會顯示這一次，請自己記好。"
    )


class BotService:
    """把 Discord 事件轉成帳號服務層的呼叫。"""

    def __init__(
        self,
        store: AccountStore,
        gateway: DiscordGateway,
        *,
        guild_id: str,
        role_id: str,
        new_password: Callable[[], str] = _new_password,
        new_suffix: Callable[[], str] = _new_suffix,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self.guild_id = guild_id
        self.role_id = role_id
        self._new_password = new_password
        self._new_suffix = new_suffix

    @classmethod
    def from_settings(
        cls, settings: BotSettings, store: AccountStore, gateway: DiscordGateway
    ) -> BotService:
        return cls(store, gateway, guild_id=settings.guild_id, role_id=settings.role_id)

    # -- 查詢 -----------------------------------------------------------------

    def has_role(self, user_id: str) -> bool:
        """向 Discord 重查（不信任事件附帶的身分組）。"""
        roles = self.gateway.member_roles(self.guild_id, user_id)
        return roles is not None and self.role_id in roles

    # -- 指令 -----------------------------------------------------------------

    def handle_command(self, event: CommandEvent) -> None:
        if event.guild_id != self.guild_id:
            self.gateway.reply(event, WRONG_GUILD)
            return
        if not self.has_role(event.user_id):
            self.gateway.reply(event, NEED_ROLE)
            return
        try:
            if event.command == "register":
                self._register(event)
            else:
                self._reset(event)
        except AccountError as exc:  # 名稱不合規則或撞名；訊息不含密碼
            self.gateway.reply(event, str(exc))

    def _pick_username(self, event: CommandEvent) -> str:
        if event.username is not None:
            name = normalize_username(event.username)
            if USERNAME_RE.fullmatch(name) is None:
                raise AccountError("帳號名稱要 3～20 字的英文字母、數字或底線")
            if self.store.find(name) is not None:
                raise AccountError(f"帳號名稱 {name} 已經有人用了，請換一個")
            return name
        return derive_username(
            event.user_name, lambda n: self.store.find(n) is not None, self._new_suffix
        )

    def _register(self, event: CommandEvent) -> None:
        existing = self.store.by_discord(event.user_id)
        if existing is not None:
            template = ALREADY_DISABLED if existing.disabled else ALREADY
            self.gateway.reply(event, template.format(name=existing.username))
            return
        name = self._pick_username(event)
        password = self._new_password()
        record = self.store.create(name, password, discord_id=event.user_id)
        if self.gateway.send_dm(event.user_id, _register_dm(record.username, password)):
            self.gateway.reply(event, DM_SENT)
        else:
            self.gateway.reply(event, DM_FAILED_REGISTER.format(name=record.username))

    def _reset(self, event: CommandEvent) -> None:
        record = self.store.by_discord(event.user_id)
        if record is None:
            self.gateway.reply(event, NO_ACCOUNT)
            return
        if record.disabled:  # 不能用重設密碼繞過停用（代決 5E2-4）
            self.gateway.reply(event, DISABLED.format(name=record.username))
            return
        password = self._new_password()
        self.store.reset_password(record.account_id, password)
        if self.gateway.send_dm(event.user_id, _reset_dm(record.username, password)):
            self.gateway.reply(event, DM_SENT)
        else:
            self.gateway.reply(event, DM_FAILED_RESET)

    # -- 成員變動 ---------------------------------------------------------------

    def _disable_discord_user(self, user_id: str) -> AccountRecord | None:
        record = self.store.by_discord(user_id)
        if record is None or record.disabled:
            return None
        return self.store.set_disabled(record.account_id, True)

    def on_member_update(self, event: MemberUpdateEvent) -> None:
        """指定身分組被拔 → 停用；加回不自動恢復（代決 5E2-2）。"""
        if event.guild_id != self.guild_id:
            return
        if self.role_id in event.before_roles and self.role_id not in event.after_roles:
            self._disable_discord_user(event.user_id)

    def on_member_remove(self, event: MemberRemoveEvent) -> None:
        """離開或被踢出伺服器 → 停用。"""
        if event.guild_id == self.guild_id:
            self._disable_discord_user(event.user_id)

    def reconcile(self) -> list[str]:
        """Bot 啟動時：有 ``discord_id`` 的帳號重查身分組，沒有就停用（Bot 離線期間的變動）。

        回傳這次停用的帳號名稱（依名稱排序）。"""
        disabled: list[str] = []
        for record in self.store.all():
            if record.discord_id is None or record.disabled:
                continue
            if not self.has_role(record.discord_id):
                self.store.set_disabled(record.account_id, True)
                disabled.append(record.username)
        return disabled
