"""大世界隊伍與系統傭兵的 API 格式（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22.6）。

全部由後端算好（前端不寫規則）：隊伍成員、能不能雇用與理由、傭兵名單（定位、主題、技能概要）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trpg.content.world_events import NpcPortrait

__all__ = [
    "AiChoiceView",
    "LoneWolfView",
    "MercenaryView",
    "MyShadowView",
    "PartyIntroLine",
    "PartyIntroView",
    "PartyMemberView",
    "PartyView",
    "ShadowView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PartyMemberView(_ApiModel):
    """隊伍的一名成員（主角、傭兵或標準隊友）。"""

    name_zh: str
    title_zh: str
    """主角＝「主角」；傭兵＝稱號＋定位（例「盾衛・守護」）；標準隊友＝「標準隊友」。"""
    level: int
    """開戰時的等級（傭兵與標準隊友照主角等級成長，5A-SIM2）。"""
    mercenary: str | None = None
    """傭兵 ID（主角與影子為 ``None``）。"""
    shadow: str | None = None
    """影子主人的角色 ID（5C-2；不是影子為 ``None``）。"""
    ai_zh: str | None = None
    """打法（例「守衛」、「預設（守衛）」）；主角為 ``None``。"""
    companion: str | None = None
    """劇情夥伴 ID（5C-3；不是夥伴為 ``None``）。"""
    note_zh: str | None = None
    """補充說明（夥伴：「劇情夥伴：任務結束後離隊」）。"""
    backstory_zh: str | None = None
    """名字那一列下面的來歷（OB-7，#154）：開局帶來、沒換下過的賽倫（``mercenaries.yaml`` 的
    ``escort``）與有寫 ``backstory_zh`` 的劇情夥伴（阿岳）；其他成員 ``None``。"""
    portrait: NpcPortrait | None = None
    """劇情夥伴的頭像（PNL-4：人設卡 ``content/world/npcs/`` 的 ``portrait``）；其他成員 ``None``
    （傭兵照 ``PartyView.mercenaries`` 的名單、主角照主角外觀，前端已有）。"""
    region: str | None = None
    """劇情夥伴頭像框的區域色（人設卡所在的區，阿岳＝``cloud_ridge``）；其他成員 ``None``。"""


class MercenaryView(_ApiModel):
    """名單上的一名系統傭兵（每個人都一樣，9.6.8）。"""

    id: str
    name_zh: str
    title_zh: str
    role: str
    role_zh: str
    theme_zh: str
    """底稿 build 的主題說明（打法、有利與不利的地形）。"""
    skills_zh: tuple[str, ...]
    """技能概要：底稿技能的中文名（依底稿順序；開戰時照主角等級升階）。"""
    skill_ids: tuple[str, ...] = ()
    """和 ``skills_zh`` 同順序、同長度的技能 ID（UI-E3b；畫面用 ``/api/skills/{id}`` 取圖示）。"""
    hired: bool
    origin: str | None = None
    """出身界域（區域 ID，#131）；頭像框用該區的區域色。沒有＝``None``（傭兵金框）。"""
    portrait: NpcPortrait | None = None
    """頭像外觀（``mercenaries.yaml`` 的 ``portrait``，RT-4）；沒寫為 ``None``（通用剪影）。"""


class ShadowView(_ApiModel):
    """一個可以借的影子（5C-2；其他角色在城鎮整備時存的）。"""

    owner: str
    """影子主人的角色 ID（``hire`` 的 ``shadows`` 送這個）。"""
    name_zh: str
    level: int
    """影子本身的等級。"""
    role_zh: str
    """定位：玩家 build 沒有固定定位，顯示「武器・種族」（代決 5C2-9）。"""
    skills_zh: tuple[str, ...]
    """技能概要：裝備中的技能中文名（依裝備順序）。"""
    skill_ids: tuple[str, ...] = ()
    """和 ``skills_zh`` 同順序、同長度的技能 ID（UI-E3b）。內容庫的技能可以用 ``/api/skills/{id}``
    取圖示；影子自己的生成技能（存在影子裡、不在內容庫）查不到，畫面照舊寫字。"""
    borrowed_level: int
    """借用時的等級（不超過招募者，#87）。"""
    borrowed_tier: int
    """借用時的技能階級上限。"""
    capped: bool
    """借用時會被壓到招募者的上限。"""
    cap_zh: str | None = None
    """例「借用時壓到 Lv 1・技能 1 階（你的上限）」；沒被壓時 ``None``。"""
    hired: bool
    """目前在隊伍裡（借用當下的複本）。"""
    own: bool = False
    """保留給 5E（自己帳號的其他角色）；帳號還沒做，目前一律 ``False``。"""
    saved_zh: str
    """存的地點（例「霧渡鎮」）。"""
    titles: tuple[str, ...] = ()
    """影子主人帳號的紀念稱號（5F-3c 玩家名片；「碎晶的終結者（s1）」）。"""


class AiChoiceView(_ApiModel):
    """一種可選的 AI 打法（``ai_profiles.yaml``；5C-2 玩法 PM 定 ④）。"""

    id: str
    name_zh: str
    description_zh: str


class PartyIntroLine(_ApiModel):
    """隊友加入當下的一句台詞。"""

    speaker_zh: str
    text_zh: str
    portrait: NpcPortrait | None = None
    """說話者的頭像（PNL-4，OB-8）：伺服器照說話者的名字對到這段的成員（傭兵名單、劇情夥伴的人設卡）
    或主城的守印人；對不到或沒寫頭像為 ``None``（前端畫通用剪影）。"""
    region: str | None = None
    """頭像框的區域色：守印人 ``capital``、傭兵＝出身區（``None``＝傭兵金框）、
    劇情夥伴＝人設卡所在的區。"""


class PartyIntroView(_ApiModel):
    """還沒播的隊友加入台詞（OB-7，#154；對話框，不另做過場、不給選項）。

    前端播完送既有的 ``hint_seen {ids: [seen_id]}``，之後就不再出現（「重新顯示提示」清掉
    ``hints_seen`` 後會再出現一次）。已完成開局的角色（``opening`` 為 ``None``）不播。"""

    seen_id: str
    """``intro:<成員 ID>``（例 ``intro:merc_tiebi``、``intro:companion_ayue``）。"""
    member: str
    """傭兵 ID 或劇情夥伴 ID。"""
    name_zh: str
    lines: tuple[PartyIntroLine, ...]


class LoneWolfView(_ApiModel):
    """角色身上帶獨狼條件的技能與詞條，以及目前的隊伍出城會不會成立（LW-2，06 6.37「提示與標灰」）。

    ``ok`` 照隊伍面板的成員算（只有主角＝成立）；護送、守點戰開場就在我方的 NPC 也算隊友，
    出城前看不到，所以只寫在提示字裡。"""

    ok: bool
    skills_zh: tuple[str, ...] = ()
    """帶獨狼條件的技能名（技能列順序）。"""
    affixes_zh: tuple[str, ...] = ()
    """帶獨狼條件的詞條（「皮甲的「獨行的」」：物品名＋詞條名，欄位順序）。"""


class PartyView(_ApiModel):
    """目前的隊伍與雇用（09 9.6.9 #97：主角＋最多 2 名；免費、出城前在城鎮選好、野外不能換）。"""

    members: tuple[PartyMemberView, ...]
    max_hired: int
    can_hire: bool
    hire_problem_zh: str | None
    """不能換隊友的理由（例「出城前在城鎮選好，野外不能換」）；可以時為 ``None``。"""
    mercenaries: tuple[MercenaryView, ...] = ()
    """傭兵名單（名單順序）。"""
    shadows: tuple[ShadowView, ...] = ()
    """可以借的影子（不含自己；依主人 ID）。"""
    ai_choices: tuple[AiChoiceView, ...] = ()
    ai: dict[str, str] = {}
    """目前每名成員選的打法（傭兵 ID 或影子主人 ID → 打法 ID；沒有＝預設）。"""
    season_boss_ok: bool = True
    """隊伍能不能打賽季 Boss（有影子＝不能，#87）。"""
    season_boss_zh: str | None = None
    free_slots: int = 2
    """傭兵＋影子還能選幾名（劇情夥伴佔隊友位，5C-3）。"""
    companion_zh: str | None = None
    """劇情夥伴在隊時的說明（例「阿岳跟著你（霧渡新手路），佔 1 個隊友位；任務結束後離隊」）。"""
    lone_wolf: LoneWolfView | None = None
    """角色帶獨狼條件的技能或詞條時的出城前提示（LW-2）；沒帶時為 ``None``。"""


class MyShadowView(_ApiModel):
    """自己的影子（5C-2；#102）。"""

    saved: bool
    level: int | None = None
    saved_zh: str | None = None
    """存的地點與等級（例「霧渡鎮・Lv 3」）。"""
    ai: str | None = None
    """預設打法（``None``＝範本的預設）。"""
    ai_zh: str = "預設"
    can_set_ai: bool = False
    coins: int = 0
    """被借用累計的任務幣（5D 轉入角色）。"""
    reports_zh: tuple[str, ...] = ()
    """被借用的戰報（新的在前）。"""
