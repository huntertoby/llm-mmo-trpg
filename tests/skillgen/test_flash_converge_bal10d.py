"""BAL-10d 收束（``docs/design/06-技能.md`` 6.34.4「收束」「收回家族」；玩法決定 #74、#75）。

收成單體、縮小一級；以自己為中心的形狀改射程 1；最小一級不出；沒有威力不出；單發上限截斷改減費用
（減不動不出）；兩種練法（先收束 vs 先擴範圍再收束）預算守恆。"""

from __future__ import annotations

import dataclasses
from fractions import Fraction
from functools import cache

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import apply_variation, at_role_tier, derive_chain
from trpg.skillgen.flash_offer import FlashRequest, UsageSource, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.flash_trade import (
    TRADES,
    cap_points,
    has_power,
    target_power,
)
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

SINGLE = "converge_single"
STEP = "converge_step"
BONUS = 40


@cache
def lib() -> ContentLibrary:
    return library()


def _variation(template: str) -> Variation:
    found = lib().flash.minor_template(template)
    assert found is not None
    return Variation(source="minor", template=template, category=found.category)


def _apply(
    skill: SkillDef, template: str, library_: ContentLibrary | None = None
) -> SkillDef | None:
    return apply_variation(library_ or lib(), skill, _variation(template), bonus=BONUS, rng=Rng(1))


def _core(skill: SkillDef, library_: ContentLibrary | None = None) -> Fraction:
    return max(target_power(skill, library_ or lib()).values())


def _sound(before: SkillDef, after: SkillDef) -> None:
    """合法、預算窗內、強度下限不低於收束前、單發威力變高。"""
    assert not validate_skill(after, lib()), validate_skill(after, lib())
    assert skill_budget(after, lib()).ok
    assert budget_power(after, lib()) >= budget_power(before, lib())
    assert _core(after) > _core(before)


def _with_cap(permille: int) -> ContentLibrary:
    base = lib()
    rules = base.flash.rules.model_copy(update={"single_hit_cap_permille": permille})
    return dataclasses.replace(base, flash=base.flash.model_copy(update={"rules": rules}))


# ---------------------------------------------------------------------------
# 兩種形狀
# ---------------------------------------------------------------------------


def test_converge_templates_are_area_minor_from_tier_one() -> None:
    for template in (SINGLE, STEP):
        found = lib().flash.minor_template(template)
        assert found is not None
        assert (found.category, found.prefix_zh, found.min_tier) == ("area", "收束", 1)
        assert found.op in TRADES
    assert lib().flash.rules.single_hit_cap_permille == 3000


def test_converge_single_turns_an_area_into_one_target_keeping_the_range() -> None:
    skill = lib().skills["skill_tempest"]  # 3×3、射程 4、範圍骨架
    done = _apply(skill, SINGLE)
    assert done is not None
    assert done.shape.type == "single" and done.shape.range == 4
    assert done.skeleton in ("strike", "combo")  # 範圍骨架不允許單體
    _sound(skill, done)
    # 3×3（2000‰）收成單體（1000‰）：單發約 2 倍（再加這次的 +40‰）
    assert _core(done) >= 2 * _core(skill) * Fraction(9, 10)


def test_converge_single_from_a_line_uses_its_length_as_range() -> None:
    skill = lib().skills["skill_wind_blade"]  # 直線 4
    done = _apply(skill, SINGLE)
    assert done is not None
    assert done.shape.type == "single" and done.shape.range == skill.shape.size
    _sound(skill, done)


def test_converge_step_square_to_cross_and_line_minus_one() -> None:
    tempest = lib().skills["skill_tempest"]
    cross = _apply(tempest, STEP)
    assert cross is not None
    assert (cross.shape.type, cross.shape.range) == ("cross", tempest.shape.range)
    _sound(tempest, cross)
    blade = lib().skills["skill_wind_blade"]
    shorter = _apply(blade, STEP)
    assert shorter is not None
    assert shorter.shape.type == "line"
    assert shorter.shape.size == (blade.shape.size or 0) - 1
    _sound(blade, shorter)


@pytest.mark.parametrize("skill_id", ["skill_whirlwind", "skill_sanctuary"])
def test_self_centered_shapes_become_range_one(skill_id: str) -> None:
    skill = lib().skills[skill_id]  # 環形（傷害）／範圍光環（治療）
    assert skill.shape.type in ("ring", "allies_in_radius")
    done = _apply(skill, SINGLE)
    assert done is not None
    assert (done.shape.type, done.shape.range) == ("single", 1)
    _sound(skill, done)


def test_push_distance_is_kept() -> None:
    skill = lib().skills["skill_hurricane_push"]
    done = _apply(skill, STEP)
    assert done is not None
    before = [e.distance for e in skill.effects if e.type == "push"]
    after = [e.distance for e in done.effects if e.type == "push"]
    assert before == after == [2]


# ---------------------------------------------------------------------------
# 不出
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", ["skill_cleave", "skill_whirlwind", "skill_chain_lightning"])
def test_smallest_step_is_not_offered(skill_id: str) -> None:
    """錐形 2 已是最小；環形、連鎖沒有「縮小一級」。"""
    skill = lib().skills[skill_id]
    template = lib().flash.minor_template(STEP)
    assert template is not None
    assert TRADES[STEP].remove(skill, template, _variation(STEP), lib()) == []
    assert _apply(skill, STEP) is None


def test_single_target_skills_have_nothing_to_converge() -> None:
    single = next(
        s
        for s in sorted(lib().skills.values(), key=lambda s: s.id)
        if s.kind == "active" and s.shape.type == "single" and has_power(s, lib())
    )
    assert _apply(single, SINGLE) is None
    assert _apply(single, STEP) is None


def test_skills_without_power_are_not_offered() -> None:
    """只施加狀態、只造表面的範圍技沒有威力可換，兩種都不出。"""
    shapes = {"line", "cone", "cross", "square3", "ring", "chain", "allies_in_radius"}
    powerless = [
        s
        for s in sorted(lib().skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.trap is None
        and s.shape.type in shapes
        and not has_power(s, lib())
    ]
    assert powerless
    for skill in powerless[:6]:
        for template in (SINGLE, STEP):
            found = lib().flash.minor_template(template)
            assert found is not None
            assert TRADES[template].remove(skill, found, _variation(template), lib()) == []


# ---------------------------------------------------------------------------
# 單發上限
# ---------------------------------------------------------------------------


def test_cap_truncates_power_and_cuts_cost() -> None:
    skill = lib().skills["skill_whirlwind"]
    free = _apply(skill, SINGLE)
    capped_lib = _with_cap(1000)
    capped = _apply(skill, SINGLE, capped_lib)
    assert free is not None and capped is not None
    cap = cap_points(skill_budget(capped, capped_lib), capped_lib)
    assert _core(free, capped_lib) > cap  # 不設上限時會超過
    assert _core(capped, capped_lib) <= cap
    # 超過的預算改成減費用：冷卻（依 cost_cuts 的順序）比沒截斷時低，其他欄位只減不加
    assert (capped.cost.cooldown or 0) < (free.cost.cooldown or 0)
    assert (capped.cost.mana or 0) <= (free.cost.mana or 0)
    assert (capped.ap_cost or 0) <= (free.ap_cost or 0)
    assert not validate_skill(capped, capped_lib)


def test_cap_without_cost_to_cut_is_not_offered() -> None:
    skill = lib().skills["skill_all_in_chant"]
    assert _apply(skill, SINGLE) is not None
    assert _apply(skill, SINGLE, _with_cap(1000)) is None


def test_default_cap_does_not_bind_on_builtin_converge() -> None:
    """初值 3 倍：內建技能收束一次都在上限內（上限是安全欄，不是常態）。"""
    for skill in sorted(lib().skills.values(), key=lambda s: s.id):
        done = _apply(skill, SINGLE)
        if done is None:
            continue
        assert _core(done) <= cap_points(skill_budget(done, lib()), lib())


# ---------------------------------------------------------------------------
# 兩種練法：預算守恆
# ---------------------------------------------------------------------------


def _chain(skill: SkillDef, plan: list[tuple[int, str]], tier: int) -> SkillDef:
    records = tuple(FlashRecord(nth=n, variation=_variation(t)) for n, t in plan)
    state = SkillFlash(base_id=skill.id, records=records)
    return derive_chain(lib(), skill, state, 7, tier)[-1]


CHARGE = "cost_charge"
EARLY_PLANS = {
    # 直線 4：第 1 次縮小一級、第 2 次收成單體、第 4 次蓄力（冷卻已到上限，第 5 次蓄力出不來）
    "skill_wind_blade": [(1, STEP), (2, SINGLE), (4, CHARGE)],
    # 錐形 2 已是最小：第 1 次收成單體、第 4、5 次蓄力
    "skill_cleave": [(1, SINGLE), (4, CHARGE), (5, CHARGE)],
}


@pytest.mark.parametrize("skill_id", sorted(EARLY_PLANS))
def test_expanding_first_does_not_beat_converging_first(skill_id: str) -> None:
    """(a) 先收束＋蓄力 vs (b) 第 1、2 次擴範圍、第 4 次收束、第 5 次蓄力：(b) 的單發不超過 (a)，
    兩者都不超過單發上限（擴範圍時總點數不變、每個目標分到的變少，收束時再全部換回來）。"""
    skill = lib().skills[skill_id]
    tier = 3
    early = _chain(skill, EARLY_PLANS[skill_id], tier)
    late = _chain(skill, [(1, "area_plus"), (2, "area_plus"), (4, SINGLE), (5, CHARGE)], tier)
    assert early.shape.type == late.shape.type == "single"
    assert _core(late) <= _core(early)
    origin = at_role_tier(lib(), skill, tier)
    cap = cap_points(skill_budget(origin, lib()), lib())
    assert _core(early) <= cap and _core(late) <= cap


# ---------------------------------------------------------------------------
# 相容：出題、確定性
# ---------------------------------------------------------------------------


def test_converge_is_a_candidate_of_the_area_category_last() -> None:
    """出題的候選（範圍類）有兩種收束，排在範圍類最後（不搶既有模板的順位）。"""
    skill = lib().skills["skill_tempest"]
    state = acquire(skill.id).model_copy(update={"used": True})
    request = FlashRequest(skill, state, SkillUsage(), 11, category="area", tier=2)
    ranked = [v.template for v in UsageSource().ranked(lib(), request, "area", skill)]
    assert ranked[-2:] == [SINGLE, STEP]
    offer = make_offer(lib(), request)
    assert offer.options and all(o.variation.category == "area" for o in offer.options)


def test_converge_shows_up_when_earlier_area_templates_do_not_fit() -> None:
    """範圍 +1、距離 +1、換形狀都套不上的範圍技（範圍光環半徑 3 的治療），指定範圍類時收成單體
    會出現。"""
    skill = lib().skills["skill_sanctuary"]
    grown = skill.model_copy(update={"shape": skill.shape.model_copy(update={"radius": 3})})
    state = acquire(skill.id).model_copy(update={"used": True})
    request = FlashRequest(grown, state, SkillUsage(), 11, category="area", tier=1)
    offer = make_offer(lib(), request)
    assert SINGLE in [o.variation.template for o in offer.options]


def test_converge_is_deterministic() -> None:
    skill = lib().skills["skill_tempest"]
    assert _apply(skill, SINGLE) == _apply(skill, SINGLE)
    assert _apply(skill, STEP) == _apply(skill, STEP)


# ---------------------------------------------------------------------------
# BAL-10d2
# ---------------------------------------------------------------------------


def test_converge_target_ratio_can_reroll_like_other_flashes() -> None:
    """④ 目標比例 ＝ max(收束前比例＋40‰, 一般重調的隨機目標)：不同亂數抽到的比例會不同，
    但都不低於收束前的強度。"""
    skill = lib().skills["skill_tempest"]
    ratios = []
    for seed in range(1, 13):
        done = apply_variation(lib(), skill, _variation(SINGLE), bonus=BONUS, rng=Rng(seed))
        assert done is not None
        assert budget_power(done, lib()) >= budget_power(skill, lib())
        ratios.append(skill_budget(done, lib()).ratio)
    assert max(ratios) - min(ratios) >= Fraction(5, 100)
