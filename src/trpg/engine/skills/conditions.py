"""技能與效果的條件（``docs/phases/Phase2A計畫.md`` 6.1）。

這個模組只讀取狀態，不修改。條件的判斷對象（:class:`Subject`）是 **一個單位或一個格子**：

- 單位類條件（``target_hp_below``、``target_has_status``）需要單位，沒有單位時不成立；
- 格子類條件（``height_advantage``、``target_on_surface``）看格子，單位只是站在上面；
- ``self_hp_below`` 與 3D-1 的連段條件（``moved_this_turn``、``adjacent_ally``、``first_round``、
  ``cast_tag_this_turn``）只看施放者，與對象無關；``target_isolated`` 看對象單位的周圍；
  ``flanked``（Phase 3D-8c）看對象單位與施放者的相對位置：對象的對面有施放者的友方；
  ``from_behind``（Phase 3D-8d）：施放者站在對象的背後格；``self_concealed``（3D-8d）只看施放者
  有沒有 ``concealed`` 狀態。

技能層級的條件（:func:`skill_condition_met`）決定技能能否使用；效果層級的條件
（:func:`condition_met`）由解譯器對每個對象分別判斷。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from trpg.content.skills import CASTER_CONDITIONS, ConditionSpec, SkillDef, condition_text
from trpg.engine.ids import CONCEALED
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.geometry import XY
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "Subject",
    "condition_met",
    "flank_xy",
    "is_flanked",
    "skill_condition_met",
    "skill_condition_problem",
    "subjects_of",
]

_PERMILLE = 1000


class Subject(NamedTuple):
    """條件的判斷對象：站在 ``xy`` 的 ``unit``（沒有單位時為 ``None``）。"""

    unit: UnitState | None
    xy: XY


def _hp_below(unit: UnitState, permille: int) -> bool:
    return unit.hp * _PERMILLE < permille * unit.max_hp


def _has_living_ally_beside(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 相鄰（上下左右）有它的存活友方（不含自己）。"""
    x, y = unit.xy
    for xy in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)):
        other = state.unit_at(*xy)
        if other is not None and other.id != unit.id and other.alive and other.team is unit.team:
            return True
    return False


def _caster_condition_met(state: BattleState, caster: UnitState, condition: ConditionSpec) -> bool:
    """只看施放者的條件（:data:`CASTER_CONDITIONS`）。"""
    kind = condition.type
    if kind == "self_hp_below":
        assert condition.permille is not None
        return _hp_below(caster, condition.permille)
    if kind == "moved_this_turn":
        return caster.moved_this_turn
    if kind == "adjacent_ally":
        return _has_living_ally_beside(state, caster)
    if kind == "first_round":
        return state.round == 1
    if kind == "self_concealed":
        return caster.has_status(CONCEALED)
    assert kind == "cast_tag_this_turn" and condition.tag is not None
    return condition.tag in caster.turn_cast_tags


def flank_xy(caster_xy: XY, target_xy: XY) -> XY | None:
    """夾擊的「對面格」（Phase 3D-8c）：以目標為中心，施放者位在目標的哪一側（取施放者相對目標
    位移較大的那一軸，左右與上下距離相同時取左右；施放者與目標同格時沒有），對面格就是目標在
    另一側的相鄰格。"""
    dx, dy = caster_xy[0] - target_xy[0], caster_xy[1] - target_xy[1]
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return (target_xy[0] - (1 if dx > 0 else -1), target_xy[1])
    return (target_xy[0], target_xy[1] - (1 if dy > 0 else -1))


def is_flanked(state: BattleState, caster: UnitState, target: UnitState) -> bool:
    """``caster`` 對 ``target`` 夾擊：目標的對面格（:func:`flank_xy`）站著施放者的存活友方
    （不含施放者自己）。"""
    xy = flank_xy(caster.xy, target.xy)
    if xy is None:
        return False
    other = state.unit_at(*xy)
    return other is not None and other.id != caster.id and other.alive and other.team is caster.team


def _unit_condition_met(
    state: BattleState, caster: UnitState, condition: ConditionSpec, unit: UnitState
) -> bool:
    """看對象單位的條件（``target_hp_below``、``target_has_status``、``target_isolated``、
    ``flanked``）。"""
    kind = condition.type
    if kind == "target_hp_below":
        assert condition.permille is not None
        return _hp_below(unit, condition.permille)
    if kind == "target_has_status":
        assert condition.status is not None
        return unit.has_status(condition.status)
    if kind == "flanked":
        return is_flanked(state, caster, unit)
    if kind == "from_behind":
        return is_behind(caster.xy, unit)
    assert kind == "target_isolated"
    return not _has_living_ally_beside(state, unit)


_UNIT_CONDITIONS = frozenset(
    {"target_hp_below", "target_has_status", "target_isolated", "flanked", "from_behind"}
)


def condition_met(
    state: BattleState, caster: UnitState, condition: ConditionSpec | None, subject: Subject
) -> bool:
    """``condition`` 對 ``subject`` 是否成立（``None`` 永遠成立）。"""
    if condition is None:
        return True
    kind = condition.type
    if kind in CASTER_CONDITIONS:
        return _caster_condition_met(state, caster, condition)
    if kind in _UNIT_CONDITIONS:
        return subject.unit is not None and _unit_condition_met(
            state, caster, condition, subject.unit
        )
    if kind == "height_advantage":
        return state.tile(*caster.xy).height > state.tile(*subject.xy).height
    if kind == "target_on_surface":
        return state.tile(*subject.xy).surface == condition.surface
    raise ValueError(f"未知的條件：{kind}")


def subjects_of(state: BattleState, caster: UnitState, tiles: Iterable[XY]) -> list[Subject]:
    """影響範圍內（不含施放者所在格）的判斷對象；範圍只有施放者的格子時，對象是施放者自己。"""
    result = [Subject(state.unit_at(*xy), xy) for xy in tiles if xy != caster.xy]
    return result or [Subject(caster, caster.xy)]


def skill_condition_met(
    state: BattleState, caster: UnitState, skill: SkillDef, tiles: Iterable[XY]
) -> bool:
    """技能層級的條件：施放者條件（:data:`CASTER_CONDITIONS`）看施放者；其他條件要求影響範圍內至少有一個對象成立。"""
    condition = skill.condition
    if condition is None:
        return True
    if condition.type in CASTER_CONDITIONS:
        return condition_met(state, caster, condition, Subject(caster, caster.xy))
    return any(
        condition_met(state, caster, condition, subject)
        for subject in subjects_of(state, caster, tiles)
    )


def skill_condition_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, tiles: Iterable[XY]
) -> str | None:
    """技能條件不成立時的原因（繁體中文）；成立時為 ``None``。"""
    if skill_condition_met(state, caster, skill, tiles):
        return None
    assert skill.condition is not None
    rules = state.ruleset
    text = condition_text(
        skill.condition,
        status_name=lambda sid: rules.status_def(sid).name_zh,
        surface_name=lambda surface: rules.surface_def(surface).name_zh,
    )
    return f"技能條件不成立：{skill.name_zh} 需要「{text}」"
