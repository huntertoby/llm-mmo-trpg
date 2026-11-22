"""種族可以給數值（#179，CR-1 B 項）：環境被動的 ``stats``（目前只有暴擊傷害），和其他來源相加後套
全身上下限；現有 10 族都沒給，序列化不變。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, battle
from trpg.content.library import Ruleset
from trpg.content.races import RaceDef, RacePassive
from trpg.content.skills import SkillDef
from trpg.engine.crit_damage import crit_damage_permille
from trpg.engine.rules.race import race_crit_damage_permille


def _passive(**stats: Any) -> dict[str, Any]:
    races = library().ruleset.races
    assert races is not None
    data = races.by_id()["human"].passive.model_dump(mode="json")
    data["stats"] = stats
    return data


def test_no_bundled_race_gives_numbers() -> None:
    races = library().ruleset.races
    assert races is not None
    for race in races.races:
        assert race.passive.stats is None, race.id
        assert "stats" not in race.passive.model_dump(mode="json")


def test_a_passive_can_carry_a_crit_damage_number() -> None:
    passive = RacePassive.model_validate(_passive(crit_damage_permille=150))
    assert passive.stats is not None and passive.stats.crit_damage_permille == 150


@pytest.mark.parametrize("value", [0, 1500, -1500])
def test_the_number_is_checked(value: int) -> None:
    with pytest.raises(ValidationError):
        RacePassive.model_validate(_passive(crit_damage_permille=value))


def test_unknown_stats_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RacePassive.model_validate(_passive(crit_damage_permille=100, max_hp=10))


@pytest.mark.parametrize(("bonus", "expected"), [(150, 2150), (-300, 1700), (1000, 3000)])
def test_the_race_adds_to_the_crit_damage(
    monkeypatch: pytest.MonkeyPatch, bonus: int, expected: int
) -> None:
    """種族的暴擊傷害和其他來源相加，再套全身 150%～300%。"""
    skill = SkillDef.model_validate(
        make_skill(
            SID,
            {"type": "single", "range": 5},
            [{"type": "damage", "dice": "1d6", "element": "fire"}],
        ).model_dump(mode="json")
    )
    state = battle(skill, [(4, 3)])
    unit = state.units[U1]
    unit.race = "human"
    original = Ruleset.race_def

    def race_def(self: Ruleset, race_id: str) -> RaceDef:
        race = original(self, race_id)
        stats = RacePassive.model_validate(_passive(crit_damage_permille=bonus))
        return race.model_copy(update={"passive": stats})

    assert crit_damage_permille(state, unit) == 2000  # 原本的人類沒有數值
    monkeypatch.setattr(Ruleset, "race_def", race_def)
    assert race_crit_damage_permille(state.ruleset, unit) == bonus
    assert crit_damage_permille(state, unit) == expected
    unit.race = None
    assert crit_damage_permille(state, unit) == 2000
