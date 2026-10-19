"""Phase 2G-2：示範技能的行為（每個技能在戰鬥中產生預期事件）。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always, attack, scene, triggered
from tests.engine.test_reaction_skills import duel
from trpg.engine import Attack, BattleState, EndTurn, Move, ResolveResult, UseSkill, resolve
from trpg.engine.events import (
    DamageDealt,
    Healed,
    ObjectDestroyed,
    ReactionTriggered,
    ShieldGained,
    StatusApplied,
    TerrainChanged,
)
from trpg.shared.types import Pos, Team


def _cast(state: BattleState, skill_id: str, **fields: object) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))  # type: ignore[arg-type]


def _skill_battle(
    skill_id: str,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    *,
    base: str = "hero_mage",
    heights: str = FLAT7,
    objects: tuple[tuple[int, int, str], ...] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """施放者 U1 在 (3, 3)，裝備內容資料裡的真實技能 ``skill_id``。"""
    m = make_map(heights, ally=[(3, 3)], enemy=list(foes), objects=objects, surfaces=surfaces)
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill_id], base=base))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


# --- 被動：每個觸發時機一個 ------------------------------------------------


def test_crippling_crit_weakens_the_target_on_a_critical_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = scene(["skill_crippling_crit"])
    always(monkeypatch, d20=19)
    assert not triggered(attack(state).events)
    state.units[U2].attributes["con"] = 1  # type: ignore[index]
    always(monkeypatch, d20=20)
    result = attack(state)
    assert [e.trigger for e in triggered(result.events)] == ["on_crit"]
    assert [(a.target_id, a.status_id) for a in of(result, StatusApplied)] == [(U2, "weaken")]


def test_lucky_break_shields_the_holder_on_a_natural_20(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene(["skill_lucky_break"])
    always(monkeypatch, d20=20)
    result = attack(state)
    assert [e.trigger for e in triggered(result.events)] == ["on_natural_20"]
    assert [g.unit_id for g in of(result, ShieldGained)] == [U1]


def test_bloodlust_heals_the_holder_when_it_downs_a_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(["skill_bloodlust"], foe_hp=1)
    state.units[U1].hp = 10
    result = attack(state)
    assert [e.trigger for e in triggered(result.events)] == ["on_kill"]
    assert [h.target_id for h in of(result, Healed)] == [U1]


def test_steady_breath_heals_at_the_end_of_the_holders_turn() -> None:
    state = scene(["skill_steady_breath"])
    state.units[U1].hp = 10
    result = resolve(state, EndTurn(unit_id=U1))
    assert [e.trigger for e in triggered(result.events)] == ["on_turn_end"]
    assert [h.target_id for h in of(result, Healed)] == [U1]


def test_fleet_foot_hastes_the_holder_after_a_move() -> None:
    state = scene(["skill_fleet_foot"], foe_xy=(6, 6))
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3), Pos(x=1, y=3))))
    assert [e.trigger for e in triggered(result.events)] == ["on_move"]
    assert [(a.target_id, a.status_id) for a in of(result, StatusApplied)] == [(U1, "hasted")]


def test_twin_strike_fires_on_every_second_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(["skill_twin_strike"])
    first = attack(state)
    assert not triggered(first.events)
    second = attack(give_turn(first.state, U1))
    assert [e.trigger for e in triggered(second.events)] == ["every_n_hits"]
    assert len(of(second, DamageDealt)) == 2  # 普攻 ＋ 閃電


# --- 連段 ------------------------------------------------------------------


def test_conductive_strike_adds_a_second_hit_only_on_water() -> None:
    dry = _cast(
        _skill_battle("skill_conductive_strike", [(4, 3)]),
        "skill_conductive_strike",
        target_id="unit_0002",
    )
    wet_state = _skill_battle("skill_conductive_strike", [(4, 3)], surfaces=((4, 3, "water"),))
    wet = _cast(wet_state, "skill_conductive_strike", target_id="unit_0002")
    assert len(of(dry, DamageDealt)) == 1
    assert len(of(wet, DamageDealt)) == 2


# --- 反應技 ----------------------------------------------------------------


def test_reflex_ward_shields_the_owner_when_hit_by_a_ranged_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = duel(["skill_reflex_ward"], foe="bandit_archer", foe_xy=(6, 3))
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.unit_id, trig.reaction) == (U1, "skill_reflex_ward")
    assert [g.unit_id for g in of(result, ShieldGained)] == [U1]


def test_parting_slash_strikes_an_enemy_that_walks_away(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = duel(["skill_parting_slash"])
    hp = state.units[U2].hp
    result = resolve(state, Move(unit_id=U2, path=(Pos(x=4, y=3), Pos(x=5, y=3), Pos(x=6, y=3))))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.reaction, trig.trigger_unit_id) == ("skill_parting_slash", U2)
    assert result.state.units[U2].hp < hp


# --- 地形 ------------------------------------------------------------------


def test_raise_perch_raises_the_target_tiles() -> None:
    state = _skill_battle("skill_raise_perch", base="hero_archer")
    result = _cast(state, "skill_raise_perch", target_pos=Pos(x=2, y=2))
    changes = of(result, TerrainChanged)
    assert changes and all(c.height_after == c.height_before + 1 for c in changes)
    assert result.state.tile(2, 2).height == 1


def test_sinkhole_lowers_raised_ground() -> None:
    heights = "\n".join(["0000000"] * 2 + ["0022000"] + ["0000000"] * 4)
    state = _skill_battle("skill_sinkhole", heights=heights)
    result = _cast(state, "skill_sinkhole", target_pos=Pos(x=2, y=2))
    assert result.state.tile(2, 2).height == 1
    assert all(c.height_after == c.height_before - 1 for c in of(result, TerrainChanged))


def test_shatter_blast_damages_units_and_destroys_objects() -> None:
    state = _skill_battle(
        "skill_shatter_blast", [(2, 3)], objects=((3, 2, "crate"),), heights=FLAT7
    )
    result = _cast(state, "skill_shatter_blast", target_pos=Pos(x=2, y=2))
    assert of(result, ObjectDestroyed)
    assert result.state.object_at(3, 2) is None
    assert of(result, DamageDealt)
