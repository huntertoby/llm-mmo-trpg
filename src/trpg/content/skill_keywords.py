"""關鍵字推導表的 schema（Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1；資料檔
``content/skill_keywords.yaml``）。

關鍵字是玩家看技能卡就知道「哪些技能接得起來」的唯一組織方式：技能 **製造** 或 **利用** 關鍵字，
由原語、條件、觸發自動推導（推導函式在 ``trpg.skillgen.keywords``，和協同係數的機制標籤一樣不由人
填寫）。遊戲不定義流派：這裡只有 10 個關鍵字，沒有任何流派或主題分類。

一條規則恰好指定一種「來源」，再用參數縮小範圍；技能只要有任何一個符合的來源，就算製造（或
利用）該關鍵字：

- ``effect``：效果原語（含 ``then``／``win``／``lose``／``on_kill``／區域效果／修正規則的
  命中後效果）；
- ``condition``：技能、效果或修正規則上的條件；
- ``trigger``：被動技能的觸發時機；
- ``shape``：技能形狀；
- ``change``：修正規則的改變種類。

參數（``status``、``surface``、``element``、``object``、``stack``、``rule``、``on_hit``、``tag``、``skill``）必須等於該來源
上同名的欄位。
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.shared.types import Element, Surface

__all__ = ["KeywordDef", "KeywordRule", "KeywordTable"]

RuleSource = Literal["effect", "condition", "trigger", "shape", "change"]
RULE_SOURCES: tuple[RuleSource, ...] = ("effect", "condition", "trigger", "shape", "change")
RULE_PARAMS: tuple[str, ...] = (
    "status",
    "surface",
    "element",
    "object",
    "stack",
    "rule",
    "on_hit",
    "tag",
    "skill",
    "affects",
    "applies_to",
)
SKILL_FILTERS: tuple[str, ...] = ("weapon_req", "category")
"""技能層級的篩選（和來源一起成立才算符合）：技能的 ``weapon_req``（``melee``／``ranged``／
``focus``／``any``）與 ``category``（``weapon``／``spell``）。"""


class KeywordRule(ContentModel):
    """一條推導規則：一種來源（``effect`` 等）加上縮小範圍的參數。"""

    effect: str | None = Field(default=None, pattern=ID_PATTERN)
    condition: str | None = Field(default=None, pattern=ID_PATTERN)
    trigger: str | None = Field(default=None, pattern=ID_PATTERN)
    shape: str | None = Field(default=None, pattern=ID_PATTERN)
    change: str | None = Field(default=None, pattern=ID_PATTERN)
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: Surface | None = None
    element: Element | None = None
    object: str | None = Field(default=None, pattern=ID_PATTERN)
    stack: str | None = Field(default=None, pattern=ID_PATTERN)
    rule: str | None = Field(default=None, pattern=ID_PATTERN)
    on_hit: str | None = Field(default=None, pattern=ID_PATTERN)
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    skill: str | None = Field(default=None, pattern=ID_PATTERN)
    affects: Literal["self", "allies", "enemies", "all", "tiles"] | None = None
    applies_to: Literal["all_attacks", "all_skills"] | None = None
    """``change`` 專用：修正規則的 ``applies_to`` 開了這個旗標（不看標籤）。"""
    unconditional: Literal[True] | None = None
    """``change`` 專用：修正規則沒有條件（有條件的規則另有自己的關鍵字，例如對燃燒中目標）。"""
    weapon_req: Literal["melee", "ranged", "focus", "any"] | None = None
    category: Literal["weapon", "spell"] | None = None

    @model_validator(mode="after")
    def _one_source(self) -> KeywordRule:
        given = [name for name in RULE_SOURCES if getattr(self, name) is not None]
        if len(given) != 1:
            got = "、".join(given) if given else "沒有"
            raise ValueError(f"規則必須恰好指定一種來源（{'、'.join(RULE_SOURCES)}），收到 {got}")
        return self

    @property
    def source(self) -> RuleSource:
        """這條規則的來源種類。"""
        return next(name for name in RULE_SOURCES if getattr(self, name) is not None)

    @property
    def source_id(self) -> str:
        """來源的 ID（原語、條件、觸發、形狀或修正改變的 ID）。"""
        value = getattr(self, self.source)
        assert isinstance(value, str)
        return value

    def filters(self) -> dict[str, str]:
        """技能層級的篩選（:data:`SKILL_FILTERS`；名稱 → 值）。"""
        return {n: v for n in SKILL_FILTERS if (v := getattr(self, n)) is not None}

    def params(self) -> dict[str, str]:
        """已填寫的參數（名稱 → 字串值）。"""
        found: dict[str, str] = {}
        for name in RULE_PARAMS:
            value = getattr(self, name)
            if value is not None:
                found[name] = str(value.value if isinstance(value, Element | Surface) else value)
        return found


class KeywordDef(ContentModel):
    """一個關鍵字：ID、顯示名稱與說明，以及「製造」與「利用」的推導規則。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    makes: tuple[KeywordRule, ...] = Field(min_length=1)
    uses: tuple[KeywordRule, ...] = Field(min_length=1)


class KeywordTable(ContentModel):
    """``content/skill_keywords.yaml``：關鍵字清單（順序即顯示順序）。"""

    keywords: tuple[KeywordDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> KeywordTable:
        for label, values in (
            ("ID", [k.id for k in self.keywords]),
            ("名稱", [k.name_zh for k in self.keywords]),
        ):
            dup = sorted(v for v, n in Counter(values).items() if n > 1)
            if dup:
                raise ValueError(f"關鍵字{label}重複：{', '.join(dup)}")
        return self

    def ids(self) -> tuple[str, ...]:
        return tuple(k.id for k in self.keywords)

    def by_id(self) -> dict[str, KeywordDef]:
        return {k.id: k for k in self.keywords}

    def summary(self) -> str:
        return f"{len(self.keywords)} 個關鍵字"
