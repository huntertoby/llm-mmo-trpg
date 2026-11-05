"""交易與郵寄的世界動作與事件（Phase 6T-1a；08 8.16、#136）。

放在獨立模組，由 :mod:`trpg.world.actions` 併進 ``WorldAction``／``WorldEvent`` 聯集（不匯入
``actions``，避免循環）。規則在 :mod:`trpg.world.trade`。

寄信（``mail_send``）、拒收（``mail_refuse``）同時改兩個角色：日誌那一筆記下另一個角色（``counterpart``，
:class:`~trpg.world.replay.WorldLogEntry`）。領信（``mail_claim``）領自己信箱裡的信只改自己；領過期自動
退回的信（6T-1b：資料還在收件人身上）同時改兩人。6T-1a 的取回（``mail_reclaim``）在 6T-1b 拿掉。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN

__all__ = [
    "MAIL_ACTIONS",
    "PAIR_ACTIONS",
    "MailClaimAction",
    "MailClaimedEvent",
    "MailRefuseAction",
    "MailRefusedEvent",
    "MailSendAction",
    "MailSentEvent",
]

_ITEM_ID = r"^item_[a-z0-9_]+$"
_LETTER_ID = r"^mail_[0-9]{6,}$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


class MailSendAction(_Model):
    """在城鎮的郵差處寄信給指定角色（08 8.16）：附背包裡的材料、消耗品、沒穿過的裝備或金幣。"""

    kind: Literal["mail_send"] = "mail_send"
    to: str = Field(pattern=ID_PATTERN)
    """收件角色 ID。"""
    items: dict[str, int] = Field(default_factory=dict, max_length=10)
    """背包裡的物品 → 個數（腰包裡的要先拿出來）。"""
    gear: tuple[str, ...] = Field(default=(), max_length=10)
    """背包裡裝備的 ID（穿戴中的不能寄）。"""
    gold: int = Field(default=0, ge=0, le=10_000_000)
    """寄出的金幣（稅前；對方實收＝扣掉 10% 跑腿費）。"""
    note: str = Field(default="", max_length=200)
    """留言（長度上限照 ``trade.yaml`` 的 ``note_max``）。"""


class MailClaimAction(_Model):
    """在郵差處領一封信（寄給自己的、被拒收退回來的、或過期自動退回的；6T-1b）：附件進背包。"""

    kind: Literal["mail_claim"] = "mail_claim"
    letter: str = Field(pattern=_LETTER_ID)


class MailRefuseAction(_Model):
    """收件人在郵差處把一封信退回給寄件人（附件原封不動；金幣的稅不退）。"""

    kind: Literal["mail_refuse"] = "mail_refuse"
    letter: str = Field(pattern=_LETTER_ID)


MAIL_ACTIONS: Final = (MailSendAction, MailClaimAction, MailRefuseAction)
PAIR_ACTIONS: Final = (MailSendAction, MailClaimAction, MailRefuseAction)
"""可能同時改兩個角色的動作（日誌那一筆記 ``counterpart``；領信只有過期退回的那種才改兩人）。"""


# ---------------------------------------------------------------------------
# 事件
# ---------------------------------------------------------------------------


class MailSentEvent(_Model):
    kind: Literal["mail_sent"] = "mail_sent"
    letter: str
    to: str
    to_name: str
    items: dict[str, int] = Field(default_factory=dict)
    gear_names: tuple[str, ...] = ()
    gold: int = 0
    """寄出的金幣（稅前）。"""
    tax: int = 0
    received: int = 0
    """對方實收的金幣。"""
    expires_at: int = 0
    season_warning: bool = False
    """季末前 3 天內寄出：季末沒領的信會清掉。"""


class MailClaimedEvent(_Model):
    kind: Literal["mail_claimed"] = "mail_claimed"
    letter: str
    sender_name: str
    items: dict[str, int] = Field(default_factory=dict)
    gear: tuple[str, ...] = ()
    """進背包的裝備 ID（撞到背包裡的 ID 時加了序號）。"""
    gear_names: tuple[str, ...] = ()
    gold: int = 0
    returned: Literal["refused", "expired"] | None = None


class MailRefusedEvent(_Model):
    kind: Literal["mail_refused"] = "mail_refused"
    letter: str
    sender_name: str
