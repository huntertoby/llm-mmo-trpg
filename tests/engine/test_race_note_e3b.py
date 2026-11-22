"""E3b：種族被動加註的「整條被蓋過」旗標（``RaceView.passive_overridden_full``）：前端依此寫
「…蓋過，沒有作用」或「…蓋過，其他有作用」；沒被蓋過時不輸出。"""

from __future__ import annotations

from tests.engine.race_helpers import U1, race_state
from tests.engine.test_stronger_rule_e3 import _swim
from tests.engine.test_unit_rules_e2 import wear
from trpg.engine import BattleState
from trpg.engine.rules.unit_rules import race_overridden_fully
from trpg.engine.view import RaceView, project_for
from trpg.shared.types import Team


def _race(state: BattleState) -> RaceView:
    me = next(u for u in project_for(state, Team.ALLY).units if u.id == U1)
    assert me.race is not None
    return me.race


def test_partly_overridden_is_not_full() -> None:
    state = race_state("scalefolk")
    unit = wear(state, {"body": [_swim("affix_t_swim2", ["water"], 2, "站在水上，移動 +2")]})
    race = _race(state)
    assert race.passive_overridden_zh == "水的部分被身體的「站在水上，移動 +2」蓋過"
    assert race.passive_overridden_full is False
    assert not race_overridden_fully(state.ruleset, unit)


def test_fully_overridden_is_full() -> None:
    state = race_state("scalefolk")
    unit = wear(state, {"feet": [_swim("affix_t_swim2", ["water", "ice"], 2, "水冰移動 +2")]})
    race = _race(state)
    assert race.passive_overridden_zh == "被腳的「水冰移動 +2」蓋過"
    assert race.passive_overridden_full is True
    assert race_overridden_fully(state.ruleset, unit)


def test_not_overridden_omits_the_flag() -> None:
    state = race_state("scalefolk")
    race = _race(state)
    assert race.passive_overridden_zh is None
    assert race.passive_overridden_full is None
    assert "passive_overridden_full" not in race.model_dump()
    assert not race_overridden_fully(state.ruleset, state.units[U1])
    assert not race_overridden_fully(race_state(None).ruleset, race_state(None).units[U1])
