"""世界觀資料（語氣與名詞表）：放在 ``content/llm/*.yaml``，換世界觀只換資料。

Phase 4-L4 起登記於 ``content/registry.py``（``trpg content check`` 會驗證），並由
``trpg.llm.prompts`` 重新匯出。
"""

from __future__ import annotations

from pathlib import Path

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "DEFAULT_WORLD_FILE",
    "GlossaryEntry",
    "NamingRules",
    "Realm",
    "Theme",
    "WorldStyle",
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


class NamingRules(ContentModel):
    """技能命名與敘事的文字規則（Phase 4-L7）：長度上限與禁字。禁字是指令字樣、標籤與程式碼片段；
    英文字母與數字另由字元集檢查擋下（名稱只能是全形中文）。"""

    name_max_chars: int = 12
    concept_max_chars: int = 80
    flavor_max_chars: int = 80
    forbidden_terms: tuple[str, ...] = ()


class WorldStyle(ContentModel):
    id: str
    name_zh: str
    summary_zh: str
    tone_zh: str
    realms: tuple[Realm, ...]
    glossary: tuple[GlossaryEntry, ...]
    themes: tuple[Theme, ...] = ()
    naming: NamingRules = NamingRules()

    def theme_ids(self) -> tuple[str, ...]:
        return tuple(t.id for t in self.themes)

    def summary(self) -> str:
        return f"{self.name_zh}（{len(self.realms)} 個界域、{len(self.glossary)} 個名詞）"


def load_world_style(path: Path | None = None) -> WorldStyle:
    """讀取世界觀資料；預設為內容資料夾下的碎界。"""
    target = path if path is not None else default_content_dir() / DEFAULT_WORLD_FILE
    return load_content_file(target, WorldStyle)
