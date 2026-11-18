"""疾病擴散（SK-2，#166，06 6.31、6.38 第 5 點）：帶燃燒、流血、中毒的目標倒下時，狀態以剩餘回合
傳給 1 格內 1 個敵人；每次倒下最多傳 1 次。"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, U3, U4, battle, cast, hit_with, of
from trpg.engine import BattleState, state_to_json
from trpg.engine.effects import ApplyStatusEffect, DamageEffect, run_effects
from trpg.engine.events import ContagionMarked, DiseaseSpread, StatusApplied
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary
from trpg.shared.rng import Rng
from trpg.shared.types import Element

SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
CONTAGION: dict[str, Any] = {"type": "contagion"}


def plagued(state: BattleState, uid: str, *statuses: tuple[str, int]) -> None:
    unit = state.units[uid]  # type: ignore[index]
    unit.statuses = sorted(
        [*unit.statuses, *(StatusInstance(s, r, U1, contagious=True) for s, r in statuses)],
        key=lambda s: s.status_id,
    )


def kill(state: BattleState, uid: str) -> list[Any]:
    """讓 ``uid`` 受到致命傷害並倒下（不帶元素修正），回傳事件。"""
    state.units[uid].hp = 1  # type: ignore[index]
    result = run_effects(
        state,
        [
            DamageEffect(
                target_id=uid,  # type: ignore[arg-type]
                source_id=U1,
                cause="attack",
                element=Element.PHYSICAL,
                flat=50,
                apply_element_mod=False,
            )
        ],
    )
    return [result, *result.events]


def test_the_primitive_marks_existing_dots_only() -> None:
    burn = {"type": "apply_status", "status": "burning"}
    skill = make_skill(SID, SINGLE5, [burn, CONTAGION])
    state = hit_with(battle(skill, [(5, 3)]), [(4, 2)])
    result = cast(state, target_id=U2)
    (marked,) = of(result, ContagionMarked)
    assert (marked.unit_id, marked.target_id, marked.status_ids) == (U1, U2, ("burning",))
    target = result.state.units[U2]
    assert [(s.status_id, s.contagious) for s in target.statuses] == [("burning", True)]


def test_nothing_to_mark_is_silent() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    result = cast(hit_with(battle(skill, [(5, 3)])), target_id=U2)
    assert of(result, ContagionMarked) == []
    assert result.state.units[U2].statuses == []


def test_downed_carrier_spreads_with_remaining_rounds_to_the_one_adjacent_ally() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3), (5, 4), (5, 6)])  # U2 旁邊只有 U3；U4 兩格外
    plagued(state, U2, ("burning", 2), ("poison", 1))
    result, *events = kill(state, U2)
    (spread,) = [e for e in events if isinstance(e, DiseaseSpread)]
    assert (spread.from_id, spread.to_id, spread.status_ids) == (U2, U3, ("burning", "poison"))
    got = {s.status_id: s for s in result.state.units[U3].statuses}
    assert (got["burning"].remaining, got["poison"].remaining) == (2, 1)
    assert got["burning"].contagious and got["poison"].contagious  # 傳過去照樣會擴散
    assert not result.state.units[U4].statuses
    applied = [e for e in events if isinstance(e, StatusApplied)]
    assert {e.target_id for e in applied} == {U3}


def test_not_marked_or_no_neighbour_or_caster_side_does_not_spread() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3), (5, 4)], allies=[(4, 3)])
    unit = state.units[U3]  # 友方 U2 在 (4, 3)：施放者陣營不算；U3 是 (5, 3) 的敵人
    unit.statuses = [StatusInstance("burning", 2, U1)]  # 沒標記
    _, *events = kill(state, U3)
    assert not [e for e in events if isinstance(e, DiseaseSpread)]
    lonely = battle(skill, [(5, 3), (0, 6)])
    plagued(lonely, U2, ("bleed", 2))
    _, *events = kill(lonely, U2)
    assert not [e for e in events if isinstance(e, DiseaseSpread)]


def test_spreads_at_most_once_per_down_and_only_listed_statuses() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3), (5, 2), (5, 4), (6, 3)])
    plagued(state, U2, ("burning", 3), ("slow", 2))
    result, *events = kill(state, U2)
    spreads = [e for e in events if isinstance(e, DiseaseSpread)]
    assert len(spreads) == 1 and spreads[0].status_ids == ("burning",)
    infected = [u for u in result.state.units.values() if u.has_status("burning") and u.alive]
    assert [u.id for u in infected] == [spreads[0].to_id]


@settings(max_examples=25, deadline=None)
@given(st.integers(min_value=0, max_value=2**31))
def test_choice_among_several_is_seeded_and_deterministic(seed: int) -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3), (5, 2), (5, 4), (6, 3)])
    state.rng_state = Rng(seed).get_state()
    plagued(state, U2, ("burning", 3))
    first, *a = kill(state, U2)
    second, *b = kill(state, U2)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]
    (spread,) = [e for e in a if isinstance(e, DiseaseSpread)]
    assert spread.to_id in (U3, U4, "unit_0005")


def test_a_single_candidate_draws_no_random_number() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3), (5, 4)])
    plagued(state, U2, ("burning", 2))
    before = state.rng_state
    result, *_ = kill(state, U2)
    plain = battle(skill, [(5, 3), (5, 4)])
    plain_result, *_ = kill(plain, U2)
    assert before == plain.rng_state
    assert result.state.rng_state == plain_result.state.rng_state


def test_reapplying_keeps_the_mark_and_json_is_unchanged_when_unmarked() -> None:
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    state = battle(skill, [(5, 3)])
    plagued(state, U2, ("burning", 1))
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="burning", duration=3)])
    (burn,) = result.state.units[U2].statuses
    assert burn.contagious and burn.remaining == 3
    plain = battle(skill, [(5, 3)])
    plain.units[U2].statuses = [StatusInstance("burning", 2, U1)]
    assert "contagious" not in state_to_json(plain)


def test_texts() -> None:
    lib = library()
    skill = make_skill(SID, SINGLE5, [CONTAGION])
    card = effect_summary(lib, skill, skill.effects[0])
    assert "燃燒" in card and "擴散" in card
    state = battle(skill, [(5, 3), (5, 4)])
    plagued(state, U2, ("burning", 2))
    result, *events = kill(state, U2)
    (spread,) = [e for e in events if isinstance(e, DiseaseSpread)]
    assert "擴散" in (describe_event(spread, result.state) or "")


@pytest.mark.parametrize("affects", ["allies", "self"])
def test_affects_rules(affects: str) -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    skill = make_skill(SID, SINGLE5, [{"type": "contagion", "affects": affects}])
    assert validate_skill(skill, library())
