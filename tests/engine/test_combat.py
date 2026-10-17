"""判定、優劣勢、暴擊、傷害與元素修正（驗收條件 5、8）。"""

from __future__ import annotations

from fractions import Fraction
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    spawn,
    template,
    with_rolls,
)
from trpg.engine import Attack, BattleState, Defend, legal_actions, resolve
from trpg.engine.effects import ApplyStatusEffect, DamageEffect, run_effects
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.engine.rules import combat
from trpg.engine.rules.combat import (
    advantage_state,
    defense_value_permille,
    element_modifier_ppm,
    hit_modifier,
    is_hit,
)
from trpg.engine.rules.geometry import bresenham, has_line_of_sight
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, ResistGroup, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")

FLAT3 = "000\n000\n000"


def _hit_chance(modifier: int, proficiency: int = 2, target: int = 11) -> Fraction:
    hits = sum(is_hit(n, n + modifier + proficiency, target) for n in range(1, 21))
    return Fraction(hits, 20)


@pytest.mark.parametrize(
    ("attack", "defense", "expected"),
    [
        (10, 10, Fraction(60, 100)),  # 同級
        (20, 10, Fraction(80, 100)),  # 2 倍
        (40, 10, Fraction(95, 100)),  # 4 倍
        (400, 10, Fraction(95, 100)),  # 4 倍以上
        (5, 10, Fraction(40, 100)),  # 一半
        (25, 100, Fraction(20, 100)),  # 1/4
        (1, 100, Fraction(20, 100)),  # 1/4 以下
    ],
)
def test_hit_rate_table_exhaustive(attack: int, defense: int, expected: Fraction) -> None:
    """docs/專案計畫.md 5.4 的命中率表：窮舉 d20 驗證。"""
    table = library().ruleset.hit_table
    core = library().ruleset.core
    modifier = table.modifier(attack, defense)
    assert _hit_chance(modifier, core.proficiency, core.hit_target) == expected


def test_natural_one_and_twenty() -> None:
    assert not is_hit(1, 1 + 100, 11)
    assert is_hit(20, 20 - 100, 11)
    assert is_hit(10, 11, 11)
    assert not is_hit(10, 10, 11)


def _adv_chance(modifier: int, mode: str) -> Fraction:
    hits = 0
    for a, b in product(range(1, 21), repeat=2):
        n = max(a, b) if mode == "advantage" else min(a, b)
        hits += is_hit(n, n + modifier + 2, 11)
    return Fraction(hits, 400)


def test_advantage_and_disadvantage_probabilities() -> None:
    base = _hit_chance(0)
    assert _adv_chance(0, "advantage") == 1 - (1 - base) ** 2
    assert _adv_chance(0, "disadvantage") == base**2


def _duel(attacker_weapon: str = "one_handed_sword", **target_overrides: object) -> BattleState:
    """戰士 vs 盜賊。盜賊不設反應（不格擋），以便直接驗證 1A 的傷害公式。"""
    m = make_map(FLAT3)
    a = spawn(Team.ALLY, (0, 1), "hero_fighter", weapon=attacker_weapon)
    target_overrides.setdefault("reactions", [])
    t = spawn(Team.ENEMY, (1, 1), template("bandit", **target_overrides))
    state = make_state(m, [a, t])
    return give_turn(state, U1)


def test_prone_target_gives_melee_advantage_ranged_disadvantage() -> None:
    state = _duel()
    s = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="prone")]).state
    attacker, target = s.units[U1], s.units[U2]
    assert advantage_state(s, attacker, target) == "advantage"
    bow_state = _duel("bow")
    bow_state = run_effects(bow_state, [ApplyStatusEffect(target_id=U2, status_id="prone")]).state
    assert advantage_state(bow_state, bow_state.units[U1], bow_state.units[U2]) == ("disadvantage")
    # 優勢時擲兩顆取高
    s = with_rolls(s, [(20, 3), (20, 17)])
    s.active_unit = U1
    events = resolve(s, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled.rolls == (3, 17) and rolled.natural == 17 and rolled.advantage == "advantage"


@pytest.mark.parametrize(
    ("adv", "dis", "expected"),
    [
        (True, False, "advantage"),
        (False, True, "disadvantage"),
        (True, True, "none"),
        (False, False, "none"),
    ],
)
def test_combine_advantage(adv: bool, dis: bool, expected: str) -> None:
    assert combat.combine_advantage(adv, dis) == expected


def test_advantage_and_disadvantage_cancel_rolls_one_die(monkeypatch: pytest.MonkeyPatch) -> None:
    """優勢與劣勢同時存在時互相抵消：只擲一顆 d20。"""
    state = with_rolls(_duel(), [(20, 15), (20, 2)])
    monkeypatch.setattr(combat, "advantage_sources", lambda s, a, t: (True, True))
    events = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled.rolls == (15,) and rolled.advantage == "none"


def test_crit_doubles_dice_not_flat() -> None:
    state = _duel()
    # 自然 20 → 暴擊；單手劍 1d8 擲兩顆
    s = with_rolls(state, [(20, 20), (8, 5), (8, 6)])
    events = resolve(s, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    damage = next(e for e in events if isinstance(e, DamageDealt))
    assert rolled.hit and rolled.crit
    assert damage.rolls == (5, 6) and damage.crit
    # (5 + 6) + 力量 16 × 0.3 = 15.8 → 15（無條件捨去）
    assert damage.amount == 15


def test_crit_range_requires_hit() -> None:
    m = make_map(FLAT3)
    a = spawn(Team.ALLY, (0, 1), "bandit", weapon="dagger")
    t = spawn(Team.ENEMY, (1, 1), "bandit")
    # 預設數值下自然 17 以上必定命中，因此把命中門檻調高來構造「19 但失手」
    state = give_turn(make_state(m, [a, t], hit_target=30), U1)
    s = with_rolls(state, [(20, 19)])
    rolled = next(
        e
        for e in resolve(s, Attack(unit_id=U1, target_id=U2)).events
        if isinstance(e, AttackRolled)
    )
    assert rolled.natural == 19 and not rolled.hit and not rolled.crit
    # 命中時 19 即暴擊（匕首 crit_range 19）
    a2 = spawn(Team.ALLY, (0, 1), "bandit", weapon="dagger")
    t2 = spawn(Team.ENEMY, (1, 1), "bandit")
    s2 = with_rolls(give_turn(make_state(m, [a2, t2]), U1), [(20, 19), (4, 1), (4, 1)])
    events = resolve(s2, Attack(unit_id=U1, target_id=U2)).events
    rolled2 = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled2.hit and rolled2.crit


def test_natural_one_misses_even_with_huge_bonus() -> None:
    m = make_map(FLAT3)
    a = spawn(Team.ALLY, (0, 1), template("hero_fighter", attributes={"str": 500}))
    t = spawn(Team.ENEMY, (1, 1), "bandit")
    s = with_rolls(give_turn(make_state(m, [a, t]), U1), [(20, 1)])
    events = resolve(s, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled.hit_modifier == 8 and not rolled.hit
    assert not any(isinstance(e, DamageDealt) for e in events)


def test_damage_minimum_one_on_hit() -> None:
    state = _duel(resist={"physical": 1000})
    s = with_rolls(state, [(20, 15), (8, 1)])
    events = resolve(s, Attack(unit_id=U1, target_id=U2)).events
    damage = next(e for e in events if isinstance(e, DamageDealt))
    # 物理抗性 100% → 元素修正下限 25%：(1 + 4.8) × 0.25 = 1.45 → 1
    assert damage.element_mod_ppm == 250_000
    assert damage.amount == 1


def test_defend_raises_defense_by_quarter() -> None:
    state = _duel()
    unit = state.units[U1]
    rules = state.ruleset
    base = defense_value_permille(unit, rules)
    s = resolve(state, Defend(unit_id=U1)).state
    assert defense_value_permille(s.units[U1], rules) == base * 1250 // 1000
    assert s.units[U1].ap == state.units[U1].ap - 1
    with pytest.raises(IllegalActionError, match="已處於防禦姿態"):
        resolve(s, Defend(unit_id=U1))


def test_height_bonus() -> None:
    m = make_map("100\n000\n000")
    a = spawn(Team.ALLY, (0, 0), "hero_fighter")
    t = spawn(Team.ENEMY, (1, 0), "bandit")
    state = give_turn(make_state(m, [a, t]), U1)
    rolled = next(
        e
        for e in resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2)).events
        if isinstance(e, AttackRolled)
    )
    assert rolled.situational == 2
    assert rolled.total == 10 + rolled.hit_modifier + 2 + 2
    state2 = give_turn(state, U2)
    rolled2 = next(
        e
        for e in resolve(with_rolls(state2, [(20, 10)]), Attack(unit_id=U2, target_id=U1)).events
        if isinstance(e, AttackRolled)
    )
    assert rolled2.situational == -2


def test_hit_modifier_uses_ratio() -> None:
    state = _duel()
    a, t = state.units[U1], state.units[U2]
    # 戰士攻擊值 16 vs 盜賊防禦值 14 + 2 = 16 → 0
    assert hit_modifier(a, t, state.ruleset) == 0


# ---------------------------------------------------------------------------
# 元素修正
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("resist", "mods", "element", "expected_ppm"),
    [
        ({}, {}, Element.FIRE, 1_000_000),
        ({"elemental": 200}, {}, Element.FIRE, 800_000),
        ({"elemental": 200}, {}, Element.POISON, 1_000_000),  # 不同分組
        ({}, {"fire": 500}, Element.FIRE, 1_500_000),  # 個別弱點
        ({"elemental": 200}, {"fire": 500}, Element.FIRE, 1_200_000),  # 0.8 × 1.5
        ({"elemental": 200}, {"fire": -500}, Element.FIRE, 400_000),  # 0.8 × 0.5
        ({"elemental": 500}, {"fire": -800}, Element.FIRE, 250_000),  # 0.5 × 0.2 → 下限 0.25
        ({"nature": 900}, {}, Element.WIND, 250_000),  # 減傷上限 75%
        ({"spirit": -500}, {}, Element.HOLY, 1_500_000),  # 負抗性 = 易傷
        ({"physical": 300}, {"ice": 1000}, Element.ICE, 2_000_000),
    ],
)
def test_element_modifier(
    resist: dict[str, int], mods: dict[str, int], element: Element, expected_ppm: int
) -> None:
    state = _duel(resist=resist, element_mods=mods)
    target = state.units[U2]
    assert element_modifier_ppm(target, element, state.ruleset) == expected_ppm


def test_element_modifier_applied_to_damage() -> None:
    state = _duel(resist={"elemental": 200}, element_mods={"fire": 500})
    result = run_effects(
        with_rolls(state, [(6, 4)]),
        [DamageEffect(target_id=U2, element=Element.FIRE, dice="1d6", flat=6)],  # type: ignore[arg-type]
    )
    damage = next(e for e in result.events if isinstance(e, DamageDealt))
    # (4 + 6) × 0.8 × 1.5 = 12
    assert damage.amount == 12
    assert result.state.units[U2].resist[ResistGroup.ELEMENTAL] == 200


# ---------------------------------------------------------------------------
# 視線與射程
# ---------------------------------------------------------------------------


def test_bresenham_endpoints_and_symmetric_length() -> None:
    line = bresenham((0, 0), (4, 2))
    assert line[0] == (0, 0) and line[-1] == (4, 2)
    assert len(line) == 5
    assert bresenham((2, 2), (2, 2)) == [(2, 2)]


def test_line_of_sight_blocked_by_height() -> None:
    m = make_map("00000\n00200\n00000")
    a = spawn(Team.ALLY, (0, 1), "hero_archer")
    t = spawn(Team.ENEMY, (4, 1), "bandit")
    state = give_turn(make_state(m, [a, t]), U1)
    assert not has_line_of_sight(state, (0, 1), (4, 1))
    assert has_line_of_sight(state, (0, 0), (4, 0))
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        resolve(state, Attack(unit_id=U1, target_id=U2))


def test_line_of_sight_from_high_ground() -> None:
    # 高度 1 的格子擋不住高度 1 的攻擊者（需要 ≥ max + 1 才阻擋）
    m = make_map("10101\n00000\n00000")
    a = spawn(Team.ALLY, (0, 0), "hero_archer")
    t = spawn(Team.ENEMY, (4, 0), "bandit")
    state = give_turn(make_state(m, [a, t]), U1)
    assert has_line_of_sight(state, (0, 0), (4, 0))


def test_range_and_target_errors() -> None:
    m = make_map("0000000000")
    a = spawn(Team.ALLY, (0, 0), "hero_fighter")
    b = spawn(Team.ALLY, (1, 0), "hero_mage")
    t = spawn(Team.ENEMY, (9, 0), "bandit")
    state = give_turn(make_state(m, [a, b, t]), U1)
    with pytest.raises(IllegalActionError, match="目標超出射程：距離 9，射程 1"):
        resolve(state, Attack(unit_id=U1, target_id=U3))
    with pytest.raises(IllegalActionError, match="不能攻擊友方單位"):
        resolve(state, Attack(unit_id=U1, target_id=U2))
    with pytest.raises(IllegalActionError, match="找不到目標"):
        resolve(state, Attack(unit_id=U1, target_id=UnitId("unit_9999")))


# ---------------------------------------------------------------------------
# 近戰高度差（PM 決定，1B）與視線對稱
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("heights", "weapon", "allowed"),
    [
        ("10\n00", "one_handed_sword", True),  # 差 1 層可以
        ("20\n00", "one_handed_sword", False),  # 差 2 層不行
        ("02\n00", "one_handed_sword", False),  # 低打高同樣限制
        ("30\n00", "dagger", False),
        ("20\n00", "bow", True),  # 遠程不受限制
    ],
)
def test_melee_height_difference_limit(heights: str, weapon: str, allowed: bool) -> None:
    m = make_map(heights)
    a = spawn(Team.ALLY, (0, 0), "hero_fighter", weapon=weapon)
    t = spawn(Team.ENEMY, (1, 0), "bandit")
    state = give_turn(make_state(m, [a, t]), U1)
    action = Attack(unit_id=U1, target_id=U2)
    assert (action in legal_actions(state)) is allowed
    if allowed:
        resolve(state, action)
    else:
        with pytest.raises(IllegalActionError, match="高度差過大，無法近戰"):
            resolve(state, action)


def test_reach_weapon_obeys_height_limit() -> None:
    """射程 2 的長柄武器同樣受限制（以修改射程的單手劍模擬）。"""
    m = make_map("200\n000")
    lib = library()
    spear = lib.weapons["one_handed_sword"].model_copy(update={"range": 2})
    a = spawn(Team.ALLY, (0, 0), "hero_fighter")
    a = a.model_copy(update={"weapon": spear})
    t = spawn(Team.ENEMY, (2, 0), "bandit")
    state = give_turn(make_state(m, [a, t]), U1)
    with pytest.raises(IllegalActionError, match="高度差過大"):
        resolve(state, Attack(unit_id=U1, target_id=U2))


@settings(max_examples=60, deadline=None)
@given(
    heights=st.lists(st.integers(0, 3), min_size=36, max_size=36),
    a=st.tuples(st.integers(0, 5), st.integers(0, 5)),
    b=st.tuples(st.integers(0, 5), st.integers(0, 5)),
)
def test_property_line_of_sight_is_symmetric(
    heights: list[int], a: tuple[int, int], b: tuple[int, int]
) -> None:
    rows = "\n".join("".join(str(h) for h in heights[y * 6 : y * 6 + 6]) for y in range(6))
    state = _los_state(rows)
    assert has_line_of_sight(state, a, b) == has_line_of_sight(state, b, a)


def _los_state(rows: str) -> BattleState:
    cached = _LOS_CACHE.get(rows)
    if cached is None:
        lines = rows.split("\n")
        corner = (len(lines[0]) - 1, len(lines) - 1)
        m = make_map(rows, ally=[(0, 0)], enemy=[corner])
        cached = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, corner)])
        _LOS_CACHE[rows] = cached
    return cached


_LOS_CACHE: dict[str, BattleState] = {}


def test_line_of_sight_asymmetric_case_is_now_blocked_both_ways() -> None:
    """Bresenham 兩個方向的格子不同的例子：只有一個方向被擋時，兩邊都看不到。"""
    found = False
    for blocker in [(x, y) for y in range(3) for x in range(5)]:
        rows = ["00000", "00000", "00000"]
        bx, by = blocker
        rows[by] = rows[by][:bx] + "3" + rows[by][bx + 1 :]
        state = _los_state("\n".join(rows))
        a, b = (0, 0), (4, 1)
        one = all(state.tile(*c).height < 1 for c in bresenham(a, b)[1:-1])
        two = all(state.tile(*c).height < 1 for c in bresenham(b, a)[1:-1])
        if one != two:
            found = True
            assert not has_line_of_sight(state, a, b)
            assert not has_line_of_sight(state, b, a)
    assert found
