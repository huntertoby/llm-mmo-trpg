"""技能點與技能等級（Phase 3-26a，06 6.28；參數 ``content/skill_growth.yaml``）。

純函式（``RunState`` 進、``RunState`` 出），不推進節點：

- :func:`spend_points`：花技能點把裝備中的主動技能升到指定等級（只能升、不能降；每級花
  ``upgrade_cost`` 點，上限 ``max_level``）。
- :func:`respec`：營火的免費重配——全部退回 1 級、點數退回。
- :func:`set_loadout`：營火的換裝——重排裝備與備用技能；技能等級跟著技能走，所以卸下的技能升過的
  等級保留。
- :func:`battle_levels`：戰鬥設定要帶入單位的技能等級（只有裝備中的技能）。

分歧進化（Phase 3-26b）：

- :func:`raise_problem` 是「這招能不能升到這一級」的唯一檢查處；
  升到 ``evolve_level`` 而且還沒進化過的
  技能，這一輪要用過 ``evolve_uses`` 次（``RunState.skill_usage``）。
- :func:`evolution_choices`：這招的兩支進化（加深、橋接；
  :func:`trpg.skillgen.evolution.evolution_options`，
  種子 ``Rng(一輪的種子).fork("evolve/<技能 ID>")``）。同一個 ``RunState`` 必得同樣的兩支。
- :func:`spend_points` 升過 ``evolve_level`` 時必須在 ``evolve`` 選一支（沒有任何合格的進化時免選、
  照常升級）；進化後裝備中的技能換成進化後的定義（新 ID，放進 ``generated_skills``），等級與用法統計
  跟著過去，``RunState.evolutions`` 記下來源。重配（:func:`respec`）只退點數、不動進化；已進化的技能
  再升過 3 級不會再進化。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.offers import equip_problems, skill_defs
from trpg.roguelite.state import EvolutionRecord, RunState
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import keyword_distribution
from trpg.skillgen.evolution import Evolution, EvolutionRequest, evolution_options
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "battle_levels",
    "crosses_evolution",
    "evolution_choices",
    "level_of",
    "raise_problem",
    "respec",
    "set_loadout",
    "spend_points",
    "spent_points",
    "uses_of",
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


def uses_of(run: RunState, skill_id: str) -> int:
    """``skill_id`` 在這一輪用過的次數。"""
    usage = run.skill_usage.get(skill_id)
    return 0 if usage is None else usage.uses


def crosses_evolution(library: ContentLibrary, run: RunState, skill_id: str, level: int) -> bool:
    """從目前等級升到 ``level`` 會經過分歧進化（還沒進化過的技能才會）。"""
    evolve = library.ruleset.skill_growth.evolve_level
    return level_of(run, skill_id) < evolve <= level and skill_id not in run.evolutions


def raise_problem(
    library: ContentLibrary, run: RunState, skill: SkillDef | None, skill_id: str, level: int
) -> str | None:
    """``skill_id`` 不能升到 ``level`` 的原因（中文）；可以時 ``None``。"""
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
    uses = uses_of(run, skill_id)
    if crosses_evolution(library, run, skill_id, level) and uses < growth.evolve_uses:
        return (
            f"{skill.name_zh} 要在這一輪用過 {growth.evolve_uses} 次才能升到 "
            f"{growth.evolve_level} 級（分歧進化；目前 {uses} 次）"
        )
    return None


def evolution_choices(
    library: ContentLibrary, run: RunState, skill_id: str
) -> tuple[Evolution, ...]:
    """``skill_id``（主角裝備中）的兩支進化（見模組說明）；沒有合格的進化時為空。"""
    skill = skill_defs(library, run, (skill_id,))[0]
    others = skill_defs(library, run, [s for s in run.hero.skills if s != skill_id])
    request = EvolutionRequest(
        skill=skill,
        usage=run.skill_usage.get(skill_id, SkillUsage()),
        held_keywords=keyword_distribution(others, library),
        seed=Rng(run.seed).fork(f"evolve/{skill_id}").next_u32(),
    )
    return evolution_options(library, request)


def _picked_evolutions(
    library: ContentLibrary, run: RunState, levels: Mapping[str, int], evolve: Mapping[str, int]
) -> dict[str, Evolution]:
    """``levels`` 中會經過分歧進化的技能 → 選的那一支（沒有合格進化的技能不列）。不合法時拋出
    :class:`ChoiceError`。"""
    crossing = [k for k in sorted(levels) if crosses_evolution(library, run, k, levels[k])]
    extra = sorted(set(evolve) - set(crossing))
    if extra:
        raise ChoiceError(f"這些技能這次沒有分歧進化，不能選進化：{', '.join(extra)}")
    picked: dict[str, Evolution] = {}
    for skill_id in crossing:
        options = evolution_choices(library, run, skill_id)
        if not options:
            continue  # 沒有任何合格的進化模板：照常升級（報告待 PM 決定）
        pick = evolve.get(skill_id)
        if pick is None:
            raise ChoiceError(f"{skill_id} 升到這一級要選一支進化（evolve：0～{len(options) - 1}）")
        if not 0 <= pick < len(options):
            raise ChoiceError(f"{skill_id} 的進化索引必須是 0～{len(options) - 1}，收到 {pick}")
        picked[skill_id] = options[pick]
    return picked


def _apply_evolutions(run: RunState, picked: Mapping[str, Evolution]) -> RunState:
    """把技能換成進化後的定義：裝備位置不變，等級、用法統計換到新 ID，記下進化紀錄。"""
    if not picked:
        return run
    rename = {old: e.skill.id for old, e in picked.items()}
    skills = tuple(rename.get(s, s) for s in run.hero.skills)
    levels = {rename.get(k, k): v for k, v in run.skill_levels.items()}
    usage = {rename.get(k, k): v for k, v in run.skill_usage.items()}
    keep = {*skills, *run.bench}
    generated = {s.id: s for s in run.generated_skills if s.id in keep}
    generated.update({e.skill.id: e.skill for e in picked.values()})
    records = dict(run.evolutions)
    for old, e in picked.items():
        records[e.skill.id] = EvolutionRecord(
            base_id=old,
            branch=e.branch,
            template=e.template,
            keyword=e.keyword,
            fallback=e.fallback,
        )
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"skills": skills}),
            "skill_levels": {k: levels[k] for k in sorted(levels)},
            "skill_usage": {k: usage[k] for k in sorted(usage)},
            "generated_skills": tuple(generated[k] for k in sorted(generated)),
            "evolutions": {k: records[k] for k in sorted(records)},
        }
    )


def spend_points(
    library: ContentLibrary,
    run: RunState,
    levels: Mapping[str, int],
    evolve: Mapping[str, int] | None = None,
) -> RunState:
    """把 ``levels``（技能 ID → 升到的等級）花技能點升上去；
    ``evolve`` 是經過分歧進化的技能選的分支。
    任何一項不合法或點數不足時拋出 :class:`ChoiceError`（狀態不變）。"""
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
    picked = _picked_evolutions(library, run, levels, evolve or {})
    merged = {**run.skill_levels, **levels}
    spent = run.model_copy(
        update={
            "skill_points": run.skill_points - cost,
            "skill_levels": {k: merged[k] for k in sorted(merged)},
        }
    )
    return _apply_evolutions(spent, picked)


def respec(library: ContentLibrary, run: RunState) -> RunState:
    """全部技能退回 1 級，花掉的點數全部退回（分歧進化保留：進化結果跟著技能走，重選不做）。"""
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
