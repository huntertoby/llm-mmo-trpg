"""火槍與弩在反應裡的行為（Phase 3-24a2）：藉機攻擊要求近戰武器（``requires_melee_weapon``），所以
遠程的火槍與弩不會藉機攻擊，也就不會因此用掉子彈或吃貼臉懲罰。"""

from __future__ import annotations

import pytest

from tests.engine.test_weapons_24a2 import U1, U2, armed, dice, foe, kinds, state_of, weapon
from trpg.engine import Move, resolve
from trpg.engine.events import AttackRolled, ReactionTriggered
from trpg.shared.types import Pos, Team


@pytest.mark.parametrize("weapon_id", ["longgun", "crossbow"])
def test_ranged_weapons_make_no_opportunity_attack_and_keep_their_ammo(
    weapon_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    gunner = armed(
        Team.ALLY,
        (3, 2),
        weapon(weapon_id),
        reactions=[{"reaction": "opportunity_attack", "when": {"event": "enemy_leaves_adjacent"}}],
    )
    state = state_of([gunner, foe((2, 2))], active=U2)
    ammo = state.units[U1].ammo
    state.units[U2].move_points = 3
    path = (Pos(x=2, y=2), Pos(x=1, y=2))
    result = resolve(state, Move(unit_id=U2, path=path))
    assert not kinds(result.events, ReactionTriggered)
    assert not [e for e in kinds(result.events, AttackRolled) if e.attacker_id == U1]
    assert result.state.units[U1].ammo == ammo
