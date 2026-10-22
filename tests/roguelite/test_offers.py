"""升級與重骰的技能候選、裝備上限（Phase 3-5a）。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.content.skills import weapon_problem
from trpg.roguelite import ChoiceError, RunState, new_run
from trpg.roguelite.offers import equip_problems, make_offer, skill_defs, take_candidate
from trpg.roguelite.start import top_attribute
from trpg.roguelite.state import SkillOffer

BUILDS = ("build_push", "build_fire", "build_ranged", "build_healer", "build_tank")


def _offer(run: RunState) -> SkillOffer:
    return make_offer(library(), run, "level_up")


@pytest.mark.parametrize("build", BUILDS)
def test_offer_has_deepen_bridge_new_candidates(build: str) -> None:
    """Phase 3-24b2：候選來自共用產生器（加深、橋接、新方向），與武器相容、主角沒有、階級相符；
    off_route 仍標示縮放屬性與最高屬性不同的候選。"""
    lib = library()
    for seed in range(3):
        run = new_run(lib, build, seed)
        offer = _offer(run)
        top = top_attribute(run.hero.attributes)
        assert offer.top_attribute is top
        assert len(offer.candidates) == 3
        assert [t.kind for t in offer.tags] == ["deepen", "bridge", "new"]
        assert offer.off_route == tuple(
            i for i, s in enumerate(offer.candidates) if s.scaling_attr != top
        )
        weapon = lib.weapons[run.hero.weapon].weapon_class
        for skill in offer.candidates:
            assert weapon_problem(skill, weapon) is None
            assert skill.id not in run.hero.skills
            assert skill.tier == lib.roguelite.offer_tier(run.level)
        assert len({s.id for s in offer.candidates}) == 3


def test_offer_is_deterministic_and_depends_on_the_counter() -> None:
    run = new_run(library(), "build_push", 5)
    assert _offer(run) == _offer(run)
    later = run.model_copy(update={"offers_made": 1})
    assert _offer(later) != _offer(run)


def test_offer_tier_follows_the_level() -> None:
    run = new_run(library(), "build_push", 5).model_copy(update={"level": 5})
    assert {s.tier for s in _offer(run).candidates} == {library().roguelite.offer_tier(5)}


def test_skip_keeps_the_skills() -> None:
    run = new_run(library(), "build_fire", 2)
    assert take_candidate(library(), run, _offer(run), None, None) == run
    with pytest.raises(ChoiceError, match="沒有選候選"):
        take_candidate(library(), run, _offer(run), None, run.hero.skills[0])


def _with_free_slots(run: RunState) -> RunState:
    """只留前 2 個技能，讓任何候選都裝得下。"""
    hero = run.hero.model_copy(update={"skills": run.hero.skills[:2]})
    return run.model_copy(update={"hero": hero})


def _composed_offer(run: RunState) -> tuple[RunState, SkillOffer, int]:
    """找一組有「組合器」來源候選的候選（回傳該組的一輪狀態、候選與索引）。"""
    for n in range(20):
        current = run.model_copy(update={"offers_made": n})
        offer = _offer(current)
        for i, tag in enumerate(offer.tags):
            if tag.source == "composer":
                return current, offer, i
    raise AssertionError("找不到組合器來源的候選")


def test_pick_adds_the_skill_and_its_definition() -> None:
    lib = library()
    run, offer, index = _composed_offer(_with_free_slots(new_run(lib, "build_fire", 2)))
    after = take_candidate(lib, run, offer, index, None)
    assert after.hero.skills == (*run.hero.skills, offer.candidates[index].id)
    assert after.generated_skills == (offer.candidates[index],)
    assert lib.ruleset.with_skills(after.generated_skills).skill_def(offer.candidates[index].id)


def test_picking_a_pool_skill_stores_no_definition() -> None:
    """Phase 3-24b2：候選可以是技能池的手寫技能；裝上時不存定義（內容庫就有）。"""
    lib = library()
    run = _with_free_slots(new_run(lib, "build_fire", 2))
    for n in range(20):
        current = run.model_copy(update={"offers_made": n})
        offer = _offer(current)
        pool = [i for i, t in enumerate(offer.tags) if t.source == "pool"]
        if pool:
            after = take_candidate(lib, current, offer, pool[0], None)
            assert offer.candidates[pool[0]].id in lib.skills
            assert after.hero.skills[-1] == offer.candidates[pool[0]].id
            assert after.generated_skills == ()
            return
    raise AssertionError("找不到技能池來源的候選")


def test_full_slots_require_a_replacement() -> None:
    lib = library()
    run = new_run(lib, "build_push", 1)  # 主動欄位已滿（6 個）
    offer = _offer(run)
    active = next(i for i, s in enumerate(offer.candidates) if s.kind == "active")
    with pytest.raises(ChoiceError, match=r"超過欄位上限.*replace"):
        take_candidate(lib, run, offer, active, None)
    target = next(s for s in run.hero.skills if lib.skills[s].kind == "active")
    after = take_candidate(lib, run, offer, active, target)
    position = run.hero.skills.index(target)
    assert after.hero.skills[position] == offer.candidates[active].id
    assert target not in after.hero.skills
    assert not equip_problems(lib, skill_defs(lib, after, after.hero.skills))


def test_bad_index_and_unknown_replacement_are_rejected() -> None:
    lib = library()
    run = new_run(lib, "build_push", 1)
    offer = _offer(run)
    with pytest.raises(ChoiceError, match="候選索引"):
        take_candidate(lib, run, offer, 3, None)
    with pytest.raises(ChoiceError, match="主角沒有技能"):
        take_candidate(lib, run, offer, 0, "skill_nobody")


def test_equip_limits_are_six_three_one() -> None:
    lib = library()
    slots = lib.ruleset.core.skill_slots
    assert (slots.active, slots.passive, slots.reaction) == (6, 3, 1)
    actives = [s for s in lib.skills.values() if s.kind == "active" and s.rule_change_id is None]
    reactions = [s for s in lib.skills.values() if s.kind == "reaction"]
    assert not equip_problems(lib, actives[:6])
    assert equip_problems(lib, actives[:7])
    assert equip_problems(lib, reactions[:2])


def test_replaced_generated_skills_are_dropped() -> None:
    lib = library()
    run, offer, index = _composed_offer(_with_free_slots(new_run(lib, "build_fire", 2)))
    first = take_candidate(lib, run, offer, index, None)
    gen = first.generated_skills[0]
    for n in range(run.offers_made + 1, run.offers_made + 30):
        second_offer = _offer(first.model_copy(update={"offers_made": n}))
        picks = [
            i
            for i, (s, t) in enumerate(zip(second_offer.candidates, second_offer.tags, strict=True))
            if s.kind == gen.kind and s.id != gen.id and t.source == "composer"
        ]
        if picks:
            second = take_candidate(lib, first, second_offer, picks[0], gen.id)
            assert [s.id for s in second.generated_skills] == [second_offer.candidates[picks[0]].id]
            return
    raise AssertionError("找不到可替換的生成技能候選")
