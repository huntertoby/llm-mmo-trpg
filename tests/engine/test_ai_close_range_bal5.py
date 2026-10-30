"""BAL-5 B19：近距離武器（霰彈槍）的站位與單發火器開火的位置價值。

- 最佳距離由武器資料（``range_mod`` 的傷害千分比）推導，不寫死武器 ID；
- 近距離武器的位置價值偏好 1～2 格（``close_range``），保持距離不再把它推到 3 格外；
- 開火讓彈匣變空不再讓位置價值像「打不到任何敵人」（否則單發火器的普攻分數是負的）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.test_weapons_24a2 import U1, U2, armed, dice, foe, state_of, weapon
from trpg.content.environment import AiProfile
from trpg.engine import Attack, resolve
from trpg.engine.ai.utility import UtilityAI, position_value, score_action
from trpg.engine.ai.weapon_range import best_distance, damage_permille_at, is_close_range
from trpg.shared.types import Pos, Team


def _archer() -> AiProfile:
    return next(p for p in library().ai_profiles.profiles if p.id == "archer")


def test_best_distance_comes_from_the_weapon_data() -> None:
    sg = weapon("shotgun")
    assert best_distance(sg) == 1
    assert [damage_permille_at(sg, d) for d in (1, 2, 3, 4)] == [1000, 750, 500, 250]
    assert is_close_range(sg, 2)
    assert best_distance(weapon("longgun")) == 4  # 遠距加成：最佳距離在 4 格以上
    assert not is_close_range(weapon("longgun"), 2)
    assert best_distance(weapon("bow")) is None
    assert not is_close_range(weapon("bow"), 2)
    assert not is_close_range(weapon("one_handed_sword"), 2)
    # 改資料行為跟著變：把霰彈槍改成沒有遞減，就不是近距離武器
    flat = weapon("shotgun", range_mod=[])
    assert best_distance(flat) is None
    assert not is_close_range(flat, 2)


def test_every_profile_gets_the_shared_close_range_weight() -> None:
    for p in library().ai_profiles.profiles:
        if p.id != "idle":
            assert p.weights.close_range > 0, p.id


@pytest.mark.parametrize("gun", ["shotgun"])
def test_close_range_gun_prefers_one_or_two_tiles_over_three(gun: str) -> None:
    w = _archer().weights
    values = {}
    for distance in (1, 2, 3, 4):
        state = state_of([armed(Team.ALLY, (1, 2), weapon(gun)), foe((1 + distance, 2))])
        values[distance] = position_value(state, U1, w)
    assert values[1] > values[3]
    assert values[2] > values[3] > values[4]


def test_a_bow_still_keeps_its_distance() -> None:
    w = _archer().weights
    near = state_of([armed(Team.ALLY, (1, 2), weapon("bow")), foe((3, 2))])
    far = state_of([armed(Team.ALLY, (1, 2), weapon("bow")), foe((5, 2))])
    assert position_value(far, U1, w) > position_value(near, U1, w)


def test_close_range_weight_zero_restores_the_old_position_value() -> None:
    p = _archer()
    w0 = p.weights.model_copy(update={"close_range": 0})
    state = state_of([armed(Team.ALLY, (1, 2), weapon("shotgun")), foe((3, 2))])
    assert position_value(state, U1, p.weights) - position_value(state, U1, w0) == (
        p.weights.close_range * 750 // 1000
    )


def test_firing_the_last_round_does_not_lower_the_position_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    w = _archer().weights
    state = state_of([armed(Team.ALLY, (1, 2), weapon("shotgun")), foe((2, 2), max_hp=200)])
    before = position_value(state, U1, w)
    empty = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert empty.units[U1].ammo == 0
    assert position_value(empty, U1, w) == before


def test_utility_ai_fires_the_shotgun_point_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = state_of([armed(Team.ALLY, (1, 2), weapon("shotgun")), foe((2, 2), max_hp=200)])
    scored = score_action(state, Attack(unit_id=U1, target_id=U2), _archer())
    assert scored.score > 0
    assert UtilityAI(library().ai_profiles)(state) == Attack(unit_id=U1, target_id=U2)


def test_utility_ai_walks_a_shotgun_in_closer(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = state_of([armed(Team.ALLY, (1, 2), weapon("shotgun")), foe((5, 2), max_hp=200)])
    action = UtilityAI(library().ai_profiles)(state)
    path = getattr(action, "path", None)
    assert path is not None, action
    dest = path[-1]
    assert abs(dest.x - 5) + abs(dest.y - 2) <= 2
    assert Pos(x=1, y=2) != dest
