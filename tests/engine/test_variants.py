"""Phase 3-25a：戰場變奏的引擎結算（四種條件、取第一個、目標依賴的合法性與射程、等級與修正的
順序、施放事件與紀錄文字、確定性與重播）。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import SkillDef
from trpg.engine import BattleSetup, BattleState, UseSkill, legal_actions, resolve, state_to_json
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, SkillUsed
from trpg.engine.modifiers import acting_skill
from trpg.engine.runner import replay, run_battle
from trpg.engine.variants import chosen_variant, target_point, variant_holds, varied_skill
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
TIDAL = "skill_tidal_spear"
BASH = "skill_wall_brace_bash"
SPARK = "skill_oil_spark_throw"
CLEAVE = "skill_frost_ledge_cleave"
FLAT7 = "\n".join(["0000000"] * 7)
BASES = {TIDAL: "hero_mage", BASH: "hero_fighter", SPARK: "hero_archer", CLEAVE: "hero_fighter"}


def _state(
    skills: Sequence[str],
    *,
    caster: tuple[int, int] = (3, 3),
    foes: Sequence[tuple[int, int]] = ((3, 1),),
    heights: str = FLAT7,
    terrain: str | None = None,
    surfaces: Sequence[tuple[int, int, str]] = (),
    objects: Sequence[tuple[int, int, str]] = (),
    extra: Sequence[SkillDef] = (),
) -> BattleState:
    """U1 是裝備 ``skills`` 的施放者（範本依第一招技能），之後是不反應的盜賊（HP 200）。"""
    m = make_map(heights, terrain, ally=[caster], enemy=foes, surfaces=surfaces, objects=objects)
    tmpl = caster_template(list(skills), base=BASES.get(skills[0], "hero_mage"))
    spawns = [spawn(Team.ALLY, caster, tmpl)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=list(extra)), U1)


def _chosen(state: BattleState, skill_id: str, target: tuple[int, int] | None) -> str | None:
    skill = state.ruleset.skill_def(skill_id)
    found = chosen_variant(state, state.units[U1], skill, target)
    return None if found is None else found.id


# ---------------------------------------------------------------------------
# 四種條件：成立與不成立
# ---------------------------------------------------------------------------


def test_caster_surface_holds_only_when_standing_on_the_listed_surface() -> None:
    wet = _state([TIDAL], surfaces=[(3, 3, "water")])
    dry = _state([TIDAL], surfaces=[(3, 2, "water")])
    oily = _state([TIDAL], surfaces=[(3, 3, "oil")])
    assert _chosen(wet, TIDAL, (3, 1)) == "tide_pierce"
    assert _chosen(dry, TIDAL, (3, 1)) is None
    assert _chosen(oily, TIDAL, (3, 1)) is None


def test_caster_high_ground_needs_at_least_one_level_above_the_target_point() -> None:
    heights = "0000000\n0000000\n0000000\n0001000\n0000000\n0000000\n0000000"
    high = _state([TIDAL], heights=heights)
    assert _chosen(high, TIDAL, (3, 1)) == "high_tide"
    level = _state([TIDAL], heights="\n".join(["1111111"] * 7))
    assert _chosen(level, TIDAL, (3, 1)) is None
    assert _chosen(high, TIDAL, None) is None  # 沒有目標點（方向型）一律不成立


def test_adjacent_blocker_counts_walls_and_blocking_objects_in_eight_directions() -> None:
    terrain = ".......\n.......\n....#..\n.......\n.......\n.......\n......."
    wall = _state([BASH], foes=[(3, 4)], terrain=terrain)  # (4, 2) 是施放者斜前方
    crate = _state([BASH], foes=[(3, 4)], objects=[(2, 3, "crate")])
    open_field = _state([BASH], foes=[(3, 4)], objects=[(5, 3, "crate")])
    assert _chosen(wall, BASH, (3, 4)) == "braced"
    assert _chosen(crate, BASH, (3, 4)) == "braced"
    assert _chosen(open_field, BASH, (3, 4)) is None
    assert _chosen(_state([BASH], foes=[(3, 4)], caster=(0, 0)), BASH, (3, 4)) is None  # 地圖邊不算


def test_target_surface_looks_at_the_target_point() -> None:
    state = _state([SPARK], foes=[(3, 0)], surfaces=[(3, 0, "oil"), (1, 1, "water")])
    assert _chosen(state, SPARK, (3, 0)) == "oil_spark"
    assert _chosen(state, SPARK, (1, 1)) is None
    assert _chosen(state, SPARK, None) is None


def test_variant_holds_checks_one_condition_at_a_time() -> None:
    state = _state([TIDAL], surfaces=[(3, 3, "water")])
    skill = state.ruleset.skill_def(TIDAL)
    caster = state.units[U1]
    pierce, high = skill.variants
    assert variant_holds(state, caster, pierce.when, None)
    assert not variant_holds(state, caster, high.when, (3, 1))


# ---------------------------------------------------------------------------
# 多個成立取第一個；目標依賴的合法性與射程
# ---------------------------------------------------------------------------


def test_the_first_variant_in_data_order_wins_when_several_hold() -> None:
    heights = "0000000\n0000000\n0000000\n0001000\n0000000\n0000000\n0000000"
    state = _state([CLEAVE], foes=[(3, 4)], heights=heights, surfaces=[(3, 3, "ice")])
    assert _chosen(state, CLEAVE, (3, 4)) == "frost_edge"  # 寒霜刃排在崖頂下劈前面
    tidal = _state([TIDAL], heights=heights, surfaces=[(3, 3, "water")])
    assert _chosen(tidal, TIDAL, (3, 1)) == "tide_pierce"


def _tidal_targets(state: BattleState) -> list[UseSkill]:
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == TIDAL]


def test_high_ground_range_bonus_only_reaches_lower_target_points() -> None:
    """居高投矛射程 +2（3 → 5）：比自己低的目標點可以打到 5 格，同高的只能打到 3 格。"""
    heights = "0000000\n0000000\n0000000\n1000000\n0000000\n0000000\n0000000"
    high = _state([TIDAL], caster=(0, 3), foes=[(5, 3)], heights=heights)
    picks = _tidal_targets(high)
    assert UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2) in picks
    result = resolve(high, UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2))
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.variant == "high_tide"
    level = _state([TIDAL], caster=(0, 3), foes=[(5, 3)], heights="\n".join(["1111111"] * 7))
    assert UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2) not in _tidal_targets(level)
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(level, UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2))


def test_standing_in_water_turns_the_spear_into_a_lightning_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Rng, "roll", lambda _self, sides: sides)  # 每顆骰都擲最大：一定命中
    state = _state([TIDAL], foes=[(3, 1), (3, 0)], surfaces=[(3, 3, "water")])
    picks = _tidal_targets(state)
    assert picks and all(a.direction is not None for a in picks)  # 只剩直線（方向）的選取
    action = UseSkill(unit_id=U1, skill_id=TIDAL, direction="north")
    assert action in picks
    result = resolve(state, action)
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.variant == "tide_pierce"
    assert used.tiles == (Pos(x=3, y=0), Pos(x=3, y=1), Pos(x=3, y=2))
    elements = {e.element for e in result.events if isinstance(e, DamageDealt)}
    assert elements <= {"lightning"} and elements
    with pytest.raises(IllegalActionError):  # 單體的選取不再合法
        resolve(state, UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2))


def test_plain_cast_has_no_variant() -> None:
    state = _state([TIDAL])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2))
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.variant is None


# ---------------------------------------------------------------------------
# 等級與修正疊在變奏之後
# ---------------------------------------------------------------------------

_AREA_MOD = SkillDef.model_validate(
    {
        "id": "skill_t_area_mod",
        "name_zh": "測試範圍修正",
        "tier": 1,
        "rarity": "epic",
        "kind": "modifier",
        "skeleton": "modifier",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": "int",
        "shape": {"type": "self"},
        "effects": [],
        "modifiers": [{"applies_to": {"all_skills": True}, "change": {"area_delta": 1}}],
        "cost": {"mana": 0},
    }
)


def test_skill_level_applies_after_the_variant() -> None:
    """5 級小特性：基礎型態（單體，沒有可增加的範圍）是冷卻 −1；水中型態（直線 3）是範圍 +1。"""
    plain = _state([TIDAL])
    plain.units[U1].skill_levels = {TIDAL: 5}
    base = acting_skill(plain, plain.units[U1], TIDAL, UseSkill(unit_id=U1, skill_id=TIDAL))
    assert base.shape.type == "single" and base.cost.cooldown == 1
    wet = _state([TIDAL], surfaces=[(3, 3, "water")])
    wet.units[U1].skill_levels = {TIDAL: 5}
    north = UseSkill(unit_id=U1, skill_id=TIDAL, direction="north")
    form = acting_skill(wet, wet.units[U1], TIDAL, north)
    assert form.shape.type == "line" and form.shape.size == 4 and form.cost.cooldown == 2


def test_modifiers_apply_after_the_variant_and_the_level() -> None:
    wet = _state([TIDAL, _AREA_MOD.id], surfaces=[(3, 3, "water")], extra=[_AREA_MOD])
    north = UseSkill(unit_id=U1, skill_id=TIDAL, direction="north")
    assert acting_skill(wet, wet.units[U1], TIDAL, north).shape.size == 4  # 3 ＋ 修正 1
    wet.units[U1].skill_levels = {TIDAL: 5}
    assert acting_skill(wet, wet.units[U1], TIDAL, north).shape.size == 5  # ＋ 等級 1
    result = resolve(wet, north)
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.variant == "tide_pierce" and len(used.tiles) == 3  # 地圖只到 y = 0


def test_varied_skill_returns_the_same_object_without_variants() -> None:
    state = _state([TIDAL])
    plain = state.ruleset.skill_def("skill_fire_bolt")
    assert varied_skill(state, state.units[U1], plain, (3, 1)) == (plain, None)
    action = UseSkill(unit_id=U1, skill_id=TIDAL, target_id=U2)
    assert target_point(state, action) == (3, 1)
    assert target_point(state, UseSkill(unit_id=U1, skill_id=TIDAL, direction="north")) is None


# ---------------------------------------------------------------------------
# 戰鬥紀錄文字、確定性與重播
# ---------------------------------------------------------------------------


def test_the_battle_log_names_the_variant() -> None:
    state = _state([TIDAL], surfaces=[(3, 3, "water")])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=TIDAL, direction="north"))
    text = "\n".join(filter(None, (describe_event(e, result.state) for e in result.events)))
    assert "施放「潮汐之矛」（水中貫穿）（AP 2" in text


def _variant_setup() -> BattleSetup:
    lib = library()
    heights = "0000000\n0000000\n0000000\n0000000\n0000000\n0001000\n0000000"
    terrain = ".......\n.......\n.......\n.......\n.......\n.......\n#......"
    m = make_map(
        heights,
        terrain,
        ally=[(3, 6), (1, 6), (5, 6)],
        enemy=[(3, 0), (2, 1), (4, 1)],
        surfaces=[(3, 5, "water"), (1, 5, "ice"), (2, 1, "oil"), (4, 1, "oil")],
    )
    spawns = [
        spawn(Team.ALLY, (3, 6), "variant_tidecaller", skills=None),
        spawn(Team.ALLY, (1, 6), "variant_vanguard", skills=None),
        spawn(Team.ALLY, (5, 6), "variant_slinger", skills=None),
    ]
    spawns += [spawn(Team.ENEMY, xy, "bandit", skills=None) for xy in [(3, 0), (2, 1), (4, 1)]]
    assert lib.unit("variant_tidecaller").skills == (TIDAL,)
    return make_setup(m, spawns)


def test_same_seed_same_battle_and_replay_is_identical() -> None:
    setup = _variant_setup()
    policy = UtilityAI(library().ai_profiles)
    first = run_battle(setup, 5, policy)
    second = run_battle(setup, 5, policy)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert first.actions == second.actions
    again = replay(setup, 5, first.actions)
    assert state_to_json(again.state) == state_to_json(first.state)
    used = [e for e in first.events if isinstance(e, SkillUsed)]
    assert any(e.variant is not None for e in used)
