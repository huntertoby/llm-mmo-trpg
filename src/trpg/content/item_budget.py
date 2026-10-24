"""物品預算（Phase 3K-1，``docs/design/08-裝備.md`` 8.22、**8.22.1**、8.21.2）。

``content/item_gen.yaml``（:class:`ItemGenRules`）放全部係數；這個模組是 **驗證器**：

- :func:`total_budget`／:func:`slot_budget`／:func:`affix_budget`：物品等級 → 全身預算（表列等級之間
  線性內插、無條件捨去）→ 部位預算（× 部位比例）→ 詞條部分（× 詞條比例）。**和稀有度無關**（08 8.5：
  稀有度不加強度）。
- :func:`affix_points`：一條詞條的點數（:class:`~fractions.Fraction`；數值類照單位價、條件數值再乘
  成立率、其他類別固定點數、代價型取淨值）。
- :func:`item_points`、:func:`item_budget_problems`：一件物品的詞條點數（含普通物品的基礎加成）與
  檢查——點數在詞條預算的 70～100%、每條至少 2 點、條數不超過稀有度上限、類別在稀有度允許的範圍、
  觸發與武器元素詞條每件最多 1 條、基礎加成只在沒有詞條的普通物品上。

條數下限與「稀有起 1 條 build 詞條」是產生器的目標，不是檢查項目：小部位預算不夠時照「每條至少
2 點」下修（08 8.22）。傳說物品（從測試物品挑，08 8.22.1 第 7 點）不檢查。

純函式；不讀亂數、不讀時間。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import WeaponDef
from trpg.content.equipment import (
    AFFIX_CATEGORIES,
    AffixCategory,
    AffixDef,
    AttackAffix,
    ConditionalAffix,
    CostAffix,
    CostStat,
    ItemDef,
    StatAffix,
    StatKind,
    TriggerAffix,
)
from trpg.content.schemas import ContentModel
from trpg.content.slots import SLOT_TYPES, SlotType

__all__ = [
    "RARITIES",
    "RARITY_ZH",
    "BaseBonusRule",
    "BaseStrengthRule",
    "BudgetAnchor",
    "ItemBudget",
    "ItemGenRules",
    "Price",
    "Rarity",
    "RarityRule",
    "RequiredPick",
    "affix_budget",
    "affix_points",
    "base_bonus_points",
    "base_pool",
    "item_base_points",
    "item_budget",
    "item_budget_problems",
    "item_gen_problems",
    "item_points",
    "item_strength",
    "slot_budget",
    "total_budget",
]

_PERMILLE = 1000

type Rarity = Literal["common", "uncommon", "rare", "epic", "legendary"]
RARITIES: tuple[Rarity, ...] = ("common", "uncommon", "rare", "epic", "legendary")
RARITY_ZH: dict[str, str] = {
    "common": "普通",
    "uncommon": "優良",
    "rare": "稀有",
    "epic": "史詩",
    "legendary": "傳說",
}
_GENERATED: tuple[str, ...] = ("common", "uncommon", "rare", "epic")
type ConditionTier = Literal["common", "occasional", "rare"]


class Price(ContentModel):
    """單位價：每 ``per`` 單位 ``points`` 點（‰ 的數值 ``per`` 也是 ‰）。"""

    points: int = Field(ge=1)
    per: int = Field(ge=1)

    def of(self, amount: int) -> Fraction:
        return Fraction(self.points * abs(amount), self.per)


class BudgetAnchor(ContentModel):
    level: int = Field(ge=1)
    total: int = Field(ge=1)


class RarityRule(ContentModel):
    """一個稀有度的詞條條數與可用類別；``required``：要不要 1 條 build 詞條（見
    :attr:`ItemGenRules.required_picks`）。"""

    min_affixes: int = Field(ge=0, le=8)
    max_affixes: int = Field(ge=0, le=8)
    categories: tuple[AffixCategory, ...] = Field(min_length=1)
    required: bool = False

    @model_validator(mode="after")
    def _check(self) -> RarityRule:
        if self.min_affixes > self.max_affixes:
            raise ValueError("min_affixes 不可大於 max_affixes")
        return self


class RequiredPick(ContentModel):
    """「1 條 build 詞條」可以是哪些類別或哪幾條詞條。"""

    categories: tuple[AffixCategory, ...] = ()
    affixes: tuple[str, ...] = ()

    def allows(self, affix: AffixDef) -> bool:
        return affix.category in self.categories or affix.id in self.affixes


class BaseBonusRule(ContentModel):
    """普通物品的基礎加成換算：每 ``points`` 點 ＝ ``permille``‰。"""

    points: int = Field(ge=1)
    permille: int = Field(ge=1)


class BaseStrengthRule(ContentModel):
    """整件物品的基礎份額（3K-2b 起；3K-2c 照 08 8.22 的「基礎：詞條」比例；只用在「預算分數」比較，
    不是預算檢查）。

    某部位、某等級的 **基礎份額池** ＝ 部位預算 − 詞條預算（主手、身體、副手 60%，頭、手、腳 50%，
    項鍊、戒指 0）。**同部位的底材都拿整個池**（08 8.11「同一大類的總預算相同」、8.12「同等級總預算
    相同」，玩法 PM 2026-10-24）；雙手或成對武器佔掉副手，另加副手池。
    """

    fallback_level: int = Field(default=1, ge=1)
    """沒有物品等級的物品（初始裝備、基礎武器）換算份額時用的等級。"""


class ItemGenRules(ContentModel):
    """``content/item_gen.yaml``：物品產生器與物品預算的全部係數（欄位說明見資料檔）。"""

    rarity_weights: dict[Rarity, int]
    total_budget: tuple[BudgetAnchor, ...] = Field(min_length=1)
    slot_permille: dict[SlotType, int]
    affix_permille: dict[SlotType, int]
    min_fill_permille: int = Field(ge=0, le=_PERMILLE)
    min_affix_points: int = Field(ge=1)
    stat_prices: dict[StatKind, Price]
    conditional_prices: dict[Literal["hit", "damage", "defense"], Price]
    condition_rates_permille: dict[ConditionTier, int]
    conditional_rates: dict[str, ConditionTier]
    category_points: dict[AffixCategory, int]
    weapon_element_points: int = Field(ge=1)
    trigger_limit_permille: int = Field(ge=0, le=_PERMILLE)
    cost_prices: dict[CostStat, Price]
    cost_min_points: int = Field(ge=1)
    base_bonus: BaseBonusRule
    base_strength: BaseStrengthRule | None = None
    """整件物品的基礎強度換算（3K-2b）；沒填時預算分數只算詞條與基礎加成。"""
    rarities: dict[str, RarityRule]
    """產生的稀有度（不含傳說：傳說從測試物品挑）。"""
    required_picks: dict[SlotType, RequiredPick]
    weapon_attribute_preference_permille: int = Field(ge=0, le=_PERMILLE)
    max_attempts: int = Field(default=30, ge=1, le=200)
    offer_size: int = Field(default=3, ge=1, le=6)
    """戰後裝備三選一的候選件數（Phase 3K-2，07 7.1）；部位不重複。"""
    offer_attempts: int = Field(default=8, ge=1, le=50)
    """候選的某一件穿不上時（例如傳說物品會超過全身上限）最多重抽幾次。"""

    @model_validator(mode="after")
    def _check(self) -> ItemGenRules:
        if any(w < 0 for w in self.rarity_weights.values()) or not any(
            self.rarity_weights.values()
        ):
            raise ValueError("rarity_weights 不可為負，且至少一個大於 0")
        levels = [a.level for a in self.total_budget]
        if levels != sorted(set(levels)):
            raise ValueError("total_budget 的等級必須由小到大、不重複")
        if any(b.total < a.total for a, b in pairwise(self.total_budget)):
            raise ValueError("total_budget 的預算不可遞減")
        for name, table in (
            ("slot_permille", self.slot_permille),
            ("affix_permille", self.affix_permille),
        ):
            missing = [s for s in SLOT_TYPES if s not in table]
            if missing:
                raise ValueError(f"{name} 缺少部位：{', '.join(missing)}")
        missing_cat = [c for c in AFFIX_CATEGORIES if c not in ("stat", "conditional", "cost")]
        missing_cat = [c for c in missing_cat if c not in self.category_points]
        if missing_cat:
            raise ValueError(f"category_points 缺少類別：{', '.join(missing_cat)}")
        stray = sorted(set(self.rarities) - set(_GENERATED))
        if stray:
            raise ValueError(f"rarities 只能有 {', '.join(_GENERATED)}（多了 {', '.join(stray)}）")
        return self

    def rarity(self, rarity: str) -> RarityRule:
        found = self.rarities.get(rarity)
        if found is None:
            raise KeyError(f"沒有稀有度 {rarity} 的詞條規則")
        return found


# ---------------------------------------------------------------------------
# 預算
# ---------------------------------------------------------------------------


def total_budget(rules: ItemGenRules, item_level: int) -> int:
    """全身預算：表列等級之間線性內插、無條件捨去；第一個表列等級以下取第一筆，最後一個以上沿用
    最後一段的斜率（只有一筆時固定）。"""
    anchors = rules.total_budget
    if item_level <= anchors[0].level or len(anchors) == 1:
        return anchors[0].total if item_level <= anchors[0].level else anchors[-1].total
    for a, b in pairwise(anchors):
        if item_level <= b.level:
            return a.total + (item_level - a.level) * (b.total - a.total) // (b.level - a.level)
    a, b = anchors[-2], anchors[-1]
    return b.total + (item_level - b.level) * (b.total - a.total) // (b.level - a.level)


def slot_budget(rules: ItemGenRules, item_level: int, slot_type: SlotType) -> int:
    """部位預算 ＝ 全身預算 × 部位比例（無條件捨去）。"""
    return total_budget(rules, item_level) * rules.slot_permille[slot_type] // _PERMILLE


def affix_budget(rules: ItemGenRules, item_level: int, slot_type: SlotType) -> int:
    """詞條部分 ＝ 部位預算 × 詞條比例（無條件捨去）；產生器只分配這部分。"""
    return slot_budget(rules, item_level, slot_type) * rules.affix_permille[slot_type] // _PERMILLE


# ---------------------------------------------------------------------------
# 詞條點數
# ---------------------------------------------------------------------------


def _cost_points(rules: ItemGenRules, affix: CostAffix) -> Fraction:
    up = sum((rules.cost_prices[p.stat].of(p.amount) for p in affix.upside), Fraction(0))
    down = sum((rules.cost_prices[p.stat].of(p.amount) for p in affix.downside), Fraction(0))
    return max(Fraction(rules.cost_min_points), up - down)


def affix_points(rules: ItemGenRules, affix: AffixDef, value: int | None) -> Fraction:
    """一條詞條的物品預算點數（8.22.1 第 4 點）。

    - 數值：單位價 × 數值；條件數值：再 × 條件成立率；
    - 代價型：正面 − 負面，至少 ``cost_min_points``；
    - 武器元素詞條：``weapon_element_points``；觸發：類別點數，有每回合／每輪上限再 × 0.7；
    - 其他類別：類別固定點數（數值 ``N`` 不影響點數）。
    """
    if isinstance(affix, StatAffix):
        return rules.stat_prices[affix.stat].of(value or 0)
    if isinstance(affix, ConditionalAffix):
        rate = rules.condition_rates_permille[rules.conditional_rates[affix.id]]
        return rules.conditional_prices[affix.effect].of(value or 0) * Fraction(rate, _PERMILLE)
    if isinstance(affix, CostAffix):
        return _cost_points(rules, affix)
    if isinstance(affix, AttackAffix) and affix.weapon_element is not None:
        return Fraction(rules.weapon_element_points)
    points = Fraction(rules.category_points[affix.category])
    if isinstance(affix, TriggerAffix):  # limit 一定有值（預設每回合 1 次，8.21.5.3）
        points *= Fraction(rules.trigger_limit_permille, _PERMILLE)
    return points


def base_bonus_points(rules: ItemGenRules, permille: int) -> Fraction:
    """普通物品基礎加成的點數（每 ``base_bonus.permille``‰ ＝ ``base_bonus.points`` 點）。"""
    return Fraction(permille * rules.base_bonus.points, rules.base_bonus.permille)


def item_points(rules: ItemGenRules, item: ItemDef, affixes: Mapping[str, AffixDef]) -> Fraction:
    """一件物品的詞條點數合計（含基礎加成）。"""
    total = base_bonus_points(rules, item.base_bonus_permille)
    for roll in item.affixes:
        total += affix_points(rules, affixes[roll.affix], roll.value)
    return total


def base_pool(rules: ItemGenRules, item_level: int, slot_type: SlotType) -> int:
    """基礎份額池 ＝ 部位預算 − 詞條預算（08 8.22 的「基礎：詞條」比例，項鍊、戒指為 0）。"""
    return slot_budget(rules, item_level, slot_type) - affix_budget(rules, item_level, slot_type)


def item_base_points(
    rules: ItemGenRules, item: ItemDef, weapons: Mapping[str, WeaponDef]
) -> Fraction:
    """整件物品的基礎份額點數（3K-2c）：該部位、該物品等級的基礎份額池 × 底材比例
    （見 :class:`BaseStrengthRule`）；沒有 ``base_strength`` 規則時為 0。"""
    rule = rules.base_strength
    if rule is None:
        return Fraction(0)
    level = item.item_level if item.item_level is not None else rule.fallback_level
    pool = Fraction(base_pool(rules, level, item.slot_type))
    if item.slot_type == "weapon":  # 雙手或成對武器佔掉副手，另加副手池（08 8.11）
        weapon = weapons.get(item.weapon or "")
        if weapon is not None and (weapon.two_handed or weapon.paired or item.paired):
            pool += base_pool(rules, level, "offhand")
    return pool


def item_strength(
    rules: ItemGenRules,
    item: ItemDef,
    affixes: Mapping[str, AffixDef],
    weapons: Mapping[str, WeaponDef],
) -> Fraction:
    """預算分數（3K-2b）：詞條點數（含基礎加成）＋整件物品的基礎強度。"""
    return item_points(rules, item, affixes) + item_base_points(rules, item, weapons)


@dataclass(frozen=True, slots=True)
class ItemBudget:
    """一件物品的預算摘要（顯示與 3K-2 的「預算分數」用）。"""

    item_level: int
    budget: int
    """詞條部分的預算。"""
    points: Fraction
    """詞條點數合計（含基礎加成）。"""

    @property
    def fill_permille(self) -> int:
        """點數佔預算的千分比（無條件捨去）；預算 0 時為 0。"""
        if self.budget <= 0:
            return 0
        return int(self.points * _PERMILLE // self.budget)


def item_budget(
    rules: ItemGenRules, item: ItemDef, affixes: Mapping[str, AffixDef]
) -> ItemBudget | None:
    """有物品等級的物品的預算摘要；沒有物品等級時為 ``None``。"""
    if item.item_level is None:
        return None
    budget = affix_budget(rules, item.item_level, item.slot_type)
    return ItemBudget(item.item_level, budget, item_points(rules, item, affixes))


def _fmt(points: Fraction) -> str:
    return str(points.numerator) if points.denominator == 1 else f"{float(points):.2f}"


def _rarity_problems(
    rules: ItemGenRules, item: ItemDef, defs: Sequence[AffixDef], where: str
) -> list[str]:
    rarity = item.rarity or ""
    rule = rules.rarities.get(rarity)
    if rule is None:
        return [f"{where}：未知的稀有度 {rarity}（可用：{', '.join(rules.rarities)}）"]
    problems: list[str] = []
    if len(defs) > rule.max_affixes:
        problems.append(
            f"{where}：{RARITY_ZH[rarity]}最多 {rule.max_affixes} 條詞條（有 {len(defs)} 條）"
        )
    pick = rules.required_picks.get(item.slot_type)
    extra = [a for a in defs if a.category not in rule.categories]
    if len(extra) > 1:
        ids = "、".join(a.id for a in extra)
        problems.append(f"{where}：稀有度類別以外的 build 詞條每件最多 1 條（{ids}）")
    for affix in extra:
        allowed = rule.required and pick is not None and pick.allows(affix)
        if not allowed:
            problems.append(
                f"{where}：{RARITY_ZH[rarity]}物品不能有 {affix.category} 類詞條（{affix.id}）"
            )
    if item.base_bonus_permille and (rarity != "common" or defs):
        problems.append(f"{where}：只有沒有詞條的普通物品能有基礎加成")
    return problems


def item_budget_problems(
    rules: ItemGenRules, item: ItemDef, affixes: Mapping[str, AffixDef]
) -> list[str]:
    """物品預算檢查（8.22.1 第 6 點；繁體中文，空串列為通過）。傳說物品不檢查（第一版從測試物品
    挑）；沒有物品等級的物品無法檢查（回報問題）。白名單、可掛的部位與數值範圍由
    :func:`~trpg.content.equipment.item_problems` 另外檢查。"""
    where = f"物品 {item.id}"
    if item.legendary or item.rarity == "legendary":
        return []
    if item.item_level is None:
        return [f"{where}：沒有物品等級，無法檢查物品預算"]
    unknown = [r.affix for r in item.affixes if r.affix not in affixes]
    if unknown:
        return [f"{where}：未知的詞條 {', '.join(unknown)}"]
    defs = [affixes[r.affix] for r in item.affixes]
    problems = _rarity_problems(rules, item, defs, where)
    budget = affix_budget(rules, item.item_level, item.slot_type)
    points = item_points(rules, item, affixes)
    low = Fraction(budget * rules.min_fill_permille, _PERMILLE)
    if not low <= points <= budget:
        problems.append(
            f"{where}：詞條點數 {_fmt(points)} 不在預算 {budget} 的 "
            f"{rules.min_fill_permille / 10:g}%～100%（{_fmt(low)}～{budget}）"
        )
    for roll, affix in zip(item.affixes, defs, strict=True):
        each = affix_points(rules, affix, roll.value)
        if each < rules.min_affix_points:
            problems.append(
                f"{where}：詞條 {affix.id} 只有 {_fmt(each)} 點"
                f"（每條至少 {rules.min_affix_points} 點）"
            )
    if sum(1 for a in defs if isinstance(a, TriggerAffix)) > 1:
        problems.append(f"{where}：觸發詞條每件最多 1 條")
    return problems


def item_gen_problems(rules: ItemGenRules, affixes: Mapping[str, AffixDef]) -> list[str]:
    """``item_gen.yaml`` 與詞條白名單的交叉檢查：每條條件數值詞條都有成立率等級、數值與代價型用到
    的單位價都有、``required_picks`` 指名的詞條存在。"""
    problems: list[str] = []
    for affix in affixes.values():
        if isinstance(affix, ConditionalAffix) and affix.id not in rules.conditional_rates:
            problems.append(f"conditional_rates 缺少條件數值詞條 {affix.id}")
        if isinstance(affix, StatAffix) and affix.stat not in rules.stat_prices:
            problems.append(f"stat_prices 缺少 {affix.stat}（詞條 {affix.id}）")
        if isinstance(affix, CostAffix):
            missing = [p.stat for p in affix.parts if p.stat not in rules.cost_prices]
            problems += [f"cost_prices 缺少 {s}（詞條 {affix.id}）" for s in missing]
    stray = sorted(set(rules.conditional_rates) - set(affixes))
    problems += [f"conditional_rates 有未知的詞條 {a}" for a in stray]
    for slot, pick in sorted(rules.required_picks.items()):
        problems += [
            f"required_picks.{slot} 有未知的詞條 {a}" for a in pick.affixes if a not in affixes
        ]
    return problems
