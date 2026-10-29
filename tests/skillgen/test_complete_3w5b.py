"""Phase 3W-5b：完整技能的 +120‰ 實際加上去（06 6.34.6，玩法 PM 1752ae6c）。

每種結構（傷害、召喚、姿態、陷阱、被動、反應、沒有數值旋鈕）做成完整技能後，預算分數
（:func:`~trpg.skillgen.complete.complete_power`）至少 +120‰；做不到的停在上限（再也加不動）。
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.roguelite.offers import COMPLETE_SUFFIX, as_complete
from trpg.skillgen.complete import (
    _climb,
    _next_step,
    complete_gain_permille,
    complete_power,
    complete_strength,
)
from trpg.skillgen.flash import with_budget_bonus
from trpg.skillgen.validate import validate_skill

GAIN = 120


def _done(skill_id: str) -> tuple[SkillDef, SkillDef]:
    lib = library()
    before = lib.skills[skill_id]
    return before, complete_strength(lib, before)


@pytest.mark.parametrize(
    "skill_id",
    [
        "skill_fire_bolt",  # 傷害（骰子）
        "skill_bear_trap",  # 陷阱
        "skill_cinder_mine",  # 陷阱
        "skill_bloodlust",  # 被動
        "skill_riposte",  # 反應
        "skill_counterspell",  # 反應
    ],
)
def test_structures_with_number_knobs_gain_at_least_120(skill_id: str) -> None:
    before, after = _done(skill_id)
    lib = library()
    assert complete_gain_permille(before, after, lib) >= GAIN
    assert after.budget_bonus_permille == lib.flash.rules.complete.budget_permille == GAIN
    assert validate_skill(after, lib) == []
    assert (after.kind, after.skeleton, after.shape) == (before.kind, before.skeleton, before.shape)


def test_summon_gets_more_summon_hp_and_damage() -> None:
    before, after = _done("skill_summon_fire_spirit")
    (summon,) = [e for e in after.effects if e.type == "summon"]
    assert summon.power_permille is not None and summon.power_permille > 1000
    assert complete_gain_permille(before, after, library()) >= GAIN
    assert validate_skill(after, library()) == []


@pytest.mark.parametrize("skill_id", ["skill_bulwark_stance", "skill_fury_stance"])
def test_stance_gets_a_bigger_magnitude(skill_id: str) -> None:
    before, after = _done(skill_id)
    (effect,) = after.effects
    assert effect.magnitude_permille is not None and effect.magnitude_permille > 1000
    assert complete_gain_permille(before, after, library()) >= GAIN
    assert validate_skill(after, library()) == []


def test_no_number_knob_cuts_the_cost_instead() -> None:
    """沒有數值旋鈕（只有冷卻與法力）：依 cost_cuts 的順序減冷卻、再減法力，每項最少留 1。"""
    before, after = _done("skill_rune_burst")
    assert before.cost.cooldown == 3 and before.cost.mana == 8
    assert after.effects == before.effects
    assert after.cost.cooldown == 1 and after.cost.mana is not None and after.cost.mana >= 1
    assert complete_gain_permille(before, after, library()) >= GAIN
    assert validate_skill(after, library()) == []


@pytest.mark.parametrize(
    "skill_id",
    [
        "skill_rune_breaker",  # 修正型被動：沒有幅度、沒有代價
        "skill_thorn_skin",  # 被動：骰子再大一格就超出預算，也沒有代價
        "skill_quake_topple",  # 主動：沒有數值旋鈕，代價減到每項 1 還差一點
    ],
)
def test_skills_that_cannot_reach_120_stop_at_their_cap(skill_id: str) -> None:
    """達不到 +120‰ 時停在上限：再也找不到能加的一步（數值、參數、代價都試過），而且不比原本弱。"""
    before, after = _done(skill_id)
    lib = library()
    gain = complete_gain_permille(before, after, lib)
    assert 0 <= gain < GAIN
    target = complete_power(before, lib) * (1000 + GAIN) / 1000
    assert _next_step(lib, lib.flash.rules.complete, after, target) is None


def test_as_complete_renames_library_skills_and_keeps_the_numbers() -> None:
    lib = library()
    skill = lib.skills["skill_summon_fire_spirit"]
    done = as_complete(lib, skill)
    assert done.id == f"{skill.id}{COMPLETE_SUFFIX}"
    assert done.effects == complete_strength(lib, skill).effects


def test_complete_strength_is_deterministic() -> None:
    lib = library()
    skill = lib.skills["skill_fire_bolt"]
    assert complete_strength(lib, skill) == complete_strength(lib, skill)


@pytest.mark.parametrize("skill_id", ["skill_cinder_mine", "skill_chain_lightning", "skill_all_in"])
def test_gain_stays_under_150_when_a_finer_knob_can_fill_in(skill_id: str) -> None:
    """+150‰ 上限（06 6.34.6，玩法 PM ec73486f）：骰子一階就超過時先用較細的旋鈕補（這幾招不加上限
    時是 +232／+166／+172‰）。"""
    before, after = _done(skill_id)
    assert 120 <= complete_gain_permille(before, after, library()) <= 150


def test_over_150_only_when_no_capped_path_reaches_120() -> None:
    """超過 +150‰ 的只能是「只走不超過上限的步子到不了 +120‰」的技能
    例如火球：骰子一階就是 +166‰。"""
    lib = library()
    rules = lib.flash.rules.complete
    for skill_id in ("skill_fire_bolt", "skill_ember_brand"):
        before, after = _done(skill_id)
        assert complete_gain_permille(before, after, lib) > rules.cap_permille
        base = complete_power(before, lib)
        target = base * Fraction(1000 + rules.budget_permille, 1000)
        cap = base * Fraction(1000 + rules.cap_permille, 1000)
        start = with_budget_bonus(before, rules.budget_permille)
        assert _climb(lib, rules, start, target, cap)[1] < target
