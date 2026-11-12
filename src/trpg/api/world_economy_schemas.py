"""大世界經濟的 API 格式（Phase 5D-1；``docs/phases/Phase5計畫.md`` 26.5）。

全部由後端算好（前端不寫規則）：金幣與任務幣、背包與腰包、這裡的店（價格、限量剩餘、門檻、能不能買
與原因）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trpg.api.run_schemas import GearCandidateOut, HeroGearSlotOut

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
    """賣給商店一個的金幣（腰包裡的要先拿出來才能賣；不能賣為 0）。"""
    sellable: bool = True
    """商店收不收（20.1「材料不能賣」）。"""
    field_usable: bool
    """野外可以使用（藥水）。"""
    use_zh: str | None = None
    """野外使用的效果（例「HP +30%」）；不能用為 ``None``。"""
    battle_zh: str | None = None
    """放進腰包時戰鬥中的用法（例「戰鬥中 1 AP：回 2d6 HP」）；不是消耗品為 ``None``。"""
    gear: bool = False
    """背包裡的裝備（Phase 5D-2；``item`` 是這件裝備的 ID，``count`` 固定 1）。"""
    can_equip: bool = False
    """裝備可以換上（城鎮或營火、沒有遭遇）。"""
    equip_problem_zh: str | None = None
    tradable: bool = False
    """能郵寄（6T-1a，08 8.16）：材料、消耗品、沒穿過也沒綁定的裝備。"""
    bound_zh: str | None = None
    """裝備綁定的標籤（「穿過」「獨特」「首殺」；6T-1a 郵寄面板灰掉用）；沒綁定為 ``None``。"""
    origin_zh: str | None = None
    """裝備卡的「最初得自：〈原主〉（〈來源〉）」（6T-1a）。"""
    holder_zh: str | None = None
    """裝備卡的「目前持有：〈角色名〉」（6T-1a）。"""
    cross_class_zh: str | None = None
    """別大類的主手（#135）：「別大類：可交易・可分解・可賣」；同大類或不是主手為 ``None``。"""
    cross_class_lost_zh: str | None = None
    """別大類的主手卡片的下一行：「換上後不能用：〈招名〉」（目前裝的招裡要原本大類的）。"""
    opening_note_zh: str | None = None
    """開局還沒結束時裝備卡多寫的一行（OB-6：重選會收回的起始武器本體在背包時）；沒有＝``None``。"""


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
    equipped_zh: tuple[str, ...] = ()
    """穿戴中的裝備（每欄一句，例「身體：稀有布衣（3 級）」；Phase 5D-2）。"""
    resonance_zh: tuple[str, ...] = ()
    """目前觸發的裝備共鳴（Phase 5D-3，M3；例「潛影共鳴（隱蔽 2 件）：敏捷 +2」）。"""
    equipment: tuple[HeroGearSlotOut, ...] = ()
    """穿戴中（5D-4 背包畫面；9 個欄位都列，空著 ``item`` 為 ``None``；格式同一輪）。"""
    gear_cards: tuple[GearCandidateOut, ...] = ()
    """背包裡的每件裝備：物品卡、換上會放進的欄位、和該欄位目前裝備的比較（5D-4；格式同一輪的
    背包）。順序同 ``bag`` 裡的裝備。"""


class PendingLootView(_ApiModel):
    """背包滿了：戰後結算選要丟哪件（Phase 5D-2b）。``items`` 是新拿到、還沒放進背包的；
    背包裡原本的看 ``InventoryView.bag``。用 ``loot_choose`` 動作送出要丟的
    （``drop_items``、``drop_gear``）。"""

    items: tuple[BagItemView, ...]
    over_slots: int
    """全部收下還差幾格（丟掉的要騰出這麼多格）。"""
    hint_zh: str


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
    price_notes_zh: tuple[str, ...] = ()
    """買價加成的原因（5F-5c；例「熔岩潰堤失守：買價 +20%」；文字在 ``world/season.yaml``）。"""
