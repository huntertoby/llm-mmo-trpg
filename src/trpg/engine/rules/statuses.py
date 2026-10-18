"""狀態的數值效果（Phase 2B-1，``content/statuses.yaml`` 的 ``move_permille`` 等欄位）。

移動點數、傷害與治療的狀態倍率各自集中在這裡，引擎其他地方不直接判斷狀態 ID。
同一欄位有多個狀態時依序相乘，每一步以千分比整數運算並無條件捨去（目前每個欄位只有一個狀態
會改變它）。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.battle import StatusDef
from trpg.content.library import Ruleset
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute, UnitId

__all__ = [
    "base_attribute",
    "boss_converted_status",
    "damage_dealt_permille",
    "damage_taken_permille",
    "effective_attribute",
    "forced_target_sources",
    "healing_received_permille",
    "is_rooted",
    "move_points_for_turn",
    "shield_amount",
    "skip_turn_status",
]

PERMILLE = 1000
BOSS_TAG = "boss"


def boss_converted_status(rules: Ruleset, unit: UnitState, status_id: str) -> str:
    """帶 ``boss`` 標籤的單位被施加 ``control_group: hard`` 的狀態時改施加的狀態
    （``boss_control_conversion``）；不需要轉換時回傳原狀態。所有來源共用。"""
    if rules.status_def(status_id).control_group == "hard" and unit.has_tag(BOSS_TAG):
        return rules.core.boss_control_conversion.get(status_id, status_id)
    return status_id


def _combined(rules: Ruleset, unit: UnitState, field: Callable[[StatusDef], int]) -> int:
    value = PERMILLE
    for status in unit.statuses:  # 狀態清單依狀態 ID 排序，順序確定
        value = value * field(rules.status_def(status.status_id)) // PERMILLE
    return value


def move_points_for_turn(rules: Ruleset, unit: UnitState) -> int:
    """回合開始時的移動點數：速度 × 各狀態的 ``move_permille``，無條件捨去（緩速 ×50%）。"""
    return unit.speed * _combined(rules, unit, lambda d: d.move_permille) // PERMILLE


def is_rooted(rules: Ruleset, unit: UnitState) -> bool:
    """是否帶有 ``prevents_move`` 的狀態（定身）：不能主動移動，強制位移照常。"""
    return any(rules.status_def(s.status_id).prevents_move for s in unit.statuses)


def skip_turn_status(rules: Ruleset, unit: UnitState) -> str | None:
    """讓單位跳過回合的狀態 ID（暈眩）；沒有時為 ``None``。同時也代表不能執行反應。"""
    for status in unit.statuses:
        if rules.status_def(status.status_id).skip_turn:
            return status.status_id
    return None


def damage_dealt_permille(rules: Ruleset, unit: UnitState) -> int:
    """自己造成的攻擊傷害倍率（‰；虛弱 750）。"""
    return _combined(rules, unit, lambda d: d.damage_dealt_permille)


def damage_taken_permille(rules: Ruleset, unit: UnitState) -> int:
    """受到的骰值傷害倍率（‰；易傷 1250）。"""
    return _combined(rules, unit, lambda d: d.damage_taken_permille)


def healing_received_permille(rules: Ruleset, unit: UnitState) -> int:
    """受到的治療倍率（‰；中毒 500）。"""
    return _combined(rules, unit, lambda d: d.healing_received_permille)


def effective_attribute(rules: Ruleset, unit: UnitState, attr: Attribute) -> int:
    """有效屬性 ＝ 基礎屬性 ＋ 所有狀態的 ``attr_bonus``（Phase 2D-1，激昂 +2）。

    引擎內所有用到屬性的判定（命中比例、防禦值、抵抗與對抗判定、傷害／治療／護盾的屬性縮放）
    都經過這裡；**先攻** 在戰鬥開始時擲，用基礎屬性（``tests/engine/test_effective_attribute.py``
    掃描原始碼確認沒有其他地方直接讀 ``.attributes[``）。
    """
    value = unit.attributes[attr]
    for status in unit.statuses:
        value += rules.status_def(status.status_id).attr_bonus.get(attr, 0)
    return value


def base_attribute(unit: UnitState, attr: Attribute) -> int:
    """基礎屬性（不含狀態加值）。只有先攻使用——先攻在戰鬥開始時擲，不受狀態影響。"""
    return unit.attributes[attr]


def shield_amount(rules: Ruleset, unit: UnitState) -> int:
    """目前所有護盾（``absorbs_damage``）的吸收量總和。"""
    return sum(
        s.amount or 0
        for s in unit.statuses
        if s.amount is not None and rules.status_def(s.status_id).absorbs_damage
    )


def forced_target_sources(rules: Ruleset, unit: UnitState) -> frozenset[UnitId]:
    """對 ``unit`` 嘲諷（``forces_target``）的狀態來源（嘲諷者）。"""
    return frozenset(
        s.source_id
        for s in unit.statuses
        if s.source_id is not None and rules.status_def(s.status_id).forces_target
    )
