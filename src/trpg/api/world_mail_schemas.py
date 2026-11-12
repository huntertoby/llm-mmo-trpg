"""郵寄的 API 格式（Phase 6T-1a；08 8.16、#136；畫面在 6T-1b，``docs/art/郵寄外觀.md``）。

全部由後端算好（前端不寫規則）：郵差與他這次要說的話、收件匣、退件・過期、寄出中的信、能寄的背包
物品（灰掉的原因）、寄件前的檢查（跑腿費、對方實收、全部問題）、有信時郵差頭上的「✉」。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.world_economy_schemas import BagItemView
from trpg.api.world_field_schemas import FieldHeroView
from trpg.content.world_events import NpcPortrait
from trpg.world.trade_audit import AuditFlag

__all__ = [
    "LetterItemView",
    "LetterView",
    "MailActionResponse",
    "MailBadgeView",
    "MailProblemView",
    "MailQuoteView",
    "MailRecipientView",
    "MailTabLinesView",
    "MailView",
    "PostmanView",
    "TradeAuditView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PostmanView(_ApiModel):
    """一位郵差（系統 NPC）。"""

    id: str
    name_zh: str
    race_zh: str
    role_zh: str
    region: str
    location: str
    place_zh: str
    """所在城鎮的名字。"""
    portrait: NpcPortrait | None = None


class MailBadgeView(_ApiModel):
    """郵差頭上的「✉」（世界畫面用；做法同任務「！」）。角色所在區域有郵差時才有。"""

    postman: str
    """郵差的 NPC ID。"""
    region: str
    location: str
    here: bool
    """角色現在就在郵差那裡（可以打開郵寄面板）。"""
    unread: int
    """收件匣能領的信數。"""
    returned: int
    """退件・過期能取回的信數。"""
    bubble: str | None
    """有信（``unread`` 或 ``returned`` 大於 0）時是「✉」，沒有為 ``None``。"""


class LetterItemView(_ApiModel):
    item: str
    name_zh: str
    count: int
    color: str | None = None
    """染料的顏色（``items.yaml`` 的 ``color``；QI-7 物品圖示）；不是染料為 ``None``。"""
    rare: bool | None = None
    """稀有材料（``items.yaml`` 的 ``rare``；QI-7 物品圖示的框線色）；不是材料為 ``None``。"""


class LetterView(_ApiModel):
    """一封信（收件匣、退件・過期、寄出中共用）。"""

    id: str
    sender: str
    sender_name: str
    recipient: str
    recipient_name: str
    from_zh: str
    """寄自哪裡（城鎮名）。"""
    sent_at: int
    expires_at: int
    days_left: int
    """還剩幾天退回（無條件進位；過期＝0）。"""
    note: str
    items: tuple[LetterItemView, ...] = ()
    gear: tuple[BagItemView, ...] = ()
    """附件裝備的卡片資料（含「最初得自」）。"""
    gold: int
    """對方實收的金幣（已扣稅）。"""
    tax: int
    status_zh: str
    """「可以領」「被拒收退回」「過期退回」「寄出中」等。"""
    action: str | None = None
    """這封信能做的事：``claim``（領取；被拒收、過期自動退回的信也是，6T-1b 拿掉 ``reclaim``）；
    不能為 ``None``。"""
    can_act: bool = False
    problem_zh: str | None = None
    """``action`` 現在做不了的原因（不在郵差這裡、背包放不下）；能做為 ``None``。"""
    can_refuse: bool = False
    """收件匣的信可以退回寄件人。"""


class MailTabLinesView(_ApiModel):
    """郵差在各分頁說的話（6T-1c；``world/trade.yaml`` 的 ``tab_*``，沒填的已換成打開面板那句）。"""

    send: str
    inbox: str
    """收件匣有信時。"""
    inbox_empty: str
    """收件匣沒有信時（沒填用「寄東西」那句）。"""
    returned: str


class MailView(_ApiModel):
    """郵寄面板（``GET …/mail``）。"""

    postman: PostmanView | None
    """所在區域的郵差；沒有郵差的區域為 ``None``。"""
    here: bool
    """角色在郵差這裡（寄信、領信都要在這裡）。"""
    here_problem_zh: str | None = None
    line_zh: str | None = None
    """郵差這次要說的話（打開面板：有信說「有你的信」、否則「打開」那句；等級不到說那句）。"""
    inbox: tuple[LetterView, ...] = ()
    returned: tuple[LetterView, ...] = ()
    """退件・過期：被拒收退回的、寄出去過期的。"""
    outgoing: tuple[LetterView, ...] = ()
    """寄出中（對方還沒領、還沒過期）。"""
    sendable: tuple[BagItemView, ...] = ()
    """背包裡的東西（``tradable`` 為假的灰掉，``bound_zh`` 是原因）。"""
    gold: int
    mailbox_count: int
    mailbox_max: int
    max_attachments: int
    note_max: int
    tax_permille: int
    min_level: int
    level_ok: bool
    return_days: int
    season_warning_zh: str | None = None
    """季末前 3 天：「季末沒領的信會清掉」。"""
    footer_zh: str
    """面板底下的一行說明。"""
    send_note_zh: str = ""
    """寄東西分頁「寄出」下方的小字（6T-1b：過期的信自動退回；文字在 ``world/trade.yaml``）。"""
    tab_lines: MailTabLinesView | None = None
    """郵差在各分頁說的話（6T-1c；沒有郵差為 ``None``）。等級不到時前端照舊用 ``line_zh``。"""


class MailRecipientView(_ApiModel):
    """寄給誰：別的帳號的角色（自己帳號的不列）。"""

    character_id: str
    name_zh: str
    level: int
    region: str
    place_zh: str
    """所在地點的名字。"""
    can_receive: bool
    """等級到了、信箱沒滿（裝備的等級上限另在寄件前檢查）。"""
    problem_zh: str | None = None
    hero_look: FieldHeroView | None = None
    """（QK-9b）收件人的 Q 版頭像：紙娃娃外觀（同角色清單的 ``hero_look``）。
    純顯示，不影響規則、存檔、重播；舊資料沒有時為 ``None``（前端畫灰色剪影）。"""
    origin_realm: str | None = None
    """（QK-9b）收件人出身的區域 ID（頭像框色）；沒有出身為 ``None``。"""


class MailProblemView(_ApiModel):
    code: str
    text_zh: str


class MailQuoteView(_ApiModel):
    """寄件前的檢查（``POST …/mail/quote``；不寫日誌）。全部通過 ``ok`` 才能寄。"""

    ok: bool
    gold: int
    tax: int
    received: int
    """對方實收。"""
    value: int
    """估值（交易帳、稽核用）。"""
    tax_zh: str
    """「跑腿費 10%：−N　對方實收 M」（沒寄金幣為空字串）。"""
    problems: tuple[MailProblemView, ...] = ()
    line_zh: str | None = None
    """郵差對第一個有台詞的問題說的話（等級不到、寄給自己帳號、對方拿不動）。"""
    season_warning_zh: str | None = None


class MailActionResponse(_ApiModel):
    """寄、領、拒收、取回之後：郵寄面板＋這次的結果句子與郵差的話。"""

    mail: MailView
    events: tuple[str, ...] = ()
    line_zh: str | None = None


class TradeAuditView(_ApiModel):
    """稽核報表（管理者；只出報表，不自動處理）。"""

    season_id: str
    trades: int
    flags: tuple[AuditFlag, ...] = Field(default_factory=tuple)
