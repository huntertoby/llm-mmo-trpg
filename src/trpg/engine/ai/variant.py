"""AI 與戰場變奏（Phase 3-25a，``docs/phases/Phase3計畫.md`` 33 PM 決定 #9）。

- 評估技能時看 **目標點選出的型態**（:func:`cast_form`）：合法動作已經列出每個型態的選取
  （:mod:`trpg.engine.skills.forms`），預覽也以同一個型態結算，所以每個可行型態都會被評估。
- 「移到觸發條件的格子再施放」：移動的目的地能讓某招現在可用的技能的變奏成立（而現在的位置
  不成立）時，移動分數加 ``basic.variant_position_bonus``（:func:`variant_move_bonus`）。只看
  與施放者位置有關的條件（站的表面、相鄰牆壁或擋路物件、居高——目的地比某個存活敵人高）；
  目標格表面與施放者位置無關，不加分。不做多回合規劃。

這個模組只讀狀態。
"""

from __future__ import annotations

from trpg.content.skills import SkillDef, VariantWhen
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.targeting import skill_problem
from trpg.engine.state import BattleState, UnitState
from trpg.engine.variants import target_point, variant_holds, varied_skill
from trpg.shared.types import Pos

__all__ = ["cast_form", "variant_move_bonus"]


def cast_form(state: BattleState, action: UseSkill) -> SkillDef:
    """``action`` 施放的型態（基礎或變奏；未套等級與修正，同 ``skill_def`` 的層級）。"""
    skill = state.ruleset.skill_def(action.skill_id)
    if not skill.variants:
        return skill
    caster = state.units[action.unit_id]
    return varied_skill(state, caster, skill, target_point(state, action))[0]


def _lower_enemy(state: BattleState, unit: UnitState, xy: XY) -> bool:
    height = state.tile(*xy).height
    return any(
        state.tile(*other.xy).height < height
        for other in state.living_units()
        if other.team is not unit.team
    )


def _position_holds(state: BattleState, unit: UnitState, when: VariantWhen) -> bool:
    """與施放者位置有關的條件在 ``unit`` 現在的位置是否成立（居高：比某個存活敵人高）。"""
    if when.target_surface is not None:
        return False
    if when.caster_high_ground is not None:
        return _lower_enemy(state, unit, unit.xy)
    return variant_holds(state, unit, when, None)


def variant_move_bonus(state: BattleState, unit: UnitState, dest: XY, points: int) -> int:
    """移到 ``dest`` 能讓某招現在可用的技能的變奏成立（現在的位置不成立）時為 ``points``，
    否則 0。"""
    if points <= 0 or dest == unit.xy:
        return 0
    rules = state.ruleset
    moved: UnitState | None = None
    for skill_id in sorted(unit.all_skills):
        skill = rules.skill_def(skill_id)
        if not skill.variants:
            continue
        if skill_problem(state, unit, modifiers.acting_skill(state, unit, skill_id)) is not None:
            continue
        if moved is None:
            moved = unit.clone()
            moved.pos = Pos(x=dest[0], y=dest[1])
        for variant in skill.variants:
            if _position_holds(state, moved, variant.when) and not _position_holds(
                state, unit, variant.when
            ):
                return points
    return 0
