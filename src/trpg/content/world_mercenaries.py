"""系統傭兵名單（``content/world/mercenaries.yaml``，Phase 5C-1；09 9.6.8 #87、9.6.9 #97、
9.6.11 #117）。

- 一隊 3 人：主角＋最多 ``max_hired`` 名傭兵（#97）；雇用免費、只能在城鎮選（世界動作 ``hire``，
  :mod:`trpg.world.party`）。
- 每名傭兵是固定 build（事先公布、每個人都一樣，#87）：底稿取自 ``content/sim/builds.yaml``
  （#117），戰鬥單位＝底稿的英雄範本換成傭兵的 ID 與暫名；等級與技能階級照主角成長（5A-SIM2）。

跨檔案檢查（底稿存在、不是白板或對照組）在 :mod:`trpg.content.library`。
"""

from __future__ import annotations

from collections import Counter
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.world_events import NpcPortrait

__all__ = [
    "MERCENARY_ROLES",
    "MIN_PER_ROLE",
    "CompanionDef",
    "EscortDef",
    "MercenaryDef",
    "MercenaryRole",
    "MercenaryTable",
    "PartyLine",
]

type MercenaryRole = Literal["damage", "guardian", "support", "control"]
"""定位（9.6.8：輸出、守護、輔助、控制）。"""

MERCENARY_ROLES: Final[dict[str, str]] = {
    "damage": "輸出",
    "guardian": "守護",
    "support": "輔助",
    "control": "控制",
}
"""定位 → 中文（依 9.6.8 的順序）。"""

MIN_PER_ROLE: Final = 2
"""每種定位至少幾名（9.6.8「各至少 2 種固定 build」）。"""


class MercenaryDef(ContentModel):
    """一名系統傭兵。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    """暫名（9.6.11 #117），也是戰鬥單位的名字。"""
    title_zh: str = Field(min_length=1)
    """稱號（例：近戰劍客）。"""
    role: MercenaryRole
    build: str = Field(pattern=ID_PATTERN)
    """底稿：``content/sim/builds.yaml`` 的 build ID。"""
    origin: str | None = Field(default=None, pattern=ID_PATTERN)
    """出身界域（``regions.yaml`` 的區域 ID；#131、RT-4）：名字與外觀照該區風格，頭像框用
    該區的區域色。純顯示，不影響數值；``None``＝沒有出身（頭像用傭兵金框）。"""
    portrait: NpcPortrait | None = None
    """頭像外觀（寫法同 NPC 人設卡的 ``portrait``，6C-7；RT-4 照
    ``docs/art/sample/merc-portraits.html``）。沒寫＝通用剪影。"""


class PartyLine(ContentModel):
    """隊友加入當下的一句台詞（OB-7，#154：對話框，不另做過場、不給選項）。"""

    speaker_zh: str = Field(min_length=1)
    text_zh: str = Field(min_length=1)


class EscortDef(ContentModel):
    """開局帶的護衛（OB-7，#154；09 9.6「預設隊友的出場」）：``mercenary`` 必須在 ``default_party``
    裡；``intro`` 是確定出發後、傳送前的台詞；``backstory_zh`` 是隊伍面板名字下面那行來歷（只給開局
    帶來的那一位，在城鎮換掉後重新雇用的不顯示）。"""

    mercenary: str = Field(pattern=ID_PATTERN)
    backstory_zh: str = Field(min_length=1)
    intro: tuple[PartyLine, ...] = Field(min_length=1)


class CompanionDef(ContentModel):
    """劇情夥伴（5C-3；09 9.6.9 #97：主線或任務鏈給的 NPC，只在對應任務裡跟著，佔一個隊友位）。

    戰鬥單位＝底稿 build 的英雄範本換成夥伴的 ID 與名字（同傭兵）；哪些任務帶他寫在任務的
    ``companion``（``content/world/quests/``）。"""

    id: str = Field(pattern=ID_PATTERN)
    npc: str = Field(pattern=ID_PATTERN)
    """人設卡（``content/world/npcs/``）的 NPC ID；好感度記在這個 NPC 上。"""
    name_zh: str = Field(min_length=1)
    title_zh: str = Field(min_length=1)
    build: str = Field(pattern=ID_PATTERN)
    """底稿：``content/sim/builds.yaml`` 的 build ID。"""
    ai_profile: str | None = Field(default=None, pattern=ID_PATTERN)
    """夥伴的打法（``ai_profiles.yaml``；5C-3b：阿岳＝弓手，保持距離遠程射擊）；``None``＝底稿預設。"""
    affinity_per_win: int = Field(default=0, ge=0, le=100)
    """帶他打贏一場給的好感度（18.7.6：阿岳 +2）。"""
    affinity_daily_cap: int = Field(default=0, ge=0, le=100)
    """同一天（6 點刷新）這種好感度最多加多少（18.7.6：阿岳每天最多 +6）。"""
    backstory_zh: str | None = Field(default=None, min_length=1)
    """隊伍面板名字下面那行來歷（OB-7，#154）；``None``＝不顯示。"""
    join_lines: tuple[PartyLine, ...] = ()
    """加入當下的台詞（OB-7，#154；開局還沒結束的角色才播，見 ``trpg.api.world_party_intro``）。"""


class MercenaryTable(ContentModel):
    """``content/world/mercenaries.yaml``。"""

    max_hired: int = Field(default=2, ge=1, le=2)
    """一次最多帶幾名（#97：主角＋最多 2 名隊友）。"""
    mercenaries: tuple[MercenaryDef, ...] = Field(min_length=1)
    ai_choices: tuple[str, ...] = ()
    """在城鎮替傭兵與影子選的 AI 打法（``ai_profiles.yaml`` 的 ID；5C-2，玩法 PM 定 ④）。空＝只能用
    預設。"""
    shadow_daily_coins: int = Field(default=1, ge=0)
    """影子每天第一次被借用給主人的任務幣（5C-2，#102；初值）。"""
    shadow_reports_kept: int = Field(default=20, ge=1)
    """影子紀錄保留的戰報則數（5C-2）。"""
    default_party: tuple[str, ...] = ()
    """新角色一開始帶的傭兵（依出場順序；5C-3；#154 起只帶賽倫）。空＝獨行。"""
    companions: tuple[CompanionDef, ...] = ()
    """劇情夥伴（5C-3，#97：只在對應任務裡跟著，佔一個隊友位）。"""
    escort: EscortDef | None = None
    """開局帶的護衛的台詞與來歷（OB-7，#154）。"""

    @model_validator(mode="after")
    def _check(self) -> MercenaryTable:
        dup = sorted(k for k, n in Counter(m.id for m in self.mercenaries).items() if n > 1)
        if dup:
            raise ValueError(f"傭兵 ID 重複：{', '.join(dup)}")
        counts: Counter[str] = Counter(m.role for m in self.mercenaries)
        short = [MERCENARY_ROLES[r] for r in MERCENARY_ROLES if counts[r] < MIN_PER_ROLE]
        if short:
            raise ValueError(f"每種定位至少 {MIN_PER_ROLE} 名（9.6.8），不足：{'、'.join(short)}")
        if len(set(self.ai_choices)) != len(self.ai_choices):
            raise ValueError("ai_choices 不能重複")
        self._check_defaults()
        return self

    def _check_defaults(self) -> None:
        known = {m.id for m in self.mercenaries}
        party = self.default_party
        if len(set(party)) != len(party) or len(party) > self.max_hired:
            raise ValueError(f"default_party 不能重複、最多 {self.max_hired} 名")
        unknown = [m for m in party if m not in known]
        if unknown:
            raise ValueError(f"default_party 有不在名單的傭兵：{', '.join(unknown)}")
        if self.escort is not None and self.escort.mercenary not in party:
            raise ValueError(f"escort 的 {self.escort.mercenary} 要在 default_party 裡")
        ids = [c.id for c in self.companions]
        clash = sorted({i for i in ids if ids.count(i) > 1} | (set(ids) & known))
        if clash:
            raise ValueError(f"劇情夥伴 ID 重複或和傭兵相撞：{', '.join(clash)}")

    def companion_by_id(self) -> dict[str, CompanionDef]:
        return {c.id: c for c in self.companions}

    def by_id(self) -> dict[str, MercenaryDef]:
        return {m.id: m for m in self.mercenaries}
