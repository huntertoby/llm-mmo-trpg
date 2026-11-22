"""E3：地形規則「表面傷害免疫」（``surface_damage_immunity``，08 8.29 E3）：只擋站在表面上的回合開始
傷害（``cause="surface"``），其他來源照常；AI 的 ``_harmful`` 看這條免疫（E2 裁定 4）。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.race_helpers import U1, end_turn, of, race_state
from tests.engine.test_ai_immunity_e2 import switch
from tests.engine.test_unit_rules_e2 import terrain, wear
from trpg.content.environment import AiProfile
from trpg.engine import BattleState
from trpg.engine.ai.utility.position import _harmful, position_value
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import ApplyStatusEffect
from trpg.engine.events import DamageDealt
from trpg.engine.rules.race import surface_damage_immune
from trpg.shared.types import Surface

POISON_PROOF = terrain(
    "affix_t_poison_proof", "毒表面不會傷害你", rule="surface_damage_immunity", surfaces=["poison"]
)


def _on_poison(*, immune: bool) -> BattleState:
    state = race_state(None, me=(3, 3), foes=((6, 6),), surfaces=[(3, 3, "poison")])
    if immune:
        wear(state, {"feet": [POISON_PROOF]})
    return state


def _next_own_turn(state: BattleState) -> list[DamageDealt]:
    """U1 結束回合，直到 U1 的下一個回合開始；回傳這段期間 U1 受到的傷害。"""
    hits: list[DamageDealt] = []
    result = end_turn(state)
    hits += [e for e in of(result, DamageDealt) if e.target_id == U1]
    while result.state.active_unit != U1:
        result = end_turn(result.state)
        hits += [e for e in of(result, DamageDealt) if e.target_id == U1]
    return hits


def test_query() -> None:
    plain, proof = _on_poison(immune=False), _on_poison(immune=True)
    assert not surface_damage_immune(plain.ruleset, plain.units[U1], Surface.POISON)
    assert surface_damage_immune(proof.ruleset, proof.units[U1], Surface.POISON)
    assert not surface_damage_immune(proof.ruleset, proof.units[U1], Surface.HOLY)


def test_blocks_turn_start_surface_damage() -> None:
    plain = _next_own_turn(_on_poison(immune=False))
    assert [e.cause for e in plain] == ["surface"]
    assert _next_own_turn(_on_poison(immune=True)) == []


def test_other_sources_still_hurt() -> None:
    state = _on_poison(immune=True)
    state = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id="poison")]).state
    hits = _next_own_turn(state)
    assert hits and all(e.cause != "surface" for e in hits)


def _brute() -> AiProfile:
    return next(p for p in library().ai_profiles.profiles if p.id == "brute")


def test_ai_harmful_sees_the_immunity() -> None:
    proof = _on_poison(immune=True)
    assert not _harmful(proof, (3, 3), proof.units[U1])
    assert _harmful(proof, (3, 3))  # 沒有指定單位：照舊
    plain = _on_poison(immune=False)
    assert _harmful(plain, (3, 3), plain.units[U1])  # 看不見這條免疫的單位照樣避開
    switch(proof, on=False)
    assert _harmful(proof, (3, 3), proof.units[U1])


def test_ai_position_value_does_not_count_its_own_tile_as_a_hazard() -> None:
    w = _brute().weights
    on = _on_poison(immune=True)
    off = switch(_on_poison(immune=True), on=False)
    assert position_value(on, U1, w) - position_value(off, U1, w) == w.hazard
