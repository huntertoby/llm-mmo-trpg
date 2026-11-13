"""大世界事件、情境判定、NPC、任務、線頭的 API 格式（Phase 5B-5；
``docs/phases/Phase5計畫.md`` 18.3、18.4）。

全部由後端算好（前端不寫規則）；文字已經套過隱藏地點的提示語（18.5：揭露前不出現名稱）。
玩家輸入（情境判定的回答、聊天）是純文字欄位，後端只把它放進 LLM 的 ``<player_input>``
（``wrap_player_input``，代決 5B5-5）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.run_schemas import OfferOut
from trpg.content.battle import ID_PATTERN
from trpg.content.world_events import NpcPortrait
from trpg.content.world_situations import PLAYER_TEXT_LIMIT, Outcome

__all__ = [
    "CARE_CITE_MAX",
    "CareLineView",
    "ChatRequest",
    "CiteFactView",
    "DialogLineView",
    "EventSolutionView",
    "EventView",
    "NpcHereView",
    "PendingOfferView",
    "QuestHereView",
    "QuestLogView",
    "QuestStepView",
    "SituationAnswerRequest",
    "SituationOpenRequest",
    "SituationResultView",
    "SituationView",
    "StoryView",
    "ThreadView",
    "WorldLlmRequest",
    "WorldLlmView",
]

CARE_CITE_MAX = 4
"""一次最多引用幾筆事實（同提議的用心清單上限）。"""


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# 請求
# ---------------------------------------------------------------------------


class WorldLlmRequest(_ApiModel):
    """大世界的 LLM 開關：``true`` 打開（先探測，連不到維持關閉）、``false`` 關閉、``null`` 回到
    伺服器設定（18.2）。"""

    enabled: bool | None = None


class SituationOpenRequest(_ApiModel):
    """打開事件的某個情境判定解法（說書人寫情境敘述）。"""

    template: str = Field(pattern=ID_PATTERN)


class SituationAnswerRequest(_ApiModel):
    """送出情境判定的回答（**第一次送出即定案**，9.6.4）。``text`` 只放進 LLM 的
    ``<player_input>``；``cite`` 是玩家點選引用的事實編號（``CiteFactView.fact``）。"""

    template: str = Field(pattern=ID_PATTERN)
    text: str = Field(default="", max_length=PLAYER_TEXT_LIMIT)
    cite: tuple[str, ...] = Field(default=(), max_length=CARE_CITE_MAX)


class ChatRequest(_ApiModel):
    """和所在地點的 NPC 自由聊天（9.6.7 #3：只換資訊）。``text`` 只放進 LLM 的
    ``<player_input>``。"""

    npc: str = Field(pattern=ID_PATTERN)
    text: str = Field(min_length=1, max_length=PLAYER_TEXT_LIMIT)


# ---------------------------------------------------------------------------
# 顯示
# ---------------------------------------------------------------------------


class WorldLlmView(_ApiModel):
    enabled: bool
    """說書人與情境提議現在用本機模型。"""
    default: bool
    """伺服器設定（``config/llm.toml`` 的 ``generate``）。"""
    overridden: bool
    """有人改過開關（``false`` ＝ 跟著伺服器設定）。"""
    notice_zh: str | None = None
    """打開時連不到模型的提示；健康檢查說模型不可用時也顯示（5E-3）。"""
    model_available: bool | None = None
    """本機模型的健康檢查結果（5E-3）：``null``＝還沒檢查（開關關著時不 ping）。"""


class StoryView(_ApiModel):
    """一段說書人的文字（旁白、情境、結果、回話）。"""

    text_zh: str
    more_zh: str = ""
    """「多講一點」（可空）。"""
    source: Literal["llm", "fallback", "authored"]
    """``llm``＝說書人；``fallback``＝LLM 不可用或核對不過時的降級模板（前端標「模板文字」）；
    ``authored``＝內容寫好的專用文字（機遇保底的旁白，5B-4e；5D-4 起不標模板）。"""


class EventSolutionView(_ApiModel):
    index: int
    kind: str
    kind_zh: str
    note_zh: str
    hint_zh: str = ""
    """補充說明（TXT-1）：只放在說明卡；空＝沒有。"""
    attributes_zh: str
    """可用的屬性（中文，「、」連）。"""
    template: str | None
    """情境判定的模板；其他解法為 ``None``。"""
    available: bool
    unavailable_zh: str | None = None
    cost_supplies: int = 0
    """交涉付出的補給（5B-5b）；其他解法為 0。"""
    can_pay: bool = True
    """補給付得起交涉（持有線頭時不付補給也能用）。"""
    waive_thread: str | None = None
    """持有且沒過期、可以抵掉付出的線頭 ID；沒有時為 ``None``。"""
    waive_zh: str | None = None
    """上述線頭的文字。"""


class CiteFactView(_ApiModel):
    """可以點選引用的事實（9.6.4：持有的線索、和 NPC 的往來、拿得出來的交換條件）。"""

    fact: str
    item: Literal["clue", "npc_bond", "exchange"]
    item_zh: str
    text_zh: str
    insert_zh: str | None = None
    """點選引用時插進回答的文字（5C-3d：引擎要在原文找到這筆的關鍵詞才算；這段文字一定找得到）。
    ``None``＝關鍵詞都含還沒發現的地點名，不插（玩家要自己寫）。"""


class SituationView(_ApiModel):
    """最近一次打開的情境判定（還沒送出）。"""

    template: str
    note_zh: str
    attributes_zh: str
    methods_zh: str
    base_dc: int
    story: StoryView | None
    facts: tuple[CiteFactView, ...] = ()


class EventView(_ApiModel):
    """事件卡（9.6.7 #6、#7）。"""

    skeleton: str
    location_name_zh: str
    actor_zh: str
    motive_zh: str
    story: StoryView | None
    """開場旁白；還沒敘述時為 ``None``。"""
    who_zh: str
    want_zh: str
    obstacle_zh: str
    stakes_zh: str
    follows_zh: str | None = None
    """接的線頭文字。"""
    solutions: tuple[EventSolutionView, ...]
    leave_zh: str
    situation: SituationView | None = None
    art_url: str | None = None
    """事件卡插圖（6C-7，21.7「一張插圖」）；插圖還沒有，目前一律 ``None``
    （前端畫場景色塊＋圖示）。"""
    art: str | None = None
    """事件卡插圖的場景 ID（6C-ART2，骨架的 ``art``；只畫）；``None``＝前端照第一個不是放棄的選項
    的圖示挑，不認得的值前端退回古碑。"""
    region: str | None = None
    """事件所在的區域（6C-ART2：插圖的背景依區域換；只畫）。"""


class CareLineView(_ApiModel):
    item_zh: str
    text_zh: str
    counted: bool
    reason_zh: str = ""


class SituationResultView(_ApiModel):
    """這次請求的情境判定明細與結果敘述。"""

    template: str
    note_zh: str
    attribute_zh: str
    method_zh: str
    dice: tuple[int, int]
    mode_zh: str
    roll: int
    attribute_mod: int
    care: tuple[CareLineView, ...]
    care_bonus: int
    race_bonus: int
    total: int
    base_dc: int
    dc_shift: int
    dc: int
    outcome: Outcome
    outcome_zh: str
    effects_zh: tuple[str, ...]
    """獎懲（經驗、補給、HP、下一場修正、線頭、發現地點）。"""
    story: StoryView | None = None
    source: Literal["llm", "fallback"]
    """提議的來源（LLM 或降級）。"""


class NpcHereView(_ApiModel):
    id: str
    name_zh: str
    role_zh: str
    affinity: int
    rank: str
    rank_zh: str
    range_zh: str
    """級距，例「中立（−9～19）」。"""
    talk_zh: str
    """這一級聊得到什麼。"""
    portrait: NpcPortrait | None = None
    """頭像外觀（人設卡的 ``portrait``，6C-7）；沒寫為 ``None``（前端用通用剪影）。"""


class DialogLineView(_ApiModel):
    """這次請求的 NPC 回話或聊到的內容。"""

    npc: str | None
    speaker_zh: str
    kind: Literal["rumor", "quest_entry", "secret", "chat", "nothing", "tavern"]
    text_zh: str
    more_zh: str = ""
    source: Literal["llm", "fallback"] | None = None


class QuestStepView(_ApiModel):
    text_zh: str
    done: bool
    current: bool
    place_zh: str | None = None
    """地點（PNL-3：``text_zh`` 第一個「：」前面，例「渡口石階」）；沒有「：」時 ``None``。"""
    task_zh: str | None = None
    """要做的事（PNL-3：「：」後面；沒有「：」時是整句）。舊資料沒有時前端用 ``text_zh``。"""


class QuestLogView(_ApiModel):
    id: str
    name_zh: str
    kind_zh: str
    summary_zh: str
    giver_zh: str | None
    steps: tuple[QuestStepView, ...]
    done: bool
    route_zh: str | None = None
    """目前這一步往哪走（6F-2，筆記 U3：方向與出口，例「往東邊的出口 → 渡口石階」）；就在這裡、
    不知道路或沒有地點目標時 ``None``。"""
    advice_zh: str | None = None
    """建議（6F-2，筆記 U4：新手任務鏈完成前，主線標「建議先完成霧渡新手路」）。"""
    giver_portrait: NpcPortrait | None = None
    """委託人頭像（PNL-3，人設卡的 ``portrait``）；沒有委託人或沒寫頭像時 ``None``
    （前端用通用剪影）。"""
    giver_region: str | None = None
    """委託人頭像框的區域色（PNL-3；任務所在區域）。"""


class QuestHereView(_ApiModel):
    """在這裡可以接的任務。"""

    id: str
    name_zh: str
    kind_zh: str
    summary_zh: str
    giver_zh: str | None
    can_accept: bool
    problem_zh: str | None = None
    advice_zh: str | None = None
    """建議（6F-2，同 :attr:`QuestLogView.advice_zh`）。"""


class PendingOfferView(_ApiModel):
    """任務給的技能三選一（07 7.6）。"""

    quest_name_zh: str
    step_zh: str
    offer: OfferOut
    can_replace: bool
    """在城鎮或營火（可以直接裝上、指定替換）；野外學到的放進備用。"""
    place_zh: str
    source: Literal["quest", "opportunity", "wish"] = "quest"
    """三選一從哪來（``PendingOffer.source``：``quest``、``opportunity``、``wish``…；WP-2 起給前端
    分辨許願池的標題與跳過鈕）。"""
    refund: int = 0
    """都不拿時退還的任務幣（許願池，#88 2b；其他來源 0）。前端的跳過鈕
    寫「都不拿（退 N 任務幣）」。"""


class ThreadView(_ApiModel):
    id: str
    text_zh: str
    scope: Literal["personal", "world"]
    scope_zh: str
    expires_zh: str
    left_zh: str | None = None
    """剩多久（PNL-3 #26：「剩 2 天 23 小時」「剩不到 1 小時」，前面配鐘圖示）；
    ``expires_zh`` 照舊給 HUD 追蹤列。"""
    npc_zh: str | None = None
    location_zh: str | None = None
