"""敘事一致性詞表（Phase 4-L11）：``content/llm/effect_words.yaml``。

LLM 寫的名稱與敘事提到某組的詞時，技能效果裡必須有該組 ``matches`` 的其中一項（狀態、元素、表面、
原語）。檢查本身在 :mod:`trpg.llm.consistency`；這裡只有資料格式與載入。
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import Field, model_validator

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "DEFAULT_EFFECT_WORDS_FILE",
    "EffectMatches",
    "EffectWordGroup",
    "EffectWords",
    "load_effect_words",
]

DEFAULT_EFFECT_WORDS_FILE = "llm/effect_words.yaml"


class EffectMatches(ContentModel):
    """一組詞對應的效果：任一項出現在技能裡就算對得上。"""

    statuses: tuple[str, ...] = ()
    elements: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    primitives: tuple[str, ...] = ()
    units: tuple[str, ...] = ()
    """召喚物範本 ID（``content/units/summons/``）。"""

    def facts(self) -> tuple[str, ...]:
        """``kind:id`` 形式的效果鍵（和 :func:`trpg.llm.consistency.skill_facts` 同格式）。"""
        return (
            *(f"status:{s}" for s in self.statuses),
            *(f"element:{e}" for e in self.elements),
            *(f"surface:{s}" for s in self.surfaces),
            *(f"primitive:{p}" for p in self.primitives),
            *(f"unit:{u}" for u in self.units),
        )


class EffectWordGroup(ContentModel):
    id: str
    words: tuple[str, ...] = Field(min_length=1)
    ignore: tuple[str, ...] = ()
    """含這些詞的片段不算提到（例如「風格」不算提到風）。"""
    matches: EffectMatches

    @model_validator(mode="after")
    def _check(self) -> EffectWordGroup:
        if not self.matches.facts():
            raise ValueError(f"詞組 {self.id} 沒有任何對應的效果")
        return self


class EffectWords(ContentModel):
    groups: tuple[EffectWordGroup, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> EffectWords:
        ids = [g.id for g in self.groups]
        if len(ids) != len(set(ids)):
            raise ValueError("詞組 id 重複")
        return self

    def summary(self) -> str:
        return f"{len(self.groups)} 組敘事一致性詞"


@cache
def _load_default() -> EffectWords:
    return load_content_file(default_content_dir() / DEFAULT_EFFECT_WORDS_FILE, EffectWords)


def load_effect_words(path: Path | None = None) -> EffectWords:
    """讀取詞表；預設為內容資料夾下的 ``llm/effect_words.yaml``（快取）。"""
    return _load_default() if path is None else load_content_file(path, EffectWords)
