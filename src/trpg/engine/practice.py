"""靶場測試模式（#147，``docs/design/21-探索地圖與城鎮.md`` 21.5）：判定用的純查詢。

規則只有帶 :class:`PracticeRules` 開場的戰鬥才生效（``BattleSetup.practice`` →
``BattleState.practice``）；``None`` 的戰鬥每個分支都不走。旗標不放 ``Ruleset``，規則包雜湊不變。

- 主角（:func:`is_practice_hero`）：我方的非召喚物。
- 木樁（:func:`is_practice_target`）：帶 ``target_tag`` 標籤的單位。必中看目標，不看攻擊者。

資源補滿與自動過輪在 :mod:`trpg.engine.turns`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from trpg.shared.types import Team

if TYPE_CHECKING:
    from trpg.engine.state import BattleState, UnitState

__all__ = [
    "PASS_ROUND_ACTIONS",
    "PracticeRules",
    "hold_standing",
    "is_practice_hero",
    "is_practice_target",
]

PASS_ROUND_ACTIONS = frozenset({"attack", "use_skill", "use_race_skill"})
"""主角做完會自動過一輪的動作：放招（含種族技）與普攻。推撞、絆摔等基本動作不過輪。"""


class PracticeRules(BaseModel):
    """靶場測試模式的設定（可序列化，隨 ``BattleLog`` 存下，重播不依賴資料檔）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_tag: str = "training_dummy"
    """木樁的單位標籤：必中、對抗必成、HP 歸 0 不倒下只對帶這個標籤的單位生效。"""


def is_practice_target(state: BattleState, unit: UnitState) -> bool:
    """測試模式中的木樁。"""
    rules = state.practice
    return rules is not None and unit.has_tag(rules.target_tag)


def is_practice_hero(state: BattleState, unit: UnitState) -> bool:
    """測試模式中的主角：我方的非召喚物。"""
    return state.practice is not None and unit.team is Team.ALLY and not unit.is_summon


def hold_standing(state: BattleState, unit: UnitState) -> None:
    """測試模式：主角與木樁 HP 歸 0 時改成 1（不倒下）。其他單位與實戰不受影響。"""
    if unit.hp <= 0 and (is_practice_hero(state, unit) or is_practice_target(state, unit)):
        unit.hp = 1
