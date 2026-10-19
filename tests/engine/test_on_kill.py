"""技能內的擊殺時效果（Phase 3D-8b，``docs/phases/Phase3D計畫.md`` 8.2、8.4）：擊殺與未擊殺、返還
AP、本技能冷卻歸零、其他原語、一個效果只結算一次、schema 限制、預算、預覽、文字、AI 與重播。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill, no_reactions
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, preview, state_to_json
from trpg.engine.events import ApRefunded, DamageDealt, Healed, SkillCooldownChanged, UnitDowned
from trpg.engine.rewrites import ap_cap
from trpg.narrative.events import describe_event
from trpg.narrative.skills import skill_card
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

REFUND_AP: dict[str, Any] = {"type": "refund_ap", "amount": 1}
REFUND_COOLDOWN: dict[str, Any] = {"type": "refund_cooldown"}


def strike(
    on_kill: list[dict[str, Any]],
    *,
    shape: dict[str, Any] | None = None,
    ap_cost: int = 2,
    cooldown: int | None = 2,
) -> SkillDef:
    """武器技：傷害 ×2 ＋ ``on_kill``。"""
    effect = {"type": "damage", "multiplier_permille": 2000, "on_kill": on_kill}
    cost: dict[str, Any] = {"mana": 0}
    if cooldown is not None:
        cost["cooldown"] = cooldown
    data = make_skill(
        SID,
        shape or {"type": "single", "range": "weapon"},
        [effect],
        category="weapon",
        ap_cost=ap_cost,
        cost=cost,
    ).model_dump(mode="json")
    data["skeleton"] = "strike"
    return SkillDef.model_validate(data)


def arena(skill: SkillDef, foes: list[Any]) -> BattleState:
    """U1 戰士（施放者）在 (3, 3)；敵人從 U2 起。"""
    return battle(skill, foes, base="hero_fighter")


def weak(xy: tuple[int, int], hp: int = 1) -> tuple[int, int, Any]:
    return (*xy, no_reactions("bandit", max_hp=hp))


def tough(xy: tuple[int, int]) -> tuple[int, int, Any]:
    return (*xy, no_reactions("bandit", max_hp=500))


# ---------------------------------------------------------------------------
# 擊殺時結算
# ---------------------------------------------------------------------------


def test_a_kill_refunds_ap_and_resets_the_cooldown() -> None:
    state = hit_with(arena(strike([REFUND_AP, REFUND_COOLDOWN]), [weak((4, 3))]))
    ap_before = state.units[U1].ap
    result = cast(state, target_id=U2)
    assert [e.unit_id for e in of(result, UnitDowned)] == [U2]
    (refund,) = of(result, ApRefunded)
    assert (refund.unit_id, refund.amount) == (U1, 1) and refund.skill_id == SID
    caster = result.state.units[U1]
    assert caster.ap == ap_before - 2 + 1 == refund.ap_after
    assert SID not in caster.cooldowns  # 冷卻歸零
    changes = [(e.skill_id, e.remaining) for e in of(result, SkillCooldownChanged)]
    assert changes == [(SID, 2), (SID, 0)]  # 先進冷卻，擊殺後歸零


def test_no_kill_means_no_refund() -> None:
    state = hit_with(arena(strike([REFUND_AP, REFUND_COOLDOWN]), [tough((4, 3))]))
    result = cast(state, target_id=U2)
    assert of(result, UnitDowned) == [] and of(result, ApRefunded) == []
    assert result.state.units[U1].cooldowns[SID] == 2
    assert result.state.units[U1].ap == state.units[U1].ap - 2


def test_a_miss_means_no_refund() -> None:
    state = arena(strike([REFUND_AP]), [weak((4, 3))])
    from tests.engine.helpers import with_rolls  # noqa: PLC0415

    state = with_rolls(state, [(20, 1)])  # 自然 1：失手
    result = cast(state, target_id=U2)
    assert of(result, DamageDealt) == [] and of(result, ApRefunded) == []


def test_the_effect_resolves_once_even_when_several_enemies_go_down() -> None:
    skill = strike([REFUND_AP], shape={"type": "cross", "range": 4}, ap_cost=2)
    state = arena(skill, [weak((4, 3)), weak((4, 4))])
    state = hit_with(state, [(20, 19)])
    result = cast(state, target_pos={"x": 4, "y": 3})
    assert len(of(result, UnitDowned)) == 2
    assert len(of(result, ApRefunded)) == 1


def test_the_refund_never_goes_above_the_ap_cap() -> None:
    skill = strike([{"type": "refund_ap", "amount": 2}], ap_cost=1)
    state = hit_with(arena(skill, [weak((4, 3))]))
    state.units[U1].ap = ap_cap(state.ruleset.core)
    result = cast(state, target_id=U2)
    assert result.state.units[U1].ap == ap_cap(state.ruleset.core)
    (refund,) = of(result, ApRefunded)
    assert refund.amount == 1  # 付 1 點之後只能補回 1 點


def test_a_full_ap_pool_produces_no_event() -> None:
    skill = strike([REFUND_AP], ap_cost=1)
    state = hit_with(arena(skill, [weak((4, 3))]))
    state.units[U1].ap = ap_cap(state.ruleset.core) + 1  # 超過上限（測試用）
    assert of(cast(state, target_id=U2), ApRefunded) == []


def test_ordinary_primitives_apply_to_the_caster() -> None:
    skill = strike(
        [{"type": "heal", "dice": "1d4"}, {"type": "apply_status", "status": "guarded"}],
        ap_cost=1,
    )
    state = hit_with(arena(skill, [weak((4, 3))]), [(4, 2)])
    state.units[U1].hp = 1
    result = cast(state, target_id=U2)
    (heal,) = of(result, Healed)
    assert heal.target_id == U1 and result.state.units[U1].hp > 1
    assert result.state.units[U1].has_status("guarded")


def test_a_killing_blow_from_someone_else_does_not_count() -> None:
    from trpg.engine.effects import run_effects  # noqa: PLC0415
    from trpg.engine.effects.models import DamageEffect  # noqa: PLC0415

    state = arena(strike([REFUND_AP]), [weak((4, 3)), tough((6, 6))])
    result = run_effects(state, [DamageEffect(target_id=U2, mode="lethal")])
    assert of(result, ApRefunded) == []


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def _skill_with(on_kill: list[dict[str, Any]] | None, **fields: Any) -> dict[str, Any]:
    data = strike([REFUND_AP]).model_dump(mode="json")
    effect = {"type": "damage", "multiplier_permille": 2000}
    if on_kill is not None:
        effect["on_kill"] = on_kill
    data["effects"] = [effect]
    data.update(fields)
    return data


def test_schema_limits_on_kill() -> None:
    SkillDef.model_validate(_skill_with([REFUND_AP, REFUND_COOLDOWN]))
    with pytest.raises(ValueError, match="1 到 2"):
        SkillDef.model_validate(_skill_with([REFUND_AP, REFUND_COOLDOWN, REFUND_AP]))
    with pytest.raises(ValueError, match="1 到 2"):
        SkillDef.model_validate(_skill_with([]))
    with pytest.raises(ValueError, match="只能使用"):
        SkillDef.model_validate(_skill_with([{"type": "damage", "dice": "1d4"}]))
    with pytest.raises(ValueError, match="amount"):
        SkillDef.model_validate(_skill_with([{"type": "refund_ap", "amount": 3}]))
    with pytest.raises(ValueError, match="amount"):
        SkillDef.model_validate(_skill_with([{"type": "refund_ap"}]))
    with pytest.raises(ValueError, match="施放者"):
        SkillDef.model_validate(_skill_with([{**REFUND_AP, "affects": "enemies"}]))
    with pytest.raises(ValueError, match="冷卻"):
        SkillDef.model_validate(_skill_with([REFUND_COOLDOWN], cost={"mana": 0}))


def test_on_kill_is_only_for_the_skills_own_damage_effect() -> None:
    with pytest.raises(ValueError, match="只有 damage"):
        SkillDef.model_validate(
            _skill_with(None, effects=[{"type": "heal", "dice": "1d6", "on_kill": [REFUND_AP]}])
        )
    with pytest.raises(ValueError, match="只能出現在 on_kill"):
        SkillDef.model_validate(_skill_with(None, effects=[REFUND_AP]))
    nested = {
        "type": "gamble",
        "chance_permille": 500,
        "win": [{"type": "damage", "multiplier_permille": 1000, "on_kill": [REFUND_AP]}],
    }
    with pytest.raises(ValueError, match="on_kill"):
        SkillDef.model_validate(
            _skill_with(None, effects=[{"type": "damage", "multiplier_permille": 1000}, nested])
        )
    passive = _skill_with([REFUND_AP], kind="passive", ap_cost=None)
    with pytest.raises(ValueError):
        SkillDef.model_validate(passive)


def test_cross_file_checks_validate_the_primitives_inside_on_kill() -> None:
    lib = library()
    skill = SkillDef.model_validate(
        _skill_with([{"type": "apply_status", "status": "no_such_status"}])
    )
    rules = lib.ruleset
    from trpg.content.skills import skill_problems  # noqa: PLC0415

    problems = skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )
    assert any("no_such_status" in p and "on_kill" in p for p in problems)


# ---------------------------------------------------------------------------
# 預算、預覽、文字、示範技能、AI
# ---------------------------------------------------------------------------


def test_the_budget_counts_the_on_kill_effects_times_the_expected_kill_rate() -> None:
    lib = library()
    plain = strike([REFUND_AP], cooldown=2)
    with_cooldown = strike([REFUND_AP, REFUND_COOLDOWN], cooldown=2)
    report = skill_budget(with_cooldown, lib)
    (row,) = [e for e in report.effects if e.type == "on_kill"]
    rules = lib.budget
    expected = (rules.refund_ap_points + rules.restore_cooldown_points * 2) * (
        rules.on_kill_expected_permille
    )
    assert row.points * 1000 == expected
    assert skill_budget(plain, lib).total < report.total


def test_the_preview_shows_the_refund_in_the_max_outcome() -> None:
    state = arena(strike([REFUND_AP]), [weak((4, 3))])
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert any(isinstance(e, ApRefunded) for e in p.max_events)


def test_the_log_and_the_skill_card_describe_the_on_kill_effects() -> None:
    state = hit_with(arena(strike([REFUND_AP, REFUND_COOLDOWN]), [weak((4, 3))]))
    result = cast(state, target_id=U2)
    (refund,) = of(result, ApRefunded)
    assert "返還了 1 AP" in (describe_event(refund, result.state) or "")
    card = str(skill_card(library(), library().skills["skill_ash_harvest"]))
    assert "若這一招讓敵人倒下" in card and "返還 1 AP" in card and "冷卻歸零" in card


def test_the_demo_skill_is_valid_in_budget_and_equipped() -> None:
    lib = library()
    skill = lib.skills["skill_ash_harvest"]
    assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
    assert "skill_ash_harvest" in lib.builds.by_id()["build_bomber"].hero.skills
    assert any(e.on_kill for e in skill.effects)


def test_the_ai_values_a_skill_that_can_finish_an_enemy() -> None:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415

    state = arena(strike([REFUND_AP, REFUND_COOLDOWN]), [weak((4, 3))])
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == SID


def test_the_state_stays_deterministic_with_on_kill() -> None:
    state = hit_with(arena(strike([REFUND_AP, REFUND_COOLDOWN]), [weak((4, 3))]))
    assert state_to_json(cast(state, target_id=U2).state) == state_to_json(
        cast(state, target_id=U2).state
    )
