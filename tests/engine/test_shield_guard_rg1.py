"""RG-1：盾兵掩護（#162，``docs/design/09-世界與敘事.md`` 9.6.6「盾兵」；
規格 ``docs/phases/PhaseRG計畫.md`` 1.2）。

每列一條規則句、實際跑引擎（內建的持盾弟子）：盾兵站在遠程同伴朝向攻擊者的那一側時，遠程攻擊命中
−``shield_guard_hit_penalty``；繞到側面、把盾兵推開、近戰、高處都擋不到；不和掩護物疊加；不保護
近戰同伴與盾兵自己。AI：盾兵的位置價值偏好擋在遠程同伴前面、遠程同伴偏好站在盾兵後面。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from trpg.engine import Attack, BattleState, preview, resolve
from trpg.engine.ai.utility.position import _covered_from, _screened_allies
from trpg.engine.events import AttackRolled
from trpg.engine.rules.combat import half_cover
from trpg.narrative.events import describe_event
from trpg.shared.types import Pos, Team, UnitId

SHOOTER, WARD, GUARD = (UnitId(f"unit_000{i}") for i in range(1, 4))
ROW = "0" * 10
PENALTY = library().ruleset.core.shield_guard_hit_penalty


def scene(
    shooter: tuple[int, int] = (1, 4),
    *,
    ward: str = "sect_crane_archer",
    guard_at: tuple[int, int] = (5, 4),
    weapon: str = "bow",
    heights: Sequence[str] | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
) -> BattleState:
    """SHOOTER（我方）在 ``shooter``；WARD（敵方，預設雲鶴使）在 (6, 4)；GUARD（敵方持盾弟子）在
    ``guard_at``。"""
    rows = "\n".join(heights or [ROW] * 9)
    m = make_map(rows, ally=[shooter], enemy=[(6, 4), guard_at], objects=objects)
    spawns = [
        spawn(Team.ALLY, shooter, template("hero_archer", reactions=[]), weapon, skills=()),
        spawn(Team.ENEMY, (6, 4), template(ward, reactions=[], max_hp=300)),
        spawn(Team.ENEMY, guard_at, template("sect_shield_disciple", reactions=[], max_hp=300)),
    ]
    return give_turn(make_state(m, spawns), SHOOTER)


def cover_of(state: BattleState, target: UnitId = WARD) -> tuple[int, UnitId | None]:
    found = half_cover(state, state.units[SHOOTER], state.units[target])
    return (0, None) if found is None else (found.penalty, found.unit_id)


def test_a_shield_guard_in_front_covers_the_ranged_ally() -> None:
    state = scene()
    assert cover_of(state) == (PENALTY, GUARD)
    result = resolve(state, Attack(unit_id=SHOOTER, target_id=WARD))
    (roll,) = [e for e in result.events if isinstance(e, AttackRolled)]
    assert roll.cover == -PENALTY and roll.cover_unit_id == GUARD and roll.cover_object_id is None
    text = describe_event(roll, result.state) or ""
    assert "盾兵掩護" in text and "持盾弟子的盾擋住" in text


def test_the_preview_names_the_shield_guard() -> None:
    p = preview(scene(), Attack(unit_id=SHOOTER, target_id=WARD))
    assert any("盾兵掩護" in note and "持盾弟子" in note for note in p.notes)


def test_shooting_from_the_side_goes_around_the_shield() -> None:
    assert cover_of(scene(shooter=(6, 0))) == (0, None)


def test_pushing_the_guard_away_removes_the_cover() -> None:
    state = scene()
    state.units[GUARD].pos = Pos(x=5, y=6)  # 被推開、撞開
    assert cover_of(state) == (0, None)


@pytest.mark.parametrize("weapon", ["spear", "one_handed_sword"])
def test_melee_attacks_ignore_the_shield(weapon: str) -> None:
    state = scene(shooter=(4, 4), guard_at=(6, 5), weapon=weapon)
    state.units[GUARD].pos = Pos(x=5, y=4)  # 擋在 SHOOTER 與 WARD 之間（長柄矛打得到 2 格）
    assert cover_of(state) == (0, None)


def test_shooting_from_high_ground_ignores_the_shield() -> None:
    rows = ["0000000000"] * 4 + ["2200000000"] + ["0000000000"] * 4
    assert cover_of(scene(heights=rows)) == (0, None)


def test_the_shield_does_not_stack_with_cover_objects() -> None:
    state = scene(guard_at=(6, 5), objects=[(5, 4, "crate")])
    if library().ruleset.object_def("crate").tags.count("half_cover") == 0:
        pytest.skip("crate 不是半掩護物件")
    state.units[GUARD].pos = Pos(x=6, y=3)
    found = half_cover(state, state.units[SHOOTER], state.units[WARD])
    assert found is not None and found.unit_id is None and found.object_id is not None


def test_melee_allies_and_the_guard_itself_are_not_protected() -> None:
    assert cover_of(scene(ward="sect_swordsman")) == (0, None)
    state = scene()
    state.units[WARD].pos = Pos(x=4, y=4)  # 雲鶴使站到盾兵前面：盾兵在它背後，不擋
    assert cover_of(state, GUARD) == (0, None)


def test_zero_penalty_turns_the_shield_off() -> None:
    state = scene()
    core = state.ruleset.core.model_copy(update={"shield_guard_hit_penalty": 0})
    state.ruleset = state.ruleset.model_copy(update={"core": core})
    assert cover_of(state) == (0, None)


def test_the_two_shield_troops_carry_the_tag_and_old_shieldbearers_do_not() -> None:
    lib = library()
    assert "shield_guard" in lib.unit("sect_shield_disciple").tags
    assert "shield_guard" in lib.unit("molten_shell_trooper").tags
    assert "shield_guard" not in lib.unit("bandit_shieldbearer").tags


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_the_guard_values_standing_in_front_of_the_ranged_ally() -> None:
    state = scene(guard_at=(6, 7))
    guard = state.units[GUARD]
    enemies = [state.units[SHOOTER]]
    assert _screened_allies(state, guard, (5, 4), enemies) == 1  # 擋在弓手與雲鶴使之間
    assert _screened_allies(state, guard, (7, 4), enemies) == 0  # 站在雲鶴使背後
    assert _screened_allies(state, guard, (6, 7), enemies) == 0  # 不相鄰
    profile = next(p for p in library().ai_profiles.profiles if p.id == "guard")
    assert profile.weights.screen > 0


def test_the_ranged_ally_values_standing_behind_a_guard() -> None:
    state = scene()
    ward = state.units[WARD]
    enemies = [state.units[SHOOTER]]
    assert _covered_from(state, ward, (6, 4), enemies) == 1
    assert _covered_from(state, ward, (6, 2), enemies) == 0


@settings(max_examples=25, deadline=None)
@given(x=st.integers(min_value=0, max_value=9), y=st.integers(min_value=0, max_value=8))
def test_without_shield_troops_cover_matches_the_object_rule(x: int, y: int) -> None:
    """性質：場上沒有盾兵（盾兵換成一般盜賊）時，任何位置射擊的掩護結果都只來自掩護物件。"""
    if (x, y) in {(6, 4), (5, 4)}:
        return
    state = scene()
    state.units[GUARD].tags = tuple(t for t in state.units[GUARD].tags if t != "shield_guard")
    state.units[SHOOTER].pos = Pos(x=x, y=y)
    found = half_cover(state, state.units[SHOOTER], state.units[WARD])
    assert found is None or found.unit_id is None
