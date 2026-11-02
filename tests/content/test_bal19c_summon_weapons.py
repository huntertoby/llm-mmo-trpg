"""BAL-19c（玩法決定 #110，06 6.27.4）：召喚物關鍵字的武器技——力量、敏捷武器路線也拿得到同路線的
召喚技；召喚物的成長跟著手上武器的屬性（召喚法術仍看意志）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import UnitSummoned
from trpg.engine.summons.core import growth_of
from trpg.shared.types import Team
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import minimum_tier, validate_skill

LIB = library()
SKILLS = sorted(s for s in LIB.skills if s.startswith("skill_sum_"))


def test_weapon_summons_cover_strength_and_dexterity() -> None:
    attrs = {(LIB.skills[s].weapon_req, LIB.skills[s].scaling_attr) for s in SKILLS}
    assert {("melee", "str"), ("ranged", "dex")} <= attrs
    for sid in SKILLS:
        skill = LIB.skills[sid]
        assert skill.category == "weapon" and validate_skill(skill, LIB) == []
        assert "summon" in derive_keywords(skill, LIB.keywords, exclusive_only=True).all()
    # 1 階就能出的（基本召喚物）：力量、敏捷各至少 1 招
    tier_one = {LIB.skills[s].scaling_attr for s in SKILLS if minimum_tier(LIB.skills[s], LIB) == 1}
    assert {"str", "dex"} <= tier_one


def _battle(skill: SkillDef, strength: int):  # type: ignore[no-untyped-def]
    m = make_map("\n".join(["000000000"] * 9), ally=[(0, 4)], enemy=[(6, 4)])
    base = "hero_fighter" if skill.weapon_req == "melee" else "hero_archer"
    attrs = {"str": strength, "dex": strength}
    spawns = [
        spawn(Team.ALLY, (0, 4), caster_template([skill], base=base, attributes=attrs)),
        spawn(Team.ENEMY, (6, 4), no_reactions()),
    ]
    return give_turn(make_state(m, spawns), "unit_0001")


@pytest.mark.parametrize("sid", ["skill_sum_grave_blade", "skill_sum_spirit_arrow"])
def test_weapon_summons_play_and_grow_with_the_weapon_attribute(sid: str) -> None:
    skill = LIB.skills[sid]
    weak, strong = _battle(skill, 10), _battle(skill, 18)
    caster = weak.units["unit_0001"]
    assert (
        growth_of(strong, strong.units["unit_0001"], sid).attr_mod
        > growth_of(weak, caster, sid).attr_mod
    )
    action = next(a for a in legal_actions(weak) if isinstance(a, UseSkill) and a.skill_id == sid)
    events = resolve(weak, action).events
    assert any(isinstance(e, UnitSummoned) for e in events)
