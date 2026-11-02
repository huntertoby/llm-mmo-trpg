"""大世界經濟的 API 格式（Phase 5D-1；``docs/phases/Phase5計畫.md`` 25.5）。

全部由後端算好（前端不寫規則）：金幣與任務幣、背包與腰包、這裡的店（價格、限量剩餘、門檻、能不能買
與原因）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "BagItemView",
    "InventoryView",
    "ShopItemView",
    "ShopView",
    "WalletView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class WalletView(_ApiModel):
    gold: int
    quest_coins: int


class BagItemView(_ApiModel):
    """背包或腰包裡的一種物品。"""

    item: str
    name_zh: str
    kind_zh: str
    count: int
    description_zh: str
    sell_price: int
    """賣給商店一個的金幣（腰包裡的要先拿出來才能賣）。"""
    field_usable: bool
    """野外可以使用（藥水）。"""
    use_zh: str | None = None
    """野外使用的效果（例「HP +30%」）；不能用為 ``None``。"""
    battle_zh: str | None = None
    """放進腰包時戰鬥中的用法（例「戰鬥中 1 AP：回 2d6 HP」）；不是消耗品為 ``None``。"""


class InventoryView(_ApiModel):
    bag: tuple[BagItemView, ...]
    slots_used: int
    slots_max: int
    pouch: tuple[BagItemView, ...]
    pouch_count: int
    pouch_max: int
    can_pouch: bool
    """可以整理腰包（城鎮或營火、沒有遭遇、不在戰鬥）。"""
    pouch_problem_zh: str | None
    consumables: tuple[BagItemView, ...] = ()
    """背包＋腰包合計的消耗品（整理腰包的選單用；``count`` 是合計個數）。"""


class ShopItemView(_ApiModel):
    item: str
    name_zh: str
    kind_zh: str
    description_zh: str
    price: int
    weekly: bool
    """每週限量的區域特產。"""
    stock_zh: str | None
    """限量剩餘（例「本週剩 3 個」）；不限量為 ``None``。"""
    locked: bool
    """還沒到好感度門檻（8.26.1）。"""
    lock_zh: str | None
    """門檻說明（例「柳掌櫃好感度到友善才賣」）。"""
    can_buy: bool
    problem_zh: str | None
    """不能買的原因；可以買時為 ``None``。"""
    battle_zh: str | None = None


class ShopView(_ApiModel):
    """角色所在地點的店（8.26.1）。"""

    shop: str
    name_zh: str
    npc: str
    npc_name_zh: str
    rank_zh: str
    """店主目前的好感度級名。"""
    affinity_zh: str | None
    """消費加好感度的說明（例「每次消費柳掌櫃好感度 +2（每天最多 +4，今天還能 +2）」）。"""
    items: tuple[ShopItemView, ...]
    can_trade: bool
    """可以買賣（沒有遭遇、不在戰鬥）。"""
    trade_problem_zh: str | None
