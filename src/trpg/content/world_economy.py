"""大世界的經濟：貨幣規則、物品與商店（Phase 5D-1；``docs/phases/Phase5計畫.md`` 26.2）。

- ``content/world/economy.yaml``（:class:`EconomyRules`）：背包 30 格、腰包 3 個（08 8.17）、一格疊
  幾個、賣價比例、打贏戰鬥給的金幣、完成任務給的任務幣（8.15；數值是開發 PM 定的初值）。
- ``content/world/items.yaml``（:class:`WorldItemTable`）：消耗品（藥水、投擲瓶；戰鬥中的用法是
  一招「道具技能」，和 ``content/skills/`` 同一套檢查、**不進技能池**）、材料、染料。
- ``content/world/shops/<region>.yaml``（:class:`ShopTable`）：區域商人；只賣消耗品、粗料、染料
  與本區特產（特產每週限量，8.26.1）；好感度門檻用級名（09 9.6.11 #116）。

跨檔案檢查（區域、NPC、道具技能的引用與費用）在 :func:`load_world_economy`（技能檢查由內容庫傳入）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef
from trpg.content.skills.queries import ITEM_SKILL_TAG
from trpg.content.world_quests import AffinityRank
from trpg.shared.errors import ContentError

__all__ = [
    "ECONOMY_FILE",
    "ITEMS_FILE",
    "ITEM_KINDS",
    "ITEM_SKILL_TAG",
    "SHOPS_DIR",
    "BattleGold",
    "EconomyRules",
    "ItemKind",
    "MaterialGrade",
    "QuestCoins",
    "ShopAffinity",
    "ShopDef",
    "ShopStock",
    "ShopTable",
    "WeeklyStock",
    "WorldEconomy",
    "WorldItemDef",
    "WorldItemTable",
    "load_world_economy",
    "shop_problems",
]

ECONOMY_FILE: Final = "world/economy.yaml"
ITEMS_FILE: Final = "world/items.yaml"
SHOPS_DIR: Final = "world/shops"

type ItemKind = Literal["consumable", "material", "dye", "supply"]
type MaterialGrade = Literal["coarse", "fine", "superior"]
ITEM_KINDS: Final[dict[str, str]] = {
    "consumable": "消耗品",
    "material": "材料",
    "dye": "染料",
    "supply": "補給",
}
"""物品種類 → 中文。"""

_ITEM_ID = r"^item_[a-z0-9_]+$"
_STACKS: Final[dict[ItemKind, int]] = {"consumable": 10, "material": 20, "dye": 10, "supply": 1}
_COLOR = r"^#[0-9A-Fa-f]{6}$"


def _duplicates(values: Iterable[str]) -> list[str]:
    return sorted(k for k, n in Counter(values).items() if n > 1)


class BattleGold(ContentModel):
    """打贏一場的金幣（8.15「戰鬥」）：陣容含精英用 ``elite``；每高 1 級
    +``level_step_permille``‰。"""

    battle: int = Field(default=15, ge=0)
    elite: int = Field(default=45, ge=0)
    level_step_permille: int = Field(default=100, ge=0, le=1000)

    def gold_for(self, *, elite: bool, level: int) -> int:
        base = self.elite if elite else self.battle
        return base * (1000 + self.level_step_permille * (max(1, level) - 1)) // 1000


class QuestCoins(ContentModel):
    """完成任務的任務幣（8.15「任務」）：依任務種類，``by_quest`` 可個別覆寫。"""

    by_kind: dict[str, int] = Field(default_factory=dict)
    by_quest: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> QuestCoins:
        bad = sorted(k for k in self.by_kind if k not in {"starter", "main", "chain", "hidden"})
        if bad:
            raise ValueError(f"quest_coins.by_kind 有未知的任務種類：{bad}")
        if any(v < 0 for v in (*self.by_kind.values(), *self.by_quest.values())):
            raise ValueError("任務幣不可為負")
        return self

    def coins_for(self, quest: str, kind: str) -> int:
        return self.by_quest.get(quest, self.by_kind.get(kind, 0))


class EconomyRules(ContentModel):
    """``content/world/economy.yaml``（26.2 第 1 點）。"""

    bag_slots: int = Field(default=30, ge=1, le=200)
    pouch_slots: int = Field(default=3, ge=0, le=10)
    stack_max: dict[ItemKind, int] = Field(default_factory=lambda: dict(_STACKS))
    sell_permille: int = Field(default=500, ge=0, le=1000)
    unsellable_kinds: tuple[ItemKind, ...] = ()
    """不能賣的種類（20.1「材料不能賣」）。"""
    start_gold: int = Field(default=0, ge=0)
    battle_gold: BattleGold = Field(default_factory=BattleGold)
    quest_coins: QuestCoins = Field(default_factory=QuestCoins)

    @model_validator(mode="after")
    def _check(self) -> EconomyRules:
        missing = [k for k in _STACKS if self.stack_max.get(k, 0) < 1]
        if missing:
            raise ValueError(f"stack_max 缺少或小於 1：{missing}")
        return self

    def sellable(self, kind: ItemKind) -> bool:
        return kind not in self.unsellable_kinds

    def sell_price(self, price: int) -> int:
        return max(1, price * self.sell_permille // 1000)


class WorldItemDef(ContentModel):
    """一種物品（26.2 第 2 點）。"""

    id: str = Field(pattern=_ITEM_ID)
    name_zh: str = Field(min_length=1)
    kind: ItemKind
    description_zh: str = ""
    price: int = Field(ge=1)
    """金幣價格（商店照它賣；賣價照 ``sell_permille``）。"""
    region: str | None = Field(default=None, pattern=ID_PATTERN)
    """區域特產（8.14；商店的 ``weekly`` 只能賣本區特產）。"""
    skill: SkillDef | None = None
    """消耗品在戰鬥中的用法（道具技能；1 AP、每個用一次，8.17）。"""
    field_hp_permille: int = Field(default=0, ge=0, le=1000)
    """野外使用回最大 HP 的 ‰（09 9.6.11 #113「靠藥水」）。"""
    field_mana_permille: int = Field(default=0, ge=0, le=1000)
    color: str | None = Field(default=None, pattern=_COLOR)
    supplies: int = Field(default=0, ge=0, le=10)
    """補給（``kind: supply``）買一個加幾點補給；不進背包（20.1）。"""
    rare: bool = False
    """稀有材料（20.2「精英必掉 1 份稀有或家族材料」；Phase 5D-2）。"""
    grade: MaterialGrade | None = None
    """通用料的階（粗、精、上；08 8.26.2 打造的物品等級上限 3／7／10 用，5D-3）。"""

    @property
    def field_usable(self) -> bool:
        return self.field_hp_permille > 0 or self.field_mana_permille > 0

    @model_validator(mode="after")
    def _check(self) -> WorldItemDef:
        if (self.kind == "consumable") != (self.skill is not None):
            raise ValueError(f"物品 {self.id}：只有消耗品有 skill，而且消耗品必須有")
        if self.kind != "consumable" and self.field_usable:
            raise ValueError(f"物品 {self.id}：只有消耗品能在野外使用")
        if (self.kind == "supply") != (self.supplies > 0):
            raise ValueError(f"物品 {self.id}：只有補給有 supplies，而且補給必須有")
        if (self.kind == "dye") != (self.color is not None):
            raise ValueError(f"物品 {self.id}：只有染料有 color，而且染料必須有")
        if self.kind != "material" and (self.rare or self.grade is not None):
            raise ValueError(f"物品 {self.id}：只有材料有 rare／grade")
        skill = self.skill
        if skill is not None:
            problems = []
            if ITEM_SKILL_TAG not in skill.tags:
                problems.append(f"道具技能要帶標籤 {ITEM_SKILL_TAG}")
            if skill.kind != "active" or skill.ap_cost != 1:
                problems.append("道具技能必須是主動、1 AP（8.17）")
            if skill.cost.uses_per_battle != 1:
                problems.append("道具技能的 cost.uses_per_battle 必須是 1（每個用一次）")
            if problems:
                raise ValueError(f"物品 {self.id}：{'；'.join(problems)}")
        return self


class WorldItemTable(ContentModel):
    """``content/world/items.yaml``。"""

    items: tuple[WorldItemDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> WorldItemTable:
        dup = _duplicates(i.id for i in self.items)
        if dup:
            raise ValueError(f"物品 ID 重複：{dup}")
        dup = _duplicates(i.skill.id for i in self.items if i.skill is not None)
        if dup:
            raise ValueError(f"道具技能 ID 重複：{dup}")
        return self

    def item_by_id(self) -> dict[str, WorldItemDef]:
        return {i.id: i for i in self.items}


class ShopStock(ContentModel):
    """常駐商品；``rank``＝店主好感度至少到這級才賣（8.26.1）。"""

    item: str = Field(pattern=_ITEM_ID)
    rank: AffinityRank | None = None


class WeeklyStock(ContentModel):
    """每週限量的區域特產（8.26.1）：每週 ``min``～``max`` 個（不同時由賽季種子決定）；
    ``rank``＝門檻。"""

    item: str = Field(pattern=_ITEM_ID)
    rank: AffinityRank | None = None
    min: int = Field(ge=0, le=99)
    max: int = Field(ge=0, le=99)

    @model_validator(mode="after")
    def _check(self) -> WeeklyStock:
        if self.min > self.max:
            raise ValueError(f"限量商品 {self.item}：min 不可大於 max")
        return self


class ShopAffinity(ContentModel):
    """在店裡消費一次，店主好感度 +``per_purchase``，每天最多 +``daily_max``（18.7.6）。"""

    per_purchase: int = Field(ge=1, le=100)
    daily_max: int = Field(ge=1, le=100)


class ShopDef(ContentModel):
    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    npc: str = Field(pattern=ID_PATTERN)
    """店主（人設卡 ID）；店在他的地點。"""
    stock: tuple[ShopStock, ...] = ()
    weekly: tuple[WeeklyStock, ...] = ()
    affinity: ShopAffinity | None = None

    @model_validator(mode="after")
    def _check(self) -> ShopDef:
        dup = _duplicates([*(s.item for s in self.stock), *(w.item for w in self.weekly)])
        if dup:
            raise ValueError(f"店 {self.id} 的商品重複：{dup}")
        return self

    def stock_of(self, item: str) -> ShopStock | None:
        return next((s for s in self.stock if s.item == item), None)

    def weekly_of(self, item: str) -> WeeklyStock | None:
        return next((w for w in self.weekly if w.item == item), None)


class ShopTable(ContentModel):
    """``content/world/shops/<region>.yaml``。"""

    region: str = Field(pattern=ID_PATTERN)
    shops: tuple[ShopDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ShopTable:
        dup = _duplicates(s.id for s in self.shops)
        if dup:
            raise ValueError(f"店 ID 重複：{dup}")
        return self

    def shop_by_id(self) -> dict[str, ShopDef]:
        return {s.id: s for s in self.shops}


@dataclass(frozen=True)
class WorldEconomy:
    """內容庫的經濟資料；沒有 ``economy.yaml`` 時 ``rules`` 為 ``None``（經濟功能關閉）。"""

    rules: EconomyRules | None = None
    items: dict[str, WorldItemDef] = field(default_factory=dict)
    shops: dict[str, ShopTable] = field(default_factory=dict)

    def item_skills(self) -> dict[str, WorldItemDef]:
        """道具技能 ID → 物品。"""
        return {i.skill.id: i for i in self.items.values() if i.skill is not None}


def shop_problems(
    table: ShopTable,
    items: Mapping[str, WorldItemDef],
    *,
    has_region: bool,
    npcs: Collection[str] | None,
) -> list[str]:
    """一個區域的商店檔的跨檔案問題（26.2 第 3 點；依店、商品順序）。``npcs`` 為 ``None``＝該區沒有
    人設卡（不檢查店主，舊內容資料夾照常載入）。"""
    problems: list[str] = []
    if not has_region:
        problems.append(f"區域 {table.region} 沒有地點圖")
    for shop in table.shops:
        if npcs is not None and shop.npc not in npcs:
            problems.append(f"店 {shop.id} 的店主 {shop.npc} 不在 {table.region} 的人設卡")
        for stock in shop.stock:
            item = items.get(stock.item)
            if item is None:
                problems.append(f"店 {shop.id} 的商品 {stock.item} 不在 world/items.yaml")
            elif item.kind == "material" and item.grade != "coarse":  # 通用 1 階（08 8.14）
                problems.append(f"店 {shop.id} 只能賣粗料這種材料（8.26.1），不能賣 {item.id}")
        for weekly in shop.weekly:
            item = items.get(weekly.item)
            if item is None:
                problems.append(f"店 {shop.id} 的限量商品 {weekly.item} 不在 world/items.yaml")
            elif item.region != table.region:
                problems.append(f"店 {shop.id} 的限量商品 {weekly.item} 不是 {table.region} 的特產")
    return problems


def load_world_economy(
    root: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    regions: Collection[str],
    npcs_by_region: Mapping[str, Collection[str]],
    check_skill: Callable[[SkillDef], list[str]] | None = None,
) -> WorldEconomy:
    """載入 ``world/economy.yaml``、``world/items.yaml``、``world/shops/``；不存在＝空。

    ``regions`` 是有地點圖的區域；``check_skill`` 是內容庫給的技能引用與費用檢查（道具技能和
    ``content/skills/`` 同一套）。"""
    rules_path = root / ECONOMY_FILE
    rules: EconomyRules | None = None
    if rules_path.is_file():
        rules = load_content_file(rules_path, EconomyRules)
        files.append((rules_path, rules))
    items_path = root / ITEMS_FILE
    items: dict[str, WorldItemDef] = {}
    if items_path.is_file():
        table = load_content_file(items_path, WorldItemTable)
        problems = [
            f"物品 {i.id} 的區域 {i.region} 沒有地點圖"
            for i in table.items
            if i.region is not None and i.region not in regions
        ]
        if check_skill is not None:
            for item in table.items:
                if item.skill is not None:
                    problems += [f"物品 {item.id} 的道具技能：{p}" for p in check_skill(item.skill)]
        if problems:
            raise ContentError(items_path, "；".join(problems))
        files.append((items_path, table))
        items = table.item_by_id()
    shops: dict[str, ShopTable] = {}
    directory = root / SHOPS_DIR
    for path in sorted(directory.glob("*.yaml")) if directory.is_dir() else ():
        shop_table = load_content_file(path, ShopTable)
        if shop_table.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {shop_table.region!r}）")
        problems = shop_problems(
            shop_table,
            items,
            has_region=shop_table.region in regions,
            npcs=npcs_by_region.get(shop_table.region),
        )
        if problems:
            raise ContentError(path, "；".join(problems))
        files.append((path, shop_table))
        shops[shop_table.region] = shop_table
    owners: dict[str, str] = {}
    for region, shop_table in sorted(shops.items()):
        for shop in shop_table.shops:
            if shop.id in owners:
                path = directory / f"{region}.yaml"
                raise ContentError(path, f"店 {shop.id} 和 {owners[shop.id]}.yaml 重複")
            owners[shop.id] = region
    return WorldEconomy(rules=rules, items=items, shops=shops)
