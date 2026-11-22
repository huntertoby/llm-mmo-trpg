"""內容資料的 pydantic schema。

所有內容 model 都繼承 :class:`ContentModel`：``extra="forbid"``（拼錯欄位就報錯）、
``frozen=True``（載入後不可修改）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.shared.types import ELEMENT_RESIST_GROUP, Element, ResistGroup

__all__ = ["ContentModel", "ElementEntry", "ElementTable", "duplicates", "field_bounds"]


def duplicates(values: Iterable[str]) -> list[str]:
    """``values`` 裡重複出現的值（排序、不重複）；驗證「ID 重複」用。"""
    seen: set[str] = set()
    dup: set[str] = set()
    for value in values:
        if value in seen:
            dup.add(value)
        seen.add(value)
    return sorted(dup)


class ContentModel(BaseModel):
    """內容資料 model 的基底。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def summary(self) -> str:
        """``trpg content check`` 顯示的一行摘要（子類別可覆寫）。"""
        return "通過驗證"


def field_bounds(model: type[ContentModel], name: str) -> tuple[int, int]:
    """``model`` 的整數欄位 ``name`` 的 ``ge``／``le``（HC-4b2：讓組合器的範圍照技能 schema，不另外
    寫數字；HC-7 b 起數值工坊的欄位範圍也讀它）。"""
    low: int | None = None
    high: int | None = None
    for meta in model.model_fields[name].metadata:
        low = getattr(meta, "ge", low)
        high = getattr(meta, "le", high)
    assert low is not None and high is not None, f"{model.__name__}.{name} 沒有上下限"
    return low, high


class ElementEntry(ContentModel):
    """``content/elements.yaml`` 的一筆元素資料。"""

    id: Element
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    resist_group: ResistGroup

    @model_validator(mode="after")
    def _resist_group_matches_code(self) -> ElementEntry:
        expected = ELEMENT_RESIST_GROUP[self.id]
        if self.resist_group is not expected:
            raise ValueError(
                f"元素 {self.id.value} 的 resist_group 應為 {expected.value}，"
                f"收到 {self.resist_group.value}"
            )
        return self


class ElementTable(ContentModel):
    """``content/elements.yaml``：每個 :class:`~trpg.shared.types.Element` 恰好出現一次。"""

    elements: tuple[ElementEntry, ...]

    @model_validator(mode="after")
    def _each_element_exactly_once(self) -> ElementTable:
        counts = Counter(entry.id for entry in self.elements)
        # 依列舉定義順序檢查，讓錯誤訊息穩定
        missing = [e.value for e in Element if counts[e] == 0]
        duplicated = [e.value for e in Element if counts[e] > 1]
        problems: list[str] = []
        if missing:
            problems.append(f"缺少元素：{', '.join(missing)}")
        if duplicated:
            problems.append(f"重複的元素：{', '.join(duplicated)}")
        if problems:
            raise ValueError("；".join(problems))
        return self

    def by_id(self, element: Element) -> ElementEntry:
        """依元素取得資料（驗證後保證存在）。"""
        for entry in self.elements:
            if entry.id is element:
                return entry
        raise KeyError(element)  # pragma: no cover - 驗證已保證每個元素都存在

    def summary(self) -> str:
        return f"{len(self.elements)} 種元素"
