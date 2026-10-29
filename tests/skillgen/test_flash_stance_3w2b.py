"""Phase 3W-2b 第 1、2 點：姿態的每招維持費與元素姿態（轉型、費用類、修正類）。

行為一致：每個元素在 2、3 階都轉得成同元素姿態且落在預算窗；卡片的數字＝實戰（元素加成、維持費）；
費用類 ±1 搭配效果升降且分數不低於變化前；修正類嚴格變強。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import caster_template, library, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1
from trpg.content.skills import SkillDef
from trpg.engine.rules.statuses import damage_dealt_permille
from trpg.engine.state import StatusInstance
from trpg.narrative.status_info import status_rules
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash import apply_variation, at_tier
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.validate import validate_skill

ELEMENT_SKILLS = ("fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow")
TRANSFORM = Variation(source="transform", template="to_stance", category="transform")
LIGHT = Variation(source="minor", template="stance_cost_light", category="cost")
HEAVY = Variation(source="minor", template="stance_cost_heavy", category="cost")
POTENCY = Variation(source="minor", template="stance_potency", category="modifier")


def _sources(element: str) -> list[SkillDef]:
    """這個元素的主動傷害技（依 ID 排序）。"""
    lib = library()
    wanted = Element(element)
    return [
        skill
        for skill in sorted(lib.skills.values(), key=lambda s: s.id)
        if skill.kind == "active"
        and not skill.followup
        and [e for e in skill.effects if e.type == "damage" and e.element is wanted]
    ]


def _stance(element: str, tier: int) -> SkillDef | None:
    """這個元素的技能（取第一個轉得成姿態的）在 ``tier`` 階轉成的姿態。"""
    lib = library()
    for source in _sources(element):
        done = apply_variation(lib, at_tier(source, tier), TRANSFORM, bonus=120, rng=Rng(7))
        if done is not None:
            return done
    return None


def test_every_element_has_a_five_level_ladder_in_the_data() -> None:
    lib = library()
    ladders = lib.flash.stance_ladders
    assert set(ladders) == {"physical", *ELEMENT_SKILLS, "guard", "flame", "frost"}
    statuses = lib.ruleset.statuses.by_id()
    for element in ("physical", *ELEMENT_SKILLS):
        ladder = ladders[element]
        assert len(ladder) == 5
        points = [statuses[s].budget_points or 0 for s in ladder]
        assert points == sorted(points) and len(set(points)) == 5
        permille = [statuses[s].element_dealt_permille for s in ladder]
        assert permille == sorted(permille) and len(set(permille)) == 5  # 隨級數變強
        for status in ladder:
            assert statuses[status].stance and statuses[status].element_dealt is Element(element)


@pytest.mark.parametrize("tier", [2, 3])
@pytest.mark.parametrize("element", ELEMENT_SKILLS)
def test_element_skill_transforms_into_its_own_element_stance_within_budget(
    element: str, tier: int
) -> None:
    lib = library()
    stance = _stance(element, tier)
    assert stance is not None, (element, tier)
    assert stance.kind == "stance" and stance.stance_upkeep >= 1
    assert stance.effects[0].status in lib.flash.stance_ladders[element]
    assert validate_skill(stance, lib) == []
    report = skill_budget(stance, lib)
    assert report.ratio >= report.min_ratio and report.ratio <= report.max_ratio
    # 這個階級下的元素姿態要比 1 階的更強（隨角色階級變強）
    status = lib.ruleset.status_def(stance.effects[0].status)
    assert status.element_dealt_permille >= 1100


def test_higher_tier_gives_a_stronger_stance() -> None:
    lib = library()
    for element in ELEMENT_SKILLS:
        low, high = _stance(element, 2), _stance(element, 3)
        assert low is not None and high is not None
        assert low.effects[0].status is not None and high.effects[0].status is not None
        low_status = lib.ruleset.status_def(low.effects[0].status)
        high_status = lib.ruleset.status_def(high.effects[0].status)
        assert high_status.element_dealt_permille > low_status.element_dealt_permille


def test_no_element_attack_becomes_the_physical_stance() -> None:
    lib = library()
    plain = next(
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.category == "weapon"
        and not s.followup
        and all(e.element in (None, Element.PHYSICAL) for e in s.effects if e.type == "damage")
        and any(e.type == "damage" for e in s.effects)
        and not [t for t in s.tags if t in ELEMENT_SKILLS]
    )
    got = apply_variation(lib, at_tier(plain, 2), TRANSFORM, bonus=120, rng=Rng(7))
    assert got is not None and got.effects[0].status in lib.flash.stance_ladders["physical"]


def test_support_skill_still_gets_a_defensive_stance() -> None:
    lib = library()
    heals = [
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and [e.type for e in s.effects] == ["heal"] and not s.followup
    ]
    assert heals
    defensive = {"stance_bulwark", "stance_guard", "stance_ironwall", "stance_bastion"}
    for tier in (1, 2, 3):
        got = [
            apply_variation(lib, at_tier(h, tier), TRANSFORM, bonus=120, rng=Rng(7)) for h in heals
        ]
        made = [g for g in got if g is not None]
        assert made, tier  # 每個階級至少有一招輔助技轉得成防守姿態
        assert all(g.effects[0].status in defensive for g in made)


@pytest.mark.parametrize("tier", [2, 3])
def test_card_numbers_match_the_engine_for_every_level(tier: int) -> None:
    """卡片（狀態規則句）寫的元素加成＝引擎實際用的倍率。"""
    lib = library()
    for element in ("physical", *ELEMENT_SKILLS):
        for status_id in lib.flash.stance_ladders[element]:
            status = lib.ruleset.status_def(status_id)
            text = "".join(status_rules(status, lib))
            assert f"×{status.element_dealt_permille / 10:g}%" in text
    del tier


@pytest.mark.parametrize("tier", [2, 3])
def test_cost_light_and_heavy_trade_upkeep_for_effect_without_losing_power(tier: int) -> None:
    lib = library()
    seen_light = seen_heavy = 0
    for element in ELEMENT_SKILLS:
        stance = _stance(element, tier)
        assert stance is not None
        before = budget_power(stance, lib)
        ladder = lib.flash.stance_ladders[element]
        level = ladder.index(stance.effects[0].status)
        light = apply_variation(lib, stance, LIGHT, bonus=160, rng=Rng(3), replaced=None)
        heavy = apply_variation(lib, stance, HEAVY, bonus=160, rng=Rng(3), replaced=None)
        if light is not None:
            seen_light += 1
            assert light.stance_upkeep == stance.stance_upkeep - 1
            assert ladder.index(light.effects[0].status) < level  # 效果降低
            assert budget_power(light, lib) >= before
            assert validate_skill(light, lib) == []
        if heavy is not None:
            seen_heavy += 1
            assert heavy.stance_upkeep == stance.stance_upkeep + 1
            assert ladder.index(heavy.effects[0].status) > level  # 效果提高
            assert budget_power(heavy, lib) >= before
            assert validate_skill(heavy, lib) == []
    assert seen_light >= 4 and seen_heavy >= 4, (seen_light, seen_heavy)


@pytest.mark.parametrize("tier", [2, 3])
def test_stance_potency_is_strictly_stronger_with_the_same_upkeep(tier: int) -> None:
    lib = library()
    done = 0
    for element in ELEMENT_SKILLS:
        stance = _stance(element, tier)
        assert stance is not None
        got = apply_variation(lib, stance, POTENCY, bonus=160, rng=Rng(3))
        if got is None:
            continue
        done += 1
        assert got.stance_upkeep == stance.stance_upkeep
        assert budget_power(got, lib) > budget_power(stance, lib)
        assert stance.effects[0].status is not None and got.effects[0].status is not None
        old = lib.ruleset.status_def(stance.effects[0].status)
        new = lib.ruleset.status_def(got.effects[0].status)
        assert new.element_dealt_permille > old.element_dealt_permille
    assert done >= 4


def test_stance_templates_only_apply_to_stances() -> None:
    lib = library()
    bolt = at_tier(_sources("fire")[0], 2)
    for variation in (LIGHT, HEAVY, POTENCY):
        assert apply_variation(lib, bolt, variation, bonus=40, rng=Rng(1)) is None


def test_engine_multiplier_for_each_ladder_level_matches_the_data() -> None:
    lib = library()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([], max_hp=99)),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=99)),
        ],
    )
    unit = state.units[U1]
    for element in ("physical", *ELEMENT_SKILLS):
        for status_id in lib.flash.stance_ladders[element]:
            unit.statuses = [StatusInstance(status_id=status_id)]
            wanted = lib.ruleset.status_def(status_id).element_dealt_permille
            assert damage_dealt_permille(lib.ruleset, unit, Element(element)) == wanted
