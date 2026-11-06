"""``copy_skill``（Phase 3C-4b，``docs/phases/Phase3C計畫.md`` 7）：複製本輪最後施放的主動技能。

- 戰鬥狀態記錄 ``casts``（本輪以 ``UseSkill`` 施放過的主動技能：施放者、技能、當輪）。
- 可複製的條件（:func:`copy_source`）：本輪內「最後一個別人施放的」（不算複製者自己的）、施放者
  仍在場上而且複製者看得到它（視線）；技能本身不能是傳說、改寫規則型（含 ``copy_skill``）、陷阱、
  敵人專用（``enemy_only``，5F-R1）
  或有層數需求的技能（保守）。
- 複製的技能由複製者重新選目標（:func:`copy_selections`），不扣法力與 AP、不進冷卻、不花源力，但
  沉默、射程、視線與技能條件都要合法（:func:`copy_free_problem`、``selections``）；不檢查
  ``weapon_req``（技能的傷害與射程照複製者自己的武器算）。
- 玩家：``UseSkill``（沒有 ``copy_cast``）→ 結算暫停（``Pending.kind == "copy_skill"``）→
  ``Decision`` 帶 ``copy_cast``（複製技能的選取）繼續；AI 與重播直接在 ``UseSkill.copy_cast``
  給出選取。
"""

from __future__ import annotations

from collections.abc import Iterator

from trpg.engine.actions import UseSkill
from trpg.engine.copy_rules import (
    copy_free_problem,
    copy_source,
    has_copy_effect,
    uncopyable_reason,
)
from trpg.engine.skills.targeting import SkillArea, copy_problem, selections
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "copy_free_problem",
    "copy_problem",
    "copy_selections",
    "copy_source",
    "has_copy_effect",
    "uncopyable_reason",
]


def copy_selections(state: BattleState, caster: UnitState) -> Iterator[tuple[UseSkill, SkillArea]]:
    """``caster`` 複製的技能目前所有合法的選取與影響範圍（確定性順序，同 ``selections``）。"""
    found = copy_source(state, caster)
    if isinstance(found, str):
        return
    skill = found[0]
    if copy_free_problem(state, caster, skill) is not None:
        return
    yield from selections(state, caster, skill)
