"""技能與效果的條件（``docs/phases/Phase2A計畫.md`` 6.1）。

這個模組只讀取狀態，不修改。條件的判斷對象（:class:`Subject`）是 **一個單位或一個格子**：

- 單位類條件（``target_hp_below``、``target_has_status``）需要單位，沒有單位時不成立；
- 格子類條件（``height_advantage``、``target_on_surface``）看格子，單位只是站在上面；
- ``self_hp_below`` 只看施放者，與對象無關。

技能層級的條件（:func:`skill_condition_met`）決定技能能否使用；效果層級的條件
（:func:`condition_met`）由解譯器對每個對象分別判斷。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from trpg.content.skills import ConditionSpec, SkillDef, condition_text
from trpg.engine.rules.geometry import XY
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "Subject",
    "condition_met",
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


def condition_met(
    state: BattleState, caster: UnitState, condition: ConditionSpec | None, subject: Subject
) -> bool:
    """``condition`` 對 ``subject`` 是否成立（``None`` 永遠成立）。"""
    if condition is None:
        return True
    kind = condition.type
    unit = subject.unit
    if kind == "self_hp_below":
        assert condition.permille is not None
        return _hp_below(caster, condition.permille)
    if kind == "target_hp_below":
        assert condition.permille is not None
        return unit is not None and _hp_below(unit, condition.permille)
    if kind == "target_has_status":
        assert condition.status is not None
        return unit is not None and unit.has_status(condition.status)
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
    """技能層級的條件：``self_hp_below`` 看施放者；其他條件要求影響範圍內至少有一個對象成立。"""
    condition = skill.condition
    if condition is None:
        return True
    if condition.type == "self_hp_below":
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
