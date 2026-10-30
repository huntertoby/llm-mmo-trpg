"""施放者 AI 的灌注技能（Phase 3-33d，6.29.3；權重在 ``content/ai_profiles.yaml`` 的 ``summon:``）。

AI 把「灌注 ``skill`` 給召喚物 ``s``」當作一個候選動作：

- **技能價值**：在一個假設的狀態上（:func:`infuse_setups`），讓召喚物用灌注快照的數字、從自己的
  位置施放牠依模式會選的選取（:func:`~trpg.engine.skill_infusion.infused_pick`），由效用 AI 以完整
  預覽評分（呼叫端負責）；
- **存活機率**（:func:`survival`，保守估計）：召喚物 HP ÷（HP ＋ 能打到牠的敵人數 ×
  ``infuse_threat_damage``）；能打到 ＝ 敵人與召喚物的距離不超過敵人的武器射程 ＋ 速度；
- 分數 ＝ 技能價值 × ``infuse_value_permille`` ‰ × 存活機率 × 省下的 AP（BAL-5 B5：灌注固定花
  ``summon_infuse_ap_cost``，技能本身要 2 AP 時省 1 AP，乘 技能 AP ÷ 灌注 AP，至少 1）；只在高於
  其他動作的最佳分數時灌注。

敵我規則對稱（任何由效用 AI 操作、帶著召喚物的施放者都會考慮）。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import SummonAiRules
from trpg.engine.actions import InfuseSkill, UseSkill
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skill_infusion import infuse_problem, infused_pick, snapshot
from trpg.engine.state import BattleState, UnitState

__all__ = ["InfuseSetup", "ap_ratio", "infuse_setups", "infuse_value", "survival"]

_PERMILLE = 1000


@dataclass(frozen=True, slots=True)
class InfuseSetup:
    """一個灌注候選：``action`` 是施放者的動作；``sim`` 是假設召喚物正在施放的狀態（召喚物是行動者、
    帶著施放者的數字、資源足夠），``pick`` 是牠會選的選取。"""

    action: InfuseSkill
    sim: BattleState
    pick: UseSkill


def survival(state: BattleState, summon: UnitState, rules: SummonAiRules) -> Fraction:
    """召喚物撐到下一個自己回合的機率（保守估計，見模組說明）。"""
    threats = sum(
        1
        for e in state.living_units()
        if e.team is not summon.team and manhattan(e.xy, summon.xy) <= e.weapon.range + e.speed
    )
    incoming = threats * rules.infuse_threat_damage
    return Fraction(summon.hp, max(summon.hp + incoming, 1))


def _cast_state(
    state: BattleState, owner: UnitState, summon: UnitState, skill_id: str
) -> BattleState:
    """假設的狀態：召喚物是行動者、用施放者的屬性快照與武器，裝著這招技能、資源足夠
    （代價已由施放者付，不影響召喚物）。"""
    sim = state.clone()
    unit = sim.units[summon.id]
    snap = snapshot(state, owner, skill_id)
    skill = state.ruleset.skill_def(skill_id)
    unit.attributes = dict(snap.attributes)
    unit.weapon = owner.weapon
    unit.skills = (skill_id,)
    unit.granted_skills = ()
    unit.mana = max(unit.mana, skill.cost.mana)
    unit.stamina = max(unit.stamina, skill.cost.stamina)
    unit.cooldowns = {}
    unit.skill_uses = {}
    unit.ap = max(unit.ap, skill.ap_cost or 0, 1)
    sim.active_unit = unit.id
    sim.pending = None
    return sim


def infuse_setups(
    state: BattleState, owner: UnitState, rules: SummonAiRules
) -> Iterator[InfuseSetup]:
    """``owner`` 目前可以灌注、而且召喚物選得到目標的所有候選（召喚物依 ID、技能依裝備順序）。
    ``infuse_value_permille`` 為 0 時沒有候選。"""
    if rules.infuse_value_permille <= 0:
        return
    summons = [s for s in state.units_sorted() if s.owner_id == owner.id and s.alive]
    for summon in summons:
        for skill_id in owner.all_skills:
            action = InfuseSkill(unit_id=owner.id, summon_id=summon.id, skill_id=skill_id)
            if infuse_problem(state, owner, action) is not None:
                continue
            found = infused_pick(state, summon.id, skill_id, owner.id)
            if found is None:
                continue
            yield InfuseSetup(action, _cast_state(state, owner, summon, skill_id), found[0])


def ap_ratio(state: BattleState, skill_id: str) -> Fraction:
    """灌注省下的 AP 比例（BAL-5 B5）：技能 AP ÷ 灌注 AP，至少 1。"""
    cost = max(state.ruleset.core.summon_infuse_ap_cost, 1)
    skill_ap = state.ruleset.skill_def(skill_id).ap_cost or 1
    return max(Fraction(skill_ap, cost), Fraction(1))


def infuse_value(
    score: Fraction, chance: Fraction, rules: SummonAiRules, ratio: Fraction = Fraction(1)
) -> Fraction:
    """灌注的分數：技能價值 × ``infuse_value_permille`` ‰ × 存活機率 × 省下的 AP 比例。"""
    return score * Fraction(rules.infuse_value_permille, _PERMILLE) * chance * ratio
