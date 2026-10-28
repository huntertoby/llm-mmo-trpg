"""種族技的整場戰鬥（Phase 3R-2）：AI 會用、同種子重播一致、設定種族的入口。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.race_helpers import all_races
from trpg.engine import UseRaceSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.setup import BattleSetup, BattleSetupError, assign_races, build_setup
from trpg.shared.types import Team
from trpg.sim.lineup import default_lineup

MAP = "dark_forest"
ALWAYS_USED = ("elf", "fox", "dragonkin", "dwarf", "cyborg", "fiend", "seafolk")
"""在 dark_forest 的預設陣容裡，AI 的使用條件（ai/race.py）三個種子內一定會觸發的種族。"""


def _setup(races: list[str | None]) -> BattleSetup:
    lib = library()
    allies, enemies = default_lineup(lib, MAP)
    setup = build_setup(lib, MAP, allies, enemies, max_rounds=12)
    return assign_races(setup, Team.ALLY, races)


def _used(race: str) -> tuple[int, list[tuple[BattleSetup, int]]]:
    ai = UtilityAI(library().ai_profiles)
    total, runs = 0, []
    for seed in range(3):
        setup = _setup([race, race, race])
        result = run_battle(setup, seed, ai)
        total += sum(isinstance(a, UseRaceSkill) for a in result.actions)
        runs.append((setup, seed))
    return total, runs


@pytest.mark.parametrize("race", ALWAYS_USED)
def test_ai_uses_the_race_skill_and_the_replay_matches(race: str) -> None:
    used, runs = _used(race)
    assert used > 0, f"{race} 的種族技從來沒有被 AI 用過"
    ai = UtilityAI(library().ai_profiles)
    setup, seed = runs[0]
    original = run_battle(setup, seed, ai)
    again = replay(setup, seed, original.actions)
    assert again.events == original.events  # 含種族技的重播一致
    assert run_battle(setup, seed, ai).actions == original.actions  # 同種子同決策


def test_every_race_finishes_a_battle_without_errors() -> None:
    ai = UtilityAI(library().ai_profiles)
    for race in all_races():
        result = run_battle(_setup([race.id, None, None]), 5, ai)
        assert result.state.ended, race.id


def test_race_skill_actions_survive_the_json_log() -> None:
    ai = UtilityAI(library().ai_profiles)
    setup = _setup(["fox", "fox", "fox"])
    original = run_battle(setup, 1, ai)
    log = original.to_log()
    assert any(step.type == "use_race_skill" for step in log.actions)
    restored = BattleLog.model_validate_json(log.model_dump_json())
    assert restored.actions == log.actions


def test_assign_races_rejects_unknown_races_and_too_many() -> None:
    lib = library()
    allies, enemies = default_lineup(lib, MAP)
    setup = build_setup(lib, MAP, allies, enemies)
    with pytest.raises(BattleSetupError, match="未知的種族"):
        assign_races(setup, Team.ALLY, ["elfin"])
    with pytest.raises(BattleSetupError, match="種族指定過多"):
        assign_races(setup, Team.ALLY, ["elf"] * 9)


def test_assign_races_skips_blanks_and_keeps_the_library_templates() -> None:
    lib = library()
    allies, enemies = default_lineup(lib, MAP)
    setup = build_setup(lib, MAP, allies, enemies)
    raced = assign_races(setup, Team.ALLY, ["", "elf"])
    mine = [s for s in raced.units if s.team is Team.ALLY]
    assert [s.template.race for s in mine] == [None, "elf", None]
    assert all(lib.unit(a).race is None for a in allies)  # 內容庫的範本不變
