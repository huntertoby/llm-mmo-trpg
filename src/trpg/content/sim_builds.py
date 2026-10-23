"""代表性 build 的資料檔（``content/sim/builds.yaml``；Phase 2C-3 5.3）。

一個 build ＝ 一名英雄（屬性、HP、武器、行為模式、技能清單）。build 矩陣（``trpg sim matrix``）的
我方隊伍是「build 英雄 ＋ 標準隊友」，敵方用地圖的 ``encounter.enemies``。build 的 ID 就是英雄範本的
ID（唯一，所以批次報表能以單位範本區分 build 英雄）。

只定義 schema；技能是否存在、與武器是否相容由 ``trpg.content.library`` 載入時檢查。
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.schemas import ContentModel

__all__ = ["BuildDef", "BuildTable"]


class BuildDef(ContentModel):
    """一個代表性 build：主題說明與英雄範本（欄位同 :class:`UnitTemplate`）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    theme_zh: str = Field(min_length=1)
    """主題與設計意圖（哪種地圖有利、哪種不利）。"""
    hero: UnitTemplate
    """英雄範本；``hero.id`` 必須等於 build 的 ``id``。"""
    blank: bool = False
    """白板主角（沒有任何技能，一輪中從升級長出技能）：允許空技能清單，不列入 build 矩陣與
    ``trpg run auto`` 的隨機抽選。"""

    reference: bool = False
    """對照組 build（Phase 3-32a，例如普攻流弓手 vs 技能流弓手）：只給專用的對照腳本使用，不列入
    build 矩陣與 ``trpg run auto`` 的隨機抽選。"""

    @field_validator("hero")
    @classmethod
    def _scaled(cls, hero: UnitTemplate) -> UnitTemplate:
        """build 英雄是主角：法力與耐力上限依屬性（Phase 3H-2，07 7.2）。"""
        return hero if hero.scaled_resources else hero.model_copy(update={"scaled_resources": True})

    @model_validator(mode="after")
    def _check(self) -> BuildDef:
        if self.hero.id != self.id:
            raise ValueError(f"build {self.id} 的 hero.id 必須相同（收到 {self.hero.id}）")
        if not self.hero.skills and not self.blank:
            raise ValueError(f"build {self.id} 沒有技能")
        return self


class BuildTable(ContentModel):
    """``content/sim/builds.yaml``。"""

    companions: tuple[str, ...] = Field(min_length=1)
    """標準隊友的單位範本 ID（依序加在 build 英雄之後）。"""
    builds: tuple[BuildDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> BuildTable:
        dup = sorted(k for k, n in Counter(b.id for b in self.builds).items() if n > 1)
        if dup:
            raise ValueError(f"build ID 重複：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, BuildDef]:
        return {b.id: b for b in self.builds}

    def sim_builds(self) -> tuple[BuildDef, ...]:
        """模擬用的 build（排除白板主角與對照組）。"""
        return tuple(b for b in self.builds if not b.blank and not b.reference)

    def summary(self) -> str:
        return f"{len(self.builds)} 個 build，隊友 {', '.join(self.companions)}"
