"""改寫規則型原語（Phase 3C-4a 6.3）：``grant_ap``、``reset_cooldown``、``cheat_death``。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    ApGranted,
    DeathCheated,
    EffectFizzled,
    SkillCooldownChanged,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
)
from trpg.engine.state import StatusInstance
from trpg.engine.turns import start_turn
from trpg.shared.types import Team

SID = "skill_t_rewrite"


def rewrite(effect: dict[str, Any], shape: dict[str, Any] | None = None) -> SkillDef:
    """測試用技能（普通稀有度、沒有代價；schema 不檢查稀有度與冷卻，驗證器才檢查）。"""
    return make_skill(SID, shape or {"type": "self"}, [effect])


def scene(skill: SkillDef, *, ally_hp: int | None = None) -> BattleState:
    """U1 施放者（我方）、U2 隊友、U3 敵人；輪到 U1。"""
    m = make_map(FLAT7, ally=[(3, 3), (4, 4)], enemy=[(4, 3)])
    ally = no_reactions("hero_fighter", **({"max_hp": ally_hp} if ally_hp else {}))
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([skill])),
            spawn(Team.ALLY, (4, 4), ally, skills=None),
            spawn(Team.ENEMY, (4, 3), no_reactions()),
        ],
        skills=[skill],
    )
    return give_turn(state, U1)


def cast(state: BattleState, **target: Any) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, **target))


# ---------------------------------------------------------------------------
# grant_ap
# ---------------------------------------------------------------------------

SELF_AP = {"type": "grant_ap", "amount": 2, "affects": "self"}


def test_grant_ap_gives_the_caster_ap_immediately() -> None:
    state = scene(rewrite(SELF_AP))
    result = cast(state)
    (event,) = [e for e in result.events if isinstance(e, ApGranted)]
    assert (event.unit_id, event.amount, event.ap_after, event.deferred) == (U1, 2, 4, False)
    assert result.state.units[U1].ap == 4  # 3 − 1（施放）＋ 2


def test_grant_ap_above_the_turn_cap_is_lost() -> None:
    state = scene(rewrite(SELF_AP))
    state.units[U1].ap = 4  # 本回合上限 ＝ ap_per_turn 3 ＋ ap_carry_max 1
    result = cast(state)
    (event,) = [e for e in result.events if isinstance(e, ApGranted)]
    assert (event.amount, event.ap_after) == (1, 4)


def test_grant_ap_only_once_per_unit_per_round() -> None:
    state = scene(rewrite({"type": "grant_ap", "amount": 1, "affects": "self"}))
    first = cast(state).state
    assert first.units[U1].ap == 3
    second = cast(first)
    assert not [e for e in second.events if isinstance(e, ApGranted)]
    (fizzled,) = [e for e in second.events if isinstance(e, EffectFizzled)]
    assert (fizzled.effect_kind, fizzled.reason) == ("grant_ap", "already_granted")
    assert second.state.units[U1].ap == 2
    next_round = second.state.clone()
    next_round.round += 1
    assert [e.amount for e in cast(next_round).events if isinstance(e, ApGranted)] == [1]


def test_grant_ap_to_an_ally_waits_for_their_turn_and_respects_the_cap() -> None:
    skill = rewrite({"type": "grant_ap", "amount": 2}, {"type": "single", "range": 3})
    result = cast(scene(skill), target_id=U2)
    (event,) = [e for e in result.events if isinstance(e, ApGranted)]
    assert (event.unit_id, event.amount, event.ap_after, event.deferred) == (U2, 2, 2, True)
    state = result.state
    assert state.units[U2].ap_pending == 2
    state.units[U2].ap_carry = 1
    ctx = Ctx(state)
    start_turn(ctx, U2)
    assert state.units[U2].ap == 4  # min(3 ＋ 保留 1 ＋ 給予 2, 上限 4)
    assert state.units[U2].ap_pending == 0


def test_grant_ap_cannot_target_enemies() -> None:
    with pytest.raises(ValueError, match="不能搭配 affects: enemies"):
        bad = rewrite({"type": "grant_ap", "amount": 1, "affects": "enemies"})
        _problems(bad)


# ---------------------------------------------------------------------------
# reset_cooldown
# ---------------------------------------------------------------------------

RESET_ALL = {"type": "reset_cooldown", "which": "all"}
SINGLE = {"type": "single", "range": 3}


def _with_cooldowns(skill: SkillDef) -> BattleState:
    state = scene(skill)
    state.units[U2].cooldowns = {
        "skill_fire_bolt": 2,  # 一般技能（標籤 fire）
        "skill_shield_bash": 3,
        "skill_time_surge": 2,  # 花源力的傳說：不重置
        SID: 4,  # 這個技能本身：不重置
    }
    state.units[U1].cooldowns = {"skill_fire_bolt": 2}
    return state


def test_reset_cooldown_clears_ally_cooldowns_except_source_skills_and_itself() -> None:
    result = cast(_with_cooldowns(rewrite(RESET_ALL, SINGLE)), target_id=U2)
    reset = [
        (e.unit_id, e.skill_id, e.remaining)
        for e in result.events
        if isinstance(e, SkillCooldownChanged) and e.remaining == 0
    ]
    assert reset == [(U2, "skill_fire_bolt", 0), (U2, "skill_shield_bash", 0)]
    assert result.state.units[U2].cooldowns == {"skill_time_surge": 2, SID: 4}
    assert result.state.units[U1].cooldowns == {"skill_fire_bolt": 2}  # 施放者自己不受影響


def test_reset_cooldown_by_tag() -> None:
    skill = rewrite({"type": "reset_cooldown", "which": "tag", "tag": "fire"}, SINGLE)
    result = cast(_with_cooldowns(skill), target_id=U2)
    assert result.state.units[U2].cooldowns == {
        "skill_shield_bash": 3,
        "skill_time_surge": 2,
        SID: 4,
    }


def test_reset_cooldown_on_self_or_without_cooldowns_fizzles() -> None:
    skill = rewrite(RESET_ALL, SINGLE)
    state = _with_cooldowns(skill)
    state.units[U2].cooldowns = {}
    (fizzled,) = [e for e in cast(state, target_id=U2).events if isinstance(e, EffectFizzled)]
    assert (fizzled.effect_kind, fizzled.reason) == ("reset_cooldown", "no_cooldown")
    radius = rewrite(RESET_ALL, {"type": "allies_in_radius", "radius": 2})
    state = _with_cooldowns(radius)
    result = cast(state)
    assert result.state.units[U1].cooldowns == {"skill_fire_bolt": 2}  # 範圍含自己也不重置自己
    assert result.state.units[U2].cooldowns == {"skill_time_surge": 2, SID: 4}


def test_reset_cooldown_needs_which_and_tag_rules() -> None:
    for effect, message in (
        ({"type": "reset_cooldown"}, "必須填 which"),
        ({"type": "reset_cooldown", "which": "tag"}, "which: tag 必須填 tag"),
        ({"type": "reset_cooldown", "which": "all", "tag": "fire"}, "which: all 不可填 tag"),
        ({"type": "heal", "dice": "1d4", "which": "all"}, "只有 reset_cooldown 使用"),
    ):
        with pytest.raises(ValueError, match=message):
            rewrite(effect, SINGLE)
    with pytest.raises(ValueError, match="不能搭配 affects: self"):
        _problems(rewrite({**RESET_ALL, "affects": "self"}))


# ---------------------------------------------------------------------------
# cheat_death
# ---------------------------------------------------------------------------


def _undying(state: BattleState, unit: Any = U2) -> BattleState:
    state.units[unit].statuses = [StatusInstance("undying", 2, U1)]
    return state


def test_cheat_death_applies_undying_to_an_ally() -> None:
    skill = rewrite({"type": "cheat_death", "duration": 2}, SINGLE)
    result = cast(scene(skill), target_id=U2)
    (applied,) = [e for e in result.events if isinstance(e, StatusApplied)]
    assert (applied.target_id, applied.status_id, applied.duration) == (U2, "undying", 2)


def test_undying_blocks_lethal_damage_once(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, die=6)
    state = _undying(scene(rewrite(SELF_AP)))
    state.units[U2].hp = 3
    enemy_turn = give_turn(state, U3)
    first = resolve(enemy_turn, Attack(unit_id=U3, target_id=U2))
    saved = first.state.units[U2]
    assert saved.hp == 1 and not saved.downed and not saved.has_status("undying")
    (cheated,) = [e for e in first.events if isinstance(e, DeathCheated)]
    removed = [e for e in first.events if isinstance(e, StatusRemoved)]
    assert cheated.unit_id == U2 and cheated.prevented > 0
    assert [(e.status_id, e.reason) for e in removed] == [("undying", "spent")]
    again = give_turn(first.state, U3)
    again.units[U3].ap = 3
    second = resolve(again, Attack(unit_id=U3, target_id=U2))
    assert second.state.units[U2].downed  # 只擋一次
    assert any(isinstance(e, UnitDowned) for e in second.events)


@pytest.mark.parametrize(
    ("cause", "mode"), [("fall", "percent_max_hp"), ("deadly_terrain", "lethal")]
)
def test_undying_does_not_stop_falls_or_deadly_terrain(cause: str, mode: str) -> None:
    state = _undying(scene(rewrite(SELF_AP)))
    state.units[U2].hp = 2
    ctx = Ctx(state)
    damage = DamageEffect.model_validate(
        {
            "target_id": U2,
            "cause": cause,
            "mode": mode,
            "permille": 1000,
            "apply_element_mod": False,
        }
    )
    execute(ctx, [damage])
    assert state.units[U2].downed
    assert not [e for e in ctx.events if isinstance(e, DeathCheated)]


def test_undying_does_not_trigger_on_non_lethal_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, die=1)
    state = _undying(scene(rewrite(SELF_AP)))
    result = resolve(give_turn(state, U3), Attack(unit_id=U3, target_id=U2))
    assert result.state.units[U2].has_status("undying")
    assert not [e for e in result.events if isinstance(e, DeathCheated)]


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def _ai_scene(skill_id: str, *, hp: int | None = None, source: int = 2) -> BattleState:
    lib = library()
    skill = lib.skills[skill_id]
    m = make_map(FLAT7, ally=[(0, 0), (0, 1)], enemy=[(6, 6)])
    hero = caster_template([skill], base="hero_mage").model_copy(update={"ai_profile": "support"})
    hero_spawn = spawn(Team.ALLY, (0, 0), hero).model_copy(update={"source": source})
    ally = no_reactions("hero_fighter")
    state = make_state(
        m,
        [hero_spawn, spawn(Team.ALLY, (0, 1), ally), spawn(Team.ENEMY, (6, 6), no_reactions())],
    )
    state = give_turn(state, U1)
    if hp is not None:
        state.units[U2].hp = hp
    return state


def test_the_ai_casts_the_ap_legendary_on_itself_when_it_has_source() -> None:
    state = _ai_scene("skill_time_surge")
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_time_surge"
    no_source = _ai_scene("skill_time_surge", source=0)
    no_source.units[U1].source = 0
    action = UtilityAI(library().ai_profiles)(no_source)
    assert not (isinstance(action, UseSkill) and action.skill_id == "skill_time_surge")


def test_the_ai_saves_undying_for_a_wounded_ally() -> None:
    policy = UtilityAI(library().ai_profiles)
    healthy = policy(_ai_scene("skill_undying_oath"))
    assert not (isinstance(healthy, UseSkill) and healthy.skill_id == "skill_undying_oath")
    wounded = policy(_ai_scene("skill_undying_oath", hp=6))
    assert isinstance(wounded, UseSkill) and wounded.skill_id == "skill_undying_oath"
    assert wounded.target_id == U2


def _problems(skill: SkillDef) -> None:
    from trpg.content.skills import skill_problems  # noqa: PLC0415

    rules = library().ruleset
    problems = skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )
    if problems:
        raise ValueError("；".join(problems))
