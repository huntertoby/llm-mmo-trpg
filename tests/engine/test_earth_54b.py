"""Phase 3-54b：大地（06 6.33，#58）——石膚、震波、升降地形限大地、大範圍越貴越稀有。

表格測試：石膚 × 元素、震波 × 對象、形狀格數 × 稀有度；行為一致測試（卡片＝實戰）；含測試用大地
技能的整場重播。（沒有新增種子技能：種子技能在 3-54c。）
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import SID, U1, battle, cast, hit_with, of, script_rolls
from trpg.content.skills import SkillDef, skill_elements
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, EffectFizzled, SkillUsed, StatusApplied
from trpg.engine.rules.statuses import damage_taken_permille, move_points_for_turn
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import StatusInstance, state_to_json
from trpg.narrative.skills import effect_summary
from trpg.narrative.status_info import status_rules
from trpg.shared.types import Element, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import rarity_requirements, validate_skill

LIB = library()
FOE = UnitId("unit_0002")
LINE3 = {"type": "line", "size": 3}


def _skill(effects: list[dict[str, Any]], shape: dict[str, Any], **extra: Any) -> SkillDef:
    skill = make_skill(SID, shape, effects)
    return skill.model_copy(update=extra) if extra else skill


# ---------------------------------------------------------------------------
# 石膚
# ---------------------------------------------------------------------------


def _damage_to(element: str, *, stoneskin: bool) -> int:
    skill = make_skill(
        SID, {"type": "single", "range": 3}, [{"type": "damage", "dice": "3d6", "element": element}]
    )
    state = battle(skill, foes=[(4, 3)])
    if stoneskin:
        state.units[FOE].statuses.append(StatusInstance("stoneskin", 2))
    result = cast(hit_with(state), target_id=FOE)
    (hit,) = [e for e in of(result, DamageDealt) if e.target_id == FOE]
    return hit.amount


@pytest.mark.parametrize("element", [e.value for e in Element])
def test_stoneskin_only_reduces_physical_dice_damage(element: str) -> None:
    plain, skinned = _damage_to(element, stoneskin=False), _damage_to(element, stoneskin=True)
    if element == "physical":
        assert skinned == plain * 700 // 1000
        assert skinned < plain
    else:
        assert skinned == plain


def test_stoneskin_numbers_come_from_the_status_data() -> None:
    status = LIB.ruleset.status_def("stoneskin")
    assert (status.physical_taken_permille, status.move_delta, status.duration) == (700, -1, 2)
    assert status.beneficial and status.polarity == "buff"


@pytest.mark.parametrize("speed", [0, 1, 4, 6])
def test_stoneskin_takes_one_move_point_with_a_floor_of_zero(speed: int) -> None:
    state = battle(_skill([{"type": "damage", "dice": "1d4", "element": "earth"}], LINE3))
    unit = state.units[U1]
    unit.speed = speed
    before = move_points_for_turn(state.ruleset, unit)
    unit.statuses.append(StatusInstance("stoneskin", 2))
    assert move_points_for_turn(state.ruleset, unit) == max(0, before - 1)


def test_stoneskin_stacks_multiplicatively_with_vulnerable() -> None:
    state = battle(_skill([{"type": "damage", "dice": "1d4", "element": "earth"}], LINE3))
    unit = state.units[U1]
    unit.statuses.append(StatusInstance("stoneskin", 2))
    assert damage_taken_permille(state.ruleset, unit, Element.PHYSICAL) == 700
    assert damage_taken_permille(state.ruleset, unit, Element.FIRE) == 1000
    assert damage_taken_permille(state.ruleset, unit) == 1000


def test_stoneskin_is_applied_by_a_skill_and_lasts_two_rounds() -> None:
    skill = make_skill(
        SID,
        {"type": "self"},
        [{"type": "apply_status", "status": "stoneskin", "affects": "self"}],
    )
    result = cast(battle(skill, foes=[(6, 6)]))
    (applied,) = [e for e in of(result, StatusApplied) if e.status_id == "stoneskin"]
    assert applied.target_id == U1
    status = next(s for s in result.state.units[U1].statuses if s.status_id == "stoneskin")
    assert status.remaining in (1, 2)


def test_stoneskin_card_text_says_the_numbers() -> None:
    text = "".join(status_rules(LIB.ruleset.status_def("stoneskin"), LIB))
    assert "70%" in text and "物理" in text and "-1" in text


# ---------------------------------------------------------------------------
# 震波
# ---------------------------------------------------------------------------


def _shockwave(affects: str | None = None, shape: dict[str, Any] | None = None) -> SkillDef:
    effect: dict[str, Any] = {"type": "shockwave"}
    if affects is not None:
        effect["affects"] = affects
    return make_skill(SID, shape or LINE3, [effect])


def _flying() -> Any:
    return no_reactions(tags=["flying"])


def test_shockwave_knocks_down_every_enemy_in_the_line(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_shockwave(), foes=[(4, 3), (5, 3), (6, 3), (3, 6)])
    script_rolls(monkeypatch, [19, 19, 19])
    result = cast(state, direction="east")
    prone = {e.target_id for e in of(result, StatusApplied) if e.status_id == "prone"}
    assert prone == {UnitId("unit_0002"), UnitId("unit_0003"), UnitId("unit_0004")}
    assert not result.state.units[UnitId("unit_0005")].has_status("prone")  # 不在線上


def test_shockwave_does_not_roll_a_contest() -> None:
    state = battle(_shockwave(), foes=[(4, 3)])
    result = cast(hit_with(state), direction="east")
    assert not [e for e in result.events if type(e).__name__ == "ManeuverRolled"]
    assert result.state.units[FOE].has_status("prone")


def test_shockwave_does_not_affect_flying_units(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_shockwave(), foes=[(4, 3, _flying()), (5, 3)])
    script_rolls(monkeypatch, [19, 19])
    result = cast(state, direction="east")
    assert not result.state.units[FOE].has_status("prone")
    assert result.state.units[UnitId("unit_0003")].has_status("prone")
    (fizzle,) = [e for e in of(result, EffectFizzled) if e.reason == "shockwave_flying"]
    assert fizzle.effect_kind == "shockwave"


def test_shockwave_skips_units_that_are_already_prone() -> None:
    state = battle(_shockwave(), foes=[(4, 3)])
    state.units[FOE].statuses.append(StatusInstance("prone", None))
    result = cast(hit_with(state), direction="east")
    assert not [e for e in of(result, StatusApplied) if e.status_id == "prone"]


@pytest.mark.parametrize(
    ("affects", "ally_down"), [("enemies", False), ("all", True), ("allies", True)]
)
def test_shockwave_targets_follow_affects(
    affects: str, ally_down: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = battle(_shockwave(affects), allies=[(5, 3)], foes=[(4, 3)])
    script_rolls(monkeypatch, [19, 19])
    result = cast(state, direction="east")
    assert result.state.units[UnitId("unit_0002")].has_status("prone") is ally_down
    foe = result.state.units[UnitId("unit_0003")]
    assert foe.has_status("prone") is (affects != "allies")


def test_shockwave_can_only_use_a_line_shape() -> None:
    bad = _shockwave(shape={"type": "cross", "range": 3})
    assert any("shockwave" in v.message or "shape" in v.rule for v in validate_skill(bad, LIB))


def test_shockwave_card_matches_what_happens() -> None:
    skill = _shockwave()
    line = effect_summary(LIB, skill, skill.effects[0])
    assert "震波" in line and "會飛" in line
    assert LIB.ruleset.primitives.by_id()["shockwave"].base_points == 4


# ---------------------------------------------------------------------------
# 升降地形限大地、大範圍越貴越稀有
# ---------------------------------------------------------------------------


def _terrain(primitive: str, shape: dict[str, Any], *, tags: tuple[str, ...] = (), **extra: Any) -> SkillDef:
    skill = _skill([{"type": primitive}], shape, tags=tags, rarity="epic", skeleton="control")
    return skill.model_copy(update=extra) if extra else skill


def _problems(skill: SkillDef) -> list[str]:
    return [v.rule for v in validate_skill(skill, LIB)]


@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_terrain_without_earth_is_rejected(primitive: str) -> None:
    skill = _terrain(primitive, {"type": "cross", "range": 3}, tags=("fire",))
    assert "exclusion.terrain_needs_earth" in _problems(skill)


@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_terrain_with_the_earth_tag_passes_the_rule(primitive: str) -> None:
    skill = _terrain(primitive, {"type": "cross", "range": 3}, tags=("earth",))
    assert "exclusion.terrain_needs_earth" not in _problems(skill)
    assert skill_elements(skill) == {Element.EARTH}


def test_terrain_with_an_earth_damage_effect_passes_the_rule() -> None:
    skill = _skill(
        [
            {"type": "damage", "dice": "1d6", "element": "earth"},
            {"type": "raise_terrain", "affects": "tiles"},
        ],
        {"type": "cross", "range": 3},
        skeleton="control",
        rarity="epic",
    )
    assert "exclusion.terrain_needs_earth" not in _problems(skill)


def test_physical_or_other_elements_do_not_count_as_earth() -> None:
    skill = _skill(
        [{"type": "damage", "dice": "1d6", "element": "physical"}, {"type": "lower_terrain"}],
        {"type": "cross", "range": 3},
        skeleton="control",
        rarity="epic",
    )
    assert "exclusion.terrain_needs_earth" in _problems(skill)


# 形狀格數（content/skill_shapes.yaml 的 cell_count）→ 最低稀有度（content/skill_budget.yaml）
@pytest.mark.parametrize(
    ("shape", "cells", "minimum"),
    [
        ({"type": "single", "range": 3}, 1, "rare"),  # 升降地形原語本身最低稀有
        ({"type": "line", "size": 3}, 3, "rare"),
        ({"type": "line", "size": 4}, 4, "rare"),
        ({"type": "cross", "range": 3}, 5, "rare"),
        ({"type": "line", "size": 6}, 6, "rare"),
        ({"type": "square3", "range": 3}, 9, "epic"),
        ({"type": "cone", "size": 4}, 16, "epic"),
    ],
)
@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_terrain_area_sets_the_minimum_rarity(
    shape: dict[str, Any], cells: int, minimum: str, primitive: str
) -> None:
    skill = _terrain(primitive, shape, tags=("earth",))
    needs = [n for n in rarity_requirements(skill, LIB) if n.rule == "terrain_area"]
    shape_cells = LIB.ruleset.shapes.by_id()[shape["type"]].cell_count
    assert shape_cells is not None and shape_cells.count_for(skill.shape.param_values()) == cells
    tiers = LIB.budget.terrain_area_rarity
    expected = next((t.rarity for t in reversed(tiers) if cells >= t.min_cells), None)
    assert [n.minimum for n in needs] == ([expected] if expected else [])
    if cells >= 7:  # noqa: PLR2004 - 規格的 7 格以上
        assert expected == "epic" == minimum
    elif cells >= 4:  # noqa: PLR2004 - 規格的 4～6 格
        assert expected == "rare" == minimum


def test_a_rare_skill_cannot_use_seven_cells_but_an_epic_one_can() -> None:
    rare = _terrain("raise_terrain", {"type": "square3", "range": 3}, tags=("earth",), rarity="rare")
    assert "rarity.terrain_area" in _problems(rare)
    epic = rare.model_copy(update={"rarity": "epic"})
    assert "rarity.terrain_area" not in _problems(epic)


def test_a_common_skill_cannot_use_four_to_six_cells() -> None:
    skill = _terrain("lower_terrain", {"type": "line", "size": 5}, tags=("earth",), rarity="common")
    assert "rarity.terrain_area" in _problems(skill)


# ---------------------------------------------------------------------------
# 預算（震波、擴散格數）
# ---------------------------------------------------------------------------


def test_shockwave_points_come_from_the_primitive_and_the_shape() -> None:
    narrow = skill_budget(_shockwave(shape={"type": "line", "size": 2}), LIB)
    wide = skill_budget(_shockwave(shape={"type": "line", "size": 5}), LIB)
    assert wide.total > narrow.total > 0


def test_wind_spread_two_costs_more_than_one() -> None:
    def total(spread: int | None) -> Any:
        hit: dict[str, Any] = {"type": "damage", "dice": "2d6", "element": "wind", "affects": "tiles"}
        if spread is not None:
            hit["spread"] = spread
        return skill_budget(make_skill(SID, {"type": "line", "size": 3}, [hit]), LIB).total

    assert total(None) == total(1) < total(2)
    ratio = LIB.budget.wind_spread_permille
    assert total(2) == total(1) * ratio[1] / ratio[0]


# ---------------------------------------------------------------------------
# 重播：含大地測試技能的整場戰鬥
# ---------------------------------------------------------------------------


def test_a_battle_with_earth_test_skills_replays_identically() -> None:
    quake = make_skill(
        "skill_t_quake",
        {"type": "line", "size": 4},
        [{"type": "damage", "dice": "1d6", "element": "earth"}, {"type": "shockwave"}],
    )
    skin = make_skill(
        "skill_t_skin",
        {"type": "self"},
        [{"type": "apply_status", "status": "stoneskin", "affects": "self"}],
    )
    kit = [quake, skin]
    flat = "\n".join(["000000000"] * 9)
    m = make_map(flat, ally=[(1, 3), (1, 5)], enemy=[(6, 3), (7, 4)])
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template(kit, max_hp=60)),
        spawn(Team.ALLY, (1, 5), caster_template(kit, max_hp=60)),
        spawn(Team.ENEMY, (6, 3), template("bandit", max_hp=80)),
        spawn(Team.ENEMY, (7, 4), template("bandit", max_hp=80)),
    ]
    setup = make_setup(m, spawns, skills=kit, max_rounds=12)
    run = run_battle(setup, 11, UtilityAI(LIB.ai_profiles))
    again = replay(setup, 11, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    used = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
    assert used & {"skill_t_quake", "skill_t_skin"}

