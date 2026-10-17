"""內容資料的 pydantic schema。

所有內容 model 都繼承 :class:`ContentModel`：``extra="forbid"``（拼錯欄位就報錯）、
``frozen=True``（載入後不可修改）。
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.shared.types import Element

__all__ = ["ContentModel", "ElementEntry", "ElementTable"]


class ContentModel(BaseModel):
    """內容資料 model 的基底。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def summary(self) -> str:
        """``trpg content check`` 顯示的一行摘要（子類別可覆寫）。"""
        return "通過驗證"


class ElementEntry(ContentModel):
    """``content/elements.yaml`` 的一筆元素資料。"""

    id: Element
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)


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
