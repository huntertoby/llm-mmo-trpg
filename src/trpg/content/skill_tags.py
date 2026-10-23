"""技能標籤的中文名（Phase 3-41a；資料檔 ``content/skill_tags.yaml``）。

技能的 ``tags`` 是自由字串，被修正規則、條件、觸發、超載層數與刻印引用。玩家看到的說明一律用這裡的
中文名；查不到時用 :data:`UNKNOWN_TAG_TEXT` 帶過，不把英文代號拼進說明。
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = ["UNKNOWN_TAG_TEXT", "SkillTagDef", "SkillTagTable"]

UNKNOWN_TAG_TEXT = "特定"
"""對照表查不到的標籤顯示成「帶「特定」標籤」（不顯示英文代號）。"""


class SkillTagDef(ContentModel):
    """一個技能標籤：ID、中文名與（選填）刻印符文的單字。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    rune_zh: str | None = Field(default=None, min_length=1, max_length=2)


class SkillTagTable(ContentModel):
    """``content/skill_tags.yaml``。"""

    tags: tuple[SkillTagDef, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> SkillTagTable:
        dup = sorted(k for k, n in Counter(t.id for t in self.tags).items() if n > 1)
        if dup:
            raise ValueError(f"技能標籤 ID 重複：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, SkillTagDef]:
        return {t.id: t for t in self.tags}

    def name(self, tag: str) -> str:
        """標籤的中文名；查不到時為 :data:`UNKNOWN_TAG_TEXT`。"""
        found = next((t for t in self.tags if t.id == tag), None)
        return UNKNOWN_TAG_TEXT if found is None else found.name_zh

    def names(self) -> dict[str, str]:
        """標籤 ID → 中文名。"""
        return {t.id: t.name_zh for t in self.tags}

    def rune_names(self) -> dict[str, str]:
        """有刻印單字的標籤 ID → 單字。"""
        return {t.id: t.rune_zh for t in self.tags if t.rune_zh is not None}
