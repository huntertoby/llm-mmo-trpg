"""Phase 2E-2 4.5：反應技（觸發事件、不花 AP、法力與冷卻、共用次數、prompt、深度、射程上限）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, Decision, EndTurn, Move, resolve, resume
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ReactionDeclined,
    ReactionTriggered,
    TriggerLimitReached,
)
from trpg.engine.state import StatusInstance
from trpg.shared.types import Pos, Team

RIPOSTE = "skill_riposte"


def reaction_skill(
    skill_id: str,
    event: str,
    *,
    shape: dict[str, Any] | None = None,
    effects: list[dict[str, Any]] | None = None,
    cost: dict[str, Any] | None = None,
) -> SkillDef:
    """測試專用反應技（不經驗證器）。預設：對觸發者一次 80% 武器傷害。"""
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"反應 {skill_id[-4:]}",
            "tier": 1,
            "rarity": "rare",
            "kind": "reaction",
            "skeleton": "reaction",
            "category": "weapon",
            "weapon_req": "melee",
            "ap_cost": None,
            "scaling_attr": "str",
            "shape": shape or {"type": "single", "range": 4},
            "effects": effects or [{"type": "damage", "multiplier_permille": 800}],
            "reaction": {"event": event},
            "cost": cost or {"mana": 0},
        }
    )


def duel(
    skills: list[SkillDef | str],
    *,
    foe: str = "bandit",
    foe_xy: tuple[int, int] = (4, 3),
    owner_hp: int = 999,
    foe_turn: bool = True,
    **core: int,
) -> BattleState:
    """U1（反應技持有者，戰士）在 (3, 3)；U2（敵人）在 ``foe_xy``，預設輪到敵人。"""
    defs = [s for s in skills if isinstance(s, SkillDef)]
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe_xy])
    owner = caster_template(skills, base="hero_fighter", max_hp=owner_hp)
    enemy = no_reactions(foe, max_hp=999)
    spawns = [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, foe_xy, enemy)]
    state = make_state(m, spawns, skills=defs, **core)  # type: ignore[arg-type]
    return give_turn(state, U2 if foe_turn else U1)


def test_content_riposte_hits_back_for_free_when_meleed(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = duel([RIPOSTE])
    hp = state.units[U2].hp
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U1, RIPOSTE, U2)
    assert trig.stamina_spent == 0
    rolls = of(result, AttackRolled)
    assert [(r.attacker_id, r.target_id) for r in rolls] == [(U2, U1), (U1, U2)]
    assert result.state.units[U2].hp < hp
    assert result.state.units[U1].ap == state.units[U1].ap  # 反應不花 AP
    assert result.state.units[U1].reactions_used == 1


def test_hit_by_melee_ignores_ranged_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = duel([RIPOSTE], foe="bandit_archer", foe_xy=(6, 3))
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert of(result, DamageDealt) and not of(result, ReactionTriggered)


def test_hit_by_attack_fires_on_ranged_hits_and_misses_do_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = reaction_skill("skill_t_rx_any", "hit_by_attack", shape={"type": "single", "range": 6})
    always(monkeypatch)
    far = duel([skill], foe="bandit_archer", foe_xy=(6, 3))
    assert of(resolve(far, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)
    always(monkeypatch, d20=1)  # 大失敗：沒命中就沒有「被命中」
    missed = resolve(duel([skill]), Attack(unit_id=U2, target_id=U1))
    assert not of(missed, DamageDealt) and not of(missed, ReactionTriggered)


def test_reaction_skills_share_reactions_per_round_and_reset_each_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = duel([RIPOSTE])
    first = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert len(of(first, ReactionTriggered)) == 1
    second = resolve(first.state, Attack(unit_id=U2, target_id=U1))
    assert not of(second, ReactionTriggered)  # 每輪 1 次（reactions_per_round）
    assert second.state.units[U1].reactions_used == 1


def test_mana_and_cooldown_are_paid_and_gate_the_reaction(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = reaction_skill("skill_t_rx_cost", "hit_by_melee", cost={"mana": 5, "cooldown": 3})
    state = duel([skill])
    mana = state.units[U1].mana
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    unit = result.state.units[U1]
    assert unit.mana == mana - 5 and unit.cooldowns[skill.id] == 3
    broke = duel([skill])
    broke.units[U1].mana = 4
    assert not of(resolve(broke, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)
    cooling = duel([skill])
    cooling.units[U1].cooldowns[skill.id] = 1
    assert not of(resolve(cooling, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)


def test_a_stunned_owner_cannot_react(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = duel([RIPOSTE])
    state.units[U1].statuses.append(StatusInstance("stun", 1, U2))
    assert not of(resolve(state, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)


def test_enemy_leaves_adjacent_reaction_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = reaction_skill("skill_t_rx_leave", "enemy_leaves_adjacent")
    state = duel([skill])
    path = (Pos(x=4, y=3), Pos(x=5, y=3))
    result = resolve(state, Move(unit_id=U2, path=path))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.reaction, trig.trigger_unit_id) == (skill.id, U2)


def test_blinded_owner_cannot_target_beyond_the_range_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = reaction_skill("skill_t_rx_far", "hit_by_attack", shape={"type": "single", "range": 6})
    state = duel([skill], foe="bandit_archer", foe_xy=(6, 3))
    assert of(resolve(state, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)
    state.units[U1].statuses.append(StatusInstance("blinded", 1, U2))
    assert not of(resolve(state, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)


def test_shape_single_needs_the_trigger_in_range(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = reaction_skill(
        "skill_t_rx_short", "hit_by_attack", shape={"type": "single", "range": 2}
    )
    state = duel([skill], foe="bandit_archer", foe_xy=(6, 3))
    assert not of(resolve(state, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)


def test_self_shape_reaction_buffs_the_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = reaction_skill(
        "skill_t_rx_self",
        "hit_by_melee",
        shape={"type": "self"},
        effects=[{"type": "apply_status", "status": "guarded", "duration": 2, "affects": "self"}],
    )
    result = resolve(duel([skill]), Attack(unit_id=U2, target_id=U1))
    assert any(s.status_id == "guarded" for s in result.state.units[U1].statuses)


def test_trigger_depth_limit_stops_the_reaction(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(duel([RIPOSTE], max_trigger_depth=0), Attack(unit_id=U2, target_id=U1))
    assert of(result, TriggerLimitReached) and not of(result, ReactionTriggered)


def test_a_reaction_skill_can_use_the_prompt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    prompt = [{"reaction": RIPOSTE, "when": {"event": "hit_by_melee"}, "mode": "prompt"}]
    owner = template("hero_fighter", reactions=prompt, max_mana=99, skills=[RIPOSTE])
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    base = make_state(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))],
    )
    state = give_turn(base, U2)
    paused = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert paused.pending is not None and paused.pending.reaction == RIPOSTE
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert of(accepted, ReactionTriggered)
    assert of(accepted, AttackRolled)
    assert accepted.state.units[U1].reactions_used == 1
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert of(declined, ReactionDeclined)
    assert not of(declined, AttackRolled)


def test_auto_rule_is_added_for_equipped_reaction_skills() -> None:
    state = duel([RIPOSTE])
    rules = state.units[U1].reactions
    assert [r.reaction for r in rules] == [RIPOSTE] and rules[0].when.event == "hit_by_melee"
    assert library().skills[RIPOSTE].kind == "reaction"


def test_a_reaction_skill_is_never_a_legal_action() -> None:
    state = duel([RIPOSTE], foe_turn=False)
    from trpg.engine import UseSkill, legal_actions  # noqa: PLC0415

    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill)]
    assert resolve(state, EndTurn(unit_id=U1)).events


def test_preview_includes_the_counter_reaction(monkeypatch: pytest.MonkeyPatch) -> None:
    from trpg.engine import preview  # noqa: PLC0415

    state = duel([RIPOSTE])
    pv = preview(state, Attack(unit_id=U2, target_id=U1))
    outcomes = pv.certain + pv.possible
    assert any(o.kind == "reaction" and o.unit_id == U1 for o in outcomes)
    assert any(isinstance(e, ReactionTriggered) for e in pv.max_events)
