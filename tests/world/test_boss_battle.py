"""雲頂觀 Boss 戰的大世界接線（Phase 5F-2；``docs/phases/Phase5計畫.md`` 34.6）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import make_encounter
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.encounters import roll_lineup
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]
BOSS = "sect_mist_lock_master"


def test_summit_location_uses_boss_map_and_court(library: ContentLibrary) -> None:
    places = library.world_maps["cloud_ridge"].location_by_id()
    assert places["cloud_summit"].battle_maps == ("cloud_summit",)
    lineup = roll_lineup(library, make_encounter("cloud_summit", seed=3, level=6))
    assert [(m.unit, m.affix) for m in lineup.members] == [
        (BOSS, None),
        ("sect_array_disciple", None),
        ("sect_array_disciple", None),
        ("sect_summit_array_stone", None),
    ]


def test_grow_enemy_renames_phase_skills(library: ContentLibrary) -> None:
    grown, skills = grow_enemy(library, library.unit(BOSS), 6)
    renamed = {s.id for s in skills}
    for phase in grown.phases:
        for skill_id in phase.skills or ():
            assert skill_id in library.skills or skill_id in renamed
    base = library.unit(BOSS)
    assert [p.id for p in grown.phases] == [p.id for p in base.phases]
    # 1 階的技能在 6 級升階改名；2 階的不動
    assert any(s.endswith("_t2") for p in grown.phases for s in p.skills or ())


def test_prepare_battle_adds_grown_phase_assets(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    encounter = make_encounter("cloud_summit", seed=5, battle_map="cloud_summit", level=6)
    char = make_char(location="cloud_summit", pending_encounter=encounter, level=6)
    prepared = prepare_battle(library, char)
    setup = prepared.setup
    assert setup.map.id == "cloud_summit"
    assert setup.map.objective.leader_retreat
    assert sorted(setup.phase_weathers) == ["clear", "fog"]
    walker = setup.spawn_templates["sect_mist_walker"].template
    assert walker.level == prepared.enemy_level == 6
    boss = next(u for u in setup.units if u.template.id == BOSS)
    assert boss.team is Team.ENEMY
    for phase in boss.template.phases:  # 階段技能組都在規則包裡
        for skill_id in phase.skills or ():
            setup.ruleset.skill_def(skill_id)
    run = run_battle(setup, prepared.seed, UtilityAI(library.ai_profiles))
    assert run.state.ended
