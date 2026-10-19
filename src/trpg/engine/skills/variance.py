"""高變異與依情況縮放的傷害加成（Phase 3D-7b；設計 6.17 B、D、E，6.18 G）。

兩個純函式，都回傳要加進傷害倍率（‰，以 1000 為基準的 **加成**）的整數：

- :func:`scale_bonus`：傷害效果的 ``scaling``——每一步 ``+per_step_permille``，無條件捨去，
  不超過 ``cap_permille``；
- :func:`overload_bonus`：持有者身上的超載層數——帶 ``overload.tag`` 標籤的技能每層
  ``+per_stack_damage_permille``。
"""

from __future__ import annotations

from trpg.content.skills import ScaleSpec, SkillDef
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = ["overload_bonus", "scale_bonus", "scale_steps"]


def _enemies_adjacent(state: BattleState, unit: UnitState, team_of: UnitState) -> int:
    """``unit`` 相鄰（曼哈頓距離 1）、且對 ``team_of`` 而言是敵人的存活單位數。"""
    return sum(
        1
        for other in state.units_sorted()
        if other.alive and other.team is not team_of.team and manhattan(other.xy, unit.xy) == 1
    )


def scale_steps(state: BattleState, caster: UnitState, target: UnitState, by: str) -> int:
    """``scaling.by`` 的步數：

    - ``missing_hp_10pct``：施放者每少 10% 最大 HP 一步（不足 10% 不算）；
    - ``distance``：施放者與目標的曼哈頓距離（格）；
    - ``enemies_adjacent_target``：目標相鄰的敵方（對施放者而言）數；
    - ``enemies_adjacent_self``：施放者相鄰的敵方數。
    """
    if by == "missing_hp_10pct":
        return max(0, caster.max_hp - caster.hp) * 10 // max(1, caster.max_hp)
    if by == "distance":
        return manhattan(caster.xy, target.xy)
    if by == "enemies_adjacent_target":
        return _enemies_adjacent(state, target, caster)
    if by == "enemies_adjacent_self":
        return _enemies_adjacent(state, caster, caster)
    raise ValueError(f"未知的縮放依據：{by}")


def scale_bonus(
    state: BattleState, caster: UnitState, target: UnitState, scaling: ScaleSpec | None
) -> int:
    """``scaling`` 對 ``target`` 的傷害加成（‰）：步數 × 每步，不超過 ``cap_permille``。"""
    if scaling is None:
        return 0
    steps = scale_steps(state, caster, target, scaling.by)
    return min(steps * scaling.per_step_permille, scaling.cap_permille)


def overload_bonus(state: BattleState, caster: UnitState, skill: SkillDef) -> int:
    """超載層數（``content/stacks.yaml`` 的 ``overload``）對 ``skill`` 的傷害加成（‰）。"""
    total = 0
    for stack_id in sorted(caster.stacks):
        overload = state.ruleset.stack_def(stack_id).overload
        if overload is not None and overload.tag in skill.tags:
            total += caster.stacks[stack_id] * overload.per_stack_damage_permille
    return total
