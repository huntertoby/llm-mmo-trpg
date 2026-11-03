"""鐵匠與附魔台的 API 格式（Phase 5D-3；``docs/phases/Phase5計畫.md`` 28.5）。

全部由後端算好（前端不寫規則）：設施、能指定的 build 詞條、費用說明、背包裡的材料與傾向、世界記得的
配方（首位發現者）、可強化／重骰／指定／分解的裝備與不能的原因。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "CraftGearView",
    "CraftMaterialView",
    "CraftOptionView",
    "CraftRarityView",
    "CraftSlotView",
    "CraftingView",
    "GearAffixView",
    "RecipeView",
    "StationView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CraftOptionView(_ApiModel):
    id: str
    text_zh: str


class StationView(_ApiModel):
    station: str
    kind: str
    """``smithy``（打造、強化、分解）或 ``enchanter``（重骰、指定）。"""
    name_zh: str
    npc_name_zh: str | None = None


class CraftSlotView(_ApiModel):
    """一個能打造的部位與能指定的 build 詞條。"""

    slot_type: str
    name_zh: str
    grade_amount: int
    """要幾個通用料。"""
    affixes: tuple[CraftOptionView, ...]


class CraftRarityView(_ApiModel):
    rarity: str
    name_zh: str
    cost_zh: str
    """例「金幣 10 × 物品等級」「金幣 20 × 物品等級＋任務幣 2」。"""


class CraftMaterialView(_ApiModel):
    """背包裡能打造的材料。"""

    item: str
    name_zh: str
    count: int
    grade: bool
    """通用料（決定物品等級上限）；否則是特色材料。"""
    level_cap: int | None = None
    """通用料能打的最高物品等級（角色等級與階的上限取小的）。"""
    leaning_zh: str | None = None
    """特色材料的傾向（M2；例「傾向：敏捷 +n、本回合沒有移動：防禦 +n」）。"""
    resonance_zh: str | None = None
    """打出來的裝備帶的共鳴關鍵字（例「共鳴：隱蔽」）。"""


class RecipeView(_ApiModel):
    """世界記得的一份配方（M6）。"""

    code: str
    """配方碼（大寫）。"""
    name_zh: str
    summary_zh: str
    """部位・稀有度・物品等級・材料。"""
    discoverer_name: str
    mine: bool
    """自己是首位發現者。"""
    can_craft: bool
    problem_zh: str | None = None


class GearAffixView(_ApiModel):
    index: int
    text_zh: str
    can_change: bool
    """可以重骰或指定（獨特詞條、沒有候選時不行）。"""
    choices: tuple[CraftOptionView, ...] = ()
    """指定的候選（詞條 ID 與文字）。"""


class CraftGearView(_ApiModel):
    """背包或穿戴中的一件裝備。"""

    item: str
    name_zh: str
    worn: bool
    description_zh: str
    code: str | None = None
    """打造品的配方碼（大寫）。"""
    enhance: int = 0
    can_enhance: bool = False
    enhance_zh: str | None = None
    """下一級強化的費用（例「強化到 +1：粗料 ×1、金幣 30」）或不能的原因。"""
    can_salvage: bool = False
    salvage_zh: str | None = None
    """分解得到的精華或不能的原因。"""
    reroll_zh: str | None = None
    """重骰一條的費用（例「精華 ×1、金幣 20」）。"""
    imbue_zh: str | None = None
    affixes: tuple[GearAffixView, ...] = ()


class CraftingView(_ApiModel):
    """角色所在地點的鐵匠與附魔台（沒有設施時 ``WorldView.crafting`` 是 ``None``）。"""

    stations: tuple[StationView, ...]
    smithy: str | None
    """這裡的鐵匠 ID。"""
    enchanter: str | None
    can_use: bool
    problem_zh: str | None
    slots: tuple[CraftSlotView, ...]
    rarities: tuple[CraftRarityView, ...]
    materials: tuple[CraftMaterialView, ...]
    flavor_max: int
    recipes: tuple[RecipeView, ...]
    gear: tuple[CraftGearView, ...]
    essence: int
    """背包裡的精華。"""
    note_zh: str
    """M6：沒人試過的材料組合只看得到傾向；第一次打出的人成為首位發現者。"""
