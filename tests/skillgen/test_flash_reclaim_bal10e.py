"""BAL-10e 收回家族（``docs/design/06-技能.md`` 6.34.4「收回家族」；玩法決定 #75）。

精煉（拿掉附帶狀態、第二元素、第二關鍵字、接續段；多段併一段）、合體（召喚隻數 −1）、專注（觸發範圍
收回、觸發條件收緊；修正型被動的作用範圍與條件）、陷阱與地面格的收束。共同：只拿身上真的有的，拿掉
的預算＋40‰ 換核心數值，強度不低於收回前，單發上限照收束。"""

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
from trpg.skillgen.flash_category import allowed_categories
from trpg.skillgen.flash_derive import apply_variation, at_tier
from trpg.skillgen.flash_offer import FlashRequest, UsageSource
from trpg.skillgen.flash_ops import Draft
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.flash_trade import TRADES, cap_points, converge_gain, target_power
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

BONUS = 40
RECLAIMS = {
    "refine": ("element", "精煉"),
    "refine_merge": ("combo", "精煉"),
    "fuse": ("area", "合體"),  # BAL-10e2：數量換強度，歸範圍（輔助類只收輔助技）
    "focus_range": ("trigger", "專注"),
    "focus_condition": ("trigger", "專注"),
    "focus_mod_range": ("modifier", "專注"),
    "focus_mod_condition": ("modifier", "專注"),
}


@cache
def lib() -> ContentLibrary:
    return library()


def _variation(template: str) -> Variation:
    found = lib().flash.minor_template(template)
    assert found is not None
    return Variation(source="minor", template=template, category=found.category)


def _apply(
    skill: SkillDef, template: str, library_: ContentLibrary | None = None, *, seed: int = 1
) -> SkillDef | None:
    return apply_variation(
        library_ or lib(), skill, _variation(template), bonus=BONUS, rng=Rng(seed)
    )


def _drafts(skill: SkillDef, template: str) -> list[Draft]:
    found = lib().flash.minor_template(template)
    assert found is not None
    return list(TRADES[found.op].remove(skill, found, _variation(template), lib()))


def _core(skill: SkillDef) -> Fraction:
    return max(target_power(skill, lib()).values(), default=Fraction(0))


def _sound(before: SkillDef, after: SkillDef) -> None:
    """合法、預算窗內、強度不低於收回前。"""
    assert not validate_skill(after, lib()), validate_skill(after, lib())
    assert skill_budget(after, lib()).ok
    assert budget_power(after, lib()) >= budget_power(before, lib())


def _flashed(base: str, template: str, *, tier: int = 1, bonus: int = BONUS) -> SkillDef:
    """先閃一次做出「可以收回的部分」（連打、雙生、觸發範圍 +1、作用範圍 +1）。"""
    found = lib().flash.minor_template(template)
    variation = (
        Variation(source="major", template=template, category="deepen")
        if found is None
        else Variation(source="minor", template=template, category=found.category)
    )
    skill = at_tier(lib().skills[base], tier)
    done = apply_variation(lib(), skill, variation, bonus=bonus, rng=Rng(11))
    assert done is not None, (base, template)
    return done.model_copy(update={"budget_bonus_permille": None})


def _with_tighten(permille: int) -> ContentLibrary:
    base = lib()
    rules = base.flash.rules.model_copy(update={"tighten_permille": permille})
    return dataclasses.replace(base, flash=base.flash.model_copy(update={"rules": rules}))


def _with_cap(permille: int) -> ContentLibrary:
    base = lib()
    rules = base.flash.rules.model_copy(update={"single_hit_cap_permille": permille})
    return dataclasses.replace(base, flash=base.flash.model_copy(update={"rules": rules}))


# ---------------------------------------------------------------------------
# 登錄
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template", sorted(RECLAIMS))
def test_reclaim_templates_follow_the_design_table(template: str) -> None:
    found = lib().flash.minor_template(template)
    assert found is not None
    assert (found.category, found.prefix_zh, found.min_tier) == (*RECLAIMS[template], 1)
    assert found.op in TRADES


@pytest.mark.parametrize("template", sorted(RECLAIMS))
def test_reclaims_come_last_in_their_category(template: str) -> None:
    """收回不搶既有模板的順位（選項混合照 6.34.3，收回不擠滿選項）。"""
    found = lib().flash.minor_template(template)
    assert found is not None
    same = [t.id for t in lib().flash.minor if t.category == found.category]
    reclaims = [t.id for t in lib().flash.minor if t.category == found.category and t.op in TRADES]
    assert same[-len(reclaims) :] == reclaims


# ---------------------------------------------------------------------------
# 精煉
# ---------------------------------------------------------------------------


def test_refine_drops_the_status_and_powers_up_the_main_hit() -> None:
    skill = lib().skills["skill_fire_bolt"]  # 火焰傷害 ＋ 燃燒
    done = _apply(skill, "refine")
    assert done is not None
    assert [e.type for e in done.effects] == ["damage"]
    _sound(skill, done)
    assert _core(done) > _core(skill)


def test_refine_drops_a_second_element() -> None:
    skill = lib().skills["skill_marrow_thorn"]  # 物理 ＋ 帶條件的毒傷
    done = _apply(skill, "refine")
    assert done is not None
    assert len(done.effects) == 1 and done.effects[0].element == skill.effects[0].element
    _sound(skill, done)


def test_refine_drops_the_followup() -> None:
    skill = lib().skills["skill_death_spiral"]  # 單段傷害 ＋ 接續段
    assert skill.followup is not None
    done = _apply(skill, "refine")
    assert done is not None
    assert done.followup is None
    _sound(skill, done)
    assert _core(done) > _core(skill)


def test_refine_lets_a_control_skill_become_a_strike() -> None:
    skill = lib().skills["skill_flash_freeze"]  # 控制骨架：狀態 ＋ 冰傷
    done = _apply(skill, "refine")
    assert done is not None
    assert all(e.type != "apply_status" for e in done.effects)
    assert done.skeleton in (skill.skeleton, "strike", "combo")
    _sound(skill, done)


@pytest.mark.parametrize(
    "skill_id",
    ["skill_all_in", "skill_cinder_mine", "skill_taunting_roar"],  # 沒有附帶效果／陷阱／沒有威力
)
def test_refine_needs_something_to_drop(skill_id: str) -> None:
    assert _drafts(lib().skills[skill_id], "refine") == []


def test_refine_merge_turns_two_hits_into_one() -> None:
    skill = _flashed("skill_all_in", "multi_hit")
    assert sum(e.type == "damage" for e in skill.effects) == 2
    done = _apply(skill, "refine_merge")
    assert done is not None
    assert sum(e.type == "damage" for e in done.effects) == 1
    _sound(skill, done)
    assert _core(done) >= _core(skill)


def test_refine_merge_leaves_conditional_hits_to_refine() -> None:
    skill = lib().skills["skill_marrow_thorn"]  # 第二段帶條件、不同元素：不是「多段」
    assert _drafts(skill, "refine_merge") == []


# ---------------------------------------------------------------------------
# 合體
# ---------------------------------------------------------------------------


def test_fuse_turns_twin_summons_into_one_tougher() -> None:
    twin = _flashed("skill_summon_spirit", "summon_count", tier=2, bonus=3 * BONUS)
    before = next(e for e in twin.effects if e.type == "summon")
    assert before.count == 2
    done = _apply(twin, "fuse")
    assert done is not None
    after = next(e for e in done.effects if e.type == "summon")
    assert after.count in (None, 1) and after.power_permille is None
    assert (after.max_hp_permille or 0) > (before.max_hp_permille or 0)
    _sound(twin, done)


def test_fuse_is_offered_in_the_area_category_for_summons() -> None:
    """BAL-10e2：召喚技出題時範圍類可以出合體。"""
    twin = _flashed("skill_summon_spirit", "summon_count", tier=2, bonus=3 * BONUS)
    assert "area" in allowed_categories(lib().flash, twin, major=False)
    request = FlashRequest(twin, acquire(twin.id), SkillUsage(), 1, tier=2)
    ranked = [v.template for v in UsageSource().ranked(lib(), request, "area", twin)]
    assert "fuse" in ranked


def test_tightening_counts_as_a_fixed_budget_cut() -> None:
    """BAL-10e2：條件收緊一級固定視為拿掉 ``tighten_permille``，加 +40‰ 一起換觸發效果。"""
    assert lib().flash.rules.tighten_permille == 100
    skill = lib().skills["skill_twin_strike"]
    loose = _with_tighten(0)
    for seed in range(1, 6):
        done = _apply(skill, "focus_condition", seed=seed)
        plain = _apply(skill, "focus_condition", loose, seed=seed)
        assert done is not None and plain is not None
        assert skill_budget(done, lib()).ratio >= skill_budget(plain, loose).ratio
    done = _apply(skill, "focus_condition", seed=1)
    assert done is not None
    before = skill_budget(skill, lib())
    after = skill_budget(done, lib())
    # 收緊後的總點數至少是收緊前 ＋ 一份 140‰（佔同階可用預算）
    plain_budget = before.tier_budget * before.ap_coefficient
    wanted = before.total + plain_budget * Fraction(
        1000 + before.allowance_permille, 1000
    ) * Fraction(140, 1000)
    assert after.total >= wanted * Fraction(95, 100)


def test_fuse_needs_two_summons() -> None:
    assert _drafts(lib().skills["skill_summon_spirit"], "fuse") == []


# ---------------------------------------------------------------------------
# 專注
# ---------------------------------------------------------------------------


def test_focus_hit_by_attack_becomes_hit_by_melee() -> None:
    skill = lib().skills["skill_reflex_ward"]
    assert skill.reaction is not None and skill.reaction.event == "hit_by_attack"
    done = _apply(skill, "focus_condition")
    assert done is not None
    assert done.reaction is not None and done.reaction.event == "hit_by_melee"
    _sound(skill, done)


def test_focus_adds_a_condition_and_powers_up_the_trigger() -> None:
    skill = lib().skills["skill_twin_strike"]  # 每命中 2 次：傷害，沒有條件
    assert skill.condition is None
    done = _apply(skill, "focus_condition")
    assert done is not None
    assert done.condition is not None
    _sound(skill, done)
    assert _core(done) > _core(skill)


def test_focus_tightens_a_hp_threshold() -> None:
    skill = lib().skills["skill_second_wind"]  # 自身血量低於 50%
    assert skill.condition is not None and skill.condition.permille == 500
    done = _apply(skill, "focus_condition")
    assert done is not None
    assert done.condition is not None and done.condition.permille == 350
    _sound(skill, done)


def test_focus_status_conditions_are_already_tight() -> None:
    skill = lib().skills["skill_mark_detonation"]  # 目標帶標記
    assert _drafts(skill, "focus_condition") == []


def test_focus_range_takes_back_a_trigger_range_step() -> None:
    plain = lib().skills["skill_thorn_skin"]
    assert plain.trigger is not None and plain.trigger.max_distance == 1
    assert _drafts(plain, "focus_range") == []  # 已是最小
    wider = _flashed("skill_thorn_skin", "trigger_range")
    assert wider.trigger is not None and wider.trigger.max_distance == 2
    done = _apply(wider, "focus_range")
    assert done is not None
    assert done.trigger is not None and done.trigger.max_distance == 1
    _sound(wider, done)


def test_focus_modifier_condition_raises_the_magnitude() -> None:
    skill = lib().skills["skill_attack_mastery"]  # 普攻傷害 +5%，沒有條件
    done = _apply(skill, "focus_mod_condition")
    assert done is not None
    assert done.modifiers[0].condition is not None
    before = skill.modifiers[0].change.damage_permille or 0
    assert (done.modifiers[0].change.damage_permille or 0) > before
    _sound(skill, done)


def test_focus_modifier_range_removes_the_extra_area_rule() -> None:
    wider = _flashed("skill_war_avatar", "mod_range")
    assert len(wider.modifiers) == 2
    done = _apply(wider, "focus_mod_range")
    assert done is not None
    assert len(done.modifiers) == 1
    _sound(wider, done)


def test_focus_modifier_range_keeps_the_last_rule() -> None:
    skill = lib().skills["skill_lingering_roar"]  # 只有一條「範圍 +1」
    assert _drafts(skill, "focus_mod_range") == []


# ---------------------------------------------------------------------------
# 陷阱、地面格的收束
# ---------------------------------------------------------------------------


def test_trap_converges_to_one_tile() -> None:
    skill = lib().skills["skill_cinder_mine"]  # 觸發範圍十字
    assert skill.trap is not None and skill.trap.shape == "cross"
    done = _apply(skill, "converge_single")
    assert done is not None
    assert done.trap is not None and done.trap.shape == "single"
    assert done.shape == skill.shape  # 放置的形狀不動
    _sound(skill, done)
    assert _core(done) > _core(skill)
    assert _drafts(skill, "converge_step") == []  # 十字再小就是單格


def test_trap_square_steps_down_to_cross() -> None:
    plain = lib().skills["skill_cinder_mine"]
    assert plain.trap is not None
    square = plain.model_copy(update={"trap": plain.trap.model_copy(update={"shape": "square3"})})
    drafts = _drafts(square, "converge_step")
    assert len(drafts) == 1
    base, _ = drafts[0]
    assert base["trap"]["shape"] == "cross"


def test_single_tile_traps_do_not_converge() -> None:
    skill = lib().skills["skill_bear_trap"]
    assert _drafts(skill, "converge_single") == [] and _drafts(skill, "converge_step") == []


def test_zone_power_is_tuned_through_the_nested_effects() -> None:
    skill = lib().skills["skill_fire_wall"]  # 持續區域裡 1d6 火焰
    base = skill.model_dump(mode="json")
    effects = [e.model_dump(mode="json", exclude_none=True) for e in skill.effects]
    extra, knobs = converge_gain(base, effects, lib())
    assert extra and extra[0] is effects[0]["effects"][0]  # 同一批物件，重調會寫回草稿
    assert [k.field for k in knobs] == ["dice"]
    assert converge_gain(base, [{"type": "damage", "dice": "1d6"}], lib()) == ([], [])


# ---------------------------------------------------------------------------
# 單發上限、確定性
# ---------------------------------------------------------------------------


def test_cap_is_shared_with_converge() -> None:
    skill = lib().skills["skill_death_spiral"]
    tight = _with_cap(1000)
    done = _apply(skill, "refine", tight)
    if done is not None:
        cap = cap_points(skill_budget(done, tight), tight)
        assert max(target_power(done, tight).values()) <= cap


@pytest.mark.parametrize("template", ["refine", "focus_condition", "focus_mod_condition"])
def test_same_seed_same_result(template: str) -> None:
    skill = {
        "refine": "skill_fire_bolt",
        "focus_condition": "skill_twin_strike",
        "focus_mod_condition": "skill_attack_mastery",
    }[template]
    first = _apply(lib().skills[skill], template, seed=5)
    assert first is not None
    assert _apply(lib().skills[skill], template, seed=5) == first
