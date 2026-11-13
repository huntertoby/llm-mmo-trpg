"""蓄力（延遲段）的純查詢（Phase R3 自 :mod:`trpg.engine.delayed` 抽出；只讀狀態）。

被動觸發的收集（:mod:`trpg.engine.skill_triggers`）要在 ``attack_rolled`` 時判斷「被攻擊才釋放」的
延遲段（:func:`attacked_release`），但不需要結算；結算（:mod:`trpg.engine.delayed`）會用到效果
佇列。:mod:`trpg.engine.delayed` 照舊轉出 :data:`DELAYED_RELEASE` 與 :func:`attacked_release`。
"""

from __future__ import annotations

from trpg.content.skills import CHARGING, SkillDef
from trpg.engine.events import AttackRolled
from trpg.engine.rules.forms import breath_of
from trpg.engine.state import BattleState, StatusInstance, UnitState

__all__ = ["DELAYED_RELEASE", "attacked_release", "charged_skill", "release_of"]

DELAYED_RELEASE = "delayed_release"
"""``skill_triggers.Fired.event``：被攻擊才釋放的延遲段（等那次攻擊結算完才結算）。"""


def release_of(skill: SkillDef) -> str:
    """釋放時機：複合技能看 ``followup.release``；定向蓄力（沒有 followup）固定下回合開始。"""
    if skill.followup is None:
        return "next_turn"
    assert skill.followup.release is not None
    return skill.followup.release


def charged_skill(state: BattleState, unit: UnitState) -> tuple[StatusInstance, SkillDef] | None:
    """``unit`` 身上的蓄力狀態與它要釋放的第二段技能；沒有蓄力（或資料不完整）時為 ``None``。"""
    status = unit.get_status(CHARGING)
    if status is None or status.skill_id is None:
        return None
    if status.direction is not None:  # 定向蓄力：吐息技能由形態資料組出
        breath = breath_of(state.ruleset, unit)
        return None if breath is None else (status, breath)
    skill = state.ruleset.skill_def(status.skill_id)
    if status.lock_target is not None:  # 瞄準預告（RG-1）：射出的就是技能本身
        return status, skill
    if skill.followup is None or skill.followup.release is None:
        return None
    return status, skill


def attacked_release(state: BattleState, event: AttackRolled) -> SkillDef | None:
    """``event`` 讓哪個延遲段釋放：目標帶著 ``release: attacked`` 的蓄力、攻擊者是敵人。"""
    target = state.units.get(event.target_id)
    attacker = state.units.get(event.attacker_id)
    if target is None or attacker is None or attacker.team is target.team or not target.alive:
        return None
    charged = charged_skill(state, target)
    if charged is None:
        return None
    skill = charged[1]
    return skill if release_of(skill) == "attacked" else None
