"""三方混戰在大世界（Phase 5B-M3；``docs/phases/Phase5計畫.md`` 第 20 節）。

遭遇表的 ``third`` → 陣容的第三方 → 開戰時 ``Team.THIRD``；源晶裂痕的陣容都是三方，主線第 ④ 步
（打贏源晶裂痕）因此一定是三方混戰。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import EncounterTable, encounter_table_problems
from trpg.shared.types import Team
from trpg.world.actions import BattleEndedEvent, BattleStartedEvent, FightAction, QuestStepDoneEvent
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.encounters import EncounterLineup, reinforce_lineup, roll_lineup
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SECT = ["sect_swordsman", "sect_acolyte"]


@pytest.mark.parametrize("seed", range(6))
def test_crystal_rift_lineups_are_three_way(library: ContentLibrary, seed: int) -> None:
    lineup = roll_lineup(library, make_encounter("crystal_rift", seed=seed, level=5))
    assert lineup.group in {"rift_wraiths", "rift_scavengers"}
    assert [m.unit for m in lineup.third] == SECT
    assert all(m.affix is None for m in lineup.third)


def test_old_lineup_without_third_still_loads() -> None:
    data = {"region": "cloud_ridge", "location": "x", "group": "g", "members": [{"unit": "bandit"}]}
    assert EncounterLineup.model_validate(data).third == ()


def test_battle_setup_puts_third_after_enemies(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    encounter = make_encounter("crystal_rift", seed=1, level=5)
    char = make_char(location="crystal_rift", pending_encounter=encounter)
    prepared = prepare_battle(library, char)
    teams = [u.team for u in prepared.setup.units]
    assert teams.count(Team.THIRD) == 2
    assert teams[-2:] == [Team.THIRD, Team.THIRD]
    assert [u.template.id for u in prepared.setup.units[-2:]] == SECT
    enemies = [u for u in prepared.setup.units if u.team is Team.ENEMY]
    assert len(enemies) == len(prepared.lineup.members)
    # 第三方照地點等級成長（同敵方）
    third_hp = prepared.setup.units[-2].template.max_hp
    assert third_hp > library.unit("sect_swordsman").max_hp


def test_reinforcements_only_join_the_enemy(library: ContentLibrary) -> None:
    encounter = make_encounter("rain_terraces", seed=0, level=2)
    lineup = roll_lineup(library, encounter)
    if lineup.group != "terrace_clash":
        encounter = next(
            make_encounter("rain_terraces", seed=s, level=2)
            for s in range(1, 50)
            if roll_lineup(library, make_encounter("rain_terraces", seed=s, level=2)).group
            == "terrace_clash"
        )
        lineup = roll_lineup(library, encounter)
    grown = reinforce_lineup(library, encounter, lineup, 1).lineup
    assert len(grown.members) == len(lineup.members) + 1
    assert grown.third == lineup.third
    # 6F-4d：梯田固定戰的敵方改成新手盜賊；增援仍只進敵方（第三方不變）
    assert {m.unit for m in grown.members} <= {"bandit_rookie", "sect_swordsman", "sect_acolyte"}


def test_third_rules_are_checked(library: ContentLibrary) -> None:
    table = library.world_encounters["cloud_ridge"]
    data = table.model_dump(mode="json")
    for group in data["groups"]:
        if group["id"] == "terrace_clash":
            group["third"] = ["bandit_captain", "sect_crane_archer", "nobody"]
    broken = EncounterTable.model_validate(data)
    problems = encounter_table_problems(
        broken, world_map=library.world_maps["cloud_ridge"], catalog=library.enemy_catalog()
    )
    assert any("terrace_clash：未知的單位 nobody" in p for p in problems)
    for group in data["groups"]:
        if group["id"] == "terrace_clash":
            group["third"] = ["bandit_captain", "sect_crane_archer", "frost_crane_archer"]
            group["units"] = ["bandit", "bandit_archer"]
    broken = EncounterTable.model_validate(data)
    problems = encounter_table_problems(
        broken, world_map=library.world_maps["cloud_ridge"], catalog=library.enemy_catalog()
    )
    assert any("terrace_clash：第三方不能有精英（bandit_captain）" in p for p in problems)
    assert any("terrace_clash：遠程 3 名" in p for p in problems)


def test_main_step_four_is_won_in_a_three_way_battle(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    quest = QuestState(quest="main_mist_rift", steps_done=3, started_at=NOON)
    base = make_char(location="crystal_rift", level=10, quests=(quest,))
    for seed in range(16):
        encounter = make_encounter("crystal_rift", seed=seed, level=5, from_location="north_slope")
        char = base.model_copy(update={"pending_encounter": encounter})
        result = world_step(
            library, make_world(), char, FightAction(steps=auto_steps(library, char)), NOON
        )
        ended = next(e for e in result.events if isinstance(e, BattleEndedEvent))
        if not ended.won:
            continue
        started = next(e for e in result.events if isinstance(e, BattleStartedEvent))
        assert [m.unit for m in started.lineup.third] == SECT
        done = [e.step for e in result.events if isinstance(e, QuestStepDoneEvent)]
        assert done == ["rift_battle"]
        return
    raise AssertionError("16 個種子都打不贏源晶裂痕的三方混戰")
