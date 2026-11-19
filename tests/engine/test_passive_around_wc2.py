"""WC-2 第 3 項：被動的「自身周圍」小範圍（#167，06 6.9）在戰鬥裡作用在持有者周圍一圈。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.events import DamageDealt, SkillTriggered
from trpg.shared.rng import Rng
from trpg.shared.types import Team


def _around(radius: int = 1) -> SkillDef:
    data: dict[str, Any] = {
        "id": "skill_t_around",
        "name_zh": "環身火",
        "tier": 1,
        "rarity": "epic",
        "kind": "passive",
        "skeleton": "passive",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": "int",
        "shape": {"type": "ring", "radius": radius},
        "effects": [{"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"}],
        "condition": None,
        "trigger": {"event": "on_damaged", "target": "self", "max_per_round": 1},
        "cost": {"mana": 0},
    }
    return SkillDef.model_validate(data)


def _scene(skill: SkillDef) -> BattleState:
    """U1（我方，持有被動）在 (3, 3)；U2 敵人相鄰 (4, 3)；U3 敵人在兩格外 (5, 3)。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (5, 3)])
    owner = caster_template([skill], base="hero_fighter", max_hp=999)
    foe = no_reactions("bandit", max_mana=99, max_hp=999)
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), owner),
            spawn(Team.ENEMY, (4, 3), foe),
            spawn(Team.ENEMY, (5, 3), foe),
        ],
        skills=[skill],
    )
    return give_turn(state, U2)


def test_around_passive_hits_every_enemy_in_the_ring_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else 1)
    state = _scene(_around())
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    fired = [e for e in result.events if isinstance(e, SkillTriggered)]
    assert [(e.unit_id, e.skill_id) for e in fired] == [(U1, "skill_t_around")]
    hits = [(d.source_id, d.target_id) for d in of(result, DamageDealt)]
    assert hits == [(U2, U1), (U1, U2)]  # 兩格外的 U3 不在周圍一圈
    assert U3 not in [d.target_id for d in of(result, DamageDealt)]
