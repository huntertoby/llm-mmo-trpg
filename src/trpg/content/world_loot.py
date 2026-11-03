"""大世界的掉落規則（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.2）。

``content/world/loot.yaml``（:class:`LootRules`）：敵人家族掉材料的機率與對照、沒有家族時的通用料、
裝備掉落率與稀有度權重、裝備回收價（20.1）、系統傭兵的裝備（20.5）、各區的詞條關鍵字偏向（20.2）。
數值是 ``docs/design/20-第一季商店與裝備內容.md`` 的初值；之後只改資料。

跨檔案檢查（區域、單位、詞綴、材料）在 :func:`load_world_loot`。
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Final

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.item_budget import Rarity
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.slots import SLOTS, Slot
from trpg.content.world_economy import WorldItemDef
from trpg.shared.errors import ContentError

__all__ = [
    "LOOT_FILE",
    "GearDropRules",
    "GenericMaterial",
    "LootRules",
    "MercenaryGearRules",
    "RegionLoot",
    "load_world_loot",
    "loot_problems",
]

LOOT_FILE: Final = "world/loot.yaml"
_ITEM_ID = r"^item_[a-z0-9_]+$"
_WEAPON_SLOTS: Final = ("main_hand", "off_hand")


def _weights_ok(weights: Mapping[Rarity, int], where: str) -> None:
    if any(w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError(f"{where}：權重不能是負的，合計要大於 0")
    if "legendary" in weights:
        raise ValueError(f"{where}：掉落不產生傳說（8.22.1 第 7 點）")


class GenericMaterial(ContentModel):
    """沒有家族材料的敵人掉的通用料：地點建議等級 ≤ ``max_level`` 的第一筆（代決 5D2-2）。"""

    max_level: int = Field(ge=1)
    item: str = Field(pattern=_ITEM_ID)


class GearDropRules(ContentModel):
    """裝備掉落（20.2）。"""

    battle_permille: int = Field(ge=0, le=1000)
    """沒有精英的一場掉 1 件的機率。"""
    battle_weights: dict[Rarity, int]
    """一般掉落的稀有度權重（普通～稀有）。"""
    elite_epic_permille: int = Field(ge=0, le=1000)
    """陣容有精英：必掉 1 件，這個機率是史詩，否則照 ``battle_weights``。"""
    max_item_level: int = Field(ge=1)
    """物品等級上限（第一季 10，8.26.2）。"""

    @model_validator(mode="after")
    def _check(self) -> GearDropRules:
        _weights_ok(self.battle_weights, "gear.battle_weights")
        return self


class MercenaryGearRules(ContentModel):
    """系統傭兵的裝備（20.5）：``slots`` 裡範本沒穿的欄位穿 ``rarity`` 的系統裝備。"""

    rarity: Rarity = "rare"
    slots: tuple[Slot, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> MercenaryGearRules:
        bad = [s for s in self.slots if s in _WEAPON_SLOTS]
        if bad:
            raise ValueError(f"mercenary_gear.slots 不能有主手、副手（代決 5D2-9）：{bad}")
        if len(set(self.slots)) != len(self.slots):
            raise ValueError("mercenary_gear.slots 不能重複")
        if self.rarity == "legendary":
            raise ValueError("mercenary_gear.rarity 不能是傳說")
        return self

    def ordered_slots(self) -> tuple[Slot, ...]:
        """依欄位固定順序（8.23）。"""
        return tuple(s for s in SLOTS if s in self.slots)


class BossLoot(ContentModel):
    """區域 Boss 的保底掉落（Phase 5F-3；20.2「區域 Boss 必掉 1 件史詩」、19.2.3、18.2.3）：每角色每
    刷新日第一次打倒時，這名 Boss 的材料換成 ``material``、裝備換成 ``gear_rarity``
    （代決 5F3-15）。"""

    material: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    gear_rarity: Rarity = "epic"


class RegionLoot(ContentModel):
    """一個區域的掉落內容。"""

    keywords: tuple[str, ...] = ()
    """詞條偏向的關鍵字（20.2；稀有起的技能強化詞條優先挑這些）。"""
    families: dict[str, str] = Field(default_factory=dict)
    """敵人（單位範本或變體 ID）→ 家族材料（M1、18.2.4）。"""
    elite_affixes: dict[str, str] = Field(default_factory=dict)
    """精英詞綴 → 必掉的稀有材料（例：再生的 → 活血骨）。"""


class LootRules(ContentModel):
    """``content/world/loot.yaml``。"""

    material_permille: int = Field(ge=0, le=1000)
    """每名被擊倒的一般敵人掉 1 份材料的機率（20.2 初值 40%）。"""
    generic_by_level: tuple[GenericMaterial, ...] = Field(min_length=1)
    gear: GearDropRules
    sell_rarity_coef: dict[Rarity, int] = Field(default_factory=dict)
    """20.1 裝備回收＝物品等級 × 係數；沒列的稀有度（傳說）不收。"""
    mercenary_gear: MercenaryGearRules = Field(default_factory=MercenaryGearRules)
    families: dict[str, str] = Field(default_factory=dict)
    """各區共用的敵人 → 家族材料（5D-2b：盜賊各區都掉焦鐵）；區域的 ``families`` 優先。"""
    regions: dict[str, RegionLoot] = Field(default_factory=dict)
    bosses: dict[str, BossLoot] = Field(default_factory=dict)
    """區域 Boss（單位範本 ID）→ 保底掉落（Phase 5F-3）。"""

    @model_validator(mode="after")
    def _check(self) -> LootRules:
        levels = [g.max_level for g in self.generic_by_level]
        if levels != sorted(set(levels)):
            raise ValueError("generic_by_level 的 max_level 必須遞增且不重複")
        if any(v < 1 for v in self.sell_rarity_coef.values()):
            raise ValueError("sell_rarity_coef 的係數至少 1")
        bad = sorted(r for r in self.regions if not _is_id(r))
        if bad:
            raise ValueError(f"regions 的區域 ID 格式不對：{bad}")
        return self

    def generic_material(self, level: int) -> str:
        """地點建議等級 ``level`` 的通用料（超過最後一筆時用最後一筆）。"""
        for row in self.generic_by_level:
            if level <= row.max_level:
                return row.item
        return self.generic_by_level[-1].item

    def region(self, region: str) -> RegionLoot:
        return self.regions.get(region, RegionLoot())

    def family_material(self, region: str, unit: str) -> str | None:
        """敵人的家族材料：區域的 ``families`` 優先，其次各區共用的；都沒有時為 ``None``。"""
        return self.region(region).families.get(unit) or self.families.get(unit)

    def sell_price(self, rarity: str | None, item_level: int | None) -> int | None:
        """裝備回收價；不收時為 ``None``（代決 5D2-8）。"""
        if rarity is None or item_level is None:
            return None
        coef = self.sell_rarity_coef.get(rarity)  # type: ignore[call-overload]
        return None if coef is None else item_level * coef


def _is_id(value: str) -> bool:
    return re.fullmatch(ID_PATTERN, value) is not None


def loot_problems(
    rules: LootRules,
    *,
    regions: Collection[str],
    units: Collection[str] | None,
    affixes: Collection[str] | None,
    items: Mapping[str, WorldItemDef],
    keywords: Collection[str] | None = None,
) -> list[str]:
    """跨檔案問題（27.2；依區域、鍵排序）。``units``／``affixes`` 為 ``None``＝沒有
    ``world/enemies.yaml``（變體與詞綴不明），不檢查敵人與詞綴；``keywords``（關鍵字推導表的 ID，
    5D-2b）為 ``None``＝不檢查區域的偏向關鍵字。"""
    problems: list[str] = []

    def material(item: str, where: str) -> None:
        found = items.get(item)
        if found is None:
            problems.append(f"{where}：{item} 不在 world/items.yaml")
        elif found.kind != "material":
            problems.append(f"{where}：{item} 不是材料")

    for row in rules.generic_by_level:
        material(row.item, "generic_by_level")
    for unit, boss in sorted(rules.bosses.items()):  # 5F-3
        material(boss.material, f"bosses.{unit}")
    known = set(rules.bosses) if units is None else set(units)
    problems += [f"bosses：未知的敵人 {u}" for u in sorted(rules.bosses) if u not in known]
    for unit, item in sorted(rules.families.items()):
        if units is not None and unit not in units:
            problems.append(f"families：未知的敵人 {unit}")
        material(item, f"families.{unit}")
    for region, loot in sorted(rules.regions.items()):
        where = f"區域 {region}"
        if region not in regions:
            problems.append(f"{where}：沒有地點圖")
        unknown = sorted(k for k in loot.keywords if keywords is not None and k not in keywords)
        if unknown:
            problems.append(f"{where} 的 keywords：未知的關鍵字 {unknown}")
        for unit, item in sorted(loot.families.items()):
            if units is not None and unit not in units:
                problems.append(f"{where} 的 families：未知的敵人 {unit}")
            material(item, f"{where} 的 families.{unit}")
        for affix, item in sorted(loot.elite_affixes.items()):
            if affixes is not None and affix not in affixes:
                problems.append(f"{where} 的 elite_affixes：未知的精英詞綴 {affix}")
            material(item, f"{where} 的 elite_affixes.{affix}")
    return problems


def load_world_loot(
    root: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    regions: Collection[str],
    units: Collection[str] | None,
    affixes: Collection[str] | None,
    items: Mapping[str, WorldItemDef],
    keywords: Collection[str] | None = None,
) -> LootRules | None:
    """載入 ``world/loot.yaml``；不存在＝``None``（掉落關閉）。``units`` 是單位範本與變體 ID。"""
    path = root / LOOT_FILE
    if not path.is_file():
        return None
    rules = load_content_file(path, LootRules)
    problems = loot_problems(
        rules, regions=regions, units=units, affixes=affixes, items=items, keywords=keywords
    )
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, rules))
    return rules
