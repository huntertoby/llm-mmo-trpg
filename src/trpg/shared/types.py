"""最基礎的共用型別：ID、格子座標、元素／表面／屬性／稀有度列舉。

只放跨子套件共用的型別；戰鬥狀態模型（單位、格子等）放在 ``trpg.engine.state``。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ELEMENT_RESIST_GROUP",
    "Attribute",
    "BattleId",
    "Element",
    "ItemId",
    "MapId",
    "ObjectId",
    "Pos",
    "Rarity",
    "ResistGroup",
    "SkillId",
    "Surface",
    "Team",
    "UnitId",
    "rune_name",
    "top_attribute",
]

# ---------------------------------------------------------------------------
# ID
# ---------------------------------------------------------------------------

UnitId = NewType("UnitId", str)
ObjectId = NewType("ObjectId", str)
SkillId = NewType("SkillId", str)
ItemId = NewType("ItemId", str)
BattleId = NewType("BattleId", str)
MapId = NewType("MapId", str)

# ---------------------------------------------------------------------------
# 座標
# ---------------------------------------------------------------------------


class Pos(BaseModel):
    """格子座標（不可變、可雜湊）。

    座標系：``x`` 向右遞增、``y`` 向下遞增（與文字網格與螢幕座標一致），原點在左上角。
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    x: int = Field(ge=0)
    y: int = Field(ge=0)

    def neighbors4(self) -> list[Pos]:
        """上下左右四格，固定順序：上（y-1）、右（x+1）、下（y+1）、左（x-1）。

        不檢查地圖邊界；但座標不可為負，所以位於 ``x == 0`` 或 ``y == 0`` 時，
        超出左／上邊緣的那一格會被省略（其餘順序不變）。
        """
        candidates = (
            (self.x, self.y - 1),
            (self.x + 1, self.y),
            (self.x, self.y + 1),
            (self.x - 1, self.y),
        )
        return [Pos(x=x, y=y) for x, y in candidates if x >= 0 and y >= 0]


# ---------------------------------------------------------------------------
# 列舉（值為小寫英文；display_name 為繁體中文顯示名稱）
# ---------------------------------------------------------------------------


class Element(StrEnum):
    """傷害與效果的元素（9 種，見 ``docs/專案計畫.md`` 5.1.1）。水不是元素，只是表面。"""

    PHYSICAL = "physical"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"
    WIND = "wind"
    EARTH = "earth"
    HOLY = "holy"
    SHADOW = "shadow"

    @property
    def display_name(self) -> str:
        return _ELEMENT_NAMES[self]

    @property
    def resist_group(self) -> ResistGroup:
        """此元素所屬的抗性分組。"""
        return ELEMENT_RESIST_GROUP[self]


class ResistGroup(StrEnum):
    """4 組抗性（角色面板只顯示這 4 個數字）。"""

    PHYSICAL = "physical"
    ELEMENTAL = "elemental"
    NATURE = "nature"
    SPIRIT = "spirit"

    @property
    def display_name(self) -> str:
        return _RESIST_GROUP_NAMES[self]


class Surface(StrEnum):
    """格子的表面狀態。"""

    NONE = "none"
    OIL = "oil"
    WATER = "water"
    FIRE = "fire"
    ICE = "ice"
    POISON = "poison"
    HOLY = "holy"
    DARKNESS = "darkness"
    SMOKE = "smoke"

    @property
    def display_name(self) -> str:
        return _SURFACE_NAMES[self]


class Team(StrEnum):
    """戰鬥中的陣營。地圖起始區以此為鍵。"""

    ALLY = "ally"
    ENEMY = "enemy"

    @property
    def display_name(self) -> str:
        return _TEAM_NAMES[self]

    @property
    def opponent(self) -> Team:
        return Team.ENEMY if self is Team.ALLY else Team.ALLY


class Attribute(StrEnum):
    """角色的六屬性（成員名稱用大寫縮寫，避開 ``str``、``int`` 等內建名稱）。"""

    STR = "str"
    DEX = "dex"
    CON = "con"
    INT = "int"
    WIS = "wis"
    WIL = "wil"

    @property
    def display_name(self) -> str:
        return _ATTRIBUTE_NAMES[self]

    @property
    def is_physical(self) -> bool:
        """物理屬性（力量、敏捷、體質）；其餘三個是心智屬性（智力、感知、意志）。雙屬性武器
        同類取較高、一物理一心智取平均（08 8.11，玩法決定 #46）。"""
        return self in (Attribute.STR, Attribute.DEX, Attribute.CON)


def top_attribute(
    attributes: Mapping[Attribute, int], *, exclude: Iterable[Attribute] = ()
) -> Attribute:
    """最高的屬性；**並列時固定取六屬性順序（力量、敏捷、體質、智力、感知、意志）的第一個**
    （Phase 3H-3，``docs/design/07-角色成長.md`` 7.2；確定性）。``exclude`` 內的屬性不參與。"""
    skip = set(exclude)
    pool = [a for a in Attribute if a not in skip]
    best = max(attributes[a] for a in pool)
    return next(a for a in pool if attributes[a] == best)


class Rarity(StrEnum):
    """稀有度（技能與裝備共用）。"""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

    @property
    def display_name(self) -> str:
        return _RARITY_NAMES[self]


_ELEMENT_NAMES: dict[Element, str] = {
    Element.PHYSICAL: "物理",
    Element.FIRE: "火焰",
    Element.ICE: "冰霜",
    Element.LIGHTNING: "雷電",
    Element.POISON: "毒素",
    Element.WIND: "風",
    Element.EARTH: "大地",
    Element.HOLY: "神聖",
    Element.SHADOW: "暗影",
}

_RUNE_ELEMENT_NAMES: dict[Element, str] = {
    Element.PHYSICAL: "刃",
    Element.FIRE: "火",
    Element.ICE: "冰",
    Element.LIGHTNING: "雷",
    Element.POISON: "毒",
    Element.WIND: "風",
    Element.EARTH: "土",
    Element.HOLY: "聖",
    Element.SHADOW: "影",
}


UNKNOWN_RUNE_NAME = "符紋"
"""標籤符文查不到刻印單字時的名稱（Phase 3-41a：不把英文代號拼進名稱）。"""


def rune_name(
    element: Element | None, tag: str | None, tag_runes: Mapping[str, str] | None = None
) -> str:
    """符文的名稱（Phase 3-23），例如「雷紋」「火紋」；標籤符文為「<單字>紋」，單字取
    ``tag_runes``（``content/skill_tags.yaml`` 的 ``rune_zh``），查不到時為「符紋」。"""
    if element is not None:
        return f"{_RUNE_ELEMENT_NAMES[element]}紋"
    rune = (tag_runes or {}).get(tag or "")
    return UNKNOWN_RUNE_NAME if rune is None else f"{rune}紋"


# 對應 docs/專案計畫.md 5.1.1 的「抗性分組」欄
ELEMENT_RESIST_GROUP: dict[Element, ResistGroup] = {
    Element.PHYSICAL: ResistGroup.PHYSICAL,
    Element.FIRE: ResistGroup.ELEMENTAL,
    Element.ICE: ResistGroup.ELEMENTAL,
    Element.LIGHTNING: ResistGroup.ELEMENTAL,
    Element.POISON: ResistGroup.NATURE,
    Element.WIND: ResistGroup.NATURE,
    Element.EARTH: ResistGroup.NATURE,
    Element.HOLY: ResistGroup.SPIRIT,
    Element.SHADOW: ResistGroup.SPIRIT,
}

_RESIST_GROUP_NAMES: dict[ResistGroup, str] = {
    ResistGroup.PHYSICAL: "物理",
    ResistGroup.ELEMENTAL: "元素",
    ResistGroup.NATURE: "自然",
    ResistGroup.SPIRIT: "靈性",
}

_TEAM_NAMES: dict[Team, str] = {
    Team.ALLY: "我方",
    Team.ENEMY: "敵方",
}

_SURFACE_NAMES: dict[Surface, str] = {
    Surface.NONE: "無",
    Surface.OIL: "油",
    Surface.WATER: "水",
    Surface.FIRE: "火焰",
    Surface.ICE: "冰",
    Surface.POISON: "毒",
    Surface.HOLY: "聖光",
    Surface.DARKNESS: "黑暗",
    Surface.SMOKE: "煙霧",
}

# 對應 docs/專案計畫.md 第 7.2 節
_ATTRIBUTE_NAMES: dict[Attribute, str] = {
    Attribute.STR: "力量",
    Attribute.DEX: "敏捷",
    Attribute.CON: "體質",
    Attribute.INT: "智力",
    Attribute.WIS: "感知",
    Attribute.WIL: "意志",
}

# 對應 docs/專案計畫.md 第 8.7 節
_RARITY_NAMES: dict[Rarity, str] = {
    Rarity.COMMON: "普通",
    Rarity.UNCOMMON: "優良",
    Rarity.RARE: "稀有",
    Rarity.EPIC: "史詩",
    Rarity.LEGENDARY: "傳說",
}
