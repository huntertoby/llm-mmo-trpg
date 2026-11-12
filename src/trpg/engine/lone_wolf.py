"""獨狼的開場判定（LW-1，``docs/design/06-技能.md`` 6.37、玩法決定 #156）。

開戰那一刻，單位的陣營除了自己以外沒有其他**非召喚**單位，就是「獨狼」；**整場固定**，記在
:attr:`~trpg.engine.state.UnitState.lone_wolf`，之後隊友倒下、撤離或有單位加入都不改。

- 不算隊友：召喚物與分身（``owner_id`` 不為 ``None``）、其他陣營（含三方混戰的第三方）。
- 算隊友：同陣營的其他單位——系統傭兵、朋友的影子、劇情夥伴、其他玩家都是開場就在場的同陣營單位。
- 影子被借出時，身邊一定有招募者（同陣營），所以一律不成立；賽季影子循環賽（單挑）照判定成立。

判定只看開場狀態、不擲骰；結果只在 ``lone_wolf`` 條件（技能、被動、反應、裝備詞條）讀取。
"""

from __future__ import annotations

from trpg.engine.state import BattleState

__all__ = ["mark_lone_wolves"]


def mark_lone_wolves(state: BattleState) -> None:
    """開場（單位都放好、還沒有任何召喚之前）替每個單位記下是不是獨狼。"""
    units = state.units_sorted()
    for unit in units:
        unit.lone_wolf = not unit.is_summon and not any(
            other.id != unit.id and other.team is unit.team and not other.is_summon
            for other in units
        )
