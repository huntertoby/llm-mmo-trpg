"""地圖戰小模擬與單招施放率（NW-2a T-A8）。"""

from __future__ import annotations

from collections import Counter

import pytest

from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import TurnStarted
from trpg.engine.events.skills import SkillUsed
from trpg.engine.runner import run_battle
from trpg.sim.batch import map_spec
from trpg.sim.boss_probe import base_skill
from trpg.sim.lineup import build_allies
from trpg.sim.skill_probe import (
    MapBattle,
    SkillProbeJob,
    inject_skills,
    map_jobs,
    probe_battle,
    probe_maps,
    skill_tally,
)

MAP = "dark_forest"
BUILD = "build_fire"
SKILL = "skill_chain_lightning"


def _jobs() -> list[SkillProbeJob]:
    return map_jobs([MAP], 2, allies=[BUILD], inject=[(BUILD, SKILL)], probe=[SKILL])


@pytest.fixture(scope="module")
def battles(library: ContentLibrary) -> list[MapBattle]:
    return [probe_battle(library, job) for job in _jobs()]


def test_map_jobs_order() -> None:
    jobs = map_jobs(["a", "b"], 2)
    assert [(j.map_id, j.seed) for j in jobs] == [("a", 0), ("a", 1), ("b", 0), ("b", 1)]
    assert all(j.allies is None and j.inject == () and j.probe == () for j in jobs)


def test_deterministic(library: ContentLibrary, battles: list[MapBattle]) -> None:
    again = [probe_battle(library, job) for job in _jobs()]
    assert again == battles
    assert all(b.allies == 3 and 0 <= b.downed <= b.allies for b in battles)


def test_tally_matches_events(library: ContentLibrary, battles: list[MapBattle]) -> None:
    """分子／分母和逐場事件相加相符；彙總等於逐場相加。"""
    expected: Counter[str] = Counter()
    lib, allies = build_allies(inject_skills(library, [(BUILD, SKILL)]), [BUILD])
    for job in _jobs():
        spec = map_spec(lib, job.map_id, (job.seed,), allies=allies)
        run = run_battle(spec.setup, job.seed, UtilityAI(lib.ai_profiles))
        units = run.state.units
        for event in run.events:
            if isinstance(event, SkillUsed) and base_skill(event.skill_id) == SKILL:
                expected[f"cast|{units[event.unit_id].team.value}|{SKILL}"] += 1
            if isinstance(event, TurnStarted) and units[event.unit_id].template_id == BUILD:
                expected[f"turns|ally|{SKILL}"] += 1  # 只有 build 英雄裝了受測招
    total = skill_tally(battles)
    assert total == dict(sorted(expected.items()))
    summed: Counter[str] = Counter()
    for battle in battles:
        summed.update(battle.tally)
    assert total == dict(sorted(summed.items()))
    assert total[f"turns|ally|{SKILL}"] > 0


def test_probe_empty_counts_all(library: ContentLibrary) -> None:
    battle = probe_battle(library, SkillProbeJob(MAP, 0))
    assert any(k.startswith("turns|enemy|") for k in battle.tally)
    assert all(k.split("|")[0] in {"cast", "turns"} for k in battle.tally)


def test_inject_memory_only(library: ContentLibrary) -> None:
    builds_file = library.root / "sim" / "builds.yaml"
    before = (builds_file.stat().st_mtime_ns, builds_file.read_bytes())
    original = library.builds.by_id()[BUILD].hero.skills
    injected = inject_skills(library, [(BUILD, SKILL)])
    probe_battle(library, SkillProbeJob(MAP, 0, (BUILD,), ((BUILD, SKILL),), (SKILL,)))
    assert library.builds.by_id()[BUILD].hero.skills == original
    assert SKILL in injected.builds.by_id()[BUILD].hero.skills
    assert SKILL not in original
    assert (builds_file.stat().st_mtime_ns, builds_file.read_bytes()) == before
    assert inject_skills(library, ()) is library


def test_inject_slot_rules(library: ContentLibrary) -> None:
    hero = library.builds.by_id()[BUILD].hero
    same = inject_skills(library, [(BUILD, hero.skills[0])])  # 已裝：不變
    assert same.builds.by_id()[BUILD].hero.skills == hero.skills
    defs = library.skills
    kind = defs[SKILL].slot_kind
    slots = library.ruleset.core.skill_slots
    limit = getattr(slots, kind)
    extra = sorted(
        s
        for s in defs
        if defs[s].slot_kind == kind and s not in hero.skills and s != SKILL and s == base_skill(s)
    )
    lib = library
    for skill in [*extra[: limit + 1], SKILL]:  # 塞到滿之後再裝：替換同類最後一招
        try:
            lib = inject_skills(lib, [(BUILD, skill)])
        except ValueError:
            continue
        skills = lib.builds.by_id()[BUILD].hero.skills
        assert skills[-1] == skill or skill in skills
        assert sum(1 for s in skills if defs[s].slot_kind == kind) <= limit
    final = lib.builds.by_id()[BUILD].hero.skills
    assert SKILL in final
    kinds = [s for s in final if defs[s].slot_kind == kind]
    assert len(kinds) == limit and kinds[-1] == SKILL
    with pytest.raises(ValueError, match="未知的 build"):
        inject_skills(library, [("build_nope", SKILL)])
    with pytest.raises(ValueError, match="未知的技能"):
        inject_skills(library, [(BUILD, "skill_nope")])


def test_probe_maps(library: ContentLibrary) -> None:
    maps = probe_maps(library)
    assert maps == sorted(maps)
    assert "training_range" not in maps
    assert not any(m.startswith("test_") for m in maps)
    assert all(library.map(m).encounter is not None for m in maps)
    assert MAP in maps
