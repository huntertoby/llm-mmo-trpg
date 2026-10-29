"""Phase 3W-9：一輪裡的角色升階重算、手寫技能換 ID、候選照角色階級、舊存檔（``/10``）轉換。"""

from __future__ import annotations

import json

from tests.roguelite.helpers import library
from trpg.content.skills import SkillDef
from trpg.roguelite import (
    SAVE_FORMAT,
    RunSave,
    dumps_save,
    loads_save,
    new_dev_run,
    new_keyword_run,
    next_node,
    upgrade_save,
)
from trpg.roguelite.battle import SavedBattle
from trpg.roguelite.offers import at_run_tier, candidate_request, library_base, skill_defs
from trpg.roguelite.retier import run_tier, sync_skill_tier
from trpg.roguelite.state import LevelUpNode, RunState
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.skill_tier import character_tier
from trpg.skillgen.validate import validate_skill

LIB = library()
HANDWRITTEN = "skill_fire_bolt"


def _run() -> RunState:
    return new_keyword_run(LIB, "fire_staff", ("ignite", "charged"), 3)


def _owned(run: RunState) -> list[SkillDef]:
    return skill_defs(LIB, run, (*run.hero.skills, *run.bench))


def _level_to(run: RunState, level: int) -> RunState:
    """升到 ``level`` 的前一級，留一次升級給 ``next_node``。"""
    return run.model_copy(update={"level": level - 1, "levels_pending": 1})


def test_a_new_run_starts_at_character_tier_one() -> None:
    run = _run()
    assert run.skill_tier == character_tier(LIB, 1) == 1
    assert all(s.tier == 1 for s in _owned(run))


def test_crossing_a_tier_retunes_every_skill_between_battles() -> None:
    run = _run()
    second = next(lv for lv in range(2, 10) if character_tier(LIB, lv) == 2)
    before = {s.id: budget_power(s, LIB) for s in _owned(run)}
    after = next_node(LIB, _level_to(run, second))
    assert isinstance(after.node, LevelUpNode)
    assert after.skill_tier == 2 and run_tier(LIB, after) == 2
    assert after.node.offer.tier == 2
    for skill in _owned(after):
        assert skill.tier == 2
        assert budget_power(skill, LIB) >= before[skill.id]  # 不低於升階前
        assert validate_skill(skill, LIB) == []
    for candidate in after.node.offer.candidates:
        assert candidate.tier == 2


def test_a_level_up_without_a_tier_change_keeps_the_skills() -> None:
    run = _run()
    after = next_node(LIB, run.model_copy(update={"levels_pending": 1}))
    if character_tier(LIB, 2) == 1:
        assert after.generated_skills == run.generated_skills
        assert after.hero.skills == run.hero.skills


def test_handwritten_skills_become_tier_copies_and_keep_their_flash_state() -> None:
    run = _run()
    hero = run.hero.model_copy(update={"skills": (*run.hero.skills, HANDWRITTEN)})
    run = run.model_copy(
        update={
            "hero": hero,
            "flash": {HANDWRITTEN: acquire(HANDWRITTEN).model_copy(update={"used": True})},
            "level": 3,
            "skill_tier": 1,
        }
    )
    synced = sync_skill_tier(LIB, run)
    copy_id = f"{HANDWRITTEN}_t{character_tier(LIB, 3)}"
    assert copy_id in synced.hero.skills and HANDWRITTEN not in synced.hero.skills
    assert set(synced.flash) == {copy_id} and synced.flash[copy_id].used
    copy = synced.generated(copy_id)
    assert copy is not None and copy.tier == character_tier(LIB, 3)
    assert library_base(LIB, copy_id) == HANDWRITTEN
    assert HANDWRITTEN in candidate_request(LIB, synced).exclude  # 候選不再出原本那招
    assert budget_power(copy, LIB) >= budget_power(LIB.skills[HANDWRITTEN], LIB)
    again = sync_skill_tier(LIB, synced.model_copy(update={"level": 5, "skill_tier": 2}))
    assert f"{HANDWRITTEN}_t3" in again.hero.skills  # 再升階換成新階級的後綴


def test_pool_candidates_are_retuned_to_the_character_tier() -> None:
    """手寫池退回的候選（原本的階級）照角色階級重配，卡片上的數字就是拿到後的數字（3W-4 #8）。"""
    skill = LIB.skills[HANDWRITTEN]
    moved = at_run_tier(LIB, skill, 3)
    assert moved.id == f"{HANDWRITTEN}_t3" and moved.tier == 3
    assert validate_skill(moved, LIB) == []
    assert at_run_tier(LIB, skill, skill.tier) is skill


def _old_text(run: RunState, battle: SavedBattle | None = None) -> str:
    raw = json.loads(dumps_save(RunSave(run_id="old", run=run, battle=battle)))
    raw["format"] = "trpg-run/10"
    del raw["run"]["skill_tier"]
    return json.dumps(raw)


def test_old_saves_are_upgraded_between_battles() -> None:
    run = new_dev_run(LIB, next(iter(LIB.dev_starters.by_id())), 2)
    old = run.model_copy(update={"level": 5})
    loaded = loads_save(_old_text(old))
    assert loaded.format == SAVE_FORMAT == "trpg-run/12"
    assert loaded.run.skill_tier is None
    upgraded = upgrade_save(LIB, loaded)
    tier = character_tier(LIB, 5)
    assert upgraded.run.skill_tier == tier
    assert all(s.tier == tier for s in _owned(upgraded.run))
    assert upgrade_save(LIB, upgraded) == upgraded  # 已是新格式：不變
    back = loads_save(dumps_save(upgraded))
    assert back.run == upgraded.run


def test_old_saves_in_battle_wait_for_the_next_node() -> None:
    run = _run().model_copy(update={"level": 5})
    battle = SavedBattle(index=1, seed=run.plan_of(1).seed, steps=[], orders=[])
    loaded = loads_save(_old_text(run, battle))
    assert upgrade_save(LIB, loaded) == loaded  # 戰鬥中：技能不動（重播用存檔當時的技能）
    synced = sync_skill_tier(LIB, loaded.run)
    assert synced.skill_tier == character_tier(LIB, 5)
