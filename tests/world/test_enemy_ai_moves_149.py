"""#149 補上的招，效用 AI 實際選得到（CB-2a；跑 AI，不只查資料）。

每招：把敵人放進空地圖對兩名英雄，打最多 ``MAX_ROUNDS`` 輪、``MAX_SEEDS`` 個種子，看 AI 有沒有放過。
頭目階段招：把該階段的招式組當成範本技能（不靠打進第 N 階段），只驗 AI 會不會選。
選不到的列在 ``RARELY_CHOSEN``（寫進 CB-2a 報告），不強求 AI 選。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import make_map, spawn
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events.skills import SkillUsed
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, with_phase_assets
from trpg.shared.types import Team

MAX_SEEDS = 40
MAX_ROUNDS = 8
HEROES = ("hero_fighter", "hero_archer")
PLAIN = "\n".join(["000000000"] * 9)

ADDED = (
    ("sect_acolyte", "skill_guardian_aegis"),
    ("sect_swordsman", "skill_rending_strike"),
    ("sect_array_disciple", "skill_pincer_strike"),
    ("sect_puppeteer", "skill_wil_void_pull"),
    ("sect_mist_swordsman", "skill_shadow_ambush"),
    ("mist_wolf", "skill_pincer_strike"),
    ("mountain_leopard", "skill_rending_strike"),
    ("stoneback_bear", "skill_bone_crusher"),
    ("shard_golem", "skill_quake_wave"),
    ("bandit", "skill_rending_strike"),
    ("bandit", "skill_venom_blade"),
    ("bandit_archer", "skill_rng_venom_arrow"),
    ("bandit_shieldbearer", "skill_taunting_roar"),
    ("bandit_captain", "skill_gale_kick"),
    ("bandit_captain", "skill_rending_strike"),
    ("ember_lizard", "skill_kindle_pop"),
    ("heart_ember_lizard", "skill_kindle_pop"),
    ("frost_ember_lizard", "skill_frost_touch"),
    ("fire_dust_bat", "skill_cinder_dive"),
    ("lava_tortoise", "skill_fire_bolt"),
    ("magma_slug", "skill_slime_glob"),
    ("lava_beetle", "skill_parry_riposte"),
    ("furnace_matriarch", "skill_ember_bite"),
    ("sulfur_beast", "skill_venom_gore"),
    ("scorched_colossus", "skill_bone_crusher"),
    ("molten_lord", "skill_lava_spout"),
    ("frost_crane_archer", "skill_frost_feather"),
)
BOSS_PHASE = (
    ("ashen_heart", "shell", "skill_ashen_oath"),
    ("sect_mist_lock_master", "sword_array", "skill_guardian_aegis"),
    ("sect_mist_lock_master", "return_to_one", "skill_execute"),
    ("rift_shard_lord", "three_pillars", "skill_shard_erosion"),
    ("rift_shard_lord", "three_pillars", "skill_spark_chain"),
)
AFFIXED = (
    ("mist_wolf", "mist_veiled", "skill_mist_shift"),
    ("sect_swordsman", "heart_linked", "skill_guardian_aegis"),
    ("ember_lizard", "hard_shelled", "skill_parry_riposte"),
)
RARELY_CHOSEN = frozenset(
    {
        # 引爆目標身上的燃燒：這個空地圖的戰鬥裡目標幾乎不會帶燃燒，AI 算出零收益（CB-2a 報告）
        ("ember_lizard", "skill_kindle_pop"),
        ("heart_ember_lizard", "skill_kindle_pop"),
    }
)


def _setup(library: ContentLibrary, template: UnitTemplate) -> BattleSetup:
    ally_at = ((0, 3), (0, 5))
    foe_at = ((3, 3), (3, 5))
    map_def = make_map(PLAIN, ally=ally_at, enemy=foe_at)
    spawns = [
        spawn(Team.ALLY, xy, name, skills=None) for xy, name in zip(ally_at, HEROES, strict=True)
    ]
    spawns += [spawn(Team.ENEMY, xy, template) for xy in foe_at]
    setup = BattleSetup(
        map=map_def, ruleset=library.ruleset, units=tuple(spawns), max_rounds=MAX_ROUNDS
    )
    return with_phase_assets(library, setup)


def _casts(library: ContentLibrary, template: UnitTemplate, skill: str) -> int:
    ai = UtilityAI(library.ai_profiles)
    setup = _setup(library, template)
    total = 0
    for seed in range(MAX_SEEDS):
        run = run_battle(setup, seed, ai)
        total += sum(1 for e in run.events if isinstance(e, SkillUsed) and e.skill_id == skill)
        if total:
            break
    return total


def _phase_template(library: ContentLibrary, unit: str, phase: str) -> UnitTemplate:
    base = library.units[unit]
    current = base.skills
    for entry in base.phases:
        current = entry.skills if entry.skills is not None else current
        if entry.id == phase:
            break
    tags = tuple(t for t in base.tags if t != "immovable")  # 空地圖：不能動的打不到人
    return base.model_copy(
        update={"skills": current, "phases": (), "speed": base.speed or 4, "tags": tags}
    )


def _assert_chosen(library: ContentLibrary, template: UnitTemplate, skill: str) -> None:
    key = (template.id.split("|")[0], skill)
    casts = _casts(library, template, skill)
    if key in RARELY_CHOSEN:
        return
    assert casts > 0, f"AI 在 {MAX_SEEDS} 個種子都沒有選 {skill}（{template.id}）"


@pytest.mark.parametrize(("unit", "skill"), ADDED)
def test_the_ai_picks_each_added_move(library: ContentLibrary, unit: str, skill: str) -> None:
    template = library.enemy_catalog().template(unit)
    assert skill in template.skills
    _assert_chosen(library, template, skill)


@pytest.mark.parametrize(("unit", "phase", "skill"), BOSS_PHASE)
def test_the_ai_picks_each_boss_phase_move(
    library: ContentLibrary, unit: str, phase: str, skill: str
) -> None:
    template = _phase_template(library, unit, phase)
    assert skill in template.skills
    _assert_chosen(library, template, skill)


@pytest.mark.parametrize(("unit", "affix", "skill"), AFFIXED)
def test_the_ai_picks_each_affix_move(
    library: ContentLibrary, unit: str, affix: str, skill: str
) -> None:
    catalog = library.enemy_catalog()
    template = catalog.with_affix(catalog.template(unit), affix)
    assert skill in template.skills
    _assert_chosen(library, template, skill)
