"""交易共同前置與郵寄的規則（Phase 6T-1a；08 8.15、8.16、#136）。

``content/world/trade.yaml``（:class:`TradeRules`）：

- ``trade``：所有交易方式共用的門檻（角色等級、收到的裝備物品等級上限、能交易的物品種類、金幣稅）。
- ``mail``：郵寄（信箱上限、幾天沒領退回、季末前幾天提示、附件格數、留言字數）與三區郵差（人設卡
  ＋七種情境的台詞，玩法 PM「郵差內容文字」）。
- ``audit``：稽核報表的門檻（短時間大量、估值懸殊；只出報表，不自動處理，#101）。

跨檔案檢查（郵差所在的地點要是城鎮）在 :func:`load_world_trade`。數值只改這份資料。
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.world_economy import ItemKind
from trpg.content.world_events import NpcCardDef
from trpg.shared.errors import ContentError

__all__ = [
    "DAY_SECONDS",
    "MAIL_LINE_KINDS",
    "TRADE_FILE",
    "MailLineKind",
    "MailRules",
    "MailTexts",
    "Postman",
    "PostmanLines",
    "TradeAudit",
    "TradeCommon",
    "TradeRules",
    "load_world_trade",
]

TRADE_FILE: Final = "world/trade.yaml"
DAY_SECONDS: Final = 86_400
"""現實的一天（秒）；郵寄的退件與季末提示用現實天數（玩法 PM 代決「現實 3 天」）。"""

type MailLineKind = Literal[
    "open", "has_mail", "sent", "low_level", "same_account", "too_strong", "returned"
]
MAIL_LINE_KINDS: Final[tuple[MailLineKind, ...]] = (
    "open",
    "has_mail",
    "sent",
    "low_level",
    "same_account",
    "too_strong",
    "returned",
)
"""郵差的七種情境：打開、有信、寄件成功、等級不到、寄給自己帳號、對方等級太低、退件。"""


class TradeCommon(ContentModel):
    """各種交易方式共用的門檻（08 8.16）。"""

    min_level: int = Field(default=3, ge=1)
    """角色幾級起能交易。"""
    item_level_margin: int = Field(default=2, ge=0)
    """收到的裝備，物品等級不能高於自己等級 ＋ 這個數。"""
    tradable_kinds: tuple[ItemKind, ...] = ("consumable", "material")
    """背包裡能交易的物品種類（材料、消耗品；8.16 沒列的染料不行）。"""
    gold_tax_permille: int = Field(default=100, ge=0, le=1000)
    """寄金幣的稅（8.15「10%」）；捨入照 :meth:`gold_tax`。"""

    def gold_tax(self, gold: int) -> int:
        """寄 ``gold`` 金幣扣的稅（無條件進位：至少 1，避免拆成小額免稅）。"""
        if gold <= 0:
            return 0
        return (gold * self.gold_tax_permille + 999) // 1000


class PostmanLines(ContentModel):
    """郵差的七種情境台詞（玩法 PM「郵差內容文字」第 2 節）。"""

    open: str = Field(min_length=1)
    has_mail: str = Field(min_length=1)
    sent: str = Field(min_length=1)
    low_level: str = Field(min_length=1)
    same_account: str = Field(min_length=1)
    too_strong: str = Field(min_length=1)
    returned: str = Field(min_length=1)
    tab_send: str | None = Field(default=None, min_length=1)
    """「寄東西」分頁的話（6T-1c，玩法 PM「郵差內容文字」第 4 節；選填，見 :meth:`tab_lines`）。"""
    tab_inbox: str | None = Field(default=None, min_length=1)
    """「收件匣」分頁、有信時的話（選填）。"""
    tab_inbox_empty: str | None = Field(default=None, min_length=1)
    """「收件匣」分頁、沒有信時的話（選填；沒填用「寄東西」那句）。"""
    tab_returned: str | None = Field(default=None, min_length=1)
    """「退件・過期」分頁的話（選填；分頁裡沒有退件時也用這句）。"""

    def tab_lines(self, current: str) -> dict[str, str]:
        """各分頁的話（``send``、``inbox``、``inbox_empty``、``returned``）。

        沒填的退回 ``current``（打開面板時那句）；空收件匣沒填用「寄東西」那句。
        """
        send = self.tab_send or current
        return {
            "send": send,
            "inbox": self.tab_inbox or current,
            "inbox_empty": self.tab_inbox_empty or send,
            "returned": self.tab_returned or current,
        }

    def line(self, kind: MailLineKind) -> str:
        text: str = getattr(self, kind)
        return text


class Postman(ContentModel):
    """一位郵差（系統 NPC，每個城鎮一位）：人設卡＋台詞。"""

    region: str = Field(pattern=ID_PATTERN)
    race_zh: str = ""
    card: NpcCardDef
    """人設卡（``location`` 是這一區的城鎮地點）。"""
    lines: PostmanLines


class MailTexts(ContentModel):
    """郵寄面板的固定說明句（6T-1b；``{days}``＝``return_days``）。"""

    footer_zh: str = "信只能在城鎮的郵差這裡領；{days} 天沒領會自動退回寄件人，季末清掉。"
    """收件匣、退件分頁底下的一行。"""
    send_note_zh: str = "{days} 天內沒人領，會自動退回給你（跑腿費不退）；季末沒領的信會清掉。"
    """寄東西分頁「寄出」下方的小字（玩法 PM 決定 6T-1a 第 6 項：過期的信自動退回）。"""
    season_warning_zh: str = "季末快到了：季末沒領的信會清掉。"

    def format(self, text: str, days: int) -> str:
        return text.replace("{days}", str(days))


class MailRules(ContentModel):
    """郵寄（08 8.16 第一步；玩法 PM 3.5 代決）。"""

    mailbox_max: int = Field(default=20, ge=1)
    """信箱上限（寄給你的、還沒領也還沒過期的信）。"""
    return_days: int = Field(default=3, ge=1)
    """現實幾天沒領就退回寄件人（金幣的稅不退）。"""
    season_warning_days: int = Field(default=3, ge=0)
    """季末前幾天寄件時提示「季末沒領的信會清掉」。"""
    max_attachments: int = Field(default=3, ge=1)
    """一封信最多幾格附件（一種物品或一件裝備算一格；金幣另算）。"""
    note_max: int = Field(default=40, ge=0)
    texts: MailTexts = Field(default_factory=MailTexts)
    """面板的固定說明句（6T-1b）。"""
    postmen: tuple[Postman, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> MailRules:
        regions = [p.region for p in self.postmen]
        if len(set(regions)) != len(regions):
            raise ValueError("每一區最多一位郵差")
        ids = [p.card.id for p in self.postmen]
        if len(set(ids)) != len(ids):
            raise ValueError("郵差的 ID 重複")
        return self

    @property
    def return_seconds(self) -> int:
        return self.return_days * DAY_SECONDS

    @property
    def season_warning_seconds(self) -> int:
        return self.season_warning_days * DAY_SECONDS

    def postman_of(self, region: str) -> Postman | None:
        return next((p for p in self.postmen if p.region == region), None)


class TradeAudit(ContentModel):
    """稽核報表的門檻（08 8.16「短時間大量、估值懸殊」；只出報表，#101）。"""

    burst_count: int = Field(default=5, ge=2)
    """同一個帳號在 ``burst_seconds`` 內寄出這麼多封以上＝短時間大量。"""
    burst_seconds: int = Field(default=3600, ge=1)
    big_value: int = Field(default=500, ge=1)
    """一封信的估值這麼多以上＝大額。"""
    pair_value: int = Field(default=800, ge=1)
    """同一對帳號、單向累計估值這麼多以上，而反方向不到它的 ``lopsided_permille``＝估值懸殊。"""
    lopsided_permille: int = Field(default=200, ge=0, le=1000)


class TradeRules(ContentModel):
    """``content/world/trade.yaml``。"""

    trade: TradeCommon = Field(default_factory=TradeCommon)
    mail: MailRules
    audit: TradeAudit = Field(default_factory=TradeAudit)

    def summary(self) -> str:
        names = "、".join(p.card.name_zh for p in self.mail.postmen)
        return f"交易：{self.trade.min_level} 級起、郵差 {len(self.mail.postmen)} 位（{names}）"


def load_world_trade(
    root: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    locations: Mapping[str, Mapping[str, str]],
) -> TradeRules | None:
    """載入 ``world/trade.yaml``；不存在＝``None``（交易關閉）。``locations``＝區域 → 地點 →
    地點種類（含主城）；郵差要站在城鎮。"""
    path = root / TRADE_FILE
    if not path.is_file():
        return None
    rules = load_content_file(path, TradeRules)
    problems: list[str] = []
    for postman in rules.mail.postmen:
        where = f"郵差 {postman.card.id}"
        kinds = locations.get(postman.region)
        if kinds is None:
            problems.append(f"{where}：沒有區域 {postman.region}")
            continue
        kind = kinds.get(postman.card.location)
        if kind is None:
            problems.append(f"{where}：{postman.region} 沒有地點 {postman.card.location}")
        elif kind != "town":
            problems.append(f"{where}：{postman.card.location} 不是城鎮")
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, rules))
    return rules
