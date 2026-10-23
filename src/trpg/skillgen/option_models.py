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
- ``variants``：戰場變奏列表（子欄位在 ``fields``，Phase 3-25b）。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

__all__ = [
    "STEP_IDS",
    "Choice",
    "DraftOptions",
    "FieldSpec",
    "FieldType",
    "StepId",
    "StepOptions",
]

type StepId = Literal[
    "skeleton",
    "basics",
    "shape",
    "effects",
    "followup",
    "condition",
    "cost",
    "rarity",
    "variants",
]
STEP_IDS: tuple[StepId, ...] = (
    "skeleton",
    "basics",
    "shape",
    "effects",
    "followup",
    "condition",
    "cost",
    "rarity",
    "variants",
)
"""組技能的步驟，依序：骨架 → 基本設定（種類、類別、縮放屬性、階級、AP、觸發）→ 形狀 → 效果 →
動作段（只有位移技能可以接，可省略；Phase 3F-3b）→ 條件 → 代價 → 稀有度 → 戰場變奏（稀有以上的
主動技能才有，可省略；Phase 3-25b）。每一步的選項只取決於
前面的步驟；動作段步驟在不能接動作段的技能不會出現。"""

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
    "variants",
]


CARD_FIELDS: frozenset[str] = frozenset(
    {"skeleton", "kind", "category", "shape", "condition", "event", "target"}
)
"""用卡片排列選項的單選欄位（欄位路徑最後一段；Phase 3E-2e，原本寫死在前端）。"""
OBJECT_CHOICE_FIELDS: frozenset[str] = frozenset({"shape", "condition", "add_effect"})
"""選了之後值是物件 ``{"type": ...}`` 的單選欄位（其餘單選欄位的值就是純值）。"""


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
    locked: bool = False
    """鎖定（Phase 3H-6）：這個欄位的值由規則決定、玩家不能改（例：武器技的縮放屬性看手上武器）。
    ``choices`` 只有規則決定的那一個；畫面唯讀顯示，並把草稿的值對齊它。"""

    @model_validator(mode="before")
    @classmethod
    def _drop_derived(cls, data: Any) -> Any:
        """``card``／``object_choice`` 由欄位路徑推導；序列化後再讀回（過濾說明文字等）時忽略。"""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in ("card", "object_choice")}
        return data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def card(self) -> bool:
        """單選欄位用卡片排列（Phase 3E-2e）；前端不再依欄位名猜。"""
        return self.type == "choice" and self.field.rsplit(".", 1)[-1] in CARD_FIELDS

    @computed_field  # type: ignore[prop-decorator]
    @property
    def object_choice(self) -> bool:
        """單選欄位的值是物件 ``{"type": ...}``，選項專屬參數寫在該物件裡（Phase 3E-2e）。"""
        return self.type == "choice" and self.field.rsplit(".", 1)[-1] in OBJECT_CHOICE_FIELDS


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
