"""主題合併（R2）。

原 ``test_earth_54b.py``：

Phase 3-54b：大地（06 6.33，#58）——石膚、震波、升降地形限大地、大範圍越貴越稀有。

表格測試：石膚 × 元素、震波 × 對象、形狀格數 × 稀有度；行為一致測試（卡片＝實戰）；含測試用大地
技能的整場重播。（沒有新增種子技能：種子技能在 3-54c。）

原 ``test_earth_54e.py``：

Phase 3-54e：石膚術（石膚＋小護盾）、大地崩陷（純下陷）、隆起／下陷點數 7 與工坊純地形技能。
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
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of, script_rolls
from trpg.content.skills import SkillCost, SkillDef, skill_elements
from trpg.engine import UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    ShieldGained,
    SkillUsed,
    StatusApplied,
    TerrainChanged,
    UnitFell,
)
from trpg.engine.rules.statuses import damage_taken_permille, move_points_for_turn
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import StatusInstance, state_to_json
from trpg.narrative.skills import effect_summary
from trpg.narrative.status_info import status_rules
from trpg.shared.types import Element, Pos, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import (
    minimum_tier,
    rarity_requirements,
    structural_rarity,
    validate_skill,
)

# --- 原 test_earth_54b.py ---

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


def _terrain(
    primitive: str, shape: dict[str, Any], *, tags: tuple[str, ...] = (), **extra: Any
) -> SkillDef:
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


def test_terrain_with_an_earth_damage_effect_alone_is_not_enough() -> None:
    """3-54d：效果自己寫的元素不再決定技能算不算大地；要技能元素欄（或主題標籤）是大地。"""
    effects = [
        {"type": "damage", "dice": "1d6", "element": "earth"},
        {"type": "raise_terrain", "affects": "tiles"},
    ]
    skill = _skill(effects, {"type": "cross", "range": 3}, skeleton="control", rarity="epic")
    assert "exclusion.terrain_needs_earth" in _problems(skill)
    earth = skill.model_copy(update={"element": Element.EARTH})
    assert "exclusion.terrain_needs_earth" not in _problems(earth)


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
    definition = LIB.ruleset.shapes.by_id()[shape["type"]]
    shape_cells = definition.cell_count
    values = definition.with_defaults(skill.shape.param_values())  # 十字臂長省略＝1（5F-2b）
    assert shape_cells is not None and shape_cells.count_for(values) == cells
    tiers = LIB.budget.terrain_area_rarity
    expected = next((t.rarity for t in reversed(tiers) if cells >= t.min_cells), None)
    assert [n.minimum for n in needs] == ([expected] if expected else [])
    if cells >= 7:
        assert expected == "epic" == minimum
    elif cells >= 4:
        assert expected == "rare" == minimum


def test_a_rare_skill_cannot_use_seven_cells_but_an_epic_one_can() -> None:
    # 3W-9：稀有度只是標記（7 格算出史詩）；門檻改成最低角色階級（7 格以上 3 階）
    rare = _terrain(
        "raise_terrain", {"type": "square3", "range": 3}, tags=("earth",), rarity="rare"
    )
    assert "rarity.terrain_area" not in _problems(rare)
    assert structural_rarity(rare, LIB) == "epic"
    assert minimum_tier(rare, LIB) == 3


def test_a_common_skill_cannot_use_four_to_six_cells() -> None:
    skill = _terrain("lower_terrain", {"type": "line", "size": 5}, tags=("earth",), rarity="common")
    assert "rarity.terrain_area" not in _problems(skill)  # 3W-9：標記算出稀有、門檻 2 階
    assert structural_rarity(skill, LIB) == "rare" and minimum_tier(skill, LIB) == 2


# ---------------------------------------------------------------------------
# 預算（震波、擴散格數）
# ---------------------------------------------------------------------------


def test_shockwave_points_come_from_the_primitive_and_the_shape() -> None:
    narrow = skill_budget(_shockwave(shape={"type": "line", "size": 2}), LIB)
    wide = skill_budget(_shockwave(shape={"type": "line", "size": 5}), LIB)
    assert wide.total > narrow.total > 0


def test_wind_spread_two_costs_more_than_one() -> None:
    def total(spread: int | None) -> Any:
        hit: dict[str, Any] = {
            "type": "damage",
            "dice": "2d6",
            "element": "wind",
            "affects": "tiles",
        }
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


# ---------------------------------------------------------------------------
# 工坊：事前停用、說明
# ---------------------------------------------------------------------------

_DRAFT: dict[str, Any] = {
    "skeleton": "control",
    "kind": "active",
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "tier": 1,
    "ap_cost": 1,
    "shape": {"type": "cross", "range": 4},
}


def _effects_choice(draft: dict[str, Any], primitive: str) -> Any:
    from trpg.skillgen.options import draft_options  # noqa: PLC0415

    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "effects")
    field = next(f for f in step.fields if f.field == "effects")
    return next(c for c in field.choices if c.value == primitive)


@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_workshop_disables_terrain_until_the_skill_element_is_earth(primitive: str) -> None:
    empty = _effects_choice({**_DRAFT, "effects": []}, primitive)
    assert "大地" in empty.info["unavailable_zh"]
    earth_hit = {"type": "damage", "dice": "1d6", "element": "earth"}
    assert "unavailable_zh" in _effects_choice({**_DRAFT, "effects": [earth_hit]}, primitive).info
    fire = {**_DRAFT, "element": "fire"}
    assert "unavailable_zh" in _effects_choice({**fire, "effects": []}, primitive).info
    ok = _effects_choice({**_DRAFT, "element": "earth", "effects": []}, primitive)
    assert "unavailable_zh" not in ok.info


def test_workshop_shows_spread_only_for_wind_and_the_card_says_the_number() -> None:
    choice = _effects_choice({**_DRAFT, "skeleton": "area", "effects": []}, "damage")
    spread = next(p for p in choice.params if p.field == "spread")
    assert (spread.min, spread.max) == (1, 2)
    assert spread.show_when == {"element": "wind"}
    wind = make_skill(
        SID,
        LINE3,
        [{"type": "damage", "dice": "1d4", "element": "wind", "affects": "tiles", "spread": 2}],
    )
    assert "2 格" in effect_summary(LIB, wind, wind.effects[0])
    default = make_skill(
        SID, LINE3, [{"type": "damage", "dice": "1d4", "element": "wind", "affects": "tiles"}]
    )
    assert "1 格" in effect_summary(LIB, default, default.effects[0])


# --- 原 test_earth_54e.py ---

LIB_54E = library()
FOE_54E = U2


def _cast(skill_id: str, state: Any, **fields: Any) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


# ---------------------------------------------------------------------------
# 原語點數
# ---------------------------------------------------------------------------


def test_raise_and_lower_terrain_cost_seven_points() -> None:
    prims = LIB_54E.ruleset.primitives.by_id()
    assert (prims["raise_terrain"].base_points, prims["lower_terrain"].base_points) == (7, 7)


def test_the_reworked_terrain_skills_are_back_inside_the_budget() -> None:
    for sid in ("skill_raise_perch", "skill_sinkhole", "skill_summon_plateau_totem"):
        skill = LIB_54E.skills[sid]
        assert validate_skill(skill, LIB_54E) == [], sid
        assert skill_budget(skill, LIB_54E).ok, sid
    for sid in ("skill_raise_perch", "skill_sinkhole"):  # 形狀與名稱不變
        assert LIB_54E.skills[sid].shape.type == "cross"
        assert [e.type for e in LIB_54E.skills[sid].effects] == [
            "raise_terrain" if sid == "skill_raise_perch" else "lower_terrain"
        ]


# ---------------------------------------------------------------------------
# 石膚術
# ---------------------------------------------------------------------------


def test_stoneskin_ward_is_a_valid_common_earth_skill_in_the_window() -> None:
    skill = LIB_54E.skills["skill_stoneskin_ward"]
    assert validate_skill(skill, LIB_54E) == []
    report = skill_budget(skill, LIB_54E)
    assert report.ok and 700 <= report.ratio * 1000 <= 1000
    assert skill.rarity == "common" and skill.element is Element.EARTH
    assert [e.type for e in skill.effects] == ["apply_status", "shield"]
    dice = skill.effects[1].dice
    assert dice is not None and (dice.count, dice.sides) == (1, 6)


def test_stoneskin_ward_on_an_ally_gives_skin_and_shield_to_the_same_target() -> None:
    skill = LIB_54E.skills["skill_stoneskin_ward"]
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
    skill = LIB_54E.skills["skill_stoneskin_ward"].model_copy(update={"id": SID})
    result = _cast(SID, battle(skill, foes=[(6, 6)]), target_id=U1)
    assert {e.target_id for e in of(result, StatusApplied) if e.status_id == "stoneskin"} == {U1}
    assert {e.unit_id for e in of(result, ShieldGained)} == {U1}


# ---------------------------------------------------------------------------
# 大地崩陷
# ---------------------------------------------------------------------------


def test_earth_collapse_is_an_epic_pure_terrain_earth_skill_in_the_window() -> None:
    skill = LIB_54E.skills["skill_earth_collapse"]
    assert validate_skill(skill, LIB_54E) == []
    report = skill_budget(skill, LIB_54E)
    assert report.ok and report.ratio * 1000 >= 700
    assert skill.rarity == "epic" and skill.element is Element.EARTH
    assert skill.shape.type == "square3"
    assert [e.type for e in skill.effects] == ["lower_terrain"]


def test_earth_collapse_digs_a_pit_and_the_unit_sinks_with_the_ground() -> None:
    skill = LIB_54E.skills["skill_earth_collapse"].model_copy(update={"id": SID})
    heights = "\n".join(["2222222"] * 7)
    state = battle(skill, foes=[(4, 1)], heights=heights, caster=(1, 1))
    result = _cast(SID, state, target_pos=Pos(x=4, y=1))
    lowered = {(c.pos.x, c.pos.y) for c in of(result, TerrainChanged)}
    assert lowered == {(x, y) for x in (3, 4, 5) for y in (0, 1, 2)}
    assert all(result.state.tile(x, y).height == 1 for x, y in lowered)
    assert result.state.tile(2, 1).height == 2  # 範圍外不變：坑比四周低一層
    assert not of(result, DamageDealt)
    assert result.state.units[FOE_54E].xy == (4, 1)


def test_the_pit_makes_a_two_level_edge_so_a_second_collapse_would_drop_a_unit() -> None:
    """單次只降一層（落差 1 < 墜落門檻 2）：單位跟著地面下沉、不墜落；墜落要靠已有落差的地形。"""
    skill = LIB_54E.skills["skill_earth_collapse"].model_copy(update={"id": SID})
    heights = "\n".join(["3333333"] * 7)
    state = battle(skill, foes=[(4, 1)], heights=heights, caster=(1, 1))
    first = _cast(SID, state, target_pos=Pos(x=4, y=1))
    assert not of(first, UnitFell)
    assert LIB_54E.ruleset.core.fall_damage_min_drop == 2


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
            if skill_budget(skill, LIB_54E).ok and not [
                v for v in validate_skill(skill, LIB_54E) if v.rule.startswith("budget")
            ]:
                passing += 1
    assert passing >= 2  # 單格 1 AP 與 3×3 2 AP 都能落在 70～100%


# ---------------------------------------------------------------------------
# 重播
# ---------------------------------------------------------------------------


def test_a_battle_with_earth_collapse_replays_identically() -> None:
    from tests.engine.helpers import (  # noqa: PLC0415
        caster_template,
        make_map,
        make_setup,
        no_reactions,
        spawn,
    )
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415
    from trpg.engine.events import SkillUsed  # noqa: PLC0415
    from trpg.engine.runner import replay, run_battle  # noqa: PLC0415
    from trpg.engine.state import state_to_json  # noqa: PLC0415
    from trpg.shared.types import Team  # noqa: PLC0415

    kit = ["skill_earth_collapse", "skill_stoneskin_ward"]
    heights = "\n".join(["2222222"] * 7)
    foes = [(4, 3), (4, 4), (5, 2)]
    m = make_map(heights, ally=[(1, 3)], enemy=foes)
    spawns = [spawn(Team.ALLY, (1, 3), caster_template([LIB_54E.skills[s] for s in kit]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    setup = make_setup(m, spawns, max_rounds=12)
    run = run_battle(setup, 7, UtilityAI(LIB_54E.ai_profiles))
    again = replay(setup, 7, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    used = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
    assert "skill_stoneskin_ward" in used  # 效用 AI 不會主動挖坑（純地形沒有評分），崩陷見下面

    ai = UtilityAI(LIB_54E.ai_profiles)
    cast_once: list[bool] = []

    def scripted(state: Any) -> Any:  # 我方第一次行動先用大地崩陷，之後交給效用 AI
        if state.active.team is Team.ALLY and not cast_once:
            cast_once.append(True)
            return UseSkill(
                unit_id=state.active.id, skill_id="skill_earth_collapse", target_pos=Pos(x=4, y=3)
            )
        return ai(state)

    run = run_battle(setup, 7, scripted)
    again = replay(setup, 7, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert any(isinstance(e, TerrainChanged) for e in run.events)
    assert "skill_earth_collapse" in {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
