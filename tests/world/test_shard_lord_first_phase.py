"""CB-2d：真實的裂界門（``prepare_battle``）裡，碎晶之主三柱階段 AI 會選到替代招 ``spark_chain``。

``shock_follow`` 在 CB-2a 的模擬裡 0 次，這裡跑正式地圖、正式隊伍，不用空地圖。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import BossPhaseChanged
from trpg.engine.events.skills import SkillUsed
from trpg.engine.runner import run_battle
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.clock import day_phase
from trpg.world.party import default_party
from trpg.world.state import EncounterResult
from trpg.world.step import new_character

NOON = 1_793_592_000
LEVEL = 10
MAX_SEEDS = 12
BOSS = "rift_shard_lord"
REPLACEMENT = "skill_spark_chain"


def _casts_before_phase_two(library: ContentLibrary, seed: int) -> int:
    base = next(b.hero for b in library.builds.builds if b.id == "build_striker")
    grown, skills = grow_enemy(library, base, LEVEL)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1})
    season = library.world_season
    assert season is not None
    assert season.season_boss is not None
    encounter = EncounterResult(
        region="cloud_ridge",
        location="",
        level=LEVEL,
        battle_map=season.season_boss.battle_map,
        battle_seed=seed,
        weather="clear",
        day_phase=day_phase(NOON),
        at=NOON,
        season_boss=BOSS,
    )
    char = new_character(library, "sim", hero, region="cloud_ridge").model_copy(
        update={
            "level": LEVEL,
            "mercenaries": default_party(library),
            "generated_skills": skills,
            "pending_encounter": encounter,
        }
    )
    prepared = prepare_battle(library, char)
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    casts = 0
    for event in run.events:
        if isinstance(event, BossPhaseChanged):
            break
        if isinstance(event, SkillUsed) and event.skill_id.startswith(REPLACEMENT):
            casts += 1
    return casts


def test_the_ai_uses_the_replacement_in_the_real_three_pillars_phase(
    library: ContentLibrary,
) -> None:
    assert any(_casts_before_phase_two(library, seed) for seed in range(MAX_SEEDS))
