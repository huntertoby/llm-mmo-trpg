"""雙資源（Phase 3H-2，``docs/design/06-技能.md`` 6.10、07 7.2）：武器技花耐力、法術技花法力；
主角的法力與耐力上限依屬性；格擋與武器技共用耐力。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, battle, cast, of
from trpg.api.skill_reasons import skill_reasons
from trpg.engine import Attack, BattleState, UseSkill, legal_actions, resolve
from trpg.engine.events import ReactionTriggered, SkillUsed
from trpg.engine.preview import preview
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import build_setup
from trpg.engine.state import state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Team

SLASH = {"type": "damage", "multiplier_permille": 1000}
BOLT = {"type": "damage", "dice": "1d4", "element": "fire"}


def _weapon(stamina: int) -> BattleState:
    skill = make_skill(
        SID,
        {"type": "single", "range": "weapon"},
        [SLASH],
        category="weapon",
        cost={"stamina": stamina},
    )
    return battle(skill, [(4, 3)], base="hero_fighter")


def _blocked(state: BattleState, fragment: str) -> None:
    """技能不在合法動作裡、施放與預覽都拒絕，原因含 ``fragment``。"""
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    assert action not in legal_actions(state)
    with pytest.raises(IllegalActionError, match=fragment):
        resolve(state, action)
    with pytest.raises(IllegalActionError, match=fragment):
        preview(state, action)
    assert fragment in skill_reasons(state, U1).reasons[SID]


def test_a_weapon_skill_spends_stamina_not_mana() -> None:
    state = _weapon(8)
    before = state.units[U1]
    result = cast(state, target_id=U2)
    after = result.state.units[U1]
    assert (after.stamina, after.mana) == (before.stamina - 8, before.mana)
    used = of(result, SkillUsed)[0]
    assert (used.stamina, used.stamina_after, used.mana) == (8, after.stamina, 0)


def test_not_enough_stamina_blocks_the_weapon_skill_with_a_reason() -> None:
    state = _weapon(8)
    assert UseSkill(unit_id=U1, skill_id=SID, target_id=U2) in legal_actions(state)
    state.units[U1].stamina = 7
    state.units[U1].mana = 99  # 法力再多也沒用
    _blocked(state, "耐力不足：需要 8，剩餘 7")


def test_not_enough_mana_blocks_the_spell_and_stamina_does_not_help() -> None:
    skill = make_skill(SID, {"type": "single", "range": 5}, [BOLT], cost={"mana": 6})
    state = battle(skill, [(5, 3)])
    state.units[U1].mana = 5
    state.units[U1].stamina = 99
    _blocked(state, "法力不足：需要 6，剩餘 5")


def test_block_shares_the_stamina_pool_with_weapon_skills() -> None:
    """格擋照舊花 10 耐力；武器技先花掉耐力，耐力低於門檻（20）時就不再格擋。"""
    skill = make_skill(
        SID, {"type": "single", "range": "weapon"}, [SLASH], category="weapon", cost={"stamina": 12}
    )
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    hero = template("hero_fighter", max_hp=300, skills=[SID])  # 預設反應規則（含格擋）
    foe = no_reactions(max_hp=300)
    fresh = make_state(
        m, [spawn(Team.ALLY, (3, 3), hero), spawn(Team.ENEMY, (4, 3), foe)], skills=[skill]
    )

    def attacked(state: BattleState) -> list[ReactionTriggered]:
        s = with_rolls(give_turn(state, "unit_0002"), [(20, 15), (4, 4)])
        events = resolve(s, Attack(unit_id=U2, target_id=U1)).events
        return [e for e in events if isinstance(e, ReactionTriggered)]

    blocks = attacked(fresh)
    assert [(b.reaction, b.stamina_spent) for b in blocks] == [("block", 10)]
    spent = resolve(give_turn(fresh, U1), UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).state
    assert spent.units[U1].stamina == fresh.units[U1].stamina - 12 < 20
    assert attacked(spent) == []


# ---------------------------------------------------------------------------
# 上限依屬性（只有主角：scaled_resources）
# ---------------------------------------------------------------------------


def _unit(**overrides: object) -> tuple[int, int]:
    m = make_map(FLAT7, ally=[(0, 0)], enemy=[(6, 6)])
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), template("hero_mage", **overrides)), spawn(Team.ENEMY, (6, 6))]
    )
    unit = state.units[U1]
    return unit.max_mana, unit.max_stamina


def test_hero_caps_follow_the_highest_attribute_of_each_group() -> None:
    core = library().ruleset.core
    attrs = {a: 10 for a in Attribute} | {Attribute.WIL: 16, Attribute.INT: 12, Attribute.CON: 13}
    mana, stamina = _unit(attributes=attrs, max_mana=40, stamina=30, scaled_resources=True)
    assert core.resources.mana.per_point == core.resources.stamina.per_point == 2
    assert (mana, stamina) == (40 + (16 - 10) * 2, 30 + (13 - 10) * 2)
    low = {a: 8 for a in Attribute}
    assert _unit(attributes=low, max_mana=40, stamina=30, scaled_resources=True) == (36, 26)


def test_other_units_keep_their_fixed_caps() -> None:
    attrs = {a: 10 for a in Attribute} | {Attribute.INT: 18, Attribute.STR: 18}
    assert _unit(attributes=attrs, max_mana=40, stamina=30) == (40, 30)


def test_a_build_hero_battle_with_stamina_skills_replays_identically() -> None:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415
    from trpg.sim.matrix import library_with_builds  # noqa: PLC0415

    lib = library_with_builds(library())
    setup = build_setup(lib, "open_plain", ["build_push"], ["bandit", "bandit"], max_rounds=8)
    run = run_battle(setup, 3, UtilityAI(lib.ai_profiles))
    used = [e for e in run.events if isinstance(e, SkillUsed) and e.stamina]
    assert used, "build_push 應該會施放花耐力的武器技"
    hero = run.state.units[U1]
    assert hero.stamina < hero.max_stamina
    again = replay(setup, 3, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
