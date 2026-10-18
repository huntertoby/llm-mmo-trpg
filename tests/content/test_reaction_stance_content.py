"""Phase 2E-2：反應技、姿態、``build_guardian`` 與 ``sim_duelist`` 的內容。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill


@pytest.mark.parametrize(
    "skill_id", ["skill_stand_firm", "skill_riposte", "skill_fury_stance", "skill_bulwark_stance"]
)
def test_the_new_skills_pass_budget_validation(skill_id: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    assert validate_skill(skill, lib) == []
    assert 0.7 <= float(skill_budget(skill, lib).ratio) <= 1.0


def test_stand_firm_is_an_intercepting_reaction_and_riposte_a_melee_counter() -> None:
    skills = library().skills
    stand, riposte = skills["skill_stand_firm"], skills["skill_riposte"]
    assert stand.kind == "reaction" and stand.reaction is not None
    assert stand.reaction.event == "ally_hit_adjacent"
    assert stand.effects[0].type == "intercept" and stand.rarity == "rare"
    assert riposte.reaction is not None and riposte.reaction.event == "hit_by_melee"


def test_stances_use_the_core_ap_cost_and_a_never_expiring_status() -> None:
    lib = library()
    for skill_id, status in (
        ("skill_fury_stance", "stance_fury"),
        ("skill_bulwark_stance", "stance_bulwark"),
    ):
        skill = lib.skills[skill_id]
        assert skill.kind == "stance" and skill.ap_cost is None
        assert skill.effects[0].status == status
        definition = lib.ruleset.status_def(status)
        assert definition.stance and definition.expires == "never"
    assert lib.ruleset.core.stance_ap_cost == 1


def test_build_guardian_has_the_four_roles_and_sim_duelist_the_counter() -> None:
    lib = library()
    build = next(b for b in lib.builds.builds if b.id == "build_guardian")
    skills = build.hero.skills
    kinds = {lib.skills[s].kind for s in skills}
    assert {"active", "reaction", "stance"} <= kinds
    assert "skill_taunting_roar" in skills and "skill_stand_firm" in skills
    assert build.hero.ai_profile == "guard"
    duelist = lib.unit("sim_duelist")
    assert duelist.skills == ("skill_riposte",) and "sim" in duelist.tags
