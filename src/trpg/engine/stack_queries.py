"""層數的純查詢（不改狀態、不結算效果；Phase R3 自 :mod:`trpg.engine.stacks` 抽出）。

:mod:`trpg.engine.stacks` 會結算效果（超載），所以匯入了效果佇列；技能合法性檢查
（:mod:`trpg.engine.skills.targeting`）只需要查詢，從這裡匯入即可，不必依賴效果佇列。
:mod:`trpg.engine.stacks` 照舊轉出 :func:`required_stack`。
"""

from __future__ import annotations

from trpg.content.skills import CONSUME_STACK, SkillDef
from trpg.content.stacks import StackDef
from trpg.engine.state import BattleState

__all__ = ["required_stack"]


def required_stack(state: BattleState, skill: SkillDef) -> StackDef | None:
    """``cost.stacks`` 對應的層數：技能裡第一個 ``owner: self`` 的 ``consume_stack`` 的層數。"""
    if skill.cost.stacks is None:
        return None
    rules = state.ruleset
    for effect in skill.effects:
        if effect.type == CONSUME_STACK and effect.stack is not None:
            definition = rules.stack_def(effect.stack)
            if definition.owner == "self":
                return definition
    return None
