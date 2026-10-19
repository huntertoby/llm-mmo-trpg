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
from trpg.content.skills import EffectSpec

__all__ = ["OverloadSpec", "StackDef", "StackTable"]

_MAX_BACKLASH = 2


class OverloadSpec(ContentModel):
    """超載（Phase 3D-7b，6.17 D）：層數越疊越強，到門檻時對自己觸發懲罰並清空。

    - ``tag``：持有者帶這個標籤的技能，每層傷害 ``+per_stack_damage_permille`` ‰。
    - ``threshold``：累積到這個層數時，立刻對持有者結算 ``backlash`` 並清空（不超過 ``max``）。
    - ``backlash``：1–2 個效果，只能是 ``damage``（法術式，``dice`` ＋ ``element``，反噬傷害不會
      讓持有者低於 1 HP）或 ``apply_status``（不能是硬控、跳過回合或持續傷害，跨檔案檢查）。
    """

    tag: str = Field(pattern=ID_PATTERN)
    threshold: int = Field(ge=2, le=9)
    per_stack_damage_permille: int = Field(ge=1, le=1000)
    backlash: tuple[EffectSpec, ...]

    @model_validator(mode="after")
    def _check(self) -> OverloadSpec:
        if not 1 <= len(self.backlash) <= _MAX_BACKLASH:
            raise ValueError(
                f"backlash 必須有 1 到 {_MAX_BACKLASH} 個效果，收到 {len(self.backlash)}"
            )
        for sub in self.backlash:
            if sub.type not in ("damage", "apply_status"):
                raise ValueError(f"backlash 只能使用 damage、apply_status，收到 {sub.type}")
            if sub.affects not in (None, "self") or sub.condition is not None:
                raise ValueError("backlash 的對象固定是持有者，不可自帶 affects 或 condition")
            if sub.type == "damage" and (sub.dice is None or sub.element is None):
                raise ValueError("backlash 的 damage 必須指定 dice 與 element")
            if sub.type == "apply_status" and sub.status is None:
                raise ValueError("backlash 的 apply_status 必須指定 status")
        return self


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
    overload: OverloadSpec | None = None
    """超載（Phase 3D-7b）：只有 ``owner: self`` 的層數可以。"""

    @model_validator(mode="after")
    def _check(self) -> StackDef:
        if self.overload is not None:
            if self.owner != "self":
                raise ValueError("超載（overload）只能用在 owner: self 的層數")
            if self.overload.threshold > self.max:
                raise ValueError(f"overload.threshold 不可超過 max（{self.max}）")
        return self

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
