"""AI 會打有護盾的敵人（Phase 6F-3；12B 對照 #7「盜賊每回合都只守護」）。

大世界的預設隊伍有補師（回春）一直替大家上盾；盜賊的匕首全被護盾吸收時，傷害收益（只算扣到 HP
的部分）是 0，守護的 3 分就贏了，盜賊每回合只守護，戰鬥拖到 11 輪。6F-3 起打掉敵人的護盾照
``shield`` 權重給分（和替自己人加盾等價）。表格測試實際跑效用 AI：相鄰的敵人有沒有護盾，
盜賊都選攻擊。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from trpg.engine import Attack, BattleState, Defend
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId

LIB = library()
SEVEN = "\n".join(["0000000"] * 7)
HERO, BANDIT = UnitId("unit_0001"), UnitId("unit_0002")


def _state(shield: int | None) -> BattleState:
    m = make_map(SEVEN, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", max_hp=60)),
        spawn(Team.ENEMY, (4, 3), no_reactions("bandit")),
    ]
    state = give_turn(make_state(m, spawns), BANDIT)
    if shield is not None:
        state.units[HERO].statuses.append(
            StatusInstance(status_id="shielded", remaining=2, amount=shield)
        )
    return state


@pytest.mark.parametrize("shield", [None, 8, 30])
def test_bandit_attacks_shielded_neighbor(shield: int | None) -> None:
    state = _state(shield)
    action = UtilityAI(LIB.ai_profiles)(state)
    assert not isinstance(action, Defend)
    assert isinstance(action, Attack)
    assert action.target_id == HERO


def test_shield_break_scores_like_a_shield() -> None:
    """全被吸收的攻擊分數 > 0（之前是 0，輸給守護）；沒有護盾時分數照舊不受影響。"""
    ai = UtilityAI(LIB.ai_profiles)
    ranked = ai.rank(_state(30))
    shielded = {type(s.action): s.score for s in ranked if isinstance(s.action, Attack | Defend)}
    assert shielded[Attack] > shielded[Defend]
