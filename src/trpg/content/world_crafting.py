"""大世界的鐵匠與附魔台、裝備共鳴（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.2）。

- ``content/world/crafting.yaml``（:class:`CraftingRules`）：設施（鐵匠、附魔台）、打造的費用與材料
  用量、特色材料的傾向（M2）與共鳴關鍵字、隱藏配方（M7）、強化、重骰、指定、分解。
- ``content/world/resonance.yaml``（:class:`ResonanceRules`）：2 件共鳴（M3）的效果（現成詞條）。
- 隱藏配方的提示（5D-3b，20.4；:class:`RecipeHint`）：只說材料的意象。提示所在區域還沒有地點圖時
  （灰燼荒原）先不檢查地點，資料放好、接口（:meth:`CraftingRules.hints_at`）留給荒原內容段接上。

數值是開發 PM 定的初值（代決 5D3-*）；之後只改資料。跨檔案檢查在 :func:`load_world_crafting`、
:func:`load_world_resonance`。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.equipment import AffixDef
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.slots import SLOT_TYPES, SlotType
from trpg.content.world_economy import MaterialGrade, WorldItemDef
from trpg.shared.errors import ContentError

__all__ = [
    "CRAFTING_FILE",
    "RESONANCE_FILE",
    "CraftRarity",
    "CraftRarityCost",
    "CraftRules",
    "CraftingRules",
    "EnhanceRules",
    "FlavorMaterial",
    "HiddenRecipe",
    "ModCost",
    "RecipeHint",
    "ResonanceAffix",
    "ResonanceDef",
    "ResonanceRules",
    "StationDef",
    "crafting_problems",
    "load_world_crafting",
    "load_world_resonance",
    "resonance_problems",
]

CRAFTING_FILE: Final = "world/crafting.yaml"
RESONANCE_FILE: Final = "world/resonance.yaml"
_ITEM_ID = r"^item_[a-z0-9_]+$"
_AFFIX_ID = r"^affix_[a-z0-9_]+$"

type CraftRarity = Literal["rare", "epic"]


class StationDef(ContentModel):
    """一個設施：鐵匠（打造、強化、分解）或附魔台（重骰、指定；8.26.1）。"""

    id: str = Field(pattern=ID_PATTERN)
    kind: Literal["smithy", "enchanter"]
    name_zh: str = Field(min_length=1)
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    npc: str | None = Field(default=None, pattern=ID_PATTERN)


class CraftRarityCost(ContentModel):
    """一個稀有度的打造費用：金幣 ``gold_per_level`` × 物品等級＋任務幣（8.15 高階打造）。"""

    gold_per_level: int = Field(ge=0)
    quest_coins: int = Field(default=0, ge=0)


class CraftRules(ContentModel):
    """打造（8.13、8.20、8.26.2）。"""

    rarities: dict[CraftRarity, CraftRarityCost] = Field(min_length=1)
    grade_amount: dict[SlotType, int]
    """部位 → 通用料個數（8.13「材料用量依部位預算比例調整」）。"""
    flavor_max: int = Field(default=3, ge=0, le=5)
    """特色材料最多幾種（每種 1 個）。"""
    leaning_weight: int = Field(default=4, ge=1, le=100)
    """材料傾向的詞條在抽詞條時的權重倍數（M2）。"""
    grade_cap: dict[MaterialGrade, int]
    """通用料的階 → 物品等級上限（8.26.2：粗 3、精 7、上 10）。"""

    @model_validator(mode="after")
    def _check(self) -> CraftRules:
        missing = [s for s in SLOT_TYPES if s not in self.grade_amount]
        if missing:
            raise ValueError(f"craft.grade_amount 缺少部位：{', '.join(missing)}")
        if any(v < 1 for v in self.grade_amount.values()):
            raise ValueError("craft.grade_amount 至少 1")
        caps = [self.grade_cap.get(g) for g in ("coarse", "fine", "superior")]
        if None in caps or caps != sorted(caps):  # type: ignore[type-var]
            raise ValueError("craft.grade_cap 要有 coarse、fine、superior 且遞增")
        return self


class FlavorMaterial(ContentModel):
    """特色材料：抽詞條時的傾向（M2）與打出來的裝備帶的共鳴關鍵字（M3）。"""

    leanings: tuple[str, ...] = ()
    resonance: str | None = Field(default=None, pattern=ID_PATTERN)


class RecipeHint(ContentModel):
    """隱藏配方的一則提示（20.4，5D-3b）：在哪裡聽得到、說什麼（只說材料的意象，不說配方）。

    ``source``：``tavern``＝酒館傳聞、``rumor``＝當地的傳聞（NPC 聊天）。``location`` 是提示出現的
    地點；``region`` 還沒有地點圖時不檢查（等該區內容段）。"""

    source: Literal["tavern", "rumor"]
    region: str = Field(pattern=ID_PATTERN)
    location: str | None = Field(default=None, pattern=ID_PATTERN)
    place_zh: str = Field(min_length=1)
    """顯示用的出處（例：「餘燼集酒館」）。"""
    text_zh: str = Field(min_length=1)


class HiddenRecipe(ContentModel):
    """隱藏配方（M7、20.4）：部位相同＋特色材料組合完全相同 → 獨特裝備。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    slot_type: SlotType
    materials: tuple[str, ...] = Field(min_length=1, max_length=5)
    affix: str = Field(pattern=_AFFIX_ID)
    rarity: CraftRarity = "epic"
    hints: tuple[RecipeHint, ...] = ()
    """提示（20.4；5D-3b）。"""

    @model_validator(mode="after")
    def _check(self) -> HiddenRecipe:
        if len(set(self.materials)) != len(self.materials):
            raise ValueError(f"隱藏配方 {self.id} 的材料重複")
        return self

    def key(self) -> tuple[str, tuple[str, ...]]:
        return self.slot_type, tuple(sorted(self.materials))


class EnhanceRules(ContentModel):
    """強化 +1～+3（8.14）：每級基礎加成 ``step_permille``；金幣 ``gold_per_level`` × 物品等級 ×
    目標等級；通用料（依物品等級的階）× 目標等級。"""

    max_level: int = Field(default=3, ge=1, le=10)
    step_permille: int = Field(default=20, ge=1, le=200)
    gold_per_level: int = Field(default=10, ge=0)


class ModCost(ContentModel):
    """重骰或指定的費用：精華 ``essence`` 個；金幣 ``gold_base`` ＋ ``gold_step`` × 這件已改過
    幾次。"""

    essence: int = Field(ge=0)
    gold_base: int = Field(ge=0)
    gold_step: int = Field(ge=0)

    def gold(self, done: int) -> int:
        return self.gold_base + self.gold_step * done


class CraftingRules(ContentModel):
    """``content/world/crafting.yaml``。"""

    stations: tuple[StationDef, ...] = Field(min_length=1)
    craft: CraftRules
    essence: str = Field(default="item_essence", pattern=_ITEM_ID)
    """精華的物品 ID（分解得到、重骰與指定花掉）。"""
    materials: dict[str, FlavorMaterial] = Field(default_factory=dict)
    hidden: tuple[HiddenRecipe, ...] = ()
    enhance: EnhanceRules = Field(default_factory=EnhanceRules)
    reroll: ModCost
    imbue: ModCost
    salvage: dict[str, int] = Field(default_factory=dict)
    """稀有度 → 分解得到的精華個數；沒列的稀有度（傳說）不能分解。"""

    @model_validator(mode="after")
    def _check(self) -> CraftingRules:
        ids = [s.id for s in self.stations]
        if len(set(ids)) != len(ids):
            raise ValueError("stations 的 ID 重複")
        keys = [h.key() for h in self.hidden]
        if len(set(keys)) != len(keys):
            raise ValueError("hidden 有兩個隱藏配方的部位與材料組合相同")
        hidden_ids = [h.id for h in self.hidden]
        if len(set(hidden_ids)) != len(hidden_ids):
            raise ValueError("hidden 的 ID 重複")
        if any(v < 1 for v in self.salvage.values()):
            raise ValueError("salvage 的精華個數至少 1")
        return self

    def station(self, station_id: str) -> StationDef | None:
        return next((s for s in self.stations if s.id == station_id), None)

    def hidden_for(self, slot_type: str, materials: Collection[str]) -> HiddenRecipe | None:
        key = (slot_type, tuple(sorted(materials)))
        return next((h for h in self.hidden if h.key() == key), None)

    def hints_at(
        self, region: str, location: str | None = None, source: str | None = None
    ) -> tuple[tuple[HiddenRecipe, RecipeHint], ...]:
        """某區（某地點、某種來源）的隱藏配方提示，依資料順序（5D-3b；給酒館與聊天接上用）。"""
        return tuple(
            (h, hint)
            for h in self.hidden
            for hint in h.hints
            if hint.region == region
            and (location is None or hint.location == location)
            and (source is None or hint.source == source)
        )


class ResonanceAffix(ContentModel):
    affix: str = Field(pattern=_AFFIX_ID)
    value: int | None = None


class ResonanceDef(ContentModel):
    """一個關鍵字的共鳴：依序挑第一條掛得上的詞條（8.9）。"""

    keyword: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    affixes: tuple[ResonanceAffix, ...] = Field(min_length=1)


class ResonanceRules(ContentModel):
    """``content/world/resonance.yaml``（M3：第一季只有 2 件門檻）。"""

    pieces: int = Field(default=2, ge=2, le=9)
    resonances: tuple[ResonanceDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ResonanceRules:
        keys = [r.keyword for r in self.resonances]
        if len(set(keys)) != len(keys):
            raise ValueError("resonances 的關鍵字重複")
        return self

    def of(self, keyword: str) -> ResonanceDef | None:
        return next((r for r in self.resonances if r.keyword == keyword), None)


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


def _material_problems(
    rules: CraftingRules,
    items: Mapping[str, WorldItemDef],
    affixes: Mapping[str, AffixDef],
    keywords: Collection[str],
) -> list[str]:
    problems: list[str] = []
    essence = items.get(rules.essence)
    if essence is None or essence.kind != "material":
        problems.append(f"essence：{rules.essence} 不是 world/items.yaml 的材料")
    for item_id, flavor in sorted(rules.materials.items()):
        where = f"materials.{item_id}"
        found = items.get(item_id)
        if found is None or found.kind != "material":
            problems.append(f"{where}：不是 world/items.yaml 的材料")
        elif found.grade is not None:
            problems.append(f"{where}：通用料不能當特色材料")
        problems += [f"{where}：未知的詞條 {a}" for a in flavor.leanings if a not in affixes]
        if flavor.resonance is not None and flavor.resonance not in keywords:
            problems.append(f"{where}：未知的關鍵字 {flavor.resonance}")
    return problems


def crafting_problems(
    rules: CraftingRules,
    *,
    locations: Mapping[str, Mapping[str, str]],
    npcs: Mapping[str, Mapping[str, str]],
    items: Mapping[str, WorldItemDef],
    affixes: Mapping[str, AffixDef],
    keywords: Collection[str],
) -> list[str]:
    """跨檔案問題。``locations``：區域 → 地點 → 地點種類；``npcs``：區域 → NPC → 地點。"""
    problems: list[str] = []
    for station in rules.stations:
        where = f"設施 {station.id}"
        kinds = locations.get(station.region)
        if kinds is None:
            problems.append(f"{where}：區域 {station.region} 沒有地點圖")
            continue
        if station.location not in kinds:
            problems.append(f"{where}：{station.region} 沒有地點 {station.location}")
        if station.npc is not None and station.region in npcs:  # 沒有人設卡檔＝不檢查
            at = npcs[station.region].get(station.npc)
            if at is None:
                problems.append(f"{where}：{station.npc} 不在 {station.region} 的人設卡")
            elif at != station.location:
                problems.append(f"{where}：{station.npc} 不在 {station.location}")
    problems += _material_problems(rules, items, affixes, keywords)
    return problems + _hidden_problems(rules, locations, affixes)


def _hidden_problems(
    rules: CraftingRules,
    locations: Mapping[str, Mapping[str, str]],
    affixes: Mapping[str, AffixDef],
) -> list[str]:
    problems: list[str] = []
    for hidden in rules.hidden:
        where = f"隱藏配方 {hidden.id}"
        for item_id in hidden.materials:
            if item_id not in rules.materials:
                problems.append(f"{where}：{item_id} 不是特色材料（materials）")
        affix = affixes.get(hidden.affix)
        if affix is None:
            problems.append(f"{where}：未知的詞條 {hidden.affix}")
        elif hidden.slot_type not in affix.slots:
            problems.append(f"{where}：{hidden.affix} 不能掛在 {hidden.slot_type}")
        for hint in hidden.hints:  # 區域還沒有地點圖＝等該區內容段（5D-3b）
            kinds = locations.get(hint.region)
            if kinds is not None and hint.location is not None and hint.location not in kinds:
                problems.append(f"{where}：提示的地點 {hint.location} 不在 {hint.region}")
    return problems


def resonance_problems(
    rules: ResonanceRules, *, affixes: Mapping[str, AffixDef], keywords: Collection[str]
) -> list[str]:
    problems: list[str] = []
    for res in rules.resonances:
        where = f"共鳴 {res.keyword}"
        if res.keyword not in keywords:
            problems.append(f"{where}：未知的關鍵字")
        for entry in res.affixes:
            affix = affixes.get(entry.affix)
            if affix is None:
                problems.append(f"{where}：未知的詞條 {entry.affix}")
                continue
            if (affix.value is None) != (entry.value is None):
                problems.append(f"{where}：{entry.affix} 的 value 要和詞條的數值範圍一致")
            elif (
                affix.value is not None
                and entry.value is not None
                and not affix.value.min <= entry.value <= affix.value.max
            ):
                problems.append(f"{where}：{entry.affix} 的 value 超出範圍")
    return problems


def load_world_crafting(
    root: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    locations: Mapping[str, Mapping[str, str]],
    npcs: Mapping[str, Mapping[str, str]],
    items: Mapping[str, WorldItemDef],
    affixes: Mapping[str, AffixDef],
    keywords: Collection[str],
) -> CraftingRules | None:
    """載入 ``world/crafting.yaml``；不存在＝``None``（鐵匠與附魔台關閉）。"""
    path = root / CRAFTING_FILE
    if not path.is_file():
        return None
    rules = load_content_file(path, CraftingRules)
    problems = crafting_problems(
        rules, locations=locations, npcs=npcs, items=items, affixes=affixes, keywords=keywords
    )
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, rules))
    return rules


def load_world_resonance(
    root: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    affixes: Mapping[str, AffixDef],
    keywords: Collection[str],
) -> ResonanceRules | None:
    """載入 ``world/resonance.yaml``；不存在＝``None``（沒有共鳴）。"""
    path = root / RESONANCE_FILE
    if not path.is_file():
        return None
    rules = load_content_file(path, ResonanceRules)
    problems = resonance_problems(rules, affixes=affixes, keywords=keywords)
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, rules))
    return rules
