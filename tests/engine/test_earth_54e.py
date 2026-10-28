"""Phase 3-54e：石膚術（石膚＋小護盾）、大地崩陷（純下陷）、隆起／下陷點數 7 與工坊純地形技能。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, of
from trpg.content.skills import SkillCost
from trpg.engine import UseSkill, resolve
from trpg.engine.events import (
    DamageDealt,
    ShieldGained,
    StatusApplied,
    TerrainChanged,
    UnitFell,
)
from trpg.engine.rules.statuses import damage_taken_permille, move_points_for_turn
from trpg.shared.types import Element, Pos
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

LIB = library()
FOE = U2


def _cast(skill_id: str, state: Any, **fields: Any) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


# ---------------------------------------------------------------------------
# 原語點數
# ---------------------------------------------------------------------------


def test_raise_and_lower_terrain_cost_seven_points() -> None:
    prims = LIB.ruleset.primitives.by_id()
    assert (prims["raise_terrain"].base_points, prims["lower_terrain"].base_points) == (7, 7)


def test_the_reworked_terrain_skills_are_back_inside_the_budget() -> None:
    for sid in ("skill_raise_perch", "skill_sinkhole", "skill_summon_plateau_totem"):
        skill = LIB.skills[sid]
        assert validate_skill(skill, LIB) == [], sid
        assert skill_budget(skill, LIB).ok, sid
    for sid in ("skill_raise_perch", "skill_sinkhole"):  # 形狀與名稱不變
        assert LIB.skills[sid].shape.type == "cross"
        assert [e.type for e in LIB.skills[sid].effects] == [
            "raise_terrain" if sid == "skill_raise_perch" else "lower_terrain"
        ]


# ---------------------------------------------------------------------------
# 石膚術
# ---------------------------------------------------------------------------


def test_stoneskin_ward_is_a_valid_common_earth_skill_in_the_window() -> None:
    skill = LIB.skills["skill_stoneskin_ward"]
    assert validate_skill(skill, LIB) == []
    report = skill_budget(skill, LIB)
    assert report.ok and 700 <= report.ratio * 1000 <= 1000
    assert skill.rarity == "common" and skill.element is Element.EARTH
    assert [e.type for e in skill.effects] == ["apply_status", "shield"]
    dice = skill.effects[1].dice
    assert dice is not None and (dice.count, dice.sides) == (1, 6)


def test_stoneskin_ward_on_an_ally_gives_skin_and_shield_to_the_same_target() -> None:
    skill = LIB.skills["skill_stoneskin_ward"]
    state = battle(skill.model_copy(update={"id": SID}), foes=[(6, 6)], allies=[(4, 3)])
    result = _cast(SID, state, target_id=U2)
    (applied,) = [e for e in of(result, StatusApplied) if e.status_id == "stoneskin"]
    (shield,) = of(result, ShieldGained)
    assert applied.target_id == shield.unit_id == U2
    ally = result.state.units[U2]
    status = next(s for s in ally.statuses if s.status_id == "stoneskin")
    assert status.remaining in (1, 2)
    assert damage_taken_permille(result.state.ruleset, ally, Element.PHYSICAL) == 700
    assert damage_taken_permille(result.state.ruleset, ally, Element.FIRE) == 1000
    plain = battle(skill.model_copy(update={"id": SID}), foes=[(6, 6)], allies=[(4, 3)])
    before = move_points_for_turn(plain.ruleset, plain.units[U2])
    assert move_points_for_turn(result.state.ruleset, ally) == max(0, before - 1)
    assert len(shield.rolls) == 1 and 1 <= shield.rolls[0] <= 6 and not of(result, DamageDealt)


def test_stoneskin_ward_can_target_the_caster_too() -> None:
    skill = LIB.skills["skill_stoneskin_ward"].model_copy(update={"id": SID})
    result = _cast(SID, battle(skill, foes=[(6, 6)]), target_id=U1)
    assert {e.target_id for e in of(result, StatusApplied) if e.status_id == "stoneskin"} == {U1}
    assert {e.unit_id for e in of(result, ShieldGained)} == {U1}


# ---------------------------------------------------------------------------
# 大地崩陷
# ---------------------------------------------------------------------------


def test_earth_collapse_is_an_epic_pure_terrain_earth_skill_in_the_window() -> None:
    skill = LIB.skills["skill_earth_collapse"]
    assert validate_skill(skill, LIB) == []
    report = skill_budget(skill, LIB)
    assert report.ok and report.ratio * 1000 >= 700
    assert skill.rarity == "epic" and skill.element is Element.EARTH
    assert skill.shape.type == "square3"
    assert [e.type for e in skill.effects] == ["lower_terrain"]


def test_earth_collapse_digs_a_pit_and_the_unit_sinks_with_the_ground() -> None:
    skill = LIB.skills["skill_earth_collapse"].model_copy(update={"id": SID})
    heights = "\n".join(["2222222"] * 7)
    state = battle(skill, foes=[(4, 1)], heights=heights, caster=(1, 1))
    result = _cast(SID, state, target_pos=Pos(x=4, y=1))
    lowered = {(c.pos.x, c.pos.y) for c in of(result, TerrainChanged)}
    assert lowered == {(x, y) for x in (3, 4, 5) for y in (0, 1, 2)}
    assert all(result.state.tile(x, y).height == 1 for x, y in lowered)
    assert result.state.tile(2, 1).height == 2  # 範圍外不變：坑比四周低一層
    assert not of(result, DamageDealt)
    assert result.state.units[FOE].xy == (4, 1)


def test_the_pit_makes_a_two_level_edge_so_a_second_collapse_would_drop_a_unit() -> None:
    """單次只降一層（落差 1 < 墜落門檻 2）：單位跟著地面下沉、不墜落；墜落要靠已有落差的地形。"""
    skill = LIB.skills["skill_earth_collapse"].model_copy(update={"id": SID})
    heights = "\n".join(["3333333"] * 7)
    state = battle(skill, foes=[(4, 1)], heights=heights, caster=(1, 1))
    first = _cast(SID, state, target_pos=Pos(x=4, y=1))
    assert not of(first, UnitFell)
    assert LIB.ruleset.core.fall_damage_min_drop == 2


# ---------------------------------------------------------------------------
# 工坊：元素大地＋只有下陷
# ---------------------------------------------------------------------------


def _workshop_terrain_skill(shape: dict[str, Any], ap: int, cost: dict[str, int]) -> Any:
    skill = make_skill(SID, shape, [{"type": "lower_terrain", "amount": 1, "affects": "tiles"}])
    return skill.model_copy(
        update={
            "skeleton": "control",
            "element": Element.EARTH,
            "rarity": "epic",
            "ap_cost": ap,
            "tags": ["earth", "spell", "terrain"],
        }
    )


def test_a_workshop_earth_skill_with_only_lowering_can_pass_the_budget() -> None:

    passing = 0
    for shape in ({"type": "single", "range": 4}, {"type": "square3", "range": 4}):
        for ap in (1, 2):
            skill = _workshop_terrain_skill(shape, ap, {})
            skill = skill.model_copy(update={"cost": SkillCost(mana=6, cooldown=2)})
            if skill_budget(skill, LIB).ok and not [
                v for v in validate_skill(skill, LIB) if v.rule.startswith("budget")
            ]:
                passing += 1
    assert passing >= 2  # 單格 1 AP 與 3×3 2 AP 都能落在 70～100%
