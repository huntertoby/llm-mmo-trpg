"""E4（#175，08 8.29 E4 第 3 點）：新時機 ``on_block``「格擋時」。

只算格擋類反應（``reduce_damage``）真的結算時，含裝備讓遠程也能格擋的那種、玩家在提示裡選擇格擋；
另一方是攻擊者；替隊友擋（``intercept``）不算；KD-1 起倒地時不能反應，所以也不觸發。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_gear_g3a import always
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, Decision, resolve, resume
from trpg.engine.events import EventBase, ReactionTriggered, SkillTriggered
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
PASSIVE = "skill_t_e4_block"
STAND = "skill_stand_firm"
RANGED_BLOCK = [{"reaction": "block", "when": {"event": "targeted_by_attack"}, "mode": "auto"}]
PROMPT_BLOCK = [{"reaction": "block", "when": {"event": "targeted_by_melee"}, "mode": "prompt"}]


def passive(**filters: Any) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": PASSIVE,
            "name_zh": "測試格擋",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "wis",
            "shape": {"type": "self"},
            "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            "trigger": {"event": "on_block", "target": "self", "max_per_round": 1, **filters},
            "cost": {"mana": 0},
        }
    )


def fired(events: list[EventBase]) -> list[SkillTriggered]:
    return [e for e in events if isinstance(e, SkillTriggered) and e.skill_id == PASSIVE]


def blocker_scene(
    p: SkillDef,
    *,
    reactions: list[dict[str, Any]] | None = None,
    foe: str = "bandit",
    foe_xy: tuple[int, int] = (1, 0),
) -> BattleState:
    """U1（帶被動的戰士，(0, 0)，預設反應含格擋）被 U2（``foe``）攻擊；U2 拿到回合。"""
    m = make_map("00000\n00000", ally=[(0, 0)], enemy=[foe_xy])
    extra: dict[str, Any] = {} if reactions is None else {"reactions": reactions}
    hero = template("hero_fighter", max_hp=3000, skills=[p.id], **extra)
    spawns = [spawn(Team.ALLY, (0, 0), hero), spawn(Team.ENEMY, foe_xy, foe)]
    return give_turn(make_state(m, spawns, skills=[p]), U2)


def attack(state: BattleState) -> list[EventBase]:
    return resolve(state, Attack(unit_id=U2, target_id=U1)).events


def test_a_real_block_fires_with_the_attacker_as_other(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    events = attack(blocker_scene(passive()))
    assert [(e.unit_id, e.reaction) for e in events if isinstance(e, ReactionTriggered)] == [
        (U1, "block")
    ]
    assert [(e.unit_id, e.other_id) for e in fired(events)] == [(U1, U2)]


def test_no_block_no_trigger_for_ranged_with_the_default_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    events = attack(blocker_scene(passive(), foe="bandit_archer", foe_xy=(4, 0)))
    assert not any(isinstance(e, ReactionTriggered) for e in events)
    assert fired(events) == []


def test_gear_style_ranged_block_counts_and_filters_see_the_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """讓遠程也能格擋（規則改成 ``targeted_by_attack``）：擋下遠程普攻也算；``attack_kind`` 看被擋的
    那次攻擊。"""
    always(monkeypatch)
    for kind, expected in ((None, 1), ("ranged", 1), ("melee", 0)):
        filters = {} if kind is None else {"attack_kind": kind}
        state = blocker_scene(
            passive(**filters), reactions=RANGED_BLOCK, foe="bandit_archer", foe_xy=(4, 0)
        )
        events = attack(state)
        assert any(isinstance(e, ReactionTriggered) and e.reaction == "block" for e in events)
        assert len(fired(events)) == expected, kind


def test_choosing_to_block_in_the_prompt_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = blocker_scene(passive(), reactions=PROMPT_BLOCK)
    paused = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert paused.pending is not None
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert len(fired(accepted.events)) == 1
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert fired(declined.events) == []


def test_prone_blocker_cannot_block_so_nothing_fires(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = blocker_scene(passive())
    state.units[U1].statuses.append(StatusInstance("prone", remaining=99))
    events = attack(state)
    assert not any(isinstance(e, ReactionTriggered) for e in events)
    assert fired(events) == []


def test_guarding_an_ally_is_not_a_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """替隊友擋（挺身而出 ``intercept``）不算格擋。"""
    always(monkeypatch)
    p = passive()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (4, 4)])
    attacker = template("hero_fighter", reactions=[])
    guardian = no_reactions("hero_fighter", max_mana=99, skills=[STAND, p.id], max_hp=999)
    spawns = [
        spawn(Team.ALLY, (3, 3), attacker),
        spawn(Team.ENEMY, (4, 3), no_reactions()),
        spawn(Team.ENEMY, (4, 4), guardian),
    ]
    state = give_turn(make_state(m, spawns, skills=[p]), U1)
    events = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    assert any(isinstance(e, ReactionTriggered) and e.unit_id == U3 for e in events)
    assert fired(events) == []
