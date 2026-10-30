"""BAL-8：量測用的兩個選項，預設都等於現行行為。

- ``WeaponDef.backstab_first_only``（B18）：連擊武器的背刺只算第一下；
- ``weapon_ai.far_range``（火槍）：遠距加成武器偏好最佳距離；預設 0 ＝ 不套用。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.test_weapons_3i4 import _duel
from tests.engine.test_weapons_24a2 import U1, armed, dice, foe, kinds, shoot, state_of, weapon
from trpg.content.environment import AiProfile
from trpg.engine.ai.utility import position_value
from trpg.engine.ai.weapon_range import is_close_range, is_far_range
from trpg.engine.events import AttackRolled
from trpg.shared.types import Team


def test_defaults_keep_the_current_behaviour() -> None:
    assert not weapon("dual_dagger").backstab_first_only
    assert all(p.weights.far_range == 0 for p in library().ai_profiles.profiles)


def test_every_strike_backstabs_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=15)
    rolled = kinds(shoot(_duel("west")), AttackRolled)
    assert [r.backstab for r in rolled] == [2, 2]


def test_backstab_first_only_applies_to_the_first_strike_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch, d20=15)
    state = _duel("west", weapon("dual_dagger", backstab_first_only=True))
    rolled = kinds(shoot(state), AttackRolled)
    assert [r.backstab for r in rolled] == [2, 0]


def test_backstab_first_only_does_not_change_frontal_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch, d20=15)
    state = _duel("east", weapon("dual_dagger", backstab_first_only=True))
    assert [r.backstab for r in kinds(shoot(state), AttackRolled)] == [0, 0]


def test_far_range_weapons_are_found_from_the_data() -> None:
    assert is_far_range(weapon("longgun"), 2)
    assert not is_far_range(weapon("shotgun"), 2)  # 近距離武器
    assert not is_far_range(weapon("bow"), 2)  # 沒有距離修正
    assert not is_far_range(weapon("one_handed_sword"), 2)
    assert is_close_range(weapon("shotgun"), 2)
    assert not is_close_range(weapon("longgun"), 2)


def _archer() -> AiProfile:
    return next(p for p in library().ai_profiles.profiles if p.id == "archer")


def test_far_range_weight_prefers_the_long_distance_and_zero_is_inert() -> None:
    p = _archer()
    w0 = p.weights
    w = w0.model_copy(update={"far_range": 40})
    values = {}
    for distance in (1, 2, 3, 4, 5):
        state = state_of([armed(Team.ALLY, (1, 2), weapon("longgun")), foe((1 + distance, 2))])
        values[distance] = (position_value(state, U1, w), position_value(state, U1, w0))
    # 權重 0 ＝ 現行；權重 > 0 時加上 far_range × 距離傷害千分比 ÷ 1000
    for distance, permille in ((1, 500), (2, 1000), (3, 1000), (4, 1250), (5, 1250)):
        assert values[distance][0] - values[distance][1] == 40 * permille // 1000
