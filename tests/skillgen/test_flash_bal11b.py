"""BAL-11b 預算旋鈕套用（``docs/design/06-技能.md`` 6.34.4「BAL-11a 定」；量測見
``docs/phases/BAL-11a報告.md``）：第二關鍵字草稿修正、姿態冷卻折抵、只在閃現的細階梯。"""

from __future__ import annotations

import dataclasses
from itertools import pairwise
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.content.skills.effects import composition_rules
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import multiplier_ladder
from trpg.skillgen.flash_ops import (
    FLASH_OPS,
    MODIFIER_LADDER,
    _followup_knob,
    _graft_blocked,
    _modifier_knobs,
)
from trpg.skillgen.flash_state import Variation

KEYWORD_OPS = ("keyword_imbue", "keyword_exploit")


def _variation(template: str, keyword: str) -> Variation:
    lib = library()
    found = lib.flash.minor_template(template)
    assert found is not None
    return Variation(source="minor", template=template, category=found.category, keyword=keyword)


def _drafts(
    skill: SkillDef, template: str, keyword: str
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    lib = library()
    found = lib.flash.minor_template(template)
    assert found is not None
    return FLASH_OPS[found.op](skill, found, _variation(template, keyword), lib)


def _blocked_skills() -> list[SkillDef]:
    rules = composition_rules()
    return [
        s
        for s in sorted(library().skills.values(), key=lambda s: s.id)
        if s.kind in ("active", "passive", "reaction")
        and any(
            (r := rules.get(e.type)) is not None and (r.sole_effect or r.others_affect)
            for e in s.effects
        )
    ]


def _spell_without_damage() -> list[SkillDef]:
    return [
        s
        for s in sorted(library().skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.category == "spell"
        and all(e.type != "damage" for e in s.effects)
        and not _graft_blocked(s)
        and s.followup is None
    ]


@pytest.mark.parametrize("template", KEYWORD_OPS)
def test_sole_or_self_only_primitives_skip_keyword_templates(template: str) -> None:
    blocked = _blocked_skills()
    assert blocked, "內容裡應該有召喚、規則改變等原語的技能"
    for skill in blocked:
        assert _graft_blocked(skill)
        assert _drafts(skill, template, "ignite") == []


def test_spell_graft_damage_gets_dice_and_element() -> None:
    lib = library()
    skills = _spell_without_damage()
    assert skills
    checked = 0
    for skill in skills[:8]:
        for base, effects in _drafts(skill, "keyword_exploit", "ignite"):
            added = [e for e in effects[len(skill.effects) :] if e["type"] == "damage"]
            assert added
            for effect in added:
                assert effect["dice"] and effect["element"]
            SkillDef.model_validate({**base, "effects": effects})  # schema 合法
            checked += 1
    assert checked
    assert lib.composer.dice  # 骰子階梯存在


def test_stance_cooldown_allowance_is_small_and_capped() -> None:
    lib = library()
    allowance = lib.budget.allowance
    assert allowance.stance_cooldown_per_turn == 10
    assert allowance.stance_cooldown_cap == 50
    assert allowance.cooldown_allowance(3, stance=True) == 30
    assert allowance.cooldown_allowance(9, stance=True) == 50
    assert allowance.cooldown_allowance(3, stance=False) == 3 * allowance.cooldown_per_turn
    stance = lib.skills["skill_fury_stance"]
    with_cd = stance.model_copy(update={"cost": stance.cost.model_copy(update={"cooldown": 2})})
    parts = dict(skill_budget(with_cd, lib).allowance_parts)
    assert parts["冷卻 2 回合"] == 20


def test_mod_potency_fine_ladder_only_in_flash() -> None:
    lib = library()
    rules = [{"change": {"damage_permille": 50}}]
    _, flash = _modifier_knobs(rules, lib, op="mod_potency")
    _, plain = _modifier_knobs(rules, lib, op="")
    step = lib.flash.rules.modifier_potency_step
    assert step == 10
    assert flash[0].values == tuple(range(step, 1001, step))
    assert plain[0].values == MODIFIER_LADDER  # 升階重配、完整技能照舊


def test_followup_multiplier_fine_ladder() -> None:
    lib = library()
    name, values = _followup_knob({"type": "damage"}, lib)
    assert name == "multiplier_permille"
    base = multiplier_ladder(lib)
    assert set(base) <= set(values)
    low = [v for v in values if v < 3000]
    assert all(b - a <= lib.flash.rules.followup_multiplier_step for a, b in pairwise(low))
    off = dataclasses.replace(
        lib,
        flash=lib.flash.model_copy(
            update={"rules": lib.flash.rules.model_copy(update={"followup_multiplier_step": None})}
        ),
    )
    assert _followup_knob({"type": "damage"}, off)[1] == base
