"""普攻變形（E5，#175，``docs/design/08-裝備.md`` 8.29 E5 第 3～6 點）。

修正規則 ``attack_shape: line`` 讓持有者 **自己回合的主動普攻** 變成 2 格直線：

- 只限近戰、射程 1 的武器（:func:`suits_line`）。矛、鞭本來就打 2 格，遠程武器與法器打不出
  「從自己旁邊那格起」的直線，都不能套用（裝備卡標灰，寫 :data:`WEAPON_PROBLEM_ZH`）。
- 從自己旁邊那格（＝普攻的目標那格）起，往目標方向打 :data:`ATTACK_LINE_LENGTH` 格
  （:func:`attack_line_tiles`）；出界或視線被擋（牆）就停。
- 只打敵人：隊友站在線上不會受傷，也不會擋住後面的敵人（:func:`attack_line_extras`）。
- 藉機攻擊、監視射擊、反擊等反應攻擊照舊打單體（呼叫端 ``perform_unit_attack`` 只在
  ``primary and not reaction`` 時展開）。

合法動作（目標仍是相鄰的敵人，所以不必改 ``legal_actions``）、預覽與 AI 估值（都跑同一個
``perform_unit_attack`` 的模擬）、網頁的範圍顯示都用這裡的函式，三邊一致。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.battle import WeaponDef
from trpg.engine import modifiers
from trpg.engine.rules.footprint import strike_tiles
from trpg.engine.rules.geometry import XY, has_line_of_sight
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "ATTACK_LINE_LENGTH",
    "FULL_PERMILLE",
    "LINE",
    "WEAPON_PROBLEM_ZH",
    "AttackShapeState",
    "attack_line_extras",
    "attack_line_tiles",
    "attack_shape_state",
    "line_attack_permille",
    "problem_zh",
    "skill_problem_zh",
    "suits_line",
]

LINE = "line"
"""``attack_shape`` 目前唯一的值。"""

ATTACK_LINE_LENGTH = 2
"""直線的長度（格；8.29 E5 第 3 點「往目標方向打 2 格」，設計定的形狀，不是數值）。"""

WEAPON_PROBLEM_ZH = "這把武器不能套用"
"""拿著不能套用的武器時，裝備卡、技能列的標灰說明（8.29 E5 第 3 點原文）。"""

FULL_PERMILLE = 1000
"""沒有降傷時的倍率（‰）。"""
_PERMILLE = FULL_PERMILLE

PROBLEMS_ZH: dict[str, str] = {"weapon": WEAPON_PROBLEM_ZH}
"""沒有生效的原因 → 標灰的說明。"""


@dataclass(frozen=True, slots=True)
class AttackShapeState:
    """``unit`` 現在的普攻形狀。

    - ``shape``：生效中的形狀（``line``）；``None``＝照舊打單體。
    - ``problem``：有成立的變形規則、但沒有生效的原因：``weapon``（這把武器不能套用）；沒有時
      ``None``。
    - ``damage_permille``：變形後每一下的傷害倍率（‰；預算閘門降傷，沒有降時 1000）。
    """

    shape: str | None
    problem: str | None = None
    damage_permille: int = _PERMILLE


_PLAIN = AttackShapeState(None)


def suits_line(weapon: WeaponDef) -> bool:
    """這把武器能不能套用普攻直線：近戰、射程 1（矛、鞭射程 2 本來就打 2 格；遠程與法器不行）。"""
    return weapon.is_melee and weapon.range == 1


def attack_shape_state(state: BattleState, unit: UnitState) -> AttackShapeState:
    """``unit`` 的普攻形狀（:class:`AttackShapeState`）：沒有成立的 ``attack_shape`` 規則時照舊
    單體；有的話看實際出手的武器（形態中是天生武器）。"""
    rules = modifiers.attack_shape_rules(state, unit)
    if not rules:
        return _PLAIN
    if not suits_line(unit.weapon):
        return AttackShapeState(None, "weapon")
    return AttackShapeState(LINE)


def problem_zh(problem: str | None) -> str | None:
    """:attr:`AttackShapeState.problem` 的中文說明；沒有問題時 ``None``。"""
    return None if problem is None else PROBLEMS_ZH[problem]


def line_attack_permille(state: BattleState, unit: UnitState) -> int | None:
    """普攻直線生效時每一下的傷害倍率（‰）；沒有生效（沒有規則、武器不能套用）時 ``None``。"""
    shaped = attack_shape_state(state, unit)
    return shaped.damage_permille if shaped.shape == LINE else None


def attack_line_tiles(state: BattleState, attacker: UnitState, target: UnitState) -> tuple[XY, ...]:
    """普攻直線打到的格子：從 ``attacker`` 旁邊那格（打中目標的那一格）起，往目標方向
    :data:`ATTACK_LINE_LENGTH` 格；出界或視線被擋就停。目標不相鄰（曼哈頓距離不是 1）時只有
    目標那一格。巨型單位以出招起點與打中的那一格（:func:`strike_tiles`）定方向。"""
    origin, aim = strike_tiles(attacker, target)
    dx, dy = aim[0] - origin[0], aim[1] - origin[1]
    if abs(dx) + abs(dy) != 1:
        return (aim,)
    cells: list[XY] = [aim]
    for step in range(1, ATTACK_LINE_LENGTH):
        cell = (aim[0] + dx * step, aim[1] + dy * step)
        if not state.in_bounds(*cell) or not has_line_of_sight(state, origin, cell):
            break
        cells.append(cell)
    return tuple(cells)


def attack_line_extras(
    state: BattleState, attacker: UnitState, target: UnitState
) -> list[UnitState]:
    """普攻直線上、目標以外的敵人（由近到遠；巨型單位只算一次）：隊友不算、也不擋。"""
    found: list[UnitState] = []
    for cell in attack_line_tiles(state, attacker, target):
        unit = state.unit_at(*cell)
        if (
            unit is not None
            and unit.alive
            and unit.team is not attacker.team
            and unit.id != target.id
            and unit not in found
        ):
            found.append(unit)
    return found


def skill_problem_zh(state: BattleState, unit: UnitState, skill_id: str) -> str | None:
    """修正技 ``skill_id``（技能列的鍵）的普攻變形在 ``unit`` 身上沒有效果的原因（標灰用）：帶
    ``attack_shape`` 規則、但手上的武器不能套用時是 :data:`WEAPON_PROBLEM_ZH`；其他 ``None``。"""
    skill = state.ruleset.skill_def(skill_id)
    if not any(rule.change.attack_shape is not None for rule in skill.modifiers):
        return None
    return None if suits_line(unit.weapon) else WEAPON_PROBLEM_ZH
