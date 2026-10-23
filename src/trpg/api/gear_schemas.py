"""裝備測試介面的請求與回應（Phase 3G-G4）。

物品只有兩個來源：內容庫的測試物品（``item_id``），或手動組的 **自訂物品**（``custom``）。
自訂物品的詞條只能是白名單的 id ＋ 初值範圍內的數值——和之後 LLM 的路徑相同：
只能提議，由引擎的驗證函式（:func:`trpg.content.equipment.item_problems`、:func:`~trpg.content.equipment.loadout_problems`）裁決。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.content.slots import SlotType
from trpg.engine.view import AppearanceView, UnitView

__all__ = [
    "GearAffixInfo",
    "GearAffixPick",
    "GearCatalog",
    "GearCheck",
    "GearCheckRequest",
    "GearChoice",
    "GearCustomItem",
    "GearItemInfo",
    "GearItemLine",
    "GearOffhandInfo",
    "GearSlotInfo",
    "GearWeaponInfo",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GearAffixPick(_ApiModel):
    """自訂物品上的一條詞條：白名單 id ＋ 數值（詞條沒有數值範圍時不填）。"""

    affix: str
    value: int | None = None


class GearCustomItem(_ApiModel):
    """手動組的物品（欄位的物品種類由欄位決定，所以不必填）。

    ``weapon``：主手的武器 id；``offhand``：副手的種類 id（``offhands.yaml``，Phase 3I-2）；
    ``paired``：成對武器；``kind``：外觀造型（只影響圖示，選填）。
    """

    name_zh: str = Field(min_length=1, max_length=20)
    weapon: str | None = None
    offhand: str | None = None
    paired: bool = False
    tags: tuple[str, ...] = ()
    legendary: bool = False
    kind: str | None = None
    affixes: tuple[GearAffixPick, ...] = Field(default=(), max_length=8)


class GearChoice(_ApiModel):
    """一個欄位的選擇：內容庫物品 id，或自訂物品（二選一）。"""

    item_id: str | None = None
    custom: GearCustomItem | None = None

    @model_validator(mode="after")
    def _one_of(self) -> GearChoice:
        if (self.item_id is None) == (self.custom is None):
            raise ValueError("每個裝備欄位必須在 item_id 與 custom 之中選一個")
        return self


class GearCheckRequest(_ApiModel):
    hero_build: str | None = None
    """主角 build（開發用）；與 ``weapon``＋``keywords``／``dev_pack`` 三擇一。"""
    weapon: str | None = None
    keywords: tuple[str, ...] = ()
    dev_pack: str | None = None
    equipment: dict[str, GearChoice] = Field(default_factory=dict)


class GearSlotInfo(_ApiModel):
    slot: str
    name_zh: str
    slot_type: SlotType
    slot_type_zh: str


class GearWeaponInfo(_ApiModel):
    id: str
    name_zh: str
    weapon_class: str
    two_handed: bool


class GearOffhandInfo(_ApiModel):
    """副手種類（Phase 3I-2，``offhands.yaml``）：手動組副手時的選單。"""

    id: str
    name_zh: str
    traits_zh: tuple[str, ...] = ()


class GearAffixInfo(_ApiModel):
    """白名單的一條詞條。``name_zh`` 含 ``{n}``（數值）；沒有 ``value_min`` 的是固定效果。"""

    id: str
    name_zh: str
    category: str
    category_number: int
    category_zh: str
    slot_types: tuple[SlotType, ...]
    weapons: tuple[str, ...] = ()
    weapon_class: str | None = None
    item_tags: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    legendary_only: bool = False
    value_min: int | None = None
    value_max: int | None = None
    value_unit: str = "flat"


class GearItemLine(_ApiModel):
    affix_id: str
    text_zh: str


class GearItemInfo(_ApiModel):
    id: str
    name_zh: str
    slot_type: SlotType
    weapon: str | None = None
    weapon_name_zh: str | None = None
    offhand: str | None = None
    offhand_name_zh: str | None = None
    offhand_traits_zh: tuple[str, ...] = ()
    """副手物品的特性行（Phase 3I-2；數值取自副手資料，圓盾的「目前」值要進戰鬥才有）。"""
    two_handed: bool = False
    paired: bool = False
    tags: tuple[str, ...] = ()
    legendary: bool = False
    affixes: tuple[GearItemLine, ...] = ()
    appearance: AppearanceView = AppearanceView()


class GearCatalog(_ApiModel):
    """測試介面的選單：欄位、測試物品、詞條白名單、武器。"""

    slots: tuple[GearSlotInfo, ...]
    items: tuple[GearItemInfo, ...]
    affixes: tuple[GearAffixInfo, ...]
    weapons: tuple[GearWeaponInfo, ...]
    offhands: tuple[GearOffhandInfo, ...] = ()
    max_affixes_per_item: int
    max_cost_affixes: int
    diminishing_permille: tuple[int, ...]


class GearCheck(_ApiModel):
    """穿戴檢查：合法時附上主角（含裝備與加成來源）的單位資訊。"""

    legal: bool
    problems: tuple[str, ...] = ()
    hero: UnitView | None = None
