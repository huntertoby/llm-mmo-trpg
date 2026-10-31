"""BAL-12c 套用 BAL-12b（``docs/design/06-技能.md`` 6.34.4／6.34.6「BAL-12b 定」；量測見
``docs/phases/BAL-12b報告.md``）：完整技能大幅超過時停下、完整技能的修正細階梯、輕巧在 AP 1 時改減
冷卻或資源、延長與範圍的對象放寬、觸發效果 +1 固定值。"""

from __future__ import annotations

import dataclasses

import pytest

from tests.engine.helpers import library
from trpg.skillgen.complete import complete_gain_permille, complete_strength

# ---------------------------------------------------------------------------
# 1. 完整技能
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", ["skill_bloodlust", "skill_dread_gaze", "skill_riposte"])
def test_complete_stops_below_120_instead_of_overshooting_200(skill_id: str) -> None:
    """一步就會超過 +200‰ 的（現狀 +222～500‰）停在 +120‰ 以下最接近的一階。"""
    lib = library()
    before = lib.skills[skill_id]
    gain = complete_gain_permille(before, complete_strength(lib, before), lib)
    assert 0 <= gain < lib.flash.rules.complete.budget_permille


def test_complete_small_overshoot_is_still_accepted() -> None:
    """+150～200‰ 照舊接受（火球骰子一階 +166‰）。"""
    lib = library()
    before = lib.skills["skill_fire_bolt"]
    gain = complete_gain_permille(before, complete_strength(lib, before), lib)
    rules = lib.flash.rules.complete
    assert rules.cap_permille < gain <= (rules.stop_over_permille or 0)


def test_complete_stop_rule_is_data() -> None:
    """省略 ``stop_over_permille`` 時回到舊行為（接受超過）。"""
    lib = library()
    rules = lib.flash.rules
    old = rules.complete.model_copy(update={"stop_over_permille": None, "modifier_step": None})
    flash = lib.flash.model_copy(update={"rules": rules.model_copy(update={"complete": old})})
    lib2 = dataclasses.replace(lib, flash=flash)
    before = lib.skills["skill_bloodlust"]
    assert complete_gain_permille(before, complete_strength(lib2, before), lib2) > 200


@pytest.mark.parametrize("skill_id", ["skill_war_avatar", "skill_rune_resonance"])
def test_complete_modifier_uses_fine_ladder(skill_id: str) -> None:
    """修正幅度每 5‰：原本一格 25‰ 會超過上限的修正型被動，現在停在 +150‰ 以內。"""
    lib = library()
    before = lib.skills[skill_id]
    after = complete_strength(lib, before)
    gain = complete_gain_permille(before, after, lib)
    assert lib.flash.rules.complete.budget_permille <= gain <= lib.flash.rules.complete.cap_permille
    values = [m.change.damage_permille for m in after.modifiers if m.change.damage_permille]
    step = lib.flash.rules.complete.modifier_step
    assert step is not None and values and all(v % step == 0 for v in values)
