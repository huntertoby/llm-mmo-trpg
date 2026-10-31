"""有代價的姿態的 AI 使用條件（BAL-13d；數值在 ``ai_profiles.yaml`` 的 ``stance:``）。

效用 AI 原本不主動取消姿態，只要有預覽收益就進入；有代價的姿態（例：狂怒姿態受到的骰值傷害
×1.2）因此常在開場、離敵人還很遠時就開，血量見底也不關。這裡補兩條條件（只套用在
``risky_statuses`` 列出的姿態狀態）：

- :func:`stance_entry_blocked`：沒有敵人在 ``enter_enemy_turns`` 回合可達範圍內（曼哈頓距離 ≤
  回合數 × 速度 ＋ 普攻射程），或已符合取消條件時，不進入；
- :func:`stance_cancel`：HP 低於 ``cancel_hp_below_permille`` 且 ``cancel_enemy_radius`` 格內有敵人
  時，回合一開始就取消（``EndStance`` 不花 AP）。
"""

from __future__ import annotations

from trpg.content.environment import StanceAiRules
from trpg.content.skills import SkillDef
from trpg.engine.actions import EndStance
from trpg.engine.rules.combat import attack_reach
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = ["stance_cancel", "stance_entry_blocked"]

_PERMILLE = 1000


def _nearest_enemy(state: BattleState, unit: UnitState) -> int | None:
    distances = [
        manhattan(unit.xy, other.xy)
        for other in state.living_units()
        if other.team is not unit.team
    ]
    return min(distances) if distances else None


def _should_cancel(state: BattleState, unit: UnitState, rules: StanceAiRules) -> bool:
    if unit.hp * _PERMILLE >= unit.max_hp * rules.cancel_hp_below_permille:
        return False
    nearest = _nearest_enemy(state, unit)
    return nearest is not None and nearest <= rules.cancel_enemy_radius


def _risky_status(skill: SkillDef, rules: StanceAiRules) -> bool:
    return skill.kind == "stance" and any(
        effect.type == "apply_status" and effect.status in rules.risky_statuses
        for effect in skill.effects
    )


def stance_entry_blocked(
    state: BattleState, unit: UnitState, skill: SkillDef, rules: StanceAiRules
) -> bool:
    """``skill`` 是有代價的姿態，而且現在不該進入（敵人還不在可達範圍內，或已符合取消條件）。"""
    if not _risky_status(skill, rules):
        return False
    if _should_cancel(state, unit, rules):
        return True
    nearest = _nearest_enemy(state, unit)
    reach = rules.enter_enemy_turns * unit.speed + attack_reach(state, unit)
    return nearest is None or nearest > reach


def stance_cancel(state: BattleState, unit: UnitState, rules: StanceAiRules) -> EndStance | None:
    """``unit`` 身上有代價的姿態、且符合取消條件時回傳取消姿態的動作；否則 ``None``。"""
    if not any(s.status_id in rules.risky_statuses for s in unit.statuses):
        return None
    if unit.form is not None or not _should_cancel(state, unit, rules):
        return None
    return EndStance(unit_id=unit.id)
