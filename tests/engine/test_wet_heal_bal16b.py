"""BAL-16b（#93，05 互動表下方）：站在水上的目標受到的治療 +20%，護盾不放大。"""

from __future__ import annotations

from tests.engine.helpers import library, make_map, make_state, no_reactions, spawn
from trpg.content.keyword_derive import derive_keywords
from trpg.engine import BattleState
from trpg.engine.effects import HealEffect, ShieldEffect, run_effects
from trpg.engine.events import Healed
from trpg.engine.ids import SHIELDED
from trpg.engine.rules.statuses import shield_amount
from trpg.narrative.skills import skill_card_keywords
from trpg.shared.types import Team, UnitId

WET, DRY = UnitId("unit_0001"), UnitId("unit_0002")


def _state() -> BattleState:
    m = make_map("0000", ally=[(0, 0), (2, 0)], enemy=[(3, 0)], surfaces=[(0, 0, "water")])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ALLY, (2, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (3, 0), no_reactions()),
        ],
    )
    for uid in (WET, DRY):
        state.units[uid].hp = 10
    return state


def _healed(state: BattleState, uid: UnitId, flat: int) -> Healed:
    result = run_effects(state, [HealEffect(target_id=uid, flat=flat)])
    return next(e for e in result.events if isinstance(e, Healed))


def test_core_rule_is_twenty_percent() -> None:
    assert library().ruleset.core.wet_heal_permille == 1200


def test_heal_on_water_is_amplified() -> None:
    state = _state()
    wet, dry = _healed(state, WET, 10), _healed(state, DRY, 10)
    assert dry.amount == 10 and dry.received_permille == 1000
    assert wet.amount == 12 and wet.received_permille == 1200


def test_shield_on_water_is_not_amplified() -> None:
    state = _state()
    for uid in (WET, DRY):
        s = run_effects(state, [ShieldEffect(target_id=uid, flat=10)]).state
        assert shield_amount(s.ruleset, s.units[uid]) == 10
        assert any(i.status_id == SHIELDED for i in s.units[uid].statuses)


def test_heal_skills_show_uses_wet_on_the_card() -> None:
    lib = library()
    skill = lib.skills["skill_renewal"]
    assert "wet" in derive_keywords(skill, lib.keywords).uses
    assert "wet" not in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    refs = [r for r in skill_card_keywords(lib, skill).uses if r.id == "wet"]
    assert refs and refs[0].general and refs[0].reason_zh
