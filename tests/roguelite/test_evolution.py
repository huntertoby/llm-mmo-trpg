"""Phase 3-26b：用法統計（確定性）、進化門檻、二選一、存檔、整場重播、AI 代打跑到進化。"""

from __future__ import annotations

import json
from functools import cache

import pytest

from tests.roguelite.helpers import VICTORY, full_run, library
from trpg.engine.battle import begin_battle
from trpg.engine.events import SkillUsed
from trpg.engine.runner import apply_step
from trpg.engine.state import state_to_json
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    RunSave,
    RunState,
    apply_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_run,
    restore_battle,
)
from trpg.roguelite.growth import evolution_choices, level_of, respec, uses_of
from trpg.roguelite.offers import candidate_request
from trpg.roguelite.progress import battle_setup, hero_unit_id
from trpg.roguelite.state import BattleNode, LevelUpNode, SpendChoice
from trpg.skillgen.usage import SkillUsage, collect_usage

BUILD, SEED = VICTORY


def _first_battle() -> tuple[RunState, ActiveBattle]:
    lib = library()
    run = new_run(lib, BUILD, SEED)
    battle = ActiveBattle(lib, run)
    battle.auto()
    return run, battle


@cache
def _after_first_battle() -> RunState:
    lib = library()

    def stop(run: RunState, _battle: ActiveBattle | None) -> bool:
        return isinstance(run.node, LevelUpNode)

    run, _ = auto_play(lib, new_run(lib, BUILD, SEED), stop=stop)
    return run


def _active(run: RunState) -> str:
    """用過最多次的主動技能。"""
    lib = library()
    defs = {**lib.skills, **{s.id: s for s in run.generated_skills}}
    actives = [s for s in run.hero.skills if defs[s].kind == "active"]
    return max(actives, key=lambda s: (uses_of(run, s), -actives.index(s)))


def _with_points(run: RunState, points: int = 4) -> RunState:
    """給 ``points`` 點，並讓用過最多次的主動技能達到進化門檻（保留它實際的用法統計）。"""
    skill = _active(run)
    usage = run.skill_usage.get(skill, SkillUsage()).model_copy(update={"uses": 3})
    return run.model_copy(
        update={"skill_points": points, "skill_usage": {**run.skill_usage, skill: usage}}
    )


def test_usage_is_deterministic_and_counts_every_cast() -> None:
    lib = library()
    run, battle = _first_battle()
    setup = battle_setup(lib, run)
    seed = run.plan_of(1).seed
    hero = hero_unit_id(battle.state)
    a = collect_usage(setup, seed, battle.steps, hero, lib.keywords)
    b = collect_usage(battle_setup(lib, run), seed, list(battle.steps), hero, lib.keywords)
    assert a == b and a
    # 次數 ＝ 重播出的 skill_used 事件數
    state = begin_battle(setup, seed).state
    casts: dict[str, int] = {}
    for step in battle.steps:
        result = apply_step(state, step)
        for e in result.events:
            if isinstance(e, SkillUsed) and e.unit_id == hero:
                casts[e.skill_id] = casts.get(e.skill_id, 0) + 1
        state = result.state
    assert {k: u.uses for k, u in a.items()} == casts
    for usage in a.values():
        assert usage.targets >= 0 and sum(usage.terrain.values()) == usage.uses
        assert list(usage.target_keywords) == sorted(usage.target_keywords)


def test_finish_battle_accumulates_usage_into_the_run() -> None:
    run = _after_first_battle()
    assert run.skill_usage and all(u.uses > 0 for u in run.skill_usage.values())
    assert set(run.skill_usage) <= set(run.hero.skills)
    merged = SkillUsage(uses=1).merged(SkillUsage(uses=2, terrain={"grass": 2}))
    assert merged == SkillUsage(uses=3, terrain={"grass": 2})


def test_level_three_needs_enough_uses_and_shows_why() -> None:
    lib = library()
    run = _with_points(_after_first_battle())
    skill = _active(run)
    rare = run.model_copy(update={"skill_usage": {skill: SkillUsage(uses=2)}})
    with pytest.raises(ChoiceError, match=r"要在這一輪用過 3 次.*目前 2 次"):
        apply_choice(lib, rare, SpendChoice(levels={skill: 3}))
    # 2 級不受門檻影響
    assert level_of(apply_choice(lib, rare, SpendChoice(levels={skill: 2})), skill) == 2


def test_evolving_requires_a_pick_and_swaps_in_the_evolved_skill() -> None:
    lib = library()
    run = _with_points(_after_first_battle())
    skill = _active(run)
    options = evolution_choices(lib, run, skill)
    assert len(options) == 2 and options == evolution_choices(lib, run, skill)
    with pytest.raises(ChoiceError, match="要選一支進化"):
        apply_choice(lib, run, SpendChoice(levels={skill: 3}))
    with pytest.raises(ChoiceError, match="進化索引"):
        apply_choice(lib, run, SpendChoice(levels={skill: 3}, evolve={skill: 2}))
    with pytest.raises(ChoiceError, match="沒有分歧進化"):
        apply_choice(lib, run, SpendChoice(levels={skill: 2}, evolve={skill: 0}))
    after = apply_choice(lib, run, SpendChoice(levels={skill: 3}, evolve={skill: 1}))
    chosen = options[1].skill
    index = run.hero.skills.index(skill)
    assert after.hero.skills[index] == chosen.id and skill not in after.hero.skills
    assert level_of(after, chosen.id) == 3 and skill not in after.skill_levels
    assert after.generated(chosen.id) == chosen
    assert after.skill_usage[chosen.id] == run.skill_usage[skill]  # 統計跟著技能走
    record = after.evolutions[chosen.id]
    assert (record.base_id, record.branch, record.template) == (
        skill,
        "bridge",
        options[1].template,
    )
    assert after.skill_points == run.skill_points - 2
    # 進化前的技能不會再出現在候選
    assert skill in candidate_request(lib, after).exclude


def test_respec_keeps_the_evolution_and_it_never_evolves_twice() -> None:
    lib = library()
    run = _with_points(_after_first_battle())
    skill = _active(run)
    after = apply_choice(lib, run, SpendChoice(levels={skill: 3}, evolve={skill: 0}))
    evolved = next(iter(after.evolutions))
    reset = respec(lib, after)
    assert level_of(reset, evolved) == 1 and evolved in reset.hero.skills
    assert reset.evolutions == after.evolutions
    again = apply_choice(lib, reset, SpendChoice(levels={evolved: 3}))
    assert level_of(again, evolved) == 3 and again.evolutions == after.evolutions


@pytest.mark.slow
def test_the_save_round_trips_and_a_full_run_is_deterministic() -> None:
    run = full_run(*VICTORY)
    assert run.evolutions, "AI 代打這一輪應該至少進化一次"
    for evolved, record in run.evolutions.items():
        assert run.generated(evolved) is not None
        assert record.base_id not in run.hero.skills
    raw = json.loads(dumps_save(RunSave(run_id="e", run=run)))
    assert raw["format"] == "trpg-run/11" and raw["run"]["evolutions"]
    assert loads_save(json.dumps(raw)).run == run
    lib = library()
    again, _ = auto_play(lib, new_run(lib, BUILD, SEED))
    assert again == run


@pytest.mark.slow
def test_a_mid_battle_save_after_an_evolution_replays_bit_for_bit() -> None:
    lib = library()

    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return battle is not None and bool(run.evolutions) and len(battle.steps) >= 8

    run, battle = auto_play(lib, new_run(lib, BUILD, SEED), stop=stop)
    assert battle is not None and isinstance(run.node, BattleNode)
    assert any(s in run.evolutions for s in run.hero.skills)
    save = loads_save(dumps_save(RunSave(run_id="m", run=run, battle=battle.to_saved())))
    restored = restore_battle(lib, save)
    assert restored is not None
    assert state_to_json(restored.state) == state_to_json(battle.state)
    finished, _ = auto_play(lib, save.run, restored)
    direct, _ = auto_play(lib, run, battle)
    assert finished == direct
