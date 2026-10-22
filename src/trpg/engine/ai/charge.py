"""裝備充能啟動的評分（Phase 3G-G3a，``docs/design/08-裝備.md`` 8.21.2.7）。

啟動一條充能詞條（``ActivateCharge``）用一般的預覽計分（傷害、擊倒都在預覽的事件裡），
作用在自己的增益效果（例如 ``empowered``）另外依 ``ally_status_values`` 估值，最後乘上
``basic.charge_permille``（低權重）：AI 會啟動，但通常排在一般攻擊與技能之後。收益不是正數時不調整。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import AiProfile, BasicActionAiRules
from trpg.engine.actions import ActivateCharge
from trpg.engine.gear_charge import find_charge
from trpg.engine.state import BattleState

__all__ = ["charge_score"]

_DEFAULT_BUFF_VALUE = 3
"""``ally_status_values`` 沒列出的增益的估值（同淨化的預設）。"""


def charge_score(
    state: BattleState,
    action: ActivateCharge,
    base: Fraction,
    profile: AiProfile,
    basic: BasicActionAiRules,
) -> Fraction:
    """``base``（預覽分數）加上自我增益的價值，再乘上低權重。"""
    affix = find_charge(state.units[action.unit_id], action.affix_id)
    score = base
    if affix is not None and affix.effect_target == "self":
        for spec in affix.effects:
            if spec.type == "apply_status" and spec.status is not None:
                value = profile.ally_status_values.get(spec.status, _DEFAULT_BUFF_VALUE)
                score += profile.weights.support * value * (spec.duration or 1)
    if score <= 0:
        return score
    return score * basic.charge_permille / 1000
