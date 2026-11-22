"""暴擊傷害倍率（CR-1，``docs/design/05-戰鬥.md`` 5.4.2，#178）。

暴擊時照常擲原本的傷害骰，再多擲一組同樣顆數；多擲的那組乘（倍率 − 100%），無條件捨去
（:func:`trpg.engine.rules.combat.crit_extra_total`）。屬性加成、固定值不放大。

倍率由攻擊方在擲骰時算好，放進 :class:`~trpg.engine.effects.models.DamageEffect` 的
``crit_permille``（:func:`crit_damage_permille`）：

1. 基礎：``core.crit_damage.base_permille``（2000‰）。

全部相加，最後套全身上下限 ``core.crit_damage.min_permille``～``max_permille``（150%～300%）。
敵我用同一套規則。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from trpg.content.skills import SkillDef
from trpg.engine.modifiers import Use
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import BattleState, UnitState

__all__ = ["crit_damage_permille"]


def crit_damage_permille(
    state: BattleState,
    unit: UnitState,
    *,
    use: Use | None = None,
    subject: Subject | None = None,
    skill: SkillDef | None = None,
) -> int:
    """``unit`` 這一次攻擊的暴擊傷害倍率（‰，已套全身上下限）。

    ``skill``：施放的技能（普攻為 ``None``）；``use``：受修正規則影響的動作（被動觸發等不受修正的
    施放為 ``None``）；``subject``：這次攻擊的目標（修正規則的條件看它）。"""
    del use, subject, skill  # CR-1 A3 起接上其他來源
    rules = state.ruleset.core.crit_damage
    total = rules.base_permille
    return max(rules.min_permille, min(rules.max_permille, total))
