"""裝備授予的行為改寫的預算閘門：引擎這一側只查表（E5，玩法交接 4.1.36 待決答覆 2）。

表在規則包裡（:attr:`~trpg.content.library.Ruleset.reshape_gates`），由
:func:`trpg.skillgen.reshape_gate.gate_ruleset` 用技能預算檢查器算好；引擎不能匯入 skillgen。

- 只管 **裝備授予的** 修正技（鍵在 ``UnitState.gear_skills``，E1）的變形規則；自己學的、LLM 產生的
  修正技不受影響。
- 鍵 ``<修正技 ID>|<技能 ID>``（普攻用 ``attack``）；複本鍵 ``~2`` 查原技能。值是變形後的傷害‰，
  ``0``＝這招不能套用（標灰，寫 :data:`GATE_PROBLEM_ZH`）。**查不到的組合也當不能套用**。
- 同一招同時有好幾個裝備授予的變形修正技時，只有依技能鍵排序第一個通過閘門的那個生效（每個的閘門
  是單獨算的，疊起來的總點數沒有算過；保守做法），其他的對這招不套用。

合法動作、預覽、AI 估值與結算都經過 :func:`trpg.engine.modifiers.shaped_skill` 與
:func:`trpg.engine.modifiers.damage_permille`，所以三邊一致。這個模組只讀取狀態。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from trpg.content.library import Ruleset
from trpg.content.skill_copies import base_skill_id

if TYPE_CHECKING:
    from trpg.engine.modifiers import ActiveRule
    from trpg.engine.state import UnitState

__all__ = [
    "ATTACK_TARGET",
    "BLOCKED",
    "FULL",
    "GATE_PROBLEM_ZH",
    "gate_key",
    "gate_permille",
    "gated_rules",
]

ATTACK_TARGET = "attack"
"""普攻在閘門表裡的目標名（技能 ID 不會是這個字：技能 ID 一律以 ``skill_`` 開頭）。"""

FULL = 1000
"""沒有降傷（‰）。"""

BLOCKED = 0
"""這招不能套用。"""

GATE_PROBLEM_ZH = "這招不能套用"
"""預算閘門擋下時的標灰說明（玩法交接 4.1.36 待決答覆 2 原文）。"""

_SEP = "|"


def gate_key(modifier_id: str, target: str) -> str:
    """閘門表的鍵：``<修正技 ID>|<技能 ID 或 attack>``（修正技的複本鍵換回原技能 ID）。"""
    return f"{base_skill_id(modifier_id)}{_SEP}{target}"


def gate_permille(ruleset: Ruleset, modifier_id: str, target: str) -> int:
    """裝備授予的修正技 ``modifier_id`` 套在 ``target`` 上的傷害‰；查不到時 :data:`BLOCKED`。"""
    return ruleset.reshape_gates.get(gate_key(modifier_id, target), BLOCKED)


def gated_rules(
    ruleset: Ruleset, unit: UnitState, target: str, rules: Sequence[ActiveRule]
) -> tuple[list[ActiveRule], int]:
    """``rules``（依技能 ID、規則索引）經過閘門之後還生效的規則與傷害‰。

    不是裝備授予的規則原樣保留；裝備授予的只留第一個通過閘門的修正技（其餘的、被擋下的都拿掉）。
    沒有裝備授予的規則時回傳 ``(rules, FULL)``。"""
    gear = unit.gear_skills
    if not gear or not any(a.skill.id in gear for a in rules):
        return list(rules), FULL
    chosen: str | None = None
    permille = FULL
    for active in rules:
        key = active.skill.id
        if key in gear and chosen is None:
            found = gate_permille(ruleset, key, target)
            if found != BLOCKED:
                chosen, permille = key, found
    kept = [a for a in rules if a.skill.id not in gear or a.skill.id == chosen]
    return kept, permille
