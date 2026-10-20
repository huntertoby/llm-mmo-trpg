"""複合技能（位移 → 動作）的 AI 估計（Phase 3F-3b）。

``legal_actions`` 已把「位移段選取 × 動作段選取」列成一個個 ``UseSkill``，影響範圍是兩段的聯集。
這裡只做便宜的估計（不跑引擎）：影響範圍內的敵人越多越好、誤傷友方扣分、完全沒有敵人就不納入；
平手以落點（動作段的原點）離施放者的距離判定（近者優先，保持確定）。估計只決定誰值得完整預覽
（每個技能只保留前 ``skill_candidates`` 個，所以組合再多也只跑固定次數的 ``preview``）；
值不值得施放、落點是否安全，由預覽的收益與位置價值決定（落點的位置價值包含在 ``preview`` 裡）。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.skills import SkillDef
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState

__all__ = ["composite_estimate"]


def composite_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, area: SkillArea
) -> Fraction | None:
    """複合技能一個選取的估計；影響範圍內沒有敵方單位時為 ``None``（不納入候選）。

    Phase 3F-4a 的四種即時第二段（動作 → 位移、聚集、擊殺、命中）AI 先不使用（一律 ``None``；
    3F-4b 再評估）。"""
    if skill.followup is not None and skill.followup.when != "after_move":
        return None
    enemies = 0
    allies = 0
    for uid in area.units:
        other = state.units[uid]
        if other.id == unit.id:
            continue
        if other.team is unit.team:
            allies += 1
        else:
            enemies += 1
    if enemies == 0:
        return None
    return Fraction(3 * enemies - 3 * allies) - Fraction(manhattan(unit.xy, area.origin), 1000)
