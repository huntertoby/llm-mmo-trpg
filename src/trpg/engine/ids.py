"""引擎共用的狀態 ID、標籤與單位 ID 配發（集中定義，各模組不再各自寫字串）。

狀態 ID 必須存在於 ``content/statuses.yaml``、標籤來自單位範本或物件的 ``tags``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.shared.types import UnitId

if TYPE_CHECKING:
    from trpg.engine.state import BattleState

__all__ = [
    "ARMOR_BROKEN",
    "BOSS_TAG",
    "CONCEALED",
    "DEFENDING",
    "ELITE_TAG",
    "FLYING",
    "PENETRABLE",
    "PRONE",
    "REVEALED",
    "SHIELDED",
    "STEADFAST",
    "TOPPLABLE",
    "next_unit_id",
]

# -- 狀態 ID（``statuses.yaml``）----------------------------------------------

ARMOR_BROKEN = "armor_broken"
"""武器 ``armor_break`` 施加的狀態（``defense_break``，Phase 3-24a1）。"""
CONCEALED = "concealed"
"""隱匿。"""
DEFENDING = "defending"
"""防禦姿態。"""
PRONE = "prone"
"""倒地。"""
REVEALED = "revealed"
"""``reveal`` 施加的狀態（``prevents_concealment``）。"""
SHIELDED = "shielded"
"""``shield`` 原語施加的狀態（``absorbs_damage``）。"""

# -- 標籤（單位範本或物件的 ``tags``）------------------------------------------

BOSS_TAG = "boss"
"""首領單位的標籤。"""
ELITE_TAG = "elite"
"""精英單位的標籤（落入致命地形的規則也用它）。"""
FLYING = "flying"
"""會飛的單位標籤（Phase 3-33e2b）：移動無視地形高度差與障礙（不能停在牆內），不受地面表面影響。"""
PENETRABLE = "penetrable"
"""可被穿透攻擊穿過的物件標籤。"""
STEADFAST = "steadfast"
"""堅守單位的標籤：被推擊的距離打折（``core.steadfast_push_permille``）。"""
TOPPLABLE = "topplable"
"""可被推倒的物件標籤。"""


def next_unit_id(state: BattleState) -> UnitId:
    """戰鬥中下一個新單位（召喚物、援軍）的 ID：``unit_`` ＋ 目前單位數 ＋ 1（至少 4 位數）。"""
    return UnitId(f"unit_{len(state.units) + 1:04d}")
