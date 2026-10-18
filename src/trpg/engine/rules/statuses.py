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

__all__ = [
    "damage_dealt_permille",
    "damage_taken_permille",
    "healing_received_permille",
    "is_rooted",
    "move_points_for_turn",
    "skip_turn_status",
]

PERMILLE = 1000


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
