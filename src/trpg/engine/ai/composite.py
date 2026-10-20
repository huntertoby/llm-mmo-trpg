"""複合技能的 AI（Phase 3F-3b；3F-4b 擴充到全部六種）。

**候選估計**（:func:`composite_estimate`）：``legal_actions`` 已把複合技能的選取列成一個個
``UseSkill``（「位移 → 動作」是兩段的組合、「聚集 → 範圍打擊」的範圍含打擊段；其他種類只有第一段
的選取）。這裡只做便宜的估計（不跑引擎）：影響範圍內的敵人越多越好、誤傷友方扣分、完全沒有敵人就
不納入；平手以第二段的原點離施放者的距離判定（近者優先，保持確定）。延遲段（3F-4b）看的是以施放者
目前位置推算的預計範圍。估計只決定誰值得完整預覽（每個技能只保留前 ``skill_candidates`` 個）；
值不值得施放由預覽的收益與位置價值決定（延遲段的第二段另由 ``_rewrite_gains`` 加分）。

**第二段的選取**（:func:`choose_followup`，3F-4b）：「動作 → 位移」「擊殺 → 接下一段」的第二段在
結算時暫停（``pending.kind == "followup"``），自動對戰以這個函式回答（最簡單的近似）：

- 第二段只是一個自身位移（打帶跑的後跳）：選離最近敵人最遠的落點（拉開距離）；
- 其他：選影響範圍內「敵人數 − 友方數」最多的選取；沒有正分時放棄第二段。

平手都取 :func:`~trpg.engine.skills.followups.followup_options` 的順序（確定）。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.skills import COMPOSITE_MOVES, SkillDef
from trpg.engine.actions import Decision
from trpg.engine.delayed import delayed_selection
from trpg.engine.results import Pending
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.skills.followups import followup_options
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = ["choose_followup", "composite_estimate"]


def _sides(state: BattleState, unit: UnitState, units: tuple[UnitId, ...]) -> tuple[int, int]:
    """``units`` 中（不含 ``unit`` 自己）的敵人數與友方數。"""
    enemies = 0
    allies = 0
    for uid in units:
        other = state.units[uid]
        if other.id == unit.id or not other.alive:
            continue
        if other.team is unit.team:
            allies += 1
        else:
            enemies += 1
    return enemies, allies


def composite_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, area: SkillArea
) -> Fraction | None:
    """複合技能一個選取的估計；影響範圍（延遲段為預計範圍）內沒有敵方單位時為 ``None``。"""
    if skill.followup is not None and skill.followup.when == "delayed":
        found = delayed_selection(state, unit, skill)
        if found is None:
            return None
        area = found[1]
    enemies, allies = _sides(state, unit, area.units)
    if enemies == 0:
        return None
    return Fraction(3 * enemies - 3 * allies) - Fraction(manhattan(unit.xy, area.origin), 1000)


def _distance_to_foes(state: BattleState, unit: UnitState, xy: XY) -> int:
    foes = [u for u in state.living_units() if u.team is not unit.team]
    return min((manhattan(xy, f.xy) for f in foes), default=0)


def choose_followup(state: BattleState, pending: Pending) -> Decision:
    """回答「第二段選目標」的暫停（見模組說明）。"""
    caster = state.units[pending.unit_id]
    assert pending.skill_id is not None
    skill = state.ruleset.skill_def(pending.skill_id)
    follow = skill.followup_skill()
    assert follow is not None
    options = followup_options(state, caster, skill)
    lone_move = len(follow.effects) == 1 and follow.effects[0].type in COMPOSITE_MOVES
    best = None
    best_score = 0
    for target, area in options:
        if lone_move:
            pos = target.target_pos
            landing = area.origin if pos is None else (pos.x, pos.y)
            score = _distance_to_foes(state, caster, landing) + 1  # 一定 > 0：位移總是要做
        else:
            enemies, allies = _sides(state, caster, area.units)
            score = enemies - allies
        if score > best_score:
            best, best_score = target, score
    return Decision(unit_id=caster.id, accept=best is not None, followup_target=best)
