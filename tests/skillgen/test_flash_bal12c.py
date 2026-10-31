"""BAL-12c 套用 BAL-12b（``docs/design/06-技能.md`` 6.34.4／6.34.6「BAL-12b 定」；量測見
``docs/phases/BAL-12b報告.md``）：完整技能大幅超過時停下、完整技能的修正細階梯、輕巧在 AP 1 時改減
冷卻或資源、延長與範圍的對象放寬、觸發效果 +1 固定值。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.flash_templates import FlashTemplate
from trpg.content.skills import SkillDef
from trpg.skillgen.complete import complete_gain_permille, complete_strength
from trpg.skillgen.flash_offer import FlashRequest, try_variation
from trpg.skillgen.flash_ops import FLASH_OPS
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage

type Draft = tuple[dict[str, Any], list[dict[str, Any]]]


def _template(template_id: str) -> FlashTemplate:
    found = library().flash.minor_template(template_id)
    assert found is not None
    return found


def _variation(template_id: str) -> Variation:
    template = _template(template_id)
    return Variation(source="minor", template=template_id, category=template.category)


def _drafts(skill: SkillDef, template_id: str) -> list[Draft]:
    template = _template(template_id)
    return FLASH_OPS[template.op](skill, template, _variation(template_id), library())


def _option(skill: SkillDef, template_id: str) -> bool:
    """這招在第 1 次閃現（自己的階級）能不能出這個模板的合法選項。"""
    state = acquire(skill.id).model_copy(update={"used": True})
    request = FlashRequest(skill, state, SkillUsage(), 1, tier=skill.tier)
    return try_variation(library(), request, _variation(template_id)) is not None


def _builtin(predicate: Callable[[SkillDef], bool]) -> list[SkillDef]:
    return [s for s in sorted(library().skills.values(), key=lambda s: s.id) if predicate(s)]


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


# ---------------------------------------------------------------------------
# 2. 輕巧在 AP 1 時改減冷卻或資源
# ---------------------------------------------------------------------------


def _ap1(skill: SkillDef) -> bool:
    return skill.kind == "active" and (skill.ap_cost or 1) == 1 and skill.trap is None


def test_light_at_ap1_cuts_cooldown_or_resource_by_one_keeping_one() -> None:
    skills = _builtin(lambda s: _ap1(s) and (s.cost.cooldown or 0) > 1)
    assert skills
    for skill in skills:
        drafts = _drafts(skill, "cost_light")
        assert drafts, skill.id
        for base, _ in drafts:
            assert base.get("ap_cost") in (None, 1)
            before = skill.cost.model_dump(mode="json")
            changed = {k: v for k, v in base["cost"].items() if v != before.get(k)}
            assert len(changed) == 1, (skill.id, changed)
            ((field, value),) = changed.items()
            assert field in ("cooldown", "mana", "stamina")
            assert value == before[field] - 1 >= 1


def test_light_at_ap1_without_anything_to_cut_is_not_offered() -> None:
    skills = _builtin(
        lambda s: (
            _ap1(s)
            and (s.cost.cooldown or 0) <= 1
            and (s.cost.mana or 0) <= 1
            and (s.cost.stamina or 0) <= 1
        )
    )
    assert skills
    assert all(_drafts(s, "cost_light") == [] for s in skills)


def test_light_at_ap1_gives_legal_options() -> None:
    """AP 1 的主動技（召喚、工具技等）現在拿得到合法的輕巧（BAL-12b 量測約 40 列可救）。"""
    skills = _builtin(lambda s: _ap1(s) and (s.cost.cooldown or 0) > 1)
    assert sum(1 for s in skills if _option(s, "cost_light")) >= 5
