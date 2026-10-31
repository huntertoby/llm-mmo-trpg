"""BAL-12c 套用 BAL-12b（``docs/design/06-技能.md`` 6.34.4／6.34.6「BAL-12b 定」；量測見
``docs/phases/BAL-12b報告.md``）：完整技能大幅超過時停下、完整技能的修正細階梯、輕巧在 AP 1 時改減
冷卻或資源、延長與範圍的對象放寬、觸發效果 +1 固定值。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.flash_templates import FlashTemplate
from trpg.content.skills import SkillDef
from trpg.narrative.skills import effect_summary
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.complete import complete_gain_permille, complete_strength
from trpg.skillgen.flash_offer import FlashRequest, try_variation
from trpg.skillgen.flash_ops import FLASH_OPS, _extend_wider, base_draft, trigger_fine_knobs
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.skill_tier import retier
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


# ---------------------------------------------------------------------------
# 3. 延長與範圍的對象放寬
# ---------------------------------------------------------------------------


def _summons() -> list[SkillDef]:
    return _builtin(
        lambda s: s.kind == "active" and any(e.type == "summon" and e.duration for e in s.effects)
    )


def test_extend_falls_back_to_summon_duration() -> None:
    skills = _summons()
    assert skills
    for skill in skills:
        drafts = _drafts(skill, "extend_duration")
        assert len(drafts) == 1, skill.id
        _, effects = drafts[0]
        before = [e.duration for e in skill.effects if e.type == "summon"]
        after = [e.get("duration") for e in effects if e["type"] == "summon"]
        assert after == [d + 1 if d else d for d in before]


def test_extend_obstacle_and_inscribe() -> None:
    for skill_id, kind in (
        ("skill_gear_shield_wall", "create_obstacle"),
        ("skill_hunt_sigil", "inscribe"),
    ):
        skill = library().skills[skill_id]
        (draft,) = _drafts(skill, "extend_duration")
        before = next(e.duration for e in skill.effects if e.type == kind)
        assert next(e["duration"] for e in draft[1] if e["type"] == kind) == (before or 0) + 1


def test_extend_keeps_the_old_path_when_a_status_can_extend() -> None:
    """原本的狀態、表面、區域延長得了時照舊（不另加陷阱或召喚的回合）。"""
    skill = library().skills["skill_bear_trap"]  # 定身 2 回合可以延長
    ((base, effects),) = _drafts(skill, "extend_duration")
    assert base["trap"]["rounds"] == skill.trap.rounds if skill.trap else False
    assert any(e["type"] == "apply_status" and e["duration"] == 3 for e in effects)


def test_extend_trap_rounds_only_for_enter_traps() -> None:
    lib = library()
    traps = _builtin(lambda s: s.trap is not None)
    for skill in traps:
        assert skill.trap is not None
        wider = _extend_wider(skill, lib)
        rounds = [b["trap"]["rounds"] for b, _ in wider]
        if skill.trap.trigger == "enter":
            assert rounds == [skill.trap.rounds + 1], skill.id
        else:
            assert all(r == skill.trap.rounds for r in rounds), skill.id


def test_area_on_trap_grows_trigger_shape() -> None:
    skill = library().skills["skill_bear_trap"]
    ((base, _),) = _drafts(skill, "area_plus")
    assert (skill.trap is not None, base["trap"]["shape"]) == (True, "cross")
    assert base["shape"]["type"] == skill.shape.type


def test_area_on_ground_tile_becomes_cross() -> None:
    skill = library().skills["skill_hunt_sigil"]
    assert skill.shape.type == "ground_tile"
    ((base, _),) = _drafts(skill, "area_plus")
    assert base["shape"]["type"] == "cross"


def test_wider_extend_gives_legal_options_for_summons() -> None:
    assert sum(1 for s in _summons() if _option(s, "extend_duration")) >= 1


# ---------------------------------------------------------------------------
# 4. 觸發效果 +1 固定值
# ---------------------------------------------------------------------------


def test_trigger_fine_knob_only_for_triggered_dice_effects() -> None:
    lib = library()
    passive = lib.skills["skill_bloodlust"]  # 擊殺時治療 1d6
    base, effects = base_draft(passive)
    knobs = trigger_fine_knobs("potency", base, effects, lib)
    assert [(effects[k.index]["type"], k.field, k.values) for k in knobs] == [
        ("heal", "flat_bonus", (None, 1))
    ]
    assert trigger_fine_knobs("trigger_range", base, effects, lib) == []
    assert trigger_fine_knobs("potency", *base_draft(lib.skills["skill_fire_bolt"]), lib) == []
    weapon = lib.skills["skill_riposte"]  # 武器技的反應：傷害不加固定值
    assert weapon.category == "weapon"
    knobs = trigger_fine_knobs("potency", *base_draft(weapon), lib)
    assert all(weapon.effects[k.index].type != "damage" for k in knobs)


def test_flat_bonus_counts_in_budget_and_card_text() -> None:
    lib = library()
    skill = lib.skills["skill_fire_bolt"]
    data = skill.model_dump(mode="json")
    data["effects"][0]["flat_bonus"] = 1
    plus = SkillDef.model_validate(data)
    assert skill_budget(plus, lib).total > skill_budget(skill, lib).total
    assert "＋1＋" in effect_summary(lib, plus, plus.effects[0])


def test_flat_bonus_is_spell_only() -> None:
    lib = library()
    weapon = next(
        s
        for s in _builtin(lambda s: s.category == "weapon")
        if any(e.type == "damage" for e in s.effects)
    )
    data = weapon.model_dump(mode="json")
    index = next(i for i, e in enumerate(data["effects"]) if e["type"] == "damage")
    data["effects"][index]["flat_bonus"] = 1
    with pytest.raises(ValidationError):
        SkillDef.model_validate(data)
    _ = lib


def _without_fine() -> Any:
    lib = library()
    rules = lib.flash.rules.model_copy(update={"trigger_flat_bonus": 0})
    return dataclasses.replace(lib, flash=lib.flash.model_copy(update={"rules": rules}))


def _potency(target: Any, skill: SkillDef, tier: int) -> Any:
    state = acquire(skill.id).model_copy(update={"used": True})
    request = FlashRequest(skill, state, SkillUsage(), 1, tier=tier)
    return try_variation(target, request, _variation("trigger_potency"))


def test_trigger_fine_rescues_a_ladder_skip() -> None:
    """穩息（3 階）的「效果 +」骰子一階跳過預算窗；有 +1 固定值才調得進去（BAL-12c 量測）。"""
    lib = library()
    skill = retier(lib, lib.skills["skill_steady_breath"], 3)
    assert _potency(_without_fine(), skill, 3) is None
    option = _potency(lib, skill, 3)
    assert option is not None
    assert any(e.flat_bonus == 1 for e in option.skill.effects)


def test_trigger_fine_never_loses_an_option() -> None:
    """細旋鈕只在一般重調失敗後才試，原本合法的照舊合法、結果相同。"""
    lib, off = library(), _without_fine()
    for skill in _builtin(lambda s: s.kind in ("passive", "reaction")):
        before = _potency(off, skill, skill.tier)
        if before is not None:
            after = _potency(lib, skill, skill.tier)
            assert after is not None and after.skill == before.skill, skill.id
