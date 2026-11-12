"""近戰攻擊不讓目標轉向的兩個例外（BS-1，#157，``docs/design/06-技能.md`` 6.21.1、``05-戰鬥.md``
5.1「朝向與背刺」）。

一般規則：被近戰攻擊（不論命中與否）的單位在那次攻擊結算完後轉向攻擊者
（:func:`trpg.engine.reactions.after_attack`）。例外：

- **B 從隱蔽中出手**（``concealed``）：攻擊者在命中判定當下帶隱蔽。任何武器、敵我都適用；出手後照舊
  脫離隱蔽（潛行偷襲）。
- **C 無聲**（修正規則 ``silent_strike``）：持有者手上拿匕首類（``SILENT_WEAPONS``）時的普攻、
  武器技（``category: weapon``）與反應攻擊。被動與陷阱觸發不是「你的動作」，不受修正規則影響。

兩個都成立時記為隱蔽（B 先判斷）。只管這名攻擊者自己的攻擊：隊友的近戰攻擊、目標在自己回合的移動
與攻擊照常轉向。命中判定的事件 ``attack_rolled`` 帶 ``no_turn``（沒有例外時不輸出）。
"""

from __future__ import annotations

from typing import Literal

from trpg.content.skills import SkillDef
from trpg.engine import modifiers
from trpg.engine.ids import CONCEALED
from trpg.engine.state import BattleState, UnitState

__all__ = ["NoTurn", "no_turn_reason"]

type NoTurn = Literal["concealed", "silent"]
"""目標不轉向的原因：``concealed`` 從隱蔽中出手（B）、``silent`` 無聲（C）。"""


def no_turn_reason(
    state: BattleState,
    attacker: UnitState,
    skill: SkillDef | None = None,
    *,
    modified: bool = True,
) -> NoTurn | None:
    """``attacker`` 這次近戰攻擊（``skill`` 為 ``None`` 是普攻與反應攻擊，否則是施放的技能）的
    目標會不會轉向；``None`` 為照常轉向。呼叫端負責「這是近戰、目標不是自己」。

    ``modified``：這次施放受修正規則影響（主動、姿態、反應技；被動與陷阱觸發為 ``False``）。"""
    if attacker.has_status(CONCEALED):
        return "concealed"
    if not modified:
        return None
    if skill is None:
        use = modifiers.ATTACK
    elif skill.category == "weapon":
        use = modifiers.skill_use(skill)
    else:
        return None
    return "silent" if modifiers.silent_strike(state, attacker, use) else None
