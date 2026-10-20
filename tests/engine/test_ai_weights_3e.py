"""Phase 3E-1 #10：AI 評分的魔法數字（衝撞每敵、瞬步）搬進 ``AiWeights``，預設值不變。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.environment import AiWeights
from trpg.engine.ai.utility import _charge_estimate, _scene
from trpg.engine.skills.targeting import SkillArea
from trpg.shared.types import Team, UnitId

U1 = UnitId("unit_0001")
FLAT = "\n".join(["0000000"] * 7)


def test_the_defaults_keep_the_old_constants() -> None:
    w = AiWeights()
    assert (w.charge_per_enemy, w.shadowstep, w.shadowstep_behind) == (3, 3, 2)


def test_no_shipped_profile_overrides_the_new_weights() -> None:
    """內容裡沒有行為模式改寫這三個權重（所以戰鬥結果不變）。"""
    for profile in library().ai_profiles.profiles:
        w = profile.weights
        assert (w.charge_per_enemy, w.shadowstep, w.shadowstep_behind) == (3, 3, 2), profile.id


def test_the_charge_estimate_uses_the_weight_per_enemy() -> None:
    foes = [(2, 3), (4, 3)]
    m = make_map(FLAT, None, ally=[(0, 3)], enemy=foes)
    spawns = [spawn(Team.ALLY, (0, 3), caster_template(["skill_bull_rush"], base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=200)) for xy in foes]
    state = give_turn(make_state(m, spawns), U1)
    unit = state.units[U1]
    scene = _scene(state, unit)
    area = SkillArea(
        tiles=(), units=(UnitId("unit_0002"), UnitId("unit_0003")), origin=(5, 3), direction=None
    )
    base = AiWeights()
    heavier = base.model_copy(update={"charge_per_enemy": 10})
    zero = Fraction(0)
    low = _charge_estimate(state, unit, area, scene, base, zero)
    high = _charge_estimate(state, unit, area, scene, heavier, zero)
    assert low is not None and high is not None
    assert high - low == 2 * (10 - 3)
