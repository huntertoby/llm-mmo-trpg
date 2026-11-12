"""FL-1e：06 6.34「費用方向」第 6 點（玩法 PM e0e22fd9f）。

- 輕巧的回合可以一次降多回合，降到預算合格為止，最少留 1（FL-1d 以前的做法；點燃斬燃燒 5 → 2）。
- 預算器沒計價的回合（不死、轉移傷害）每次最多 −1；降 1 量不出有沒有扣回時照樣出輕巧（魂結 3 → 2）。
- 一次只調一項。
"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_cost import (
    LIGHT_UNPRICED_STEP,
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
UNPRICED = ("cheat_death", "redirect_damage")


def _flash(base: SkillDef) -> SkillDef:
    return derive_skill(LIB, base, with_flash(acquire(base.id), LIGHT), SEED, tier=1)


def _draft(skill: SkillDef) -> tuple[dict[str, object], list[dict[str, object]]]:
    data = skill.model_dump(mode="json", exclude_none=True)
    return data, list(data["effects"])


def _round_steps(skill: SkillDef, **effect0: object) -> list[tuple[object, ...]]:
    base, effects = _draft(skill)
    if effect0:
        effects[0] = {**effects[0], **effect0}
    return [s.values for s in _steps(LIB, base, effects, {}, up=False) if s.field == "duration"]


def test_unpriced_step_is_one() -> None:
    assert LIGHT_UNPRICED_STEP == 1
    assert MIN_DURATION == 1


def test_unpriced_rounds_offer_only_one_round_less() -> None:
    soul = LIB.skills["skill_soul_bond"]
    assert soul.effects[0].type == "redirect_damage"
    assert _round_steps(soul) == [(2,)]
    assert _round_steps(soul, duration=MIN_DURATION) == []


def test_priced_rounds_may_drop_several() -> None:
    wing = LIB.skills["skill_wing_spread"]
    assert wing.effects[0].duration == 3
    assert _round_steps(wing) == [(2, 1)]


def test_soul_bond_light_link_three_to_two() -> None:
    base = LIB.skills["skill_soul_bond"]
    light = _flash(base)
    assert base.effects[0].duration == 3
    assert light.effects[0].duration == 2
    assert strength_moves(base, light) == (False, True)


def test_kindle_light_still_drops_the_burn_to_two() -> None:
    kindle = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)
    light = _flash(kindle)
    assert kindle.effects[0].duration == 5
    assert light.effects[0].duration == 2


def test_tier_one_light_unpriced_rounds_drop_at_most_one() -> None:
    skills = sorted(
        (s for s in LIB.skills.values() if s.tier == 1 and s.kind == "active" and not s.enemy_only),
        key=lambda s: s.id,
    )
    for base in skills:
        try:
            after = _flash(base)
        except FlashError:
            continue
        old, new = strength_table(base), strength_table(after)
        for key in sorted(old):
            if key.endswith(".duration") and any(f":{t}:" in key for t in UNPRICED):
                assert old[key] - new.get(key, old[key]) <= LIGHT_UNPRICED_STEP, (base.id, key)
