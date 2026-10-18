"""層數（stack）的資料 schema（``content/stacks.yaml``；Phase 2E-3 5.1）。

層數是累積在單位身上的整數計量，由原語 ``add_stack`` 增加、``consume_stack`` 消耗：

- ``owner: self``：累積在 **施放者自己** 身上（蓄能資源，例如靜電）；
- ``owner: target``：累積在 **被命中的目標** 身上（疊印記，例如破甲印）。

只定義 schema；引擎（``trpg.engine.stacks``）依 ``id`` 查表，不寫死任何層數的 ID。
``trpg.content`` 不得匯入引擎。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = ["StackDef", "StackTable"]


class StackDef(ContentModel):
    """一種層數。

    - ``owner``：累積在施放者（``self``）或被命中的目標（``target``）身上。
    - ``max``：上限，``add_stack`` 超過時截斷。
    - ``expires_after_rounds``：每次累積（含已在上限時再累積）會刷新；之後這麼多輪沒有再累積，
      整個層數在那一輪開始時清空（省略＝不會過期）。
    - ``ai_value``：效用 AI 對每一層的估值（等值傷害點數；初值未經模擬）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    owner: Literal["self", "target"]
    max: int = Field(ge=1, le=9)
    expires_after_rounds: int | None = Field(default=None, ge=1)
    ai_value: int = Field(default=0, ge=0)

    def summary(self) -> str:
        return self.name_zh


class StackTable(ContentModel):
    """``content/stacks.yaml``。"""

    stacks: tuple[StackDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> StackTable:
        ids = [s.id for s in self.stacks]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"重複的層數 ID：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, StackDef]:
        return {s.id: s for s in self.stacks}

    def summary(self) -> str:
        return f"{len(self.stacks)} 種層數"
