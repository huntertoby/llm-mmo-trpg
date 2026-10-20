"""技能工坊的選項結構（Phase 3F-1）：:func:`trpg.skillgen.options.draft_options` 的回傳格式。

選項以「欄位」描述：每個欄位（:class:`FieldSpec`）有路徑、中文名稱與說明、型別、是否必填、數值範圍
與可選值（:class:`Choice`）。可選值可以再帶「選了它之後要填的欄位」（``params``），例如形狀
``single``
帶 ``range``、原語 ``push`` 帶 ``distance`` 與 ``affects``。網頁與之後的 LLM 技能生成（Phase 4）
都用同一份結構約束輸入。

型別（``type``）：

- ``choice``：從 ``choices`` 選一個 ``value``。
- ``multi_choice``：從 ``choices`` 選 ``min_count``–``max_count`` 個（例：修正規則的基本動作）。
- ``int``：``min``–``max`` 的整數（``None`` 表示不限）；``allow_weapon`` 時也可以填字串
  ``"weapon"``。
- ``count``：``min``–``max`` 的整數或字串 ``"all"``。
- ``dice``：``NdM`` 字串，``N`` 在 ``min``–``max``、``M`` 在 ``dice_sides`` 內。
- ``bool``：只能填 ``true``（省略＝不使用）。
- ``text``／``tags``：小寫 snake_case 字串／字串列表（標籤）。
- ``effects``：效果列表（每一項的可選原語在 ``choices``，數量 ``min_count``–``max_count``）。
- ``object``：巢狀物件，子欄位在 ``fields``（例：``scaling``、修正規則的 ``applies_to``）。
- ``modifiers``：修正規則列表（子欄位在 ``fields``）。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

__all__ = [
    "STEP_IDS",
    "Choice",
    "DraftOptions",
    "FieldSpec",
    "FieldType",
    "StepId",
    "StepOptions",
]

type StepId = Literal["skeleton", "basics", "shape", "effects", "condition", "cost", "rarity"]
STEP_IDS: tuple[StepId, ...] = (
    "skeleton",
    "basics",
    "shape",
    "effects",
    "condition",
    "cost",
    "rarity",
)
"""組技能的步驟，依序：骨架 → 基本設定（種類、類別、縮放屬性、階級、AP、觸發）→ 形狀 → 效果 →
條件 → 代價 → 稀有度。每一步的選項只取決於前面的步驟。"""

type FieldType = Literal[
    "choice",
    "multi_choice",
    "int",
    "count",
    "dice",
    "bool",
    "text",
    "tags",
    "effects",
    "object",
    "modifiers",
]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Choice(_Model):
    """一個可選值。``params``：選了它之後要填的欄位（``field`` 相對於被選的那個物件，例如形狀
    ``single`` 的 ``range`` 就是 ``shape.range``）；``info``：給畫面顯示的補充資料（例：骨架的
    最低稀有度、附帶效果上限）。"""

    value: str | int | bool
    name_zh: str
    description_zh: str = ""
    params: tuple[FieldSpec, ...] = ()
    info: dict[str, Any] = {}


class FieldSpec(_Model):
    """一個欄位。``field`` 是相對於上一層的路徑（頂層為技能定義的欄位名，例 ``shape``、
    ``cost.cooldown``）。"""

    field: str
    name_zh: str
    description_zh: str = ""
    type: FieldType
    required: bool = False
    min: int | None = None
    max: int | None = None
    allow_weapon: bool = False
    dice_sides: tuple[int, ...] = ()
    choices: tuple[Choice, ...] = ()
    fields: tuple[FieldSpec, ...] = ()
    min_count: int | None = None
    max_count: int | None = None
    default: str | int | bool | None = None


class StepOptions(_Model):
    """一個步驟：``complete`` 表示目前的技能已經填好這一步；``fields`` 是這一步的欄位與合法選項；
    ``notes_zh`` 是這一步的限制說明（例如「附帶效果最多 1 個」）。"""

    id: StepId
    name_zh: str
    description_zh: str
    complete: bool
    fields: tuple[FieldSpec, ...]
    notes_zh: tuple[str, ...] = ()


class DraftOptions(_Model):
    """:func:`~trpg.skillgen.options.draft_options` 的結果：前置步驟都完成的步驟（依序），以及
    第一個還沒完成的步驟 ``next_step``（全部完成時為 ``None``）。"""

    steps: tuple[StepOptions, ...]
    next_step: StepId | None
    problems: tuple[str, ...] = ()
    """已填的內容不在合法選項內的地方（中文；例如形狀不是骨架允許的形狀）。"""
