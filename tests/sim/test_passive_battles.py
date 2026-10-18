"""Phase 2E-1 3.9：隨機被動的整場戰鬥——不會無限觸發、深度不超過上限、可由紀錄完整重播。"""

from __future__ import annotations

from functools import cache

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.skillgen.helpers import lib
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import BattleSetup
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import SkillTriggered, TriggerLimitReached
from trpg.engine.runner import BattleLog, BattleRun, replay, run_battle
from trpg.shared.types import Team
from trpg.sim.skill_fuzz import ARENA_MAP, _spawn, _unit_template
from trpg.skillgen.random_composer import compose_random_skill


def _setup(ally_skills: list[SkillDef], enemy_skills: list[SkillDef]) -> BattleSetup:
    library = lib()
    extra = {s.id: s for s in (*ally_skills, *enemy_skills) if s.id not in library.skills}
    rules = library.ruleset.model_copy(
        update={"skills": SkillTable(skills=(*library.ruleset.skills.skills, *extra.values()))}
    )
    rules.model_post_init(None)
    hero = _unit_template(
        library, "hero_mage", skills=tuple(s.id for s in ally_skills), reactions=True, mana=99
    )
    foe = _unit_template(
        library, "bandit", skills=tuple(s.id for s in enemy_skills), reactions=True, mana=99
    )
    units = (
        _spawn(library, hero, Team.ALLY, None),
        _spawn(library, hero, Team.ALLY, None),
        _spawn(library, foe, Team.ENEMY, None),
        _spawn(library, foe, Team.ENEMY, None),
    )
    return BattleSetup(map=library.map(ARENA_MAP), ruleset=rules, units=units, max_rounds=8)


@cache
def _passive(seed: int) -> SkillDef:
    return compose_random_skill(seed, skeleton="passive", rarity="epic")


def _passives(seeds: list[int], offset: int) -> list[SkillDef]:
    skills: dict[str, SkillDef] = {}
    for seed in seeds:
        skill = _passive(seed + offset)
        skills[skill.id] = skill
    return list(skills.values())


def _check(run: BattleRun, depth_limit: int) -> int:
    triggered = [e for e in run.events if isinstance(e, SkillTriggered)]
    assert all(1 <= e.trigger_depth <= depth_limit for e in triggered)
    assert all(e.depth == depth_limit + 1 for e in run.events if isinstance(e, TriggerLimitReached))
    return len(triggered)


@settings(
    max_examples=12,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    ally=st.lists(st.integers(0, 30), min_size=1, max_size=2, unique=True),
    enemy=st.lists(st.integers(100, 130), min_size=1, max_size=2, unique=True),
    battle_seed=st.integers(0, 10_000),
)
def test_random_passives_never_loop_and_replay_exactly(
    ally: list[int], enemy: list[int], battle_seed: int
) -> None:
    setup = _setup(_passives(ally, 0), _passives(enemy, 0))
    limit = setup.ruleset.core.max_trigger_depth
    run = run_battle(setup, battle_seed, UtilityAI(lib().ai_profiles), max_actions=2000)
    assert run.state.ended
    _check(run, limit)
    again = replay(setup, battle_seed, run.actions)
    assert again.state == run.state
    assert again.events == run.events
    # 紀錄 JSON 來回之後仍能重播
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    assert replay(log.setup, log.seed, log.actions).state == run.state


def test_mutual_thorn_skin_battle_ends_and_respects_the_depth_limit() -> None:
    """雙方都有 on_damaged 反傷：戰鬥會結束、深度不超過上限。"""
    thorn = lib().skills["skill_thorn_skin"]
    other = thorn.model_copy(update={"id": "skill_thorn_skin_b"})
    setup = _setup([thorn], [other])
    run = run_battle(setup, 5, UtilityAI(lib().ai_profiles), max_actions=2000)
    assert run.state.ended
    assert _check(run, setup.ruleset.core.max_trigger_depth) > 0
