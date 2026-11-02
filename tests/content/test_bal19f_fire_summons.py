"""BAL-19f 追加（玩法 PM 2026-11-02，06 6.10 組合主題）：火杖用的「主效果召喚＋附帶元素」法術——
看智力（或意志），主效果是召喚、附帶元素效果作用在施放者自己；過預算與驗證，在引擎裡能施放。"""

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
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import UnitSummoned
from trpg.shared.types import Attribute, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import minimum_tier, validate_skill

LIB = library()
SKILLS = sorted(s for s in LIB.skills if s.startswith("skill_fsum_"))


def test_two_or_three_fire_staff_summon_spells() -> None:
    assert 2 <= len(SKILLS) <= 3


@pytest.mark.parametrize("sid", SKILLS)
def test_summon_main_effect_with_an_elemental_rider_on_the_caster(sid: str) -> None:
    skill = LIB.skills[sid]
    assert skill.category == "spell" and skill.weapon_req == "focus"
    assert skill.effects[0].type == "summon"
    assert all(e.affects == "self" for e in skill.effects[1:])
    assert {"fire", "lightning"} & set(skill.tags)
    assert validate_skill(skill, LIB) == []
    assert 0.7 <= float(skill_budget(skill, LIB).ratio) <= 1.0
    assert "summon" in derive_keywords(skill, LIB.keywords, exclusive_only=True).all()
    allowed = LIB.scaling_range(skill)
    assert skill.scaling_attr is Attribute.INT and Attribute.INT in allowed  # 可看智力
    assert Attribute.WIL in allowed  # 召喚的意志路線照舊


def test_one_of_them_opens_at_tier_one() -> None:
    assert any(minimum_tier(LIB.skills[s], LIB) == 1 for s in SKILLS)


@pytest.mark.parametrize("sid", SKILLS)
def test_fire_staff_summons_cast_in_the_engine(sid: str) -> None:
    skill = LIB.skills[sid]
    m = make_map("\n".join(["000000000"] * 9), ally=[(0, 4)], enemy=[(6, 4)])
    spawns = [
        spawn(Team.ALLY, (0, 4), caster_template([skill], base="hero_mage")),
        spawn(Team.ENEMY, (6, 4), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns), "unit_0001")
    action = next(a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == sid)
    result = resolve(state, action)
    assert any(isinstance(e, UnitSummoned) for e in result.events)
    caster = result.state.units["unit_0001"]
    rider = skill.effects[1]
    assert caster.has_status(rider.status or "")
