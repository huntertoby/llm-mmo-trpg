"""BAL-2c 用途 b：升階時形態幅度隨角色階級放大，10 個變身姿態在 1／2／3 階的預算比例都在窗內。

比照 3W-9b 點數固定的白板：維持原本的比例（夾在 70～100%），幅度上限 2000‰；維持費不動、
進入形態仍是唯一效果、預算分數不低於升階前。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import at_role_tier
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.validate import validate_skill

FORMS = sorted(s.id for s in library().skills.values() if s.form_id is not None)


def _check(skill: SkillDef) -> None:
    lib = library()
    report = skill_budget(skill, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio, (skill.id, skill.tier)
    assert 1000 <= skill.form_magnitude <= 2000
    assert skill.stance_upkeep == 0 and len(skill.effects) == 1
    assert validate_skill(skill, lib) == []


def test_all_ten_form_stances_are_covered() -> None:
    assert len(FORMS) == 10


@pytest.mark.parametrize("skill_id", FORMS)
def test_every_tier_is_inside_the_budget_window(skill_id: str) -> None:
    lib = library()
    builtin = lib.skills[skill_id]
    for tier in (1, 2, 3):
        _check(at_role_tier(lib, builtin, tier))


@pytest.mark.parametrize("skill_id", FORMS)
def test_tier_ups_grow_the_magnitude_and_never_weaken(skill_id: str) -> None:
    lib = library()
    one = at_role_tier(lib, lib.skills[skill_id], 1)
    two = retier(lib, one, 2)
    three = retier(lib, two, 3)
    for skill in (one, two, three):
        _check(skill)
    assert one.form_magnitude < two.form_magnitude < three.form_magnitude
    assert budget_power(one, lib) <= budget_power(two, lib) <= budget_power(three, lib)
    assert three.form_id == one.form_id
