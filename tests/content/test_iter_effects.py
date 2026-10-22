"""``SkillDef.iter_effects``（Phase 3E-2a）：統一的效果走訪涵蓋巢狀效果、zone 子效果、複合第二段、
陷阱、失手反噬、變奏與修正規則。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef, walk_effect
from trpg.skillgen.combo import self_combo_reasons


def _types(skill: SkillDef, **flags: bool) -> list[str]:
    return [e.type for e in skill.iter_effects(**flags)]


def test_zone_sub_effects_are_visited() -> None:
    skill = library().skills["skill_fire_wall"]
    assert _types(skill) == ["zone", "damage"]


def test_followup_effects_only_with_the_flag() -> None:
    skill = library().skills["skill_armor_break_combo"]
    assert skill.followup is not None
    base = _types(skill)
    full = _types(skill, include_followup=True)
    assert full[: len(base)] == base
    assert len(full) > len(base)
    assert full[len(base) :] == [e.type for sub in skill.followup.effects for e in walk_effect(sub)]


def test_trap_effects_are_the_skill_effects() -> None:
    skill = library().skills["skill_bear_trap"]
    assert skill.trap is not None
    assert _types(skill)  # 觸發效果就是 effects，不需要旗標


def test_backlash_only_with_the_flag() -> None:
    skill = library().skills["skill_all_in"]
    assert skill.cost.on_miss
    assert len(_types(skill, include_backlash=True)) > len(_types(skill))


def test_modifier_hit_effects_only_with_the_flag() -> None:
    skill = library().skills["skill_rune_breaker"]
    assert len(_types(skill, include_modifiers=True)) > len(_types(skill))


def test_variant_effects_only_with_the_flag() -> None:
    skill = library().skills["skill_tidal_spear"]
    extra = [v.add_effect for v in skill.variants if v.add_effect is not None]
    swaps = [v.replace_effect for v in skill.variants if v.replace_effect is not None]
    plain = _types(skill)
    with_variants = _types(skill, include_variants=True)
    assert len(with_variants) == len(plain) + len(extra) + len(swaps)


def test_variant_added_nested_effect_is_visited() -> None:
    """變奏帶進來的擊殺時效果也要走到（R1：變奏偷帶原語）。"""
    lib = library()
    base = lib.skills["skill_tidal_spear"].model_dump(mode="json", exclude_defaults=True)
    kill = lib.skills["skill_ash_harvest"].effects[0].model_dump(mode="json", exclude_defaults=True)
    head = {k: base["variants"][0][k] for k in ("id", "name_zh", "when")}
    skill = SkillDef.model_validate(dict(base, variants=[dict(head, add_effect=kill)]))
    added = _types(skill, include_variants=True)[len(_types(skill)) :]
    assert added == ["damage", "refund_ap", "refund_cooldown"]


@pytest.mark.parametrize("skill_id", sorted(library().skills))
def test_walk_is_a_superset_of_the_plain_effects(skill_id: str) -> None:
    skill = library().skills[skill_id]
    everything = _types(
        skill,
        include_followup=True,
        include_variants=True,
        include_backlash=True,
        include_modifiers=True,
    )
    assert set(_types(skill)) <= set(everything)


def test_combo_sees_zone_sub_effects_of_the_second_stage() -> None:
    """combo.py 改走統一走訪後不會漏掉 zone 子效果（不拋錯、結果是 tuple）。"""
    lib = library()
    for skill in lib.skills.values():
        assert isinstance(self_combo_reasons(skill, lib), tuple)
