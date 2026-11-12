"""FL-1e：06 6.34「費用方向」第 6 點末尾——輕巧的回合每次最多 −1（跟蓄力每次最多 +1 對稱，最少留 1；
玩法 PM 7b6fc3789）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_cost import (
    LIGHT_DURATION_STEP,
    MIN_DURATION,
    _steps,
    strength_moves,
    strength_table,
)
from trpg.skillgen.flash_derive import FlashError, derive_skill
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
SEED = 12345
LIGHT = Variation(source="minor", template="cost_light", category="cost")


def _flash(base: SkillDef) -> SkillDef:
    return derive_skill(LIB, base, with_flash(acquire(base.id), LIGHT), SEED, tier=1)


def _draft(skill: SkillDef) -> tuple[dict[str, object], list[dict[str, object]]]:
    data = skill.model_dump(mode="json", exclude_none=True)
    return data, list(data["effects"])


def _round_drops(before: SkillDef, after: SkillDef) -> list[int]:
    old, new = strength_table(before), strength_table(after)
    return [int(old[k] - new[k]) for k in sorted(old) if k.endswith(".duration") and k in new]


def test_light_round_step_is_one() -> None:
    assert LIGHT_DURATION_STEP == 1
    assert MIN_DURATION == 1


def test_light_round_steps_offer_only_one_round_less() -> None:
    for skill_id in ("skill_soul_bond", "skill_wing_spread"):
        skill = LIB.skills[skill_id]
        base, effects = _draft(skill)
        rounds = [s for s in _steps(LIB, base, effects, {}, up=False) if s.field == "duration"]
        assert rounds, skill_id
        for step in rounds:
            assert len(step.values) == 1, skill_id
            assert not step.repeat


def test_one_round_left_is_not_lowered() -> None:
    skill = LIB.skills["skill_soul_bond"]
    base, effects = _draft(skill)
    effects[0] = {**effects[0], "duration": MIN_DURATION}
    assert not [s for s in _steps(LIB, base, effects, {}, up=False) if s.field == "duration"]


def test_soul_bond_light_link_three_to_two() -> None:
    base = LIB.skills["skill_soul_bond"]
    light = _flash(base)
    assert base.effects[0].duration == 3
    assert light.effects[0].duration == 2
    assert strength_moves(base, light) == (False, True)


def test_one_round_less_still_too_strong_means_no_light() -> None:
    """−1 回合後比例仍高於合格區間（AP 2 → 1 少付太多）：不出輕巧，不會一路降。"""
    for skill_id in ("skill_wing_spread", "skill_wing_gift"):
        try:
            _flash(LIB.skills[skill_id])
        except FlashError:
            continue
        raise AssertionError(skill_id)
    kindle = compose_whiteboard(0, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)
    try:
        _flash(kindle)
    except FlashError:
        return
    raise AssertionError("kindle")


def test_tier_one_light_never_drops_more_than_one_round() -> None:
    skills = sorted(
        (s for s in LIB.skills.values() if s.tier == 1 and s.kind == "active" and not s.enemy_only),
        key=lambda s: s.id,
    )
    for base in skills:
        try:
            after = _flash(base)
        except FlashError:
            continue
        assert all(drop <= LIGHT_DURATION_STEP for drop in _round_drops(base, after)), base.id
