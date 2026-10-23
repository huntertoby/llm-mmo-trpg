"""玩法決定 #60：淨化只移除 ``polarity: debuff`` 的狀態；增益與中性（隱蔽、姿態、免死、
靈魂連結、蓄力）保留。引擎表格測試：每種狀態各一列。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import U2, battle, cast, of
from trpg.content.skills import SkillDef
from trpg.engine.events import StatusRemoved
from trpg.engine.state import StatusInstance

SID = "skill_t_prim"
_ALL_STATUSES = sorted(s.id for s in library().ruleset.statuses.statuses)


def _cleanse_skill() -> SkillDef:
    return make_skill(
        SID, {"type": "single", "range": 4}, [{"type": "cleanse", "affects": "allies"}]
    )


@pytest.mark.parametrize("status_id", _ALL_STATUSES)
def test_cleanse_removes_exactly_the_debuffs(status_id: str) -> None:
    definition = library().ruleset.status_def(status_id)
    state = battle(_cleanse_skill(), foes=[(6, 6)], allies=[(3, 4)])
    state.units[U2].statuses = [StatusInstance(status_id, 2, None)]
    result = cast(state, target_id=U2)
    removed = [e.status_id for e in of(result, StatusRemoved)]
    kept = [s.status_id for s in result.state.units[U2].statuses]
    if definition.polarity == "debuff":
        assert removed == [status_id]
        assert kept == []
    else:
        assert removed == []
        assert kept == [status_id]


def test_cleanse_keeps_every_neutral_status() -> None:
    neutral = sorted(s.id for s in library().ruleset.statuses.statuses if s.polarity == "neutral")
    assert {"concealed", "undying", "soul_link", "charging", "stance_fury"} <= set(neutral)
    state = battle(_cleanse_skill(), foes=[(6, 6)], allies=[(3, 4)])
    state.units[U2].statuses = [StatusInstance(s, 2, None) for s in neutral] + [
        StatusInstance("burning", 2, None)
    ]
    result = cast(state, target_id=U2)
    assert [e.status_id for e in of(result, StatusRemoved)] == ["burning"]
    assert sorted(s.status_id for s in result.state.units[U2].statuses) == neutral
