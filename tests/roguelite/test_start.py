"""開新一輪：主角、開局配點、每一場的安排（Phase 3-5a）。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.roguelite import ChoiceError, new_run
from trpg.roguelite.start import make_plan, primary_attribute, top_attribute
from trpg.roguelite.state import BattleNode
from trpg.shared.types import Attribute


def test_new_run_uses_the_build_hero_with_base_attributes_and_four_free_points() -> None:
    lib = library()
    run = new_run(lib, "build_push", 3, {Attribute.STR: 3, Attribute.CON: 1})
    build = lib.builds.by_id()["build_push"].hero
    assert run.hero.skills == build.skills
    assert run.hero.weapon == build.weapon
    assert run.hero.attributes[Attribute.STR] == 13
    assert run.hero.attributes[Attribute.CON] == 11
    assert sum(run.hero.attributes.values()) == 6 * 10 + 4
    # 體質加 1 點：起始 HP ＝ build 英雄原本的 HP ＋ 1 × 每點體質的 HP（Phase 3-7）
    core = lib.ruleset.core
    assert (run.hp, run.mana) == (
        core.template_max_hp(build) + core.hp_per_con_point,
        core.resources.max_for(
            "mana", build.max_mana, run.hero.attributes
        ),  # ×法力上限倍率（BAL-4b）
    )
    assert run.hp == run.max_hp_in(core)
    assert run.source == lib.ruleset.core.source_min_at_start
    assert (run.level, run.xp) == (1, 0)
    assert run.node == BattleNode(index=1)


def test_default_allocation_goes_to_the_most_used_scaling_attribute() -> None:
    lib = library()
    run = new_run(lib, "build_fire", 1)
    skills = [lib.skills[s] for s in run.hero.skills]
    attr = primary_attribute(skills)
    assert run.hero.attributes[attr] == 14
    assert top_attribute(run.hero.attributes) is attr


@pytest.mark.parametrize(
    ("allocation", "message"),
    [
        ({Attribute.STR: 3}, "必須分配 4 點"),
        ({Attribute.STR: 5, Attribute.DEX: -1}, "不可為負"),
    ],
)
def test_bad_allocation_is_rejected(allocation: dict[Attribute, int], message: str) -> None:
    with pytest.raises(ChoiceError, match=message):
        new_run(library(), "build_push", 1, allocation)


def test_unknown_build_is_rejected() -> None:
    with pytest.raises(ChoiceError, match="未知的 build"):
        new_run(library(), "build_nobody", 1)


def test_plan_has_distinct_map_types_then_the_fixed_boss() -> None:
    lib = library()
    rules = lib.roguelite
    for seed in range(20):
        plan = make_plan(lib, seed)
        assert len(plan) == rules.battles + 1
        normal, boss = plan[:-1], plan[-1]
        types = [lib.map(p.map_id).archetype for p in normal]
        assert len(set(types)) == rules.battles
        assert all(p.map_id in rules.map_pool and not p.boss for p in normal)
        assert boss.boss and boss.map_id == rules.boss.map
        assert boss.enemies == rules.boss.enemies
        for p in normal:
            assert p.enemies in rules.encounters[p.index - 1].options


def test_plan_is_derived_from_the_seed() -> None:
    lib = library()
    assert make_plan(lib, 7) == make_plan(lib, 7)
    assert make_plan(lib, 7) != make_plan(lib, 8)
    seeds = [p.seed for p in make_plan(lib, 7)]
    assert len(set(seeds)) == len(seeds)


def test_run_state_round_trips_through_json() -> None:
    run = new_run(library(), "build_ranged", 11)
    again = type(run).model_validate_json(run.model_dump_json())
    assert again == run
    assert again.model_dump_json() == run.model_dump_json()
