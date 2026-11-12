"""FL-1a：閃現「蓄力」「輕巧」一定要真的變（06 6.34「費用方向」第 1～4 點，玩法 PM 2026-11-13；
起因 ``docs/phases/閃現蓄力調查.md``）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_cost import (
    CHARGE_DURATION_CAP,
    charge_adjusted,
    strength_moves,
)
from trpg.skillgen.flash_derive import FlashError, derive_skill, with_budget_bonus
from trpg.skillgen.flash_ops import base_draft
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
SEED = 12345
CHARGE = Variation(source="minor", template="cost_charge", category="cost")
LIGHT = Variation(source="minor", template="cost_light", category="cost")

LIGHT_STRONGER_BEFORE = (
    "換位重擊",
    "火焰箭矢",
    "化形回春",
    "颶風踢",
    "鉤索箭",
    "過載電流",
    "霜寒之觸",
    "雷鳴箭",
    "收割靈魂",
    "火花連鎖",
    "靜電掌",
    "石膚術",
    "雷鳴震波",
    "雷咒",
    "毒咒",
    "雷殼守護",
)
"""調查第 4 節：AP 1 套輕巧後反而變強的 16 招。"""


def _kindle() -> SkillDef:
    """點燃斬（白板配方 kindle，種子 75；調查第 2 節）：AP 2、耐力 2、冷卻 2、燃燒 5 回合。"""
    return compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)


def _flash(base: SkillDef, *variations: Variation) -> SkillDef:
    state = acquire(base.id)
    for variation in variations:
        state = with_flash(state, variation)
    return derive_skill(LIB, base, state, SEED, tier=1)


def _named(name: str) -> SkillDef:
    return next(
        s for s in LIB.skills.values() if s.name_zh == name and s.tier == 1 and not s.enemy_only
    )


def _burning(skill: SkillDef) -> int | None:
    return next(e.duration for e in skill.effects if e.status == "burning")


def test_kindle_charge_burns_one_round_longer() -> None:
    base = _kindle()
    assert (base.cost.cooldown, _burning(base)) == (2, 5)
    charged = _flash(base, CHARGE)
    assert charged.cost.cooldown == 4
    assert _burning(charged) == 6
    assert strength_moves(base, charged) == (True, False)


def test_second_charge_turns_to_strength_when_rounds_are_capped() -> None:
    """燃燒到 6（組合器的持續上限）之後，第二次蓄力改加狀態強度（同升階：先加回合、再加強度）。"""
    twice = _flash(_kindle(), CHARGE, CHARGE)
    effect = next(e for e in twice.effects if e.status == "burning")
    step = LIB.budget.flash_cost.magnitude_step
    assert (twice.cost.cooldown, effect.duration, effect.magnitude_permille) == (5, 6, 1000 + step)


def test_charge_rounds_never_exceed_the_original_plus_two() -> None:
    """原招燃燒 3 回合、目前已經 5 回合（＝原招 +2）：蓄力不能再加回合。"""
    base = _kindle()
    origin = base.model_copy(
        update={"effects": (base.effects[0].model_copy(update={"duration": 3}),)}
    )
    current = with_budget_bonus(base, 40)
    draft = base_draft(current)
    draft[0]["cost"] = {**draft[0]["cost"], "cooldown": 4}
    done = charge_adjusted(LIB, current, draft, floor=None, origin=origin)
    assert done is not None
    assert _burning(done) == 3 + CHARGE_DURATION_CAP == 5
    assert done.effects[0].magnitude_permille is not None  # 改加強度


@pytest.mark.parametrize("name", ["殘影之誓", "喚起骷髏", "築起土牆"])
def test_no_charge_when_nothing_can_grow(name: str) -> None:
    """調查 3.1 的「只多冷卻」招：沒有可加的，不出蓄力。"""
    with pytest.raises(FlashError):
        _flash(_named(name), CHARGE)


@pytest.mark.parametrize("name", LIGHT_STRONGER_BEFORE)
def test_light_on_one_ap_never_gets_stronger(name: str) -> None:
    base = _named(name)
    assert base.ap_cost == 1
    try:
        light = _flash(base, LIGHT)
    except FlashError:
        return  # 沒有東西可以降：不出輕巧（也合格）
    up, down = strength_moves(base, light)
    assert down and not up


def test_frost_touch_light_is_not_offered() -> None:
    """FL-1a 時霜寒之觸輕巧＝法力 3 → 2、1d8 → 1d6；FL-1c（第 5 點）起法力實付 3 → 2 都是 2，
    當作沒少付，不出輕巧（``tests/skillgen/test_flash_cost_fl1c.py``）。"""
    base = _named("霜寒之觸")
    assert base.cost.mana == 3
    with pytest.raises(FlashError):
        _flash(base, LIGHT)


@pytest.mark.parametrize("name", ["喚起骷髏", "召喚石像", "隱匿"])
def test_no_light_when_nothing_can_drop(name: str) -> None:
    base = _named(name)
    assert base.ap_cost == 1
    with pytest.raises(FlashError):
        _flash(base, LIGHT)


def test_kindle_light_is_not_offered() -> None:
    """FL-1a 原本燃燒 5 → 2；FL-1e 起輕巧的回合每次最多 −1，燃燒 4 回合時比例仍高於合格區間
    （AP 2 → 1 少付太多），不出輕巧。"""
    with pytest.raises(FlashError):
        _flash(_kindle(), LIGHT)


def test_light_keeps_at_least_one_round() -> None:
    """FL-1e 起改用魂結（轉移傷害 3 → 2）。"""
    light = _flash(LIB.skills["skill_soul_bond"], LIGHT)
    assert all((e.duration or 1) >= 1 for e in light.effects)


@pytest.mark.slow
def test_scan_every_tier_one_active_skill() -> None:
    """調查的掃描（內容檔的 1 階主動技）：蓄力套得上就至少一項變強，輕巧套得上就至少一項變弱而且
    沒有一項變強。"""
    skills = [
        s for s in LIB.skills.values() if s.tier == 1 and s.kind == "active" and not s.enemy_only
    ]
    for base in sorted(skills, key=lambda s: s.id):
        for variation in (CHARGE, LIGHT):
            try:
                after = _flash(base, variation)
            except FlashError:
                continue
            up, down = strength_moves(base, after)
            if variation is CHARGE:
                assert up, base.id
            else:
                assert down and not up, base.id
