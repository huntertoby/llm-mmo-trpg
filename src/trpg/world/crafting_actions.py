"""鐵匠與附魔台的世界動作與事件（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.4）。

放在獨立模組，由 :mod:`trpg.world.actions` 併進 ``WorldAction``／``WorldEvent`` 聯集（不匯入
``actions``，避免循環）。規則在 :mod:`trpg.world.crafting`。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.slots import SlotType

__all__ = [
    "AffixChangedEvent",
    "CraftAction",
    "EnhanceAction",
    "GearCraftedEvent",
    "GearEnhancedEvent",
    "GearSalvagedEvent",
    "ImbueAction",
    "RerollAction",
    "SalvageAction",
]

_ITEM_ID = r"^item_[a-z0-9_]+$"
_AFFIX_ID = r"^affix_[a-z0-9_]+$"
CODE_PATTERN = r"^[0-9a-fA-F]{10}$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


class CraftAction(_Model):
    """在鐵匠打造（8.13、8.20）：給配方的各欄，或只給 ``code``（世界記得的配方碼）。"""

    kind: Literal["craft"] = "craft"
    station: str = Field(pattern=ID_PATTERN)
    code: str | None = Field(default=None, pattern=CODE_PATTERN)
    slot_type: SlotType | None = None
    rarity: Literal["rare", "epic"] | None = None
    affix: str | None = Field(default=None, pattern=_AFFIX_ID)
    """build 詞條（隱藏配方時不用）。"""
    grade: str | None = Field(default=None, pattern=_ITEM_ID)
    """通用料（粗、精、上料；決定物品等級上限）。"""
    materials: tuple[str, ...] = Field(default=(), max_length=5)
    """特色材料（每種 1 個；決定其餘詞條的傾向）。"""
    item_level: int | None = Field(default=None, ge=1, le=99)
    """``None``＝能打的最高等級（角色等級與通用料上限取小的）。"""

    @model_validator(mode="after")
    def _check(self) -> CraftAction:
        fields = (self.slot_type, self.rarity, self.grade)
        if self.code is not None and (any(f is not None for f in fields) or self.materials):
            raise ValueError("用配方碼打造時不能再給部位、稀有度、材料")
        if self.code is None and any(f is None for f in fields):
            raise ValueError("打造要給部位、稀有度與通用料（或給配方碼）")
        return self


class EnhanceAction(_Model):
    """在鐵匠強化一件裝備（背包或穿戴中；+1，最多 +3，8.14）。"""

    kind: Literal["enhance"] = "enhance"
    station: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=ID_PATTERN)


class RerollAction(_Model):
    """在附魔台重骰一條詞條（8.20：由「指紋＋位置＋n」決定；越骰越貴）。"""

    kind: Literal["reroll"] = "reroll"
    station: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=ID_PATTERN)
    index: int = Field(ge=0, le=7)


class ImbueAction(_Model):
    """在附魔台花精華把一條詞條指定成 ``affix``（8.20「完全沒有隨機」）。"""

    kind: Literal["imbue"] = "imbue"
    station: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=ID_PATTERN)
    index: int = Field(ge=0, le=7)
    affix: str = Field(pattern=_AFFIX_ID)


class SalvageAction(_Model):
    """在鐵匠分解背包裡的一件裝備，得到精華（8.14）。"""

    kind: Literal["salvage"] = "salvage"
    station: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=ID_PATTERN)


# ---------------------------------------------------------------------------
# 事件
# ---------------------------------------------------------------------------


class GearCraftedEvent(_Model):
    """打造完成（M6：``discovered``＝這次是首位發現者）。"""

    kind: Literal["gear_crafted"] = "gear_crafted"
    station: str
    code: str
    item: str
    name_zh: str
    slot_type: str
    rarity: str
    item_level: int
    spent: dict[str, int] = Field(default_factory=dict)
    """用掉的材料（物品 → 個數）。"""
    gold_spent: int = 0
    quest_coins_spent: int = 0
    hidden: str | None = None
    """隱藏配方的 ID（M7）。"""
    discovered: bool = False
    discoverer_name: str = ""


class GearEnhancedEvent(_Model):
    kind: Literal["gear_enhanced"] = "gear_enhanced"
    item: str
    name_zh: str
    level: int
    spent: dict[str, int] = Field(default_factory=dict)
    gold_spent: int = 0


class AffixChangedEvent(_Model):
    """重骰（``reroll``）或指定（``imbue``）一條詞條。"""

    kind: Literal["affix_changed"] = "affix_changed"
    mode: Literal["reroll", "imbue"]
    item: str
    name_zh: str
    index: int
    old: str
    new: str
    value: int | None = None
    gold_spent: int = 0
    essence_spent: int = 0
    code: str | None = None
    """改完後這件的配方碼（打造品才有；5D-3b 配方＝基礎配方＋重骰序列）。"""
    discovered: bool = False
    """這份帶序列的配方是不是第一次出現（首位發現者，M6）。"""


class GearSalvagedEvent(_Model):
    kind: Literal["gear_salvaged"] = "gear_salvaged"
    item: str
    name_zh: str
    essence: int
