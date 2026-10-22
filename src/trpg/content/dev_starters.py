"""開發者起始包的 schema（Phase 3-24b2，``docs/design/06-技能.md`` 6.27.6；資料檔
``content/dev_starters.yaml``）。

12 個測試組合只給開發者選單、CLI 與模擬使用，**不是設計規則**：遊戲不定義流派，玩家介面不顯示
``label_zh``。每個起始包 ＝ 起始武器 ＋ 關鍵字（與一般開局相同），可選擇直接指定起始技能。
跨檔案檢查（武器、關鍵字、技能存在）在 :mod:`trpg.content.library` 載入時；技能是否在該關鍵字的
技能池裡由 ``trpg.roguelite.start`` 開局時檢查（推導函式在 ``trpg.skillgen``）。
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = ["DevStarter", "DevStarterTable"]


class DevStarter(ContentModel):
    """一個開發者起始包。"""

    id: str = Field(pattern=ID_PATTERN)
    label_zh: str = Field(min_length=1)
    """只在開發者選單顯示的名稱。"""
    weapon: str = Field(pattern=ID_PATTERN)
    keywords: tuple[str, ...] = Field(min_length=1)
    skills: tuple[str, ...] = ()
    """選填：依 ``keywords`` 的順序直接指定起始技能（省略時依一般開局的規則抽）。"""

    @model_validator(mode="after")
    def _check(self) -> DevStarter:
        if len(set(self.keywords)) != len(self.keywords):
            raise ValueError(f"起始包 {self.id} 的關鍵字重複")
        if self.skills and len(self.skills) != len(self.keywords):
            raise ValueError(f"起始包 {self.id} 的 skills 必須和 keywords 一樣多")
        return self


class DevStarterTable(ContentModel):
    """``content/dev_starters.yaml``。"""

    packs: tuple[DevStarter, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> DevStarterTable:
        dup = sorted(i for i, n in Counter(p.id for p in self.packs).items() if n > 1)
        if dup:
            raise ValueError(f"起始包 ID 重複：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, DevStarter]:
        return {p.id: p for p in self.packs}

    def summary(self) -> str:
        return f"{len(self.packs)} 個開發者起始包"
