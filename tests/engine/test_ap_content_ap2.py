"""AP 相關內容（AP-2 第 3 項，05 5.2「會給 AP 的內容」，不加關鍵字）：被動新觸發「這回合用完所有 AP
時」、詞條「累積到門檻 +1 AP」（每第 3 次命中回 1 AP）、擊倒返還 1 AP 在普通、稀有技能的閃現。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from tests.engine.test_gear_g3a import always, hit, refill, scene
from trpg.content.equipment import TriggerAffix
from trpg.content.skills import SkillDef
from trpg.engine import Attack, EndTurn, resolve
from trpg.engine.events import ApGranted, ShieldGained, SkillTriggered
from trpg.engine.state import BattleState
from trpg.shared.types import Team
from trpg.skillgen.flash_offer import FlashRequest, try_variation
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage

PASSIVE = "skill_t_ap_spent"


def _passive(**trigger: Any) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": PASSIVE,
            "name_zh": "測試餘勁",
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
            "trigger": {
                "event": "on_ap_spent_all",
                "target": "self",
                "max_per_round": 1,
                **trigger,
            },
            "cost": {"mana": 0},
        }
    )


def _state(ap: int) -> BattleState:
    passive = _passive()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([passive], base="hero_fighter")),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999)),
    ]
    state = give_turn(make_state(m, spawns, skills=[passive]), U1)
    state.units[U1].ap = ap
    return state


def _fired(events: list[Any]) -> int:
    return sum(1 for e in events if isinstance(e, SkillTriggered) and e.skill_id == PASSIVE)


def test_spending_the_last_ap_fires_once() -> None:
    state = _state(2)
    first = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert first.state.units[U1].ap == 1
    assert _fired(first.events) == 0
    last = resolve(first.state, Attack(unit_id=U1, target_id=U2))
    assert last.state.units[U1].ap == 0
    assert _fired(last.events) == 1
    assert any(isinstance(e, ShieldGained) for e in last.events)


def test_ending_the_turn_with_ap_left_does_not_fire() -> None:
    state = _state(2)
    result = resolve(state, EndTurn(unit_id=U1))
    assert _fired(result.events) == 0


def test_the_trigger_is_once_per_round() -> None:
    with pytest.raises(ValidationError, match="on_ap_spent_all"):
        _passive(max_per_round=2)


def test_the_every_third_hit_affix_returns_one_ap(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [("affix_trig_every3_ap", None)]})
    granted_on: list[int] = []
    for number in range(1, 4):
        result = hit(refill(state, ap=2))
        state = result.state
        state.units[U2].hp = 999
        if [g for g in result.events if isinstance(g, ApGranted) and g.unit_id == U1]:
            granted_on.append(number)
    assert granted_on == [3]
    assert state.units[U1].ap == 2 - 1 + 1
    lib = library()
    affix = lib.affixes["affix_trig_every3_ap"]
    assert isinstance(affix, TriggerAffix)
    assert affix.trigger == "every_n_hits" and affix.n == 3
    assert [(e.type, e.amount) for e in affix.effects] == [("grant_ap", 1)]
    assert affix.effect_target == "self" and affix.limit == "per_turn"


@pytest.mark.parametrize("rarity", ["common", "rare"])
def test_kill_refund_flash_reaches_common_and_rare_skills(rarity: str) -> None:
    """「擊倒返還 1 AP」放進普通、稀有的閃現：小變化「收割」沒有稀有度門檻（AP-2 確認，不改
    資料）。"""
    lib = library()
    skills = sorted(
        (
            s
            for s in lib.skills.values()
            if s.rarity == rarity
            and s.kind == "active"
            and any(e.type == "damage" for e in s.effects)
            and not s.enemy_only
        ),
        key=lambda s: s.id,
    )
    variation = Variation(source="minor", template="kill_refund", category="extend")
    for skill in skills[:20]:
        state = acquire(skill.id).model_copy(update={"used": True})
        request = FlashRequest(skill, state, SkillUsage(), 1, tier=skill.tier)
        done = try_variation(lib, request, variation)
        if done is not None:
            kills = [k for e in done.skill.effects for k in e.on_kill or ()]
            assert any(k.type == "refund_ap" and k.amount == 1 for k in kills)
            return
    raise AssertionError(f"{rarity} 沒有任何技能做得出收割")
