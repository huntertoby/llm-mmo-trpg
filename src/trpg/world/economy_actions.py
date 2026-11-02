"""經濟的世界動作與事件（Phase 5D-1；``docs/phases/Phase5計畫.md`` 26.4）。

放在獨立模組，由 :mod:`trpg.world.actions` 併進 ``WorldAction``／``WorldEvent`` 聯集（不匯入
``actions``，避免循環）。規則在 :mod:`trpg.world.economy`。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.slots import Slot

__all__ = [
    "BuyAction",
    "CurrencyGainedEvent",
    "EquipAction",
    "ItemBoughtEvent",
    "ItemEquippedEvent",
    "ItemSoldEvent",
    "ItemUsedEvent",
    "LootGainedEvent",
    "PouchAction",
    "PouchChangedEvent",
    "PouchUsedEvent",
    "SellAction",
    "UseItemAction",
]

_ITEM_ID = r"^item_[a-z0-9_]+$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


class BuyAction(_Model):
    """在店主所在的地點向他買東西（08 8.26.1）；一次 ``buy`` 算消費一次（代決 5D1-11）。"""

    kind: Literal["buy"] = "buy"
    shop: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=_ITEM_ID)
    count: int = Field(default=1, ge=1, le=10)


class SellAction(_Model):
    """把背包裡的東西賣給商店（8.15「出售物品」得金幣；腰包裡的不賣）。"""

    kind: Literal["sell"] = "sell"
    shop: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=_ITEM_ID)
    count: int = Field(default=1, ge=1, le=99)


class PouchAction(_Model):
    """整理腰包（城鎮或營火）：整組換成 ``items``（消耗品 → 個數，合計最多 3 個，8.17）。"""

    kind: Literal["pouch"] = "pouch"
    items: dict[str, int] = Field(default_factory=dict, max_length=10)


class UseItemAction(_Model):
    """野外或城鎮使用消耗品（09 9.6.11 #113「HP 靠藥水」）；先用背包裡的，背包沒有再用腰包的。"""

    kind: Literal["use_item"] = "use_item"
    item: str = Field(pattern=_ITEM_ID)


class EquipAction(_Model):
    """把背包裡的一件裝備換上（Phase 5D-2；城鎮或營火，同換技能）；換下的放回背包。"""

    kind: Literal["equip"] = "equip"
    item: str = Field(pattern=ID_PATTERN)
    """背包裡裝備的 ID（``CharacterState.gear``）。"""
    slot: Slot | None = None
    """指定欄位（戒指 1／2）；``None``＝照物品種類自動挑（戒指先放空的）。"""


# ---------------------------------------------------------------------------
# 事件
# ---------------------------------------------------------------------------


class ItemBoughtEvent(_Model):
    kind: Literal["item_bought"] = "item_bought"
    shop: str
    item: str
    count: int
    gold_spent: int
    gold: int
    """買完剩下的金幣。"""


class ItemSoldEvent(_Model):
    kind: Literal["item_sold"] = "item_sold"
    shop: str
    item: str
    count: int
    gold_gained: int
    gold: int


class PouchChangedEvent(_Model):
    kind: Literal["pouch_changed"] = "pouch_changed"
    pouch: dict[str, int]


class ItemUsedEvent(_Model):
    kind: Literal["item_used"] = "item_used"
    item: str
    hp: int
    mana: int


class PouchUsedEvent(_Model):
    """這場戰鬥用掉的腰包道具（物品 → 個數；勝負都扣）。"""

    kind: Literal["pouch_used"] = "pouch_used"
    items: dict[str, int]


class CurrencyGainedEvent(_Model):
    """得到金幣或任務幣（8.15）。``source``：``battle``、``quest:<任務>``、``shadow``（影子被借用）。"""

    kind: Literal["currency_gained"] = "currency_gained"
    currency: Literal["gold", "quest_coins"]
    amount: int
    total: int
    source: str


class LootGainedEvent(_Model):
    """打贏一場撿到的東西（Phase 5D-2）：材料（物品 → 個數）、裝備；背包滿了沒撿到的另列。"""

    kind: Literal["loot_gained"] = "loot_gained"
    materials: dict[str, int] = Field(default_factory=dict)
    gear: tuple[str, ...] = ()
    """撿到的裝備 ID（依掉落順序）。"""
    gear_names: tuple[str, ...] = ()
    lost_materials: dict[str, int] = Field(default_factory=dict)
    lost_gear_names: tuple[str, ...] = ()


class ItemEquippedEvent(_Model):
    """換上裝備（Phase 5D-2）：欄位、換上的物品、換下的物品（沒有為 ``None``）。"""

    kind: Literal["item_equipped"] = "item_equipped"
    slot: str
    item: str
    name_zh: str
    removed: tuple[str, ...] = ()
    """換下放回背包的物品名稱（雙手武器收起副手時有 2 件）。"""
