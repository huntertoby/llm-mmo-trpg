"""X10-2a：程式認得 ``quantity_scale``（``docs/phases/PhaseX10-2a計畫.md``）。

X10-2b 起內容已換算，``quantity_scale`` 是 10；這裡把它換回 1（量類 ÷10）比對各處的倍率。
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.content.environment import SummonAiRules
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.rules import CoreRules
from trpg.content.skills import SkillDef
from trpg.content.summons import summon_dpr
from trpg.content.world_encounters import ArmorMods
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.ai.infuse import survival
from trpg.engine.ai.utility.gains import _useful_damage
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    HealEffect,
    ShieldEffect,
    run_effects,
)
from trpg.engine.events import AttackRolled, DamageDealt, Healed, ShieldGained
from trpg.engine.preview import DamageRange, dice_distribution
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_parts import _param_range_ladder, effect_knobs, quantity_randint
from trpg.skillgen.composer_special import compose_legendary
from trpg.skillgen.flash_ops import TRIGGER_FINE_OPS, trigger_fine_knobs
from trpg.skillgen.proposal_numbers import _fill_cost, minimal_filler

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def test_content_scale_is_ten(library: ContentLibrary) -> None:
    assert library.ruleset.core.quantity_scale == 10


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
    """只把 ``core.quantity_scale`` 換掉的內容庫（內容本身不動）。"""
    core = library.ruleset.core.model_copy(update={"quantity_scale": scale})
    ruleset = library.ruleset.model_copy(update={"core": core})
    return dataclasses.replace(library, ruleset=ruleset)


def _tenth(value: int) -> int:
    assert value % 10 == 0, value  # 內容換算後量類都是 10 的倍數
    return value // 10


def _div_ten(node: Any) -> Any:
    """技能資料裡的量類 ÷10（換回換算前）：代價的法力與耐力、``flat_bonus``、
    回復法力的 ``amount``。"""
    if isinstance(node, list):
        return [_div_ten(v) for v in node]
    if not isinstance(node, dict):
        return node
    out = {k: _div_ten(v) for k, v in node.items()}
    if isinstance(out.get("flat_bonus"), int):
        out["flat_bonus"] = _tenth(out["flat_bonus"])
    if (
        out.get("type") == "restore_resource"
        and out.get("resource") == "mana"
        and out.get("amount")
    ):
        out["amount"] = _tenth(out["amount"])
    cost = out.get("cost")
    if isinstance(cost, dict):
        out["cost"] = {
            k: _tenth(v) if k in ("mana", "stamina") and isinstance(v, int) else v
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
    one = scaled_library(library, 1)
    skills = _quantity_skills(library)
    assert len(skills) > 100
    flat = restore = 0
    for skill in skills:
        data = _div_ten(skill.model_dump(mode="json", exclude_none=True))
        unscaled = SkillDef.model_validate(data)
        before, after = skill_budget(unscaled, one), skill_budget(skill, library)
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
    assert knobs["amount"] == tuple(range(10, 101, 10))
    one = scaled_library(library, 1)
    primitive = one.ruleset.find_primitive("restore_resource")
    assert primitive is not None
    param = primitive.params["amount"]
    knob = next(k for k in param.knobs() if k.applies("spell", effect))
    narrow = param.model_copy(update={"max": _tenth(param.max) if param.max else None})
    assert _param_range_ladder(one, knob, narrow, effect) == tuple(range(1, 11))


def test_trigger_flat_bonus_steps_by_scale(library: ContentLibrary) -> None:
    base = {"kind": "passive", "category": "spell"}
    effects = [{"type": "heal", "dice": "1d4"}]
    op = sorted(TRIGGER_FINE_OPS)[0]
    top = library.flash.rules.trigger_flat_bonus
    (ten,) = trigger_fine_knobs(op, base, effects, library)
    assert ten.values == (None, *range(10, top + 1, 10))
    rules = library.flash.rules.model_copy(update={"trigger_flat_bonus": _tenth(top)})
    one = dataclasses.replace(
        scaled_library(library, 1), flash=library.flash.model_copy(update={"rules": rules})
    )
    (unscaled,) = trigger_fine_knobs(op, base, effects, one)
    assert unscaled.values == (None, *range(1, _tenth(top) + 1))


@pytest.mark.parametrize("scale", [1, 10])
def test_minimal_cost_is_one_times_scale(library: ContentLibrary, scale: int) -> None:
    lib = scaled_library(library, scale)
    out: dict[str, Any] = {"kind": "active", "category": "spell", "effects": [], "cost": {}}
    _fill_cost(out, lib, "spell")
    assert out["cost"]["mana"] == scale


@pytest.mark.parametrize("scale", [1, 10])
def test_minimal_filler_restore_mana_is_one_times_scale(
    library: ContentLibrary, scale: int
) -> None:
    """X10-2b（X10-2a 裁定 3）：回復法力補的最小值 1 × scale；冷卻回合不乘。"""
    fill = minimal_filler(scaled_library(library, scale))
    effects = [
        {"type": "restore_resource", "resource": "mana", "target": "self"},
        {"type": "restore_resource", "resource": "cooldown", "target": "self"},
    ]
    out = fill({"kind": "active", "category": "spell", "effects": effects})
    assert [e["amount"] for e in out["effects"]] == [scale, 1]


@pytest.mark.parametrize("scale", [1, 10])
def test_mana_cost_floor_is_one_times_scale(library: ContentLibrary, scale: int) -> None:
    """X10-2b（X10-2a 裁定 3）：打折後至少 1 × scale；原費用更少時以原費用為下限。"""
    core = library.ruleset.core.model_copy(
        update={"quantity_scale": scale, "mana_cost_permille": 100}
    )
    assert core.mana_cost(4 * scale) == scale  # 0.4 × scale → 0，下限 1 × scale
    assert core.mana_cost(30 * scale) == 3 * scale
    assert core.mana_cost(0) == 0
    if scale == 10:
        assert core.mana_cost(5) == 5


# ---------------------------------------------------------------------------
# AI 評分：量類 ÷ scale（X10-1 裁定 2），ai_profiles.yaml 的點數不動


def test_useful_damage_divides_by_scale() -> None:
    one = DamageRange(3, 9, Fraction(5), Fraction(6))
    ten = DamageRange(30, 90, Fraction(50), Fraction(60))
    hit = Fraction(3, 4)
    for hp in (4, 20):
        assert _useful_damage(ten, hit, hp * 10, 10) == _useful_damage(one, hit, hp, 1)


@pytest.mark.parametrize("scale", [1, 10])
def test_infuse_survival_same_after_x10(library: ContentLibrary, scale: int) -> None:
    """``infuse_threat_damage`` 是換算前的單位：× scale 再和 HP 相加，存活率不變。"""
    state = _duel(scale)
    unit = state.units[U2]
    unit.hp = 7 * scale
    rules = library.ai_profiles.summon.model_copy(update={"infuse_threat_damage": 2})
    assert isinstance(rules, SummonAiRules)
    assert survival(state, unit, rules) == Fraction(7, 7 + 2)  # 相鄰的戰士 1 名


# ---------------------------------------------------------------------------
# Python 預設值：量類沒有預設值（X10-2a 擋 scale 10；HC-2 起一律必填）


@pytest.mark.parametrize("scale", [1, 10])
def test_quantity_fields_are_required(library: ContentLibrary, scale: int) -> None:
    data = library.ruleset.core.model_dump()
    for section, key in (
        ("resources", "stamina_regen"),
        ("resources", "class_base"),
        ("attribute_perks", "base"),
        ("summon_growth", "hp_per_level"),
    ):
        partial = {**data, section: {k: v for k, v in data[section].items() if k != key}}
        with pytest.raises(ValidationError, match=rf"{section}\.{key}\s+Field required"):
            CoreRules.model_validate({**partial, "quantity_scale": scale})


@pytest.mark.parametrize("scale", [1, 10])
def test_form_upkeep_is_required(library: ContentLibrary, scale: int) -> None:
    ruleset = library.ruleset
    core = ruleset.core.model_copy(update={"quantity_scale": scale})
    forms = ruleset.forms.model_dump()
    del forms["upkeep_mana"]
    data = {**ruleset.model_dump(), "core": core.model_dump(), "forms": forms}
    with pytest.raises(ValidationError, match=r"forms\.upkeep_mana\s+Field required"):
        Ruleset.model_validate(data)
    data["forms"] = ruleset.forms.model_dump()
    assert Ruleset.model_validate(data).core.quantity_scale == scale


def test_armor_mods_bounds_have_no_default() -> None:
    with pytest.raises(ValidationError, match="min_total"):
        ArmorMods.model_validate(
            {"unit": "ember_heart", "max_total": 1, "mods": [{"world_flag": "a", "amount": 1}]}
        )


# ---------------------------------------------------------------------------
# X10-2b 補列：加在屬性值或量類上的常駐數值也要照比例


def test_round_shield_block_bonus_is_per_old_attribute_point(library: ContentLibrary) -> None:
    """圓盾「縮放屬性 × 每點‰」：屬性 ×10 後 ÷ scale，減傷和換算前相同。"""
    shield = library.offhands["round_shield"]
    assert shield.block_bonus is not None
    assert shield.block_extra_permille(lambda _a: 140, 10) == shield.block_extra_permille(
        lambda _a: 14
    )
    assert shield.block_extra_permille(lambda _a: 145, 10) == 72  # 145 × 5 ÷ 10，捨去


def test_control_resist_per_tier_is_scaled(library: ContentLibrary) -> None:
    perks = library.ruleset.core.attribute_perks
    by_kind = {p.kind: p.per_tier for p in perks.perks}
    assert by_kind["control_resist"] == 10  # 加在抵抗的屬性值上
    assert by_kind["collision_dealt"] == by_kind["collision_taken"] == 10
    assert by_kind["reaction_hit"] == by_kind["reveal_range"] == by_kind["surface_duration"] == 1


@pytest.mark.parametrize("scale", [1, 10])
def test_default_min_damage_is_one_times_scale(scale: int) -> None:
    state = _duel(scale)
    hp = state.units[U2].hp
    percent = DamageEffect(target_id=U2, mode="percent_max_hp", permille=0)
    after = run_effects(state, [percent]).state
    assert hp - after.units[U2].hp == scale
    explicit = DamageEffect(target_id=U2, mode="percent_max_hp", permille=0, min_damage=3)
    assert hp - run_effects(state, [explicit]).state.units[U2].hp == 3


@pytest.mark.parametrize("core", ["rule_change", "rule_rewrite"])
def test_lasting_legendary_mana_candidates_are_scaled(library: ContentLibrary, core: str) -> None:
    """X10-3c：常駐類傳說的候選法力（換算前 1、4、8、12）× quantity_scale。"""
    scale = library.ruleset.core.quantity_scale
    allowed = {1 * scale, 4 * scale, 8 * scale, 12 * scale}
    made = [
        compose_legendary(seed, library, tier=1 + seed % 3, cores=(core,)) for seed in range(12)
    ]
    skills = [s for s in made if s is not None]
    assert skills
    assert all(s.cost.mana in allowed for s in skills), [s.cost.mana for s in skills]
