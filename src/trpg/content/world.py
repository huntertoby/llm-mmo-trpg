"""世界觀資料（語氣與名詞表）：放在 ``content/llm/*.yaml``，換世界觀只換資料。

Phase 4-L4 起登記於 ``content/registry.py``（``trpg content check`` 會驗證），並由
``trpg.llm.prompts`` 重新匯出。
"""

from __future__ import annotations

from pathlib import Path

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel

__all__ = ["DEFAULT_WORLD_FILE", "GlossaryEntry", "Realm", "WorldStyle", "load_world_style"]

DEFAULT_WORLD_FILE = "llm/world_shattered.yaml"


class Realm(ContentModel):
    name_zh: str
    style_zh: str


class GlossaryEntry(ContentModel):
    term_zh: str
    meaning_zh: str


class WorldStyle(ContentModel):
    id: str
    name_zh: str
    summary_zh: str
    tone_zh: str
    realms: tuple[Realm, ...]
    glossary: tuple[GlossaryEntry, ...]

    def summary(self) -> str:
        return f"{self.name_zh}（{len(self.realms)} 個界域、{len(self.glossary)} 個名詞）"


def load_world_style(path: Path | None = None) -> WorldStyle:
    """讀取世界觀資料；預設為內容資料夾下的碎界。"""
    target = path if path is not None else default_content_dir() / DEFAULT_WORLD_FILE
    return load_content_file(target, WorldStyle)
