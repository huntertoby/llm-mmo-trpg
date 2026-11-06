"""區域主題點綴（``content/ui/region_themes.yaml``，Phase RT-1）。

設計見 ``docs/art/區域主題移植需求.md`` 第 1 節。純前端資料：前端
``client/src/ui/regionTheme.ts`` 在 build 時匯入同一份檔，依目前區域換四角飾件、
標題牌、頭像框與強調色；Python 端只驗證 schema（``trpg content check``），
不進引擎結算。RT-3 的等待動畫讀 ``ink``、``seal``、``wait_fx``。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = [
    "CORNER_KINDS",
    "FALLBACK_THEME",
    "PlaqueDef",
    "RegionTheme",
    "RegionThemeTable",
]

CORNER_KINDS: tuple[str, ...] = ("filigree", "cloud", "rivet", "shard", "gear", "shell")
"""四角飾件的畫法（與前端 ``CORNER_KINDS`` 相同）。"""

FALLBACK_THEME = "hub"
"""沒有區域、或讀不到區域時用的主題。"""

Hex = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
CornerKind = Literal["filigree", "cloud", "rivet", "shard", "gear", "shell"]


class PlaqueDef(ContentModel):
    """標題牌材質：上下兩色的直向漸層。"""

    top: Hex
    bottom: Hex


class RegionTheme(ContentModel):
    """一區的點綴。"""

    accent: Hex
    corner: CornerKind
    plaque: Annotated[str, Field(pattern=ID_PATTERN)]
    portrait_ring: Hex
    ink: Hex
    """等待動畫（RT-3）的墨色。"""
    seal: Hex
    """等待動畫（RT-3）的封蠟色。"""
    wait_fx: Literal["none", "ember", "crystal"] = "none"
    """等待動畫（RT-3）的點綴。"""


class RegionThemeTable(ContentModel):
    """``content/ui/region_themes.yaml``：標題牌材質＋區域 ID → 主題。"""

    plaques: dict[Annotated[str, Field(pattern=ID_PATTERN)], PlaqueDef] = Field(min_length=1)
    themes: dict[Annotated[str, Field(pattern=ID_PATTERN)], RegionTheme] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> RegionThemeTable:
        if FALLBACK_THEME not in self.themes:
            raise ValueError(f"必須有 {FALLBACK_THEME} 主題（沒有區域時用）")
        for region in sorted(self.themes):
            plaque = self.themes[region].plaque
            if plaque not in self.plaques:
                raise ValueError(f"{region}：未知的標題牌材質 {plaque}")
        return self

    def theme_for(self, region: str | None) -> RegionTheme:
        """該區的主題；``None`` 或沒有這區時用 ``hub``。"""
        if region is not None and region in self.themes:
            return self.themes[region]
        return self.themes[FALLBACK_THEME]

    def summary(self) -> str:
        corners = len({t.corner for t in self.themes.values()})
        plaques = len(self.plaques)
        return f"{len(self.themes)} 個區域主題（{corners} 種四角飾件、{plaques} 種標題牌）"
