"""單位的裝備狀態（Phase 3G-G1）：開戰時由裝備快照算好、戰鬥中不變的資料。

放在獨立模組，讓 :mod:`trpg.engine.state` 能引用而不循環匯入；計算與查詢在 :mod:`trpg.engine.gear`。

- :class:`GearAffix`：身上每一條詞條（含遞減權重），依詞條 id、再依遞減順序排列。G2、G3 的類別
  （技能強化、普攻附加、觸發、充能、動作、反應、改變規則）從這裡取 **生效中**（``weight_permille``
  ＞ 0）的詞條。
- :class:`GearBonus`：戰鬥中查詢的數值（命中、傷害、防禦、受到的傷害、冷卻、回合開始失去 HP），
  每個「詞條 id × 數值種類」一筆，已經遞減後加總。
- ``merged``：已經併進單位總屬性的加值（屬性、最大 HP、元素抗性、移動），遞減與上限之後；
  ``uncapped`` 是上限之前（顯示「截斷」用）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.equipment import AffixDef
from trpg.content.skills import ConditionSpec

__all__ = ["BonusStat", "GearAffix", "GearBonus", "GearItem", "GearState"]

type BonusStat = Literal[
    "hit",
    "damage_permille",
    "defense_permille",
    "damage_taken_permille",
    "cooldown_delta",
    "turn_start_hp_loss",
]
"""戰鬥中查詢的裝備數值種類。"""


@dataclass(frozen=True, slots=True)
class GearItem:
    """一個欄位上的物品（顯示用）。"""

    slot: str
    item_id: str
    name_zh: str


@dataclass(frozen=True, slots=True)
class GearAffix:
    """身上的一條詞條。

    ``weight_permille``：遞減權重——數值類依同 id 由大到小 1000／500／250／0；非數值類同 id 只有
    第一條 1000、其餘 0（不生效）。``rank``：在同 id 中的順序（0 起）。
    """

    slot: str
    item_id: str
    affix: AffixDef
    value: int | None
    weight_permille: int
    rank: int

    @property
    def active(self) -> bool:
        return self.weight_permille > 0


@dataclass(frozen=True, slots=True)
class GearBonus:
    """一筆戰鬥中查詢的裝備數值（同一詞條 id 遞減後加總）。``condition`` 為 ``None`` 時無條件；
    ``negate`` 時條件 **不** 成立才生效。"""

    affix_id: str
    stat: BonusStat
    amount: int
    condition: ConditionSpec | None = None
    negate: bool = False


@dataclass(frozen=True, slots=True)
class GearState:
    """單位的裝備狀態（沒有裝備時是空的預設值）。``cooldown_min`` 是規則包的冷卻下限（技能付代價時
    沒有規則包可查，所以一起存）。"""

    items: tuple[GearItem, ...] = ()
    affixes: tuple[GearAffix, ...] = ()
    bonuses: tuple[GearBonus, ...] = ()
    merged: tuple[tuple[str, int], ...] = ()
    uncapped: tuple[tuple[str, int], ...] = ()
    cooldown_min: int = 1

    def active_affixes(self, category: str | None = None) -> tuple[GearAffix, ...]:
        """生效中的詞條（``category`` 篩選類別）。"""
        return tuple(
            a
            for a in self.affixes
            if a.active and (category is None or a.affix.category == category)
        )
