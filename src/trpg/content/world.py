"""世界觀資料（語氣與名詞表）：放在 ``content/llm/*.yaml``，換世界觀只換資料。

Phase 4-L4 起登記於 ``content/registry.py``（``trpg content check`` 會驗證），並由
``trpg.llm.prompts`` 重新匯出。
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "DEFAULT_WORLD_FILE",
    "STYLE_EVAL_FILE",
    "ArchaicRules",
    "GlossaryEntry",
    "NamingRules",
    "Realm",
    "SkillStyle",
    "StyleEvalRules",
    "Theme",
    "WorldStyle",
    "WorldTermRules",
    "load_style_eval",
    "load_world_style",
]

DEFAULT_WORLD_FILE = "llm/world_shattered.yaml"


class Realm(ContentModel):
    name_zh: str
    style_zh: str


class GlossaryEntry(ContentModel):
    term_zh: str
    meaning_zh: str


class Theme(ContentModel):
    """主題詞（玩法決定 #48）：主題名稱、不是元素。題目帶主題時，``hint_zh`` 進 prompt 的題目區塊，
    告訴模型用哪些既有的機制組合；不改元素表。"""

    id: str
    name_zh: str
    hint_zh: str


class WorldTermRules(ContentModel):
    """世界觀詞的用量上限（Phase 4-L11，初值交玩法 PM 定稿）：名稱與敘事少用世界觀詞頭。

    - ``terms``：世界觀詞（子字串比對；由長到短、由左到右不重疊計數）。
    - ``name_prefix_chars``：名稱前 ``name_prefix_len`` 個字不得含這些字（例如「晶」「頻」）；
      名稱也不得以 ``terms`` 的詞開頭。
    - ``name_max``：名稱最多幾個世界觀詞；``text_max``：概念、施放敘事（與閃現 note）每段
      最多幾個。"""

    terms: tuple[str, ...] = ()
    name_prefix_chars: tuple[str, ...] = ()
    name_prefix_len: int = Field(default=2, ge=1)
    name_max: int = Field(default=1, ge=0)
    text_max: int = Field(default=1, ge=0)


class ArchaicRules(ContentModel):
    """古風詞（6L-1 C1、C5，#126）：中性與非東方的區域不用武俠、仙俠、文言詞。

    - ``terms``：古風詞（子字串比對）；``archaic: false`` 的風格下，名稱與兩段敘事都不可出現。
    - ``suffixes``：名稱不可用的結尾（「某某訣」）；``archaic: false`` 的風格下檢查。
    - ``always``：任何區域的 **名稱** 都不可出現（「施主」）。
    評估（:mod:`trpg.llm.style_eval`）用同一份清單統計古風詞比例。"""

    terms: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    always: tuple[str, ...] = ()


class NamingRules(ContentModel):
    """技能命名與敘事的文字規則（Phase 4-L7）：長度上限與禁字。禁字是指令字樣、標籤與程式碼片段；
    英文字母與數字另由字元集檢查擋下（名稱只能是全形中文）。"""

    name_max_chars: int = 12
    concept_max_chars: int = 80
    flavor_max_chars: int = 80
    forbidden_terms: tuple[str, ...] = ()
    world_terms: WorldTermRules = WorldTermRules()
    archaic: ArchaicRules = ArchaicRules()


class SkillStyle(ContentModel):
    """技能名稱與描述的區域風格（#126，06 6.34.7）：照 **取得地點的區域**。``region`` 是
    ``regions.yaml`` 或地點圖的區域 ID（主城是 ``capital``）；``archaic`` 為真的區才可以用古風詞
    （名稱仍不可用 :attr:`ArchaicRules.always`）。"""

    region: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name_zh: str = Field(min_length=1)
    style_zh: str = Field(min_length=1)
    archaic: bool = False


class WorldStyle(ContentModel):
    id: str
    name_zh: str
    summary_zh: str
    tone_zh: str
    realms: tuple[Realm, ...]
    glossary: tuple[GlossaryEntry, ...]
    themes: tuple[Theme, ...] = ()
    naming: NamingRules = NamingRules()
    neutral_style_zh: str = "中性奇幻"
    """沒有區域（創角、許願池、測試原型）時的技能風格（#126）。"""
    skill_styles: tuple[SkillStyle, ...] = ()

    @model_validator(mode="after")
    def _unique_styles(self) -> WorldStyle:
        regions = [s.region for s in self.skill_styles]
        if len(set(regions)) != len(regions):
            raise ValueError("skill_styles 的區域重複")
        return self

    def theme_ids(self) -> tuple[str, ...]:
        return tuple(t.id for t in self.themes)

    def skill_style(self, region: str | None) -> SkillStyle | None:
        """``region`` 的技能風格；``None`` 或沒有列出的區域回傳 ``None``（＝中性，
        :attr:`neutral_style_zh`）。"""
        if region is None:
            return None
        return next((s for s in self.skill_styles if s.region == region), None)

    def style_payload(self, region: str | None) -> dict[str, str]:
        """進 prompt 資料區的風格（#126）：``{"region": 區域名, "style_zh": 風格}``；中性時區域名是
        「無（中性）」。區域由呼叫端依世界狀態傳入，不讓 LLM 猜。"""
        style = self.skill_style(region)
        if style is None:
            return {"region": "無（中性）", "style_zh": self.neutral_style_zh}
        return {"region": style.name_zh, "style_zh": style.style_zh}

    def archaic_ok(self, region: str | None) -> bool:
        """這個區域的技能文字可不可以用古風詞（:class:`ArchaicRules`）。"""
        style = self.skill_style(region)
        return style is not None and style.archaic

    def summary(self) -> str:
        return f"{self.name_zh}（{len(self.realms)} 個界域、{len(self.glossary)} 個名詞）"


STYLE_EVAL_FILE = "llm/style_eval.yaml"


class StyleEvalRules(ContentModel):
    """文字風格分區的評估標準（Phase 6L-1 C9，``content/llm/style_eval.yaml``；
    :mod:`trpg.llm.style_eval`）。古風詞清單用 ``world_shattered.yaml`` 的 ``naming.archaic``。"""

    eval_regions: tuple[str, ...] = Field(min_length=1)
    """分區評估題目要出的區域（同一題各出一次）。"""
    neutral_regions: tuple[str, ...] = ()
    """技能名不可帶古風詞的區域。"""
    honorifics: tuple[str, ...] = ("施主",)
    formal_speakers: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """區域 → 可以用 ``honorifics`` 的 NPC（雲嶺：青霧觀修士，#127、18 18.5）。"""
    dot_share_max_permille: int = Field(default=500, ge=0, le=1000)
    """「X・Y」句式的上限（‰）。"""


def load_style_eval(path: Path | None = None) -> StyleEvalRules:
    """讀取風格評估標準；預設為內容資料夾下的 ``llm/style_eval.yaml``。"""
    target = path if path is not None else default_content_dir() / STYLE_EVAL_FILE
    return load_content_file(target, StyleEvalRules)


def load_world_style(path: Path | None = None) -> WorldStyle:
    """讀取世界觀資料；預設為內容資料夾下的碎界。"""
    target = path if path is not None else default_content_dir() / DEFAULT_WORLD_FILE
    return load_content_file(target, WorldStyle)
