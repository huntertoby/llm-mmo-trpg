"""技能變形（Phase 3D-3，``docs/phases/Phase3D計畫.md`` 3.1）：修正規則的 ``area_delta``、
``shape_to``、``allow_self_target``。

變形在選目標之前決定（條件只能是 ``self_hp_below``）：``legal_actions``、預覽與實際結算都用
:func:`trpg.engine.modifiers.shaped_skill` 變形後的技能，彼此一致。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.skills import ShapeSpec, SkillDef
from trpg.engine import BattleState, UseSkill, legal_actions, preview, resolve
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.events import DamageDealt, Healed, SkillUsed
from trpg.engine.modifiers import acting_skill, shaped_skill
from trpg.engine.skills.targeting import SkillArea
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget

BASE = "skill_t_shaped"
HERO = (3, 3)
EAST = "east"


def modifier(skill_id: str, *rules: dict[str, Any]) -> SkillDef:
    """測試用修正技能（不經驗證器）。"""
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"修正 {skill_id[-1]}",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": list(rules),
        }
    )


def rule(change: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"applies_to": {"all_skills": True}, "change": change, **extra}


def damage_skill(shape: dict[str, Any]) -> SkillDef:
    return make_skill(BASE, shape, [{"type": "damage", "dice": "1d6", "element": "fire"}])


def heal_skill(shape: dict[str, Any]) -> SkillDef:
    return make_skill(BASE, shape, [{"type": "heal", "dice": "2d6", "affects": "allies"}])


def arena(
    base: SkillDef,
    mods: list[SkillDef],
    *,
    foes: list[tuple[int, int]] | None = None,
    allies: list[tuple[int, int]] | None = None,
    hero_hp: int | None = None,
) -> BattleState:
    """U1（施放者，在 ``HERO``）裝備 ``base`` 與 ``mods``；之後依序是 ``foes``（不反應）與
    ``allies``（受傷，HP 5/200）。"""
    foe_xy = foes if foes is not None else [(6, 6)]
    ally_xy = allies or []
    m = make_map(FLAT7, ally=[HERO, *ally_xy], enemy=foe_xy)
    extra: dict[str, object] = {} if hero_hp is None else {"max_hp": 200}
    hero = caster_template([base, *mods], base="hero_mage", **extra)
    spawns = [spawn(Team.ALLY, HERO, hero)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=999)) for xy in foe_xy]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer", max_hp=200)) for xy in ally_xy]
    state = make_state(m, spawns, skills=[base, *mods])
    state = give_turn(state, U1)
    if hero_hp is not None:
        state.units[U1].hp = hero_hp
    return state


def selections(state: BattleState, skill_id: str = BASE) -> list[tuple[UseSkill, SkillArea]]:
    actions, areas = legal_actions_with_areas(state)
    return [
        (a, areas[id(a)]) for a in actions if isinstance(a, UseSkill) and a.skill_id == skill_id
    ]


def direction_area(state: BattleState, direction: str = EAST) -> SkillArea:
    (found,) = [area for a, area in selections(state) if a.direction == direction]
    return found


def tiles(area: SkillArea) -> set[tuple[int, int]]:
    return set(area.tiles)


def shape_of(state: BattleState, unit: UnitId = U1, skill_id: str = BASE) -> ShapeSpec:
    return acting_skill(state, state.units[unit], skill_id).shape


# ---------------------------------------------------------------------------
# area_delta
# ---------------------------------------------------------------------------


def test_area_delta_adds_one_to_a_cone_and_the_area_grows() -> None:
    cone = damage_skill({"type": "cone", "size": 2})
    plain = arena(cone, [])
    grown = arena(cone, [modifier("skill_t_mod_a", rule({"area_delta": 1}))])
    assert shape_of(plain).size == 2 and shape_of(grown).size == 3
    assert len(direction_area(plain).tiles) == 4  # 第 1 排 1 格、第 2 排 3 格
    assert len(direction_area(grown).tiles) == 9  # ＋第 3 排 5 格


@pytest.mark.parametrize(
    ("shape", "param", "start", "limit"),
    [
        ({"type": "line", "size": 5}, "size", 5, 6),
        ({"type": "ring", "radius": 1}, "radius", 1, 2),
        ({"type": "allies_in_radius", "radius": 2}, "radius", 2, 3),
    ],
)
def test_area_delta_grows_each_sized_shape(
    shape: dict[str, Any], param: str, start: int, limit: int
) -> None:
    state = arena(damage_skill(shape), [modifier("skill_t_mod_a", rule({"area_delta": 1}))])
    assert getattr(shape_of(state), param) == start + 1 == limit


@pytest.mark.parametrize(
    "shape",
    [
        {"type": "cone", "size": 4},
        {"type": "line", "size": 6},
        {"type": "ring", "radius": 2},
        {"type": "allies_in_radius", "radius": 3},
    ],
)
def test_area_delta_stops_at_the_shape_maximum(shape: dict[str, Any]) -> None:
    skill = damage_skill(shape)
    state = arena(skill, [modifier("skill_t_mod_a", rule({"area_delta": 1}))])
    assert shaped_skill(state, state.units[U1], skill).shape == skill.shape


def test_area_delta_leaves_fixed_size_shapes_alone() -> None:
    for shape in ({"type": "square3", "range": 4}, {"type": "cross", "range": 3}):
        skill = damage_skill(shape)
        state = arena(skill, [modifier("skill_t_mod_a", rule({"area_delta": 1}))])
        assert shaped_skill(state, state.units[U1], skill) is skill  # 沒有變化：同一個物件


def test_area_delta_stacks_and_respects_the_condition() -> None:
    cone = damage_skill({"type": "cone", "size": 2})
    two = arena(
        cone,
        [
            modifier("skill_t_mod_a", rule({"area_delta": 1})),
            modifier("skill_t_mod_b", rule({"area_delta": 1})),
        ],
    )
    assert shape_of(two).size == 4
    low = {"type": "self_hp_below", "permille": 500}
    gated = arena(cone, [modifier("skill_t_mod_a", rule({"area_delta": 1}, condition=low))])
    assert shape_of(gated).size == 2  # HP 滿：條件不成立
    hurt = arena(
        cone, [modifier("skill_t_mod_a", rule({"area_delta": 1}, condition=low))], hero_hp=50
    )
    assert shape_of(hurt).size == 3


def test_only_matching_skills_and_only_active_skills_are_reshaped() -> None:
    cone = damage_skill({"type": "cone", "size": 2})
    tagged = modifier(
        "skill_t_mod_a",
        {"applies_to": {"skill_tags": ["fire"]}, "change": {"area_delta": 1}},
    )
    state = arena(cone, [tagged])
    assert shape_of(state).size == 2  # 測試技能沒有 fire 標籤
    fire = cone.model_copy(update={"tags": ("fire",)})
    assert shaped_skill(state, state.units[U1], fire).shape.size == 3
    stance = fire.model_copy(update={"kind": "stance"})
    assert shaped_skill(state, state.units[U1], stance) is stance  # 只有主動技能變形
    reaction = fire.model_copy(update={"kind": "reaction"})
    assert shaped_skill(state, state.units[U1], reaction) is reaction


# ---------------------------------------------------------------------------
# shape_to
# ---------------------------------------------------------------------------


def test_single_to_line_changes_the_selections_and_hits_everyone_on_the_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    single = damage_skill({"type": "single", "range": 5})
    foes = [(4, 3), (5, 3), (6, 3), (3, 1)]
    plain = arena(single, [], foes=foes)
    lined = arena(single, [modifier("skill_t_mod_a", rule({"shape_to": "line"}))], foes=foes)
    # 合法動作：變形前選單位，變形後選方向
    assert all(a.target_id is not None and a.direction is None for a, _ in selections(plain))
    picks = selections(lined)
    assert [a.direction for a, _ in picks] == ["north", "east", "south", "west"][: len(picks)]
    assert all(a.target_id is None and a.direction is not None for a, _ in picks)
    area = direction_area(lined)
    assert tiles(area) == {(4, 3), (5, 3), (6, 3)}  # 直線長度 3
    # 結算：東邊三個敵人都挨打，南邊 (3, 1) 的不會
    east = next(a for a, _ in picks if a.direction == EAST)
    result = resolve(lined, east)
    assert {d.target_id for d in of(result, DamageDealt)} == {U2, U3, "unit_0004"}
    used = of(result, SkillUsed)[0]
    assert {(p.x, p.y) for p in used.tiles} == tiles(area)


def test_the_preview_shows_the_reshaped_area_and_matches_the_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    single = damage_skill({"type": "single", "range": 5})
    state = arena(
        single,
        [modifier("skill_t_mod_a", rule({"shape_to": "line"}))],
        foes=[(4, 3), (5, 3)],
    )
    east = next(a for a, _ in selections(state) if a.direction == EAST)
    pv = preview(state, east)
    assert {(x, y) for x, y in pv.affected_tiles} == {(4, 3), (5, 3), (6, 3)}
    assert set(pv.affected_units) == {U2, U3}
    result = resolve(state, east)
    assert {d.target_id for d in of(result, DamageDealt)} == set(pv.affected_units)
    # 預覽的 AP 與射程（直線沒有射程）不受影響
    assert pv.ap_cost == single.ap_cost


def test_single_to_chain_keeps_the_range_and_clamps_it(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    single = damage_skill({"type": "single", "range": 10})
    state = arena(
        single,
        [modifier("skill_t_mod_a", rule({"shape_to": "chain"}))],
        foes=[(5, 3), (6, 3)],
    )
    shape = shape_of(state)
    assert (shape.type, shape.range, shape.jumps, shape.jump_range) == ("chain", 6, 1, 2)
    first = next(a for a, _ in selections(state) if a.target_id == U2)
    result = resolve(state, first)
    assert {d.target_id for d in of(result, DamageDealt)} == {U2, U3}  # 跳一次到相鄰的第二個敵人


def test_single_to_chain_uses_the_weapon_range_for_weapon_range_skills() -> None:
    skill = make_skill(
        BASE,
        {"type": "single", "range": "weapon"},
        [{"type": "damage", "multiplier_permille": 1000}],
        category="weapon",
    )
    to_chain = modifier("skill_t_mod_a", rule({"shape_to": "chain"}))
    m = make_map(FLAT7, ally=[HERO], enemy=[(6, 6)])
    hero = caster_template([skill, to_chain], base="hero_fighter")
    state = make_state(
        m, [spawn(Team.ALLY, HERO, hero), spawn(Team.ENEMY, (6, 6))], skills=[skill, to_chain]
    )
    weapon_range = state.units[U1].weapon.range
    assert shape_of(state).range == max(1, min(6, weapon_range))


def test_line_to_cone_keeps_the_size_up_to_the_cone_maximum() -> None:
    state = arena(
        damage_skill({"type": "line", "size": 5}),
        [modifier("skill_t_mod_a", rule({"shape_to": "cone"}))],
    )
    shape = shape_of(state)
    assert (shape.type, shape.size) == ("cone", 4)
    short = arena(
        damage_skill({"type": "line", "size": 2}),
        [modifier("skill_t_mod_a", rule({"shape_to": "cone"}))],
    )
    assert shape_of(short).size == 2


def test_conversions_chain_in_skill_id_order_and_area_delta_comes_last() -> None:
    both = [
        modifier("skill_t_mod_b", rule({"shape_to": "cone"})),  # ID 排序：先轉直線、再轉錐形
        modifier("skill_t_mod_a", rule({"shape_to": "line"})),
    ]
    state = arena(damage_skill({"type": "single", "range": 4}), both)
    shape = shape_of(state)
    assert (shape.type, shape.size) == ("cone", 3)  # 單體 → 直線（3）→ 錐形（保留 3）
    bigger = arena(
        damage_skill({"type": "single", "range": 4}),
        [*both, modifier("skill_t_mod_c", rule({"area_delta": 1}))],
    )
    assert shape_of(bigger).size == 4  # area_delta 在轉換之後加上去


def test_pairs_outside_the_conversion_table_are_refused() -> None:
    """表列之外的組合不轉：環形、錐形不能變直線；單體不能直接變錐形。"""
    to_line = modifier("skill_t_mod_a", rule({"shape_to": "line"}))
    to_cone = modifier("skill_t_mod_a", rule({"shape_to": "cone"}))
    for skill, mod in (
        (damage_skill({"type": "ring", "radius": 1}), to_line),
        (damage_skill({"type": "cone", "size": 3}), to_line),
        (damage_skill({"type": "single", "range": 4}), to_cone),
        (damage_skill({"type": "cross", "range": 3}), to_cone),
    ):
        state = arena(skill, [mod])
        assert shaped_skill(state, state.units[U1], skill) is skill


def test_skills_whose_effects_need_the_original_shape_are_not_converted() -> None:
    """效果原語限定形狀（衝鋒必須是單體）時不轉：猛虎衝撞維持單體。"""
    dash = library().skills["skill_tiger_charge"]
    to_line = modifier("skill_t_mod_a", rule({"shape_to": "line"}))
    m = make_map(FLAT7, ally=[HERO], enemy=[(6, 3)])
    hero = caster_template(["skill_tiger_charge", to_line], base="hero_fighter")
    state = make_state(
        m, [spawn(Team.ALLY, HERO, hero), spawn(Team.ENEMY, (6, 3))], skills=[to_line]
    )
    assert shaped_skill(state, state.units[U1], dash) is dash


# ---------------------------------------------------------------------------
# allow_self_target
# ---------------------------------------------------------------------------


def test_a_line_heal_includes_the_caster_only_with_allow_self_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    heal = heal_skill({"type": "single", "range": 4})
    line = modifier("skill_t_mod_a", rule({"shape_to": "line"}))
    me = modifier("skill_t_mod_b", rule({"allow_self_target": True}))
    for mods, caster_healed in (([line], False), ([line, me], True)):
        state = arena(heal, mods, allies=[(4, 3)], foes=[(6, 6)])
        state.units[U1].hp = 50
        east = next(a for a, _ in selections(state) if a.direction == EAST)
        result = resolve(state, east)
        healed = {h.target_id for h in of(result, Healed)}
        assert ("unit_0003" in healed) and ((U1 in healed) is caster_healed), mods
        used = of(result, SkillUsed)[0]
        assert ((HERO[0], HERO[1]) in {(p.x, p.y) for p in used.tiles}) is caster_healed


def test_allow_self_target_is_a_no_op_for_single_target_heals_and_attacks() -> None:
    me = modifier("skill_t_mod_b", rule({"allow_self_target": True}))
    single = heal_skill({"type": "single", "range": 4})
    state = arena(single, [me], allies=[(4, 3)])
    picks = selections(state)
    assert {a.target_id for a, _ in picks} >= {U1, "unit_0003"}  # 單體本來就能選自己
    assert all(len(area.tiles) == 1 for _, area in picks)
    # 沒有對友方生效的效果（攻擊技能）：不會把施放者算進範圍
    cone = damage_skill({"type": "cone", "size": 2})
    attack = arena(cone, [me])
    assert not acting_skill(attack, attack.units[U1], BASE).include_caster
    assert HERO not in tiles(direction_area(attack))


def test_preview_and_legal_actions_include_the_caster_in_a_self_inclusive_line() -> None:
    heal = heal_skill({"type": "single", "range": 4})
    state = arena(
        heal,
        [
            modifier("skill_t_mod_a", rule({"shape_to": "line"})),
            modifier("skill_t_mod_b", rule({"allow_self_target": True})),
        ],
        allies=[(4, 3)],
    )
    area = direction_area(state)
    assert HERO in tiles(area) and U1 in area.units
    east = next(a for a, _ in selections(state) if a.direction == EAST)
    pv = preview(state, east)
    assert HERO in pv.affected_tiles and U1 in pv.affected_units


# ---------------------------------------------------------------------------
# 預算與資料
# ---------------------------------------------------------------------------


def budget_of(*rules: dict[str, Any]) -> list[Any]:
    skill = modifier("skill_t_mod_budget", *rules)
    return list(skill_budget(skill, library()).effects)


def test_the_budget_of_shape_to_is_the_shape_multiplier_difference() -> None:
    """基準傷害 7 ×（轉換後 − 轉換前的形狀倍率）× 使用次數 6（所有技能）× 站位受益 400‰。"""
    expected = {
        "line": 7 * (1400 - 1000),  # 單體 1000‰ → 直線 3 格（800 + 200 × 3）
        "chain": 7 * (1250 - 1000),  # 單體 → 連鎖 1 跳（1000 + 250 × 1）
        "cone": 7 * (1600 - 1400),  # 直線 3 格 1400‰ → 錐形 3 格 1600‰
    }
    for target, milli in expected.items():
        (effect,) = budget_of(rule({"shape_to": target}))
        assert effect.type == "modifier.shape_to"
        assert float(effect.points) == pytest.approx(milli / 1000 * 6 * 0.4), target


def test_the_budget_of_the_other_shape_changes_uses_the_flat_points() -> None:
    (grow,) = budget_of(rule({"area_delta": 1}))
    assert float(grow.points) == pytest.approx(1.4 * 6 * 0.4)
    (me,) = budget_of(rule({"allow_self_target": True}))
    assert float(me.points) == pytest.approx(2.8 * 6 * 0.4)


def test_the_shipped_shape_modifiers_pass_the_budget_and_validation() -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    for skill_id in ("skill_lingering_roar", "skill_beam_of_mercy", "skill_self_mending"):
        skill = library().skills[skill_id]
        assert validate_skill(skill, library()) == [], skill_id
        assert 0.7 <= float(skill_budget(skill, library()).ratio) <= 1.0


def test_the_conversion_table_is_validated() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    table = library().ruleset.shapes
    base = table.model_dump(mode="json")

    def with_conversions(conversions: list[dict[str, Any]]) -> None:
        type(table).model_validate({**base, "conversions": conversions})

    good: list[dict[str, Any]] = [
        {"from_shape": "single", "to": "line", "params": {"size": 3}},
        {
            "from_shape": "single",
            "to": "chain",
            "params": {"jumps": 1, "jump_range": 2},
            "keep": ["range"],
        },
        {"from_shape": "line", "to": "cone", "keep": ["size"]},
    ]
    with_conversions(good)
    bad: list[tuple[list[dict[str, Any]], str]] = [
        (
            [*good, {"from_shape": "single", "to": "ring", "params": {"radius": 1}}],
            "目標形狀必須是",
        ),
        ([*good, {"from_shape": "single", "to": "line", "params": {"size": 3}}], "重複"),
        ([{**good[0], "params": {"size": 9}}, *good[1:]], "超出"),
        ([good[0], {**good[1], "keep": []}, good[2]], "缺少 chain 的必要參數"),
        ([good[0], good[1], {**good[2], "keep": ["range"]}], "不是 line 的參數"),
        ([good[0], good[1]], "缺少目標形狀"),
        ([{"from_shape": "nope", "to": "line", "params": {"size": 3}}, *good[1:]], "形狀不存在"),
    ]
    for conversions, message in bad:
        with pytest.raises(ValidationError, match=message):
            with_conversions(conversions)


def test_legal_actions_never_list_an_action_the_resolution_would_refuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """變形後的每個合法動作都能結算（合法動作與結算用同一個變形技能）。"""
    always(monkeypatch)
    single = damage_skill({"type": "single", "range": 5})
    mods = [
        modifier("skill_t_mod_a", rule({"shape_to": "line"})),
        modifier("skill_t_mod_b", rule({"area_delta": 1})),
    ]
    state = arena(single, mods, foes=[(4, 3), (5, 5)])
    shaped = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == BASE]
    assert shaped
    for action in shaped:
        resolve(state, action)


@pytest.mark.parametrize(
    ("build", "needle"),
    [
        (
            "build_healer",
            "施放「回春」（AP 1，法力 5，冷卻 1 回合）→ 影響 4 格",
        ),  # 直線 3 格 ＋ 自己
        ("build_tank", "施放「挑釁怒吼」（AP 1，法力 1，冷卻 2 回合）→ 影響 16 格"),  # 環形半徑 1 → 2
    ],
)
def test_ai_battles_with_reshaped_skills_replay(
    build: str, needle: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AI 打整場：變形後的技能照常被使用，戰鬥紀錄重播一致。"""
    log = tmp_path / "shaping.json"
    argv = ["battle", "--map", "open_plain", "--seed", "0", "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert needle in capsys.readouterr().out
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()
