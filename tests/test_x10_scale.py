"""X10-2a：程式認得 ``quantity_scale``（``docs/phases/PhaseX10-2a計畫.md``）。

內容的 ``quantity_scale`` 是 1，所有結果都不變；這裡把它換成 10 檢查各處的倍率。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.content.library import ContentLibrary
from trpg.content.rules import CoreRules
from trpg.content.skills import SkillDef
from trpg.content.summons import summon_dpr
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    HealEffect,
    ShieldEffect,
    run_effects,
)
from trpg.engine.events import AttackRolled, DamageDealt, Healed, ShieldGained
from trpg.engine.preview import dice_distribution
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_parts import _param_range_ladder, effect_knobs, quantity_randint
from trpg.skillgen.flash_ops import TRIGGER_FINE_OPS, trigger_fine_knobs
from trpg.skillgen.proposal_numbers import _fill_cost

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def test_content_scale_is_one(library: ContentLibrary) -> None:
    assert library.ruleset.core.quantity_scale == 1


@pytest.mark.parametrize("value", [0, 2, 5, 100])
def test_scale_accepts_only_one_or_ten(library: ContentLibrary, value: int) -> None:
    data = library.ruleset.core.model_dump()
    assert CoreRules.model_validate({**data, "quantity_scale": 10}).quantity_scale == 10
    with pytest.raises(ValidationError):
        CoreRules.model_validate({**data, "quantity_scale": value})


# ---------------------------------------------------------------------------
# 引擎：骰面 × scale，d20 不乘；寫死的 1 點下限 × scale


def _duel(scale: int) -> BattleState:
    m = make_map("000\n000\n000")
    a = spawn(Team.ALLY, (0, 1), "hero_fighter", weapon="one_handed_sword")
    t = spawn(Team.ENEMY, (1, 1), template("bandit", reactions=[]))
    return give_turn(make_state(m, [a, t], quantity_scale=scale), U1)


@pytest.mark.parametrize("scale", [1, 10])
def test_damage_heal_shield_dice_times_scale(scale: int) -> None:
    state = _duel(scale)
    damage = DamageEffect(target_id=U2, dice="1d6", flat=6)  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(6, 4)]), [damage]).events
    dealt = next(e for e in events if isinstance(e, DamageDealt))
    assert dealt.rolls == (4 * scale,)
    assert dealt.amount == 4 * scale + 6
    heal = HealEffect(target_id=U2, dice="1d4")  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(4, 3)]), [heal]).events
    assert next(e for e in events if isinstance(e, Healed)).rolls == (3 * scale,)
    shield = ShieldEffect(target_id=U1, dice="1d8")  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(8, 5)]), [shield]).events
    assert next(e for e in events if isinstance(e, ShieldGained)).amount == 5 * scale


@pytest.mark.parametrize("scale", [1, 10])
def test_d20_is_not_scaled(scale: int) -> None:
    state = with_rolls(_duel(scale), [(20, 15)])
    events = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled.natural == 15
    dealt = next(e for e in events if isinstance(e, DamageDealt))
    assert dealt.rolls and all(r % scale == 0 and 0 < r <= 20 * scale for r in dealt.rolls)


@pytest.mark.parametrize("scale", [1, 10])
def test_undying_leaves_one_point_times_scale(scale: int) -> None:
    state = _duel(scale)
    state = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="undying")]).state
    hp = state.units[U2].hp
    after = run_effects(state, [DamageEffect(target_id=U2, flat=hp + 50)]).state
    assert after.units[U2].hp == scale


def test_preview_distribution_scales_faces() -> None:
    assert dice_distribution(2, 4, scale=10) == {
        k * 10: v for k, v in dice_distribution(2, 4).items()
    }
    assert dice_distribution(1, 6, 2, 10) == {
        k * 10: v for k, v in dice_distribution(1, 6, 2).items()
    }


# ---------------------------------------------------------------------------
# 預算：固定值 ÷ scale，同一招換算前後點數相同


def scaled_library(library: ContentLibrary, scale: int = 10) -> ContentLibrary:
    """只把 ``core.quantity_scale`` 換掉的內容庫（內容本身沒換算）。"""
    core = library.ruleset.core.model_copy(update={"quantity_scale": scale})
    ruleset = library.ruleset.model_copy(update={"core": core})
    return dataclasses.replace(library, ruleset=ruleset)


def _times_ten(node: Any) -> Any:
    """技能資料裡的量類 ×10：代價的法力與耐力、``flat_bonus``、回復法力的 ``amount``。"""
    if isinstance(node, list):
        return [_times_ten(v) for v in node]
    if not isinstance(node, dict):
        return node
    out = {k: _times_ten(v) for k, v in node.items()}
    if isinstance(out.get("flat_bonus"), int):
        out["flat_bonus"] *= 10
    if (
        out.get("type") == "restore_resource"
        and out.get("resource") == "mana"
        and out.get("amount")
    ):
        out["amount"] *= 10
    cost = out.get("cost")
    if isinstance(cost, dict):
        out["cost"] = {
            k: v * 10 if k in ("mana", "stamina") and isinstance(v, int) else v
            for k, v in cost.items()
        }
    return out


def _quantity_skills(library: ContentLibrary) -> list[SkillDef]:
    def has(node: Any) -> bool:
        if isinstance(node, list):
            return any(has(v) for v in node)
        if not isinstance(node, dict):
            return False
        if node.get("flat_bonus") or (node.get("type") == "restore_resource"):
            return True
        return any(has(v) for v in node.values())

    out = []
    for skill in library.ruleset.skills.skills:
        data = skill.model_dump(mode="json", exclude_none=True)
        quantity = has(data.get("effects")) or skill.cost.mana or skill.cost.stamina
        if quantity and not any(e.type == "summon" for e in skill.effects):
            out.append(skill)
    return out


def test_budget_points_same_before_and_after_x10(library: ContentLibrary) -> None:
    ten = scaled_library(library)
    skills = _quantity_skills(library)
    assert len(skills) > 100
    flat = restore = 0
    for skill in skills:
        data = _times_ten(skill.model_dump(mode="json", exclude_none=True))
        scaled = SkillDef.model_validate(data)
        before, after = skill_budget(skill, library), skill_budget(scaled, ten)
        assert before.total == after.total, skill.id
        assert [v for _, v in before.allowance_parts] == [v for _, v in after.allowance_parts]
        flat += any(e.flat_bonus for e in skill.effects)
        restore += any(e.type == "restore_resource" for e in skill.effects)
    assert flat and restore  # 兩種固定值都有被比到


def test_summon_dpr_divides_flat(library: ContentLibrary) -> None:
    first = next(s for s in library.ruleset.summons.summons if not s.template.inert)
    summon = first.model_copy(update={"weapon": first.weapon.model_copy(update={"flat": 2})})
    ten = first.model_copy(update={"weapon": first.weapon.model_copy(update={"flat": 20})})
    assert summon_dpr(ten, flat=30, scale=10) == summon_dpr(summon, flat=3)


# ---------------------------------------------------------------------------
# 組合器與 LLM：法力等範圍步距 × scale，最低花費 × scale


def test_quantity_randint_steps_by_scale() -> None:
    for seed in range(200):
        one = quantity_randint(Rng(seed), 2, 4, 1)
        ten = quantity_randint(Rng(seed), 20, 40, 10)
        assert ten == one * 10


def test_restore_mana_ladder_steps_by_scale(library: ContentLibrary) -> None:
    effect = {"type": "restore_resource", "resource": "mana"}
    knobs = dict((n, v) for n, v, _ in effect_knobs(library, effect, category="spell", weight=1))
    assert knobs["amount"] == tuple(range(1, 11))
    ten = scaled_library(library)
    primitive = ten.ruleset.find_primitive("restore_resource")
    assert primitive is not None
    param = primitive.params["amount"]
    knob = next(k for k in param.knobs() if k.applies("spell", effect))
    wide = param.model_copy(update={"max": param.max * 10 if param.max else None})
    assert _param_range_ladder(ten, knob, wide, effect) == tuple(range(10, 101, 10))


def test_trigger_flat_bonus_steps_by_scale(library: ContentLibrary) -> None:
    base = {"kind": "passive", "category": "spell"}
    effects = [{"type": "heal", "dice": "1d4"}]
    op = sorted(TRIGGER_FINE_OPS)[0]
    top = library.flash.rules.trigger_flat_bonus
    (one,) = trigger_fine_knobs(op, base, effects, library)
    assert one.values == (None, *range(1, top + 1))
    flash = library.flash.model_copy(
        update={"rules": library.flash.rules.model_copy(update={"trigger_flat_bonus": top * 10})}
    )
    ten = dataclasses.replace(scaled_library(library), flash=flash)
    (scaled,) = trigger_fine_knobs(op, base, effects, ten)
    assert scaled.values == (None, *range(10, top * 10 + 1, 10))


@pytest.mark.parametrize("scale", [1, 10])
def test_minimal_cost_is_one_times_scale(library: ContentLibrary, scale: int) -> None:
    lib = library if scale == 1 else scaled_library(library, scale)
    out: dict[str, Any] = {"kind": "active", "category": "spell", "effects": [], "cost": {}}
    _fill_cost(out, lib, "spell")
    assert out["cost"]["mana"] == scale
