"""世界觀資料（語氣與名詞表）：放在 ``content/llm/*.yaml``，換世界觀只換資料。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from trpg.content.loader import default_content_dir

DEFAULT_WORLD_FILE = "llm/world_shattered.yaml"


class Realm(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name_zh: str
    style_zh: str


class GlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    term_zh: str
    meaning_zh: str


class WorldStyle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    name_zh: str
    summary_zh: str
    tone_zh: str
    realms: tuple[Realm, ...]
    glossary: tuple[GlossaryEntry, ...]


def load_world_style(path: Path | None = None) -> WorldStyle:
    """讀取世界觀資料；預設為內容資料夾下的碎界。"""
    target = path if path is not None else default_content_dir() / DEFAULT_WORLD_FILE
    with target.open(encoding="utf-8") as f:
        return WorldStyle.model_validate(yaml.safe_load(f))
