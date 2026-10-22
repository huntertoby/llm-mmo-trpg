"""技能點與技能等級（Phase 3-26a，06 6.28；參數 ``content/skill_growth.yaml``）。

純函式（``RunState`` 進、``RunState`` 出），不推進節點：

- :func:`spend_points`：花技能點把裝備中的主動技能升到指定等級（只能升、不能降；每級花
  ``upgrade_cost`` 點，上限 ``max_level``）。
- :func:`respec`：營火的免費重配——全部退回 1 級、點數退回。
- :func:`set_loadout`：營火的換裝——重排裝備與備用技能；技能等級跟著技能走，所以卸下的技能升過的
  等級保留。
- :func:`battle_levels`：戰鬥設定要帶入單位的技能等級（只有裝備中的技能）。

3-26b（分歧進化）的接點：:func:`raise_problem` 是「這招能不能升到這一級」的唯一檢查處（門檻：3 級要
用過 N 次）；:func:`spent_points` 是已花的點數（進化後重配要一起處理）。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.offers import equip_problems, skill_defs
from trpg.roguelite.state import RunState

__all__ = [
    "battle_levels",
    "level_of",
    "raise_problem",
    "respec",
    "set_loadout",
    "spend_points",
    "spent_points",
]


def level_of(run: RunState, skill_id: str) -> int:
    """技能 ``skill_id`` 目前的等級（沒有記錄為 1）。"""
    return run.skill_levels.get(skill_id, 1)


def spent_points(library: ContentLibrary, run: RunState) -> int:
    """已經花在技能等級上的點數（重配時退回）。"""
    cost = library.ruleset.skill_growth.upgrade_cost
    return sum((level - 1) * cost for level in run.skill_levels.values())


def battle_levels(run: RunState) -> dict[str, int]:
    """要帶進戰鬥的技能等級：裝備中的技能、等級 ≥ 2，依技能 ID 排序。"""
    return {k: run.skill_levels[k] for k in sorted(run.skill_levels) if k in run.hero.skills}


def raise_problem(
    library: ContentLibrary, run: RunState, skill: SkillDef | None, skill_id: str, level: int
) -> str | None:
    """``skill_id`` 不能升到 ``level`` 的原因（中文）；可以時 ``None``。3-26b 在這裡加進化門檻。"""
    growth = library.ruleset.skill_growth
    if skill_id not in run.hero.skills or skill is None:
        return f"主角沒有裝備技能 {skill_id}，不能升級"
    if skill.kind != "active":
        return f"{skill.name_zh} 不是主動技能，不能升級"
    current = level_of(run, skill_id)
    if level <= current:
        return f"{skill.name_zh} 已經是 {current} 級，只能往上升"
    if level > growth.max_level:
        return f"技能等級最高 {growth.max_level} 級（{skill.name_zh}）"
    return None


def spend_points(library: ContentLibrary, run: RunState, levels: Mapping[str, int]) -> RunState:
    """把 ``levels``（技能 ID → 升到的等級）花技能點升上去。任何一項不合法或點數不足時拋出
    :class:`ChoiceError`（狀態不變）。"""
    growth = library.ruleset.skill_growth
    defs = {s.id: s for s in skill_defs(library, run, run.hero.skills)}
    cost = 0
    for skill_id in sorted(levels):
        target = levels[skill_id]
        problem = raise_problem(library, run, defs.get(skill_id), skill_id, target)
        if problem is not None:
            raise ChoiceError(problem)
        cost += (target - level_of(run, skill_id)) * growth.upgrade_cost
    if cost > run.skill_points:
        raise ChoiceError(f"技能點不足：需要 {cost} 點，只有 {run.skill_points} 點")
    merged = {**run.skill_levels, **levels}
    return run.model_copy(
        update={
            "skill_points": run.skill_points - cost,
            "skill_levels": {k: merged[k] for k in sorted(merged)},
        }
    )


def respec(library: ContentLibrary, run: RunState) -> RunState:
    """全部技能退回 1 級，花掉的點數全部退回。"""
    return run.model_copy(
        update={
            "skill_points": run.skill_points + spent_points(library, run),
            "skill_levels": {},
        }
    )


def set_loadout(library: ContentLibrary, run: RunState, skills: tuple[str, ...]) -> RunState:
    """新的裝備清單 ``skills``（順序即技能列順序）；沒裝上的進備用。不合法時拋出
    :class:`ChoiceError`。"""
    owned = (*run.hero.skills, *run.bench)
    unknown = sorted(set(skills) - set(owned))
    if unknown:
        raise ChoiceError(f"不能裝備沒有的技能：{', '.join(unknown)}")
    if len(set(skills)) != len(skills):
        raise ChoiceError("技能不可重複裝備")
    problems = equip_problems(library, skill_defs(library, run, skills))
    if problems:
        raise ChoiceError("；".join(problems))
    bench = tuple(sorted(set(owned) - set(skills)))
    hero = run.hero.model_copy(update={"skills": tuple(skills)})
    return run.model_copy(update={"hero": hero, "bench": bench})
