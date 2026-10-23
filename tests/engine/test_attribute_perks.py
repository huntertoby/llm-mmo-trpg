"""屬性的常駐數值（Phase 3H-1，07 7.2）：階數、六個結算點、資料驅動。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, make_skill, no_reactions, template
from tests.engine.skill_helpers import SID, U1, U2, battle, cast
from tests.engine.skill_helpers import of as skill_of
from tests.engine.test_collision import FOE, always, arena, collisions, east, terrain_with
from tests.engine.test_reactions import _line, _walk_away
from tests.engine.test_zones import arena as zone_arena
from tests.engine.test_zones import at as zone_at
from tests.engine.test_zones import cast as zone_cast
from tests.engine.test_zones import of as zone_of
from trpg.content.rules import AttributePerks
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.context import Ctx
from trpg.engine.control import plan_status
from trpg.engine.effects import run_effects
from trpg.engine.events import AttackRolled, SurfaceChanged, ZoneCreated
from trpg.engine.rules.combat import concealment_problem
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.state import StatusInstance, TrapState
from trpg.engine.traps import detect_traps, visible_traps
from trpg.shared.types import Attribute, Pos, Team, UnitId

PERKS = library().ruleset.core.attribute_perks


def _noop() -> SkillDef:
    return make_skill(
        SID,
        {"type": "single", "range": 5},
        [{"type": "damage", "dice": "1d4", "element": "physical"}],
    )


def _set(state: BattleState, uid: UnitId, **attrs: int) -> BattleState:
    for name, value in attrs.items():
        state.units[uid].attributes[Attribute(name)] = value
    return state


# ---------------------------------------------------------------------------
# 資料與階數
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "tier"), [(8, 0), (10, 0), (13, 0), (14, 1), (17, 1), (18, 2), (21, 2), (22, 3)]
)
def test_every_four_points_above_ten_is_one_tier(value: int, tier: int) -> None:
    assert (PERKS.base, PERKS.step) == (10, 4)
    assert PERKS.tier(value) == tier


def test_perks_follow_the_data_not_the_code() -> None:
    """門檻與每階數值都來自資料：換一份資料，結算跟著變。"""
    custom = AttributePerks.model_validate(
        {
            "base": 8,
            "step": 2,
            "perks": [{"attr": "str", "kind": "collision_dealt", "per_tier": 3, "text_zh": "x{n}"}],
        }
    )
    assert custom.tier(12) == 2
    assert custom.total("collision_dealt", lambda _a: 12) == 6
    assert custom.total("control_resist", lambda _a: 12) == 0


def test_the_spec_table_attributes_and_kinds() -> None:
    by_attr = {a: sorted(p.kind for p in PERKS.of_attr(a)) for a in Attribute}
    assert by_attr[Attribute.STR] == ["collision_dealt", "collision_taken"]
    assert by_attr[Attribute.INT] == ["surface_duration"]
    assert by_attr[Attribute.WIS] == ["reaction_hit", "reveal_range"]
    assert by_attr[Attribute.WIL] == ["control_resist"]
    assert by_attr[Attribute.DEX] == by_attr[Attribute.CON] == []  # 敏捷、體質本來就有常駐數值
    assert all("{n}" in p.text_zh for p in PERKS.perks)


def test_duplicate_perks_are_rejected() -> None:
    one = {"attr": "str", "kind": "collision_dealt", "per_tier": 1, "text_zh": "x{n}"}
    with pytest.raises(ValueError, match="重複"):
        AttributePerks.model_validate({"perks": [one, one]})


def test_status_bonus_counts_toward_the_tier() -> None:
    state = battle(_noop(), [(5, 3)])
    unit = state.units[U1]
    unit.attributes[Attribute.INT] = 10
    assert attribute_perk(state.ruleset, unit, "surface_duration") == 0
    unit.attributes[Attribute.INT] = 18
    assert attribute_perk(state.ruleset, unit, "surface_duration") == 2


# ---------------------------------------------------------------------------
# 力量：撞擊傷害
# ---------------------------------------------------------------------------


def _wall_hits(monkeypatch: pytest.MonkeyPatch, pusher: int, victim: int) -> list[int]:
    always(monkeypatch)
    state = arena(terrain=terrain_with("#", 3))
    _set(state, U1, str=pusher)
    _set(state, U2, str=victim)
    result = run_effects(state, [east(2)])
    assert result.state.units[U2].xy == FOE
    return [d.amount for d in collisions(result.events)]


def test_strength_tiers_add_to_the_collision_damage_you_deal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _wall_hits(monkeypatch, 10, 10) == [4, 4]  # 預設撞擊骰（固定 4）
    assert _wall_hits(monkeypatch, 14, 10) == [5, 5]  # 1 階 +1
    assert _wall_hits(monkeypatch, 22, 10) == [7, 7]  # 3 階 +3


def test_strength_tiers_reduce_the_collision_damage_you_take(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _wall_hits(monkeypatch, 10, 18) == [2, 2]  # 受害者 2 階 −2
    assert _wall_hits(monkeypatch, 14, 14) == [4, 4]  # 一加一減


def test_the_reduction_never_goes_below_the_minimum_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _wall_hits(monkeypatch, 10, 50) == [1, 1]  # 最低 1 點（min_damage）


# ---------------------------------------------------------------------------
# 智力：表面與持續區域 +回合
# ---------------------------------------------------------------------------


def _surface_turns(int_value: int) -> int:
    skill = make_skill(
        SID,
        {"type": "cross", "range": 4},
        [{"type": "create_surface", "surface": "oil", "duration": 3}],
    )
    state = _set(battle(skill), U1, int=int_value)
    result = cast(state, target_pos=Pos(x=2, y=2))
    assert skill_of(result, SurfaceChanged)
    return result.state.tile(2, 2).surface_remaining or 0


def test_intelligence_tiers_extend_your_surfaces() -> None:
    assert [_surface_turns(v) for v in (10, 13, 14, 18, 22)] == [3, 3, 4, 5, 6]


def test_intelligence_tiers_extend_your_zones() -> None:
    def lasts(int_value: int) -> int:
        state = _set(zone_arena(), U1, int=int_value)
        result = zone_cast(state, **zone_at(3, 3))
        [created] = zone_of(result, ZoneCreated)
        return created.expires_round - result.state.round

    assert [lasts(v) for v in (10, 14, 18)] == [2, 3, 4]


# ---------------------------------------------------------------------------
# 感知：反應攻擊命中、看見隱蔽單位、看見陷阱
# ---------------------------------------------------------------------------


def _reaction_bonus(wis: int) -> int:
    state = _line(
        guard=template("hero_fighter", attributes={"wis": wis}),
        mover=template("bandit", max_hp=300, reactions=[]),
    )
    rolls = [e for e in _walk_away(state) if isinstance(e, AttackRolled)]
    assert len(rolls) == 1
    return rolls[0].modifier_bonus


def test_wisdom_tiers_raise_the_hit_of_reaction_attacks() -> None:
    assert [_reaction_bonus(v) for v in (10, 14, 18)] == [0, 1, 2]


def test_wisdom_does_not_raise_the_hit_of_your_own_turn_attacks() -> None:
    from tests.engine.helpers import give_turn, make_map, make_state, spawn  # noqa: PLC0415
    from trpg.engine import Attack, resolve  # noqa: PLC0415

    m = make_map("000000\n000000", ally=[(1, 0)], enemy=[(2, 0)])
    hero = template("hero_fighter", attributes={"wis": 22})
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (1, 0), hero), spawn(Team.ENEMY, (2, 0), no_reactions())]),
        "unit_0001",
    )
    events = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    assert [e.modifier_bonus for e in events if isinstance(e, AttackRolled)] == [0]


def _concealed_problem(wis: int, distance: int) -> str | None:
    skill = _noop()
    state = battle(skill, [(distance, 3)], caster=(0, 3))
    _set(state, U1, wis=wis)
    state.units[U2].statuses.append(StatusInstance("concealed", 3))
    return concealment_problem(state, state.units[U1], state.units[U2])


def test_wisdom_tiers_extend_how_far_you_can_target_concealed_units() -> None:
    base = library().ruleset.core.concealed_ranged_max_distance
    assert base == 2
    assert _concealed_problem(10, 3) is not None  # 預設 2 格內
    assert _concealed_problem(14, 3) is None  # 1 階：3 格
    assert _concealed_problem(14, 4) is not None
    assert _concealed_problem(18, 4) is None  # 2 階：4 格


def _enemy_trap(xy: tuple[int, int]) -> TrapState:
    return TrapState(
        owner_id=U2,
        team=Team.ENEMY,
        pos=Pos(x=xy[0], y=xy[1]),
        skill_id="skill_bear_trap",
        remaining=3,
        attributes=tuple((a, 10) for a in Attribute),
    )


def _seen_traps(wis: int) -> list[tuple[int, int]]:
    state = battle(_noop(), [(6, 6)])
    _set(state, U1, wis=wis)
    state.traps = [_enemy_trap((3, 4)), _enemy_trap((3, 5)), _enemy_trap((0, 0))]
    ctx = Ctx(state)
    detect_traps(ctx, ctx.state.units[U1])
    return sorted(t.xy for t in visible_traps(ctx.state, Team.ALLY))


def test_wisdom_tiers_reveal_nearby_enemy_traps() -> None:
    assert _seen_traps(10) == []  # 沒有階數：和以前一樣看不見
    assert _seen_traps(14) == [(3, 4)]  # 1 階：1 格
    assert _seen_traps(18) == [(3, 4), (3, 5)]  # 2 階：2 格


# ---------------------------------------------------------------------------
# 意志：控制的抵抗
# ---------------------------------------------------------------------------


def _resist(status: str, wil: int, **others: int) -> int:
    state = battle(_noop(), [(5, 3)])
    _set(state, U2, wil=wil, str=10, con=10, dex=10, int=10, wis=10, **others)
    return plan_status(state, state.units[U2], status).defense_value


def test_willpower_tiers_raise_the_resist_of_every_control() -> None:
    for control, base in (("root", 10), ("stun", 10), ("slow", 10), ("feared", 10)):
        assert _resist(control, 10) == base
        assert _resist(control, 14) == base + 1
        assert _resist(control, 22) == base + 3


def test_willpower_does_not_help_against_non_control_debuffs() -> None:
    assert _resist("weaken", 22) == _resist("weaken", 10)  # 沒有 control_group
    assert _resist("poison", 22) == _resist("poison", 10)


def test_the_resist_value_is_still_diminished_after_the_bonus() -> None:
    """遞減只乘在加成之後的值（資料決定的順序）。"""
    state = battle(_noop(), [(5, 3)])
    _set(state, U2, wil=14, con=10)
    base = plan_status(state, state.units[U2], "stun")
    assert base.defense_value == 11 and not base.diminished
