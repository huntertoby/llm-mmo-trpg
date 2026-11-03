"""複製技能與敵人專用技能（Phase 5F-R1；06 6.35，玩法 PM 2026-11-03 代決）：``enemy_only`` 技能一律
不能複製，戰鬥中暫時的也不行。實際跑引擎：敵人施放一招（一般／敵人專用），再看我方的複製技能。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4, of
from tests.engine.test_passive_triggers import always
from trpg.engine import BattleState, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.copying import copy_problem, copy_selections, uncopyable_reason
from trpg.engine.events import SkillCopied
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Team

COPY = "skill_t_copy"
BOLT = "skill_t_bolt"
BOLT_EFFECT = {"type": "damage", "dice": "1d6", "element": "fire", "affects": "enemies"}


@pytest.fixture
def always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)


def _scene(*, enemy_only: bool) -> BattleState:
    """U1（我方，有複製技能）、U2（我方）、U3（敵人，施放 BOLT）、U4（敵人）；U3 已對 U2 施放 BOLT，
    同一輪輪到 U1。"""
    copy = make_skill(COPY, {"type": "self"}, [{"type": "copy_skill"}])
    bolt = make_skill(BOLT, {"type": "single", "range": 5}, [BOLT_EFFECT], cost={"mana": 3})
    bolt = bolt.model_copy(update={"enemy_only": enemy_only})
    m = make_map(FLAT7, ally=[(3, 3), (2, 3)], enemy=[(5, 3), (5, 5)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([copy])),
        spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter")),
        spawn(Team.ENEMY, (5, 3), caster_template([bolt])),
        spawn(Team.ENEMY, (5, 5), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns, skills=[copy, bolt]), U3)
    state = resolve(state, UseSkill(unit_id=U3, skill_id=BOLT, target_id=U2)).state
    return give_turn(state, U1)


def _copy_actions(state: BattleState) -> list[UseSkill]:
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == COPY]


@pytest.mark.parametrize("enemy_only", [False, True])
def test_copy_follows_enemy_only(enemy_only: bool, always_hit: None) -> None:
    state = _scene(enemy_only=enemy_only)
    caster = state.units[U1]
    bolt = state.ruleset.skill_def(BOLT)
    reason = uncopyable_reason(state, bolt)
    problem = copy_problem(state, caster)
    picks = list(copy_selections(state, caster))
    expanded, _ = legal_actions_with_areas(state, expand_copy=True)
    expanded_copies = [a for a in expanded if isinstance(a, UseSkill) and a.skill_id == COPY]
    cast = UseSkill(unit_id=U1, skill_id=BOLT, target_id=U4)
    pick = UseSkill(unit_id=U1, skill_id=COPY, copy_cast=cast)
    ai = UtilityAI(library().ai_profiles)(state)
    if not enemy_only:
        assert reason is None and problem is None
        assert picks and _copy_actions(state) and expanded_copies
        assert of(resolve(state, pick), SkillCopied)
        return
    assert reason is not None and "敵人專用" in reason
    assert problem == reason
    assert not picks  # 不列為可複製
    assert not _copy_actions(state) and not expanded_copies  # 沒有可複製的＝不能用
    with pytest.raises(IllegalActionError, match="敵人專用"):
        resolve(state, pick)
    with pytest.raises(IllegalActionError, match="敵人專用"):
        resolve(state, UseSkill(unit_id=U1, skill_id=COPY))
    assert not (isinstance(ai, UseSkill) and ai.skill_id == COPY)
