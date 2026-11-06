"""被動觸發的共用型別與常數（Phase R3 自 :mod:`trpg.engine.skill_triggers` 抽出）。

不匯入其他引擎模組。

:class:`Fired` 由被動技能、裝備詞條、修正規則、層數自動累積（:mod:`trpg.engine.stack_gain`）與
延遲段共用；放在這個葉模組，收集端不必匯入整個 ``skill_triggers``。
:mod:`trpg.engine.skill_triggers` 照舊轉出這裡的名稱。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.shared.types import UnitId

__all__ = ["GEAR_ATTACK_RUNE", "GEAR_PREFIX", "MODIFIER_ON_HIT", "Fired"]

GEAR_PREFIX = "gear:"
"""裝備詞條的 ``Fired.event`` 前綴（``gear:<觸發時機>``；``Fired.skill_id`` 為詞條 ID）。"""

GEAR_ATTACK_RUNE = "attack_rune"
"""普攻符文詞條（Phase 3-31，``rune: detonate／inscribe``）的觸發時機名稱（``Fired.event`` 為
``gear:attack_rune``；``gear_triggered.trigger`` 也用它）。"""

MODIFIER_ON_HIT = "modifier_on_hit"
"""修正規則命中後效果的 ``SkillTriggered.trigger``（不是 ``skill_triggers.yaml`` 的時機）。"""


@dataclass(frozen=True, slots=True)
class Fired:
    """一筆待結算的觸發：``seq`` 是引起它的事件順序（直接呼叫時為當下的事件序號）。"""

    seq: int
    owner_id: UnitId
    skill_id: str
    event: str
    other_id: UnitId | None
    depth: int
