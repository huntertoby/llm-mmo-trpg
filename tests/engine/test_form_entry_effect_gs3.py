"""GS-3（#173，06 6.30「高階化身的進入時效果」）：``enter_form`` 後面可以再跟 1 個施加狀態或推擊。

- 結算順序：變身 → 形態的進入獎勵 → 進入時效果（命中判定在變身之後）；
- 化形專精 ×1.5 與形態幅度都不乘在進入時效果上；
- 只有 3 階以上可以帶、要有冷卻（下限在 ``core.yaml`` 的 ``skill_limits``）；
- 形狀只能是自己（效果只給自己）或實心環形；只能是 ``apply_status``／``push``，
  排在 ``enter_form`` 後面。
"""

from __future__ import annotations

from fractions import Fraction
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
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.content.skills.limits import skill_limit_problems
from trpg.engine import UseSkill, resolve
from trpg.engine.events import (
    AttackRolled,
    FormEntered,
    ShieldGained,
    StatusApplied,
    UnitMoved,
)
from trpg.engine.state import BattleState
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

SID = "skill_t_form_entry"
MASTERY = "skill_form_mastery"
WEAKEN = {"type": "apply_status", "status": "weaken", "duration": 2}


def entry_skill(
    second: dict[str, Any] | None = None,
    *,
    shape: dict[str, Any] | None = None,
    tier: int = 3,
    cooldown: int | None = 3,
    form: str = "bear",
    magnitude: int | None = None,
) -> SkillDef:
    lead: dict[str, Any] = {"type": "enter_form", "form": form, "affects": "self"}
    if magnitude is not None:
        lead["magnitude_permille"] = magnitude
    effects = [lead] if second is None else [lead, second]
    cost: dict[str, Any] = {} if cooldown is None else {"cooldown": cooldown}
    return SkillDef.model_validate(
        {
            "id": SID,
            "name_zh": "測試化身",
            "tier": tier,
            "rarity": "epic",
            "kind": "stance",
            "skeleton": "stance",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "str",
            "shape": shape or {"type": "ring", "radius": 1, "solid": True},
            "effects": effects,
            "cost": cost,
        }
    )


def scene(
    skill: SkillDef, *, mastery: bool = False, foes: tuple[tuple[int, int], ...] = ((4, 3),)
) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    owned: list[SkillDef | str] = [skill, MASTERY] if mastery else [skill]
    owner = caster_template(owned, base="hero_fighter", max_hp=1000, stamina=400)
    spawns = [spawn(Team.ALLY, (3, 3), owner)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=9990)) for xy in foes]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    state.units[U1].ap = 8
    return state


def cast(state: BattleState) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID))


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


def test_the_entry_effect_lands_after_the_form_and_its_entry_reward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    result = cast(scene(entry_skill(WEAKEN)))
    events = list(result.events)
    entered = next(i for i, e in enumerate(events) if isinstance(e, FormEntered))
    reward = next(i for i, e in enumerate(events) if isinstance(e, ShieldGained))  # 熊：護盾
    rolled = next(i for i, e in enumerate(events) if isinstance(e, AttackRolled))
    weakened = next(
        i for i, e in enumerate(events) if isinstance(e, StatusApplied) and e.status_id == "weaken"
    )
    assert entered < reward < rolled < weakened
    assert result.state.units[U1].form.form_id == "bear"
    assert [e.target_id for e in of(result, StatusApplied) if e.status_id == "weaken"] == [U2]


def test_mastery_and_magnitude_do_not_scale_the_entry_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    plain = cast(scene(entry_skill(WEAKEN)))
    boosted = cast(scene(entry_skill(WEAKEN, magnitude=1500), mastery=True))
    shield = [e.amount for e in of(plain, ShieldGained)]
    shield_boosted = [e.amount for e in of(boosted, ShieldGained)]
    assert shield_boosted[0] > shield[0]  # 形態的進入獎勵吃得到 ×1.5 與幅度
    for result in (plain, boosted):
        weak = [e for e in of(result, StatusApplied) if e.status_id == "weaken"]
        assert [(e.target_id, e.duration) for e in weak] == [(U2, 2)]
        target = result.state.units[U2].get_status("weaken")
        assert target is not None and target.magnitude_permille in (None, 1000)


def test_a_push_entry_effect_pushes_the_adjacent_foe_by_its_own_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    push = {"type": "push", "distance": 1}
    for mastery in (False, True):
        state = scene(entry_skill(push, form="giant", magnitude=2000), mastery=mastery)
        result = cast(state)
        moved = [e for e in of(result, UnitMoved) if e.unit_id == U2]
        assert moved and result.state.units[U2].xy == (5, 3)


def test_a_self_entry_effect_conceals_only_the_caster() -> None:
    conceal = {"type": "apply_status", "status": "concealed", "duration": 1, "affects": "self"}
    result = cast(scene(entry_skill(conceal, shape={"type": "self"}, form="cat")))
    applied = [e.target_id for e in of(result, StatusApplied) if e.status_id == "concealed"]
    assert applied == [U1]


def test_the_solid_ring_entry_reaches_two_tiles_out(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    skill = entry_skill(WEAKEN, shape={"type": "ring", "radius": 2, "solid": True})
    result = cast(scene(skill, foes=((4, 3), (5, 5))))
    weak = {e.target_id for e in of(result, StatusApplied) if e.status_id == "weaken"}
    assert weak == {U2, U3}


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------


def _limits() -> Any:
    return library().ruleset.core.skill_limits


def test_tier_two_cannot_carry_an_entry_effect() -> None:
    limits = _limits()
    assert limits.min_form_entry_tier == 3
    low = entry_skill(WEAKEN, tier=limits.min_form_entry_tier - 1)
    assert any("階以上才能帶進入時效果" in p for p in skill_limit_problems(low, limits))
    ok = entry_skill(WEAKEN, tier=limits.min_form_entry_tier)
    assert skill_limit_problems(ok, limits) == []
    assert any("階以上" in v.message for v in validate_skill(low, library()))


@pytest.mark.parametrize("cooldown", [None, 1])
def test_the_cooldown_floor_blocks_a_short_cooldown(cooldown: int | None) -> None:
    limits = _limits()
    assert limits.min_form_entry_cooldown == 2
    short = entry_skill(WEAKEN, cooldown=cooldown)
    assert any("冷卻至少 2 回合" in p for p in skill_limit_problems(short, limits))
    assert skill_limit_problems(entry_skill(WEAKEN, cooldown=2), limits) == []


def test_plain_low_tier_forms_are_untouched_by_the_new_limits() -> None:
    lib = library()
    for skill_id in ("skill_form_bear", "skill_form_dragon"):
        skill = lib.ruleset.skill_def(skill_id)
        assert skill.form_entry_effect is None
        assert skill_limit_problems(skill, lib.ruleset.core.skill_limits) == []


@pytest.mark.parametrize(
    ("second", "shape", "message"),
    [
        ({"type": "damage", "dice": "1d6", "element": "physical"}, None, "唯一的效果"),
        ({"type": "pull", "distance": 1}, None, "唯一的效果"),
        (WEAKEN, {"type": "ring", "radius": 1}, "solid: true"),
        (WEAKEN, {"type": "self"}, "只能給自己"),
        (WEAKEN, {"type": "allies_in_radius", "radius": 1}, "形狀只能是"),
        ({**WEAKEN, "magnitude_permille": 1200}, None, "magnitude_permille"),
    ],
)
def test_the_entry_effect_is_limited_to_status_or_push_on_self_or_a_solid_ring(
    second: dict[str, Any], shape: dict[str, Any] | None, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        entry_skill(second, shape=shape)


def test_the_entry_effect_must_follow_the_form() -> None:
    with pytest.raises(ValidationError):
        SkillDef.model_validate(
            {
                **entry_skill(WEAKEN).model_dump(mode="json"),
                "effects": [WEAKEN, {"type": "enter_form", "form": "bear", "affects": "self"}],
            }
        )


def test_an_entry_effect_cannot_be_a_stance_status() -> None:
    stance = {"type": "apply_status", "status": "stance_guard", "affects": "self"}
    if "stance_guard" not in library().ruleset.statuses.by_id():
        pytest.skip("沒有 stance_guard")
    skill = entry_skill(stance, shape={"type": "self"})
    assert any("不能施加姿態狀態" in v.message for v in validate_skill(skill, library()))


def test_the_budget_adds_the_entry_effect_times_its_shape() -> None:
    lib = library()
    plain = skill_budget(entry_skill(None, shape={"type": "self"}, cooldown=None, tier=3), lib)
    report = skill_budget(entry_skill(WEAKEN), lib)
    assert len(report.effects) == 2
    form_part, entry = report.effects
    assert form_part.points == plain.effects[0].points  # 形態的固定點數不變
    solid = lib.budget.shape_budget["ring"].solid_by_value
    assert solid is not None and entry.shape == Fraction(solid[1], 1000)
    assert report.total == form_part.points + entry.points
