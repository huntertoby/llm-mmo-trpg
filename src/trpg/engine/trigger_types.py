"""被動觸發的共用型別與常數（Phase R3 自 :mod:`trpg.engine.skill_triggers` 抽出）。

不匯入其他引擎模組。

:class:`Fired` 由被動技能、裝備詞條、修正規則、層數自動累積（:mod:`trpg.engine.stack_gain`）與
延遲段共用；放在這個葉模組，收集端不必匯入整個 ``skill_triggers``。
:mod:`trpg.engine.skill_triggers` 照舊轉出這裡的名稱。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.shared.types import UnitId

__all__ = ["GEAR_ATTACK_RUNE", "GEAR_PREFIX", "MODIFIER_ON_HIT", "AttackInfo", "Fired"]

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
    element: str | None = None
    """E4 的元素篩選（命中時、暴擊時）：要求這次攻擊對另一方實際造成這個元素的傷害（轉換以後的）。
    命中判定時還不知道傷害的元素，所以等這一批結算時才對照 ``Ctx.dealt_elements``；
    ``None``＝不篩。"""


@dataclass(frozen=True, slots=True)
class AttackInfo:
    """目前這次攻擊的種類（E4，08 8.29 E4 第 6 點；存在 ``Ctx.attack_info``，不寫進事件）。

    - ``kind``：``melee``（和格擋同一套：普攻看武器射程、技能看技能自己的近戰判定）、``spell``
      （不是近戰的法術技）、``ranged``（其他）。
    - ``source``：``attack``（自己回合的普攻）、``skill``（技能，含被動、陷阱觸發的施放）、
      ``reaction``（反應攻擊與反應技）。
    - ``reaction``：反應的 ID（內建反應攻擊是 ``reactions.yaml`` 的 ID、反應技是技能 ID；
      召喚物反咬這類沒有反應規則的反應攻擊為 ``None``）。
    """

    attacker_id: UnitId
    kind: str
    source: str
    reaction: str | None = None
