"""FL-1d：06 6.34「費用方向」第 6 點補定的增益範圍（玩法 PM 89a524d1e）。

- 算：護盾、不死（cheat_death）、轉移傷害（redirect_damage）的回合；只對友方的區域裡巢狀的狀態
  （強度與回合，跟直接施加的狀態一樣）。
- 不算：給 AP（grant_ap）、額外反應（extra_reaction）的數量。
"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.flash_changes import flash_changes
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_cost import (
    _has_rounds,
    _steps,
    _with_value,
    strength_moves,
    strength_table,
)
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_ops import base_draft
from trpg.skillgen.flash_state import Variation, acquire, with_flash

LIB = library()
SEED = 12345
LIGHT = Variation(source="minor", template="cost_light", category="cost")


def _flash(base: SkillDef, variation: Variation) -> SkillDef:
    return derive_skill(LIB, base, with_flash(acquire(base.id), variation), SEED, tier=1)


def _edited(skill: SkillDef, **effect0: object) -> SkillDef:
    data = skill.model_dump(mode="json", exclude_none=True)
    data["effects"][0].update(effect0)
    return SkillDef.model_validate(data)


def _rows(before: SkillDef, after: SkillDef) -> dict[str, tuple[str | None, str | None, str, str]]:
    return {
        c.field: (c.before, c.after, c.direction, c.label_zh)
        for c in flash_changes(LIB, before, after)
    }


def test_rounds_now_cover_shield_undying_and_soul_link() -> None:
    for kind in ("shield", "cheat_death", "redirect_damage"):
        assert _has_rounds({"type": kind})
    for kind in ("grant_ap", "extra_reaction"):
        assert not _has_rounds({"type": kind})


def test_soul_bond_light_shortens_the_link() -> None:
    base = LIB.skills["skill_soul_bond"]
    light = _flash(base, LIGHT)
    assert base.effects[0].duration == 3
    assert light.effects[0].duration is not None and light.effects[0].duration < 3
    assert strength_moves(base, light) == (False, True)
    rows = _rows(base, light)
    assert rows["effects[0].amount"][2:] == ("worse", "轉移傷害回合")


def test_shield_without_duration_counts_as_two_rounds() -> None:
    shield = next(
        s
        for s in sorted(LIB.skills.values(), key=lambda s: s.id)
        if s.effects and s.effects[0].type == "shield" and s.effects[0].duration is None
    )
    key = next(k for k in strength_table(shield) if k.endswith(".duration"))
    assert strength_table(shield)[key] == 2
    longer = _edited(shield, duration=3)
    assert strength_moves(shield, longer) == (True, False)
    assert _rows(shield, longer)["effects[0].amount"] == ("2", "3", "better", "護盾回合")


def test_undying_rounds_show_in_changes() -> None:
    base = LIB.skills["skill_undying_oath"]
    shorter = _edited(base, duration=1)
    assert strength_moves(base, shorter) == (False, True)
    assert _rows(base, shorter)["effects[0].amount"] == ("2", "1", "worse", "不死回合")


def test_nested_status_in_an_ally_zone_is_a_status() -> None:
    """戰歌區域裡的激昂：強度表、退路的回合步驟、差異清單都看得到。"""
    base = LIB.skills["skill_war_hymn"]
    table = strength_table(base)
    assert "effects[0].effects[0]:apply_status:empowered.duration" in table
    base_dict, effects = base_draft(base)
    steps = _steps(LIB, base_dict, effects, {}, up=True)
    nested = [s for s in steps if s.sub == 0 and s.field == "duration"]
    assert nested and nested[0].values == (2,)
    trial_base, trial_effects = _with_value(base_dict, effects, nested[0], 2)
    assert trial_effects[0]["effects"][0]["duration"] == 2
    longer = SkillDef.model_validate({**trial_base, "effects": trial_effects})
    assert strength_moves(base, longer) == (True, False)
    assert _rows(base, longer)["effects[0].effects[0].amount"] == ("1", "2", "better", "激昂回合")


def test_enemy_zone_nested_effects_are_not_listed() -> None:
    fire_wall = LIB.skills["skill_fire_wall"]
    assert not any(".effects[" in k for k in strength_table(fire_wall))
