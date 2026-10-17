"""預覽（6.1-12、6.2-5）：命中率與窮舉相符；「最小傷害／確定連鎖」與實際結算一致。"""

from __future__ import annotations

from fractions import Fraction
from itertools import product

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.engine import Attack, Move, Shove, preview, resolve, state_to_json
from trpg.engine.effects import ApplyStatusEffect, run_effects
from trpg.engine.events import DamageDealt
from trpg.engine.preview import Outcome, dice_distribution, outcomes
from trpg.engine.rules.combat import is_hit
from trpg.shared.types import ObjectId, Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _exhaustive(bonus: int, mode: str = "none", crit_from: int = 21) -> tuple[Fraction, Fraction]:
    rolls = (
        [(a,) for a in range(1, 21)] if mode == "none" else list(product(range(1, 21), repeat=2))
    )
    hits = crits = 0
    for r in rolls:
        n = r[0] if mode == "none" else (max(r) if mode == "advantage" else min(r))
        h = is_hit(n, n + bonus, 11)
        hits += h
        crits += h and n >= crit_from
    return Fraction(hits, len(rolls)), Fraction(crits, len(rolls))


def test_hit_chance_matches_exhaustive_enumeration() -> None:
    m = make_map("000\n000")
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0), no_reactions())]
        ),
        U1,
    )
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert (p.hit_chance, p.crit_chance) == _exhaustive(0 + 2, crit_from=20)
    assert p.hit_chance == Fraction(3, 5)
    prone = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="prone")]).state
    p2 = preview(prone, Attack(unit_id=U1, target_id=U2))
    assert (p2.hit_chance, p2.crit_chance) == _exhaustive(2, "advantage", 20)
    assert p2.hit_chance == 1 - Fraction(2, 5) ** 2


def test_expected_damage_matches_brute_force() -> None:
    m = make_map("000")
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "bandit"),
                spawn(Team.ENEMY, (1, 0), no_reactions(max_hp=99)),
            ],
        ),
        U1,
    )
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert p.damage is not None
    hit, crit = _exhaustive(-1 + 2, crit_from=19)  # 攻擊 14 vs 防禦 16 → 修正 −1；匕首 19–20 暴擊
    assert (p.hit_chance, p.crit_chance) == (hit, crit)

    def amount(s: int) -> int:
        return max((s * 1000 + 14 * 300) // 1000, 1)  # 敏捷 14 × 0.3

    normal = Fraction(sum(amount(s) * n for s, n in dice_distribution(1, 4).items()), 4)
    doubled = Fraction(sum(amount(s) * n for s, n in dice_distribution(2, 4).items()), 16)
    assert p.damage.expected == (hit - crit) * normal + crit * doubled
    assert (p.damage.minimum, p.damage.maximum) == (amount(1), amount(8))


def test_preview_is_pure() -> None:
    m = make_map("000")
    state = give_turn(make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (1, 0))]), U1)
    before = state_to_json(state)
    preview(state, Attack(unit_id=U1, target_id=U2))
    assert state_to_json(state) == before


def test_min_damage_and_certain_chain_match_actual_resolution() -> None:
    """法師以火焰攻擊站在油上的盜賊：最小傷害與「確定連鎖」（油著火）與實際結算一致。"""
    m = make_map("00000", surfaces=[(3, 0, "oil")], enemy=[(3, 0)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_mage"),
                spawn(Team.ENEMY, (3, 0), no_reactions(max_hp=99)),
            ],
        ),
        U1,
    )
    action = Attack(unit_id=U1, target_id=U2)
    p = preview(state, action)
    assert Outcome("surface", pos=(3, 0), detail="fire") in p.certain
    actual = resolve(with_rolls(state, [(20, 15), (6, 1)]), action)  # 命中、不暴擊、傷害骰最小
    damage = next(e for e in actual.events if isinstance(e, DamageDealt))
    assert p.damage is not None and damage.amount == p.damage.minimum
    assert outcomes(list(actual.events)) == list(p.certain)
    assert state_to_json(actual.state).replace(" ", "") != ""  # 實際狀態正常
    assert (3, 0) in p.affected_tiles and U2 in p.affected_units


def test_certain_explosion_chain_matches_actual() -> None:
    m = make_map(
        "00000\n00000", objects=[(3, 0, "oil_barrel")], surfaces=[(4, 0, "oil")], enemy=[(4, 1)]
    )
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_mage"),
                spawn(Team.ENEMY, (4, 1), no_reactions(max_hp=99)),
            ],
        ),
        U1,
    )
    action = Attack(unit_id=U1, target_object_id=ObjectId("obj_0001"))
    p = preview(state, action)
    assert p.hit_chance == 1 and p.crit_chance == 0
    kinds = {o.kind for o in p.certain}
    assert {"object_exploded", "object_destroyed", "damaged", "surface"} <= kinds
    actual = resolve(with_rolls(state, [(6, 1), (6, 1), (6, 1)]), action)
    assert outcomes(list(actual.events)) == list(p.certain)
    blast_min = [e for e in p.min_events if isinstance(e, DamageDealt)]
    blast = [e for e in actual.events if isinstance(e, DamageDealt)]
    assert [e.amount for e in blast] == [e.amount for e in blast_min]


def test_possible_chain_includes_kill_on_max_damage() -> None:
    m = make_map("000")
    victim = no_reactions("bandit", max_hp=10)
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0), victim)]
        ),
        U1,
    )
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert Outcome("downed", unit_id=U2) in p.possible
    assert Outcome("downed", unit_id=U2) not in p.certain


def test_preview_move_shows_opportunity_attack() -> None:
    m = make_map("0000\n0000", enemy=[(1, 0)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), template("hero_fighter")),
                spawn(Team.ENEMY, (1, 0), no_reactions(max_hp=99)),
            ],
        ),
        U2,
    )
    p = preview(state, Move(unit_id=U2, path=(P(1, 0), P(2, 0), P(3, 0))))
    assert p.hit_chance is None
    assert Outcome("reaction", unit_id=U1, detail="opportunity_attack") in p.certain
    assert Outcome("damaged", unit_id=U2, detail="attack") in p.possible  # 可能命中


def test_shove_preview_success_chance() -> None:
    m = make_map("000", "..x", enemy=[(1, 0)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0))]), U1
    )
    p = preview(state, Shove(unit_id=U1, target_id=U2))
    # 力量 16 vs 12：比例 1.33 → 修正 round(4 × log2(1.33)) = 2；+熟練 2
    assert p.hit_chance == _exhaustive(4)[0]
    assert Outcome("downed", unit_id=U2) in p.certain  # 若成功：推入深淵必死
