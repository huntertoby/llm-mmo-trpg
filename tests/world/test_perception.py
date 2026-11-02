"""隱藏地點的感知判定（Phase 5A-2；09 9.6.11 #112）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.world.actions import LocationRevealedEvent, PerceptionCheckEvent, TravelAction
from trpg.world.clock import next_refresh_at
from trpg.world.state import CharacterState
from trpg.world.step import perception_modifier, world_step

MakeChar = Callable[..., CharacterState]


def _checks(events: tuple[object, ...]) -> list[PerceptionCheckEvent]:
    return [e for e in events if isinstance(e, PerceptionCheckEvent)]


def test_check_when_arriving_next_to_hidden(calm: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="winter_lake")
    result = world_step(calm, make_world(), char, TravelAction(to="north_slope"), NOON)
    checks = _checks(result.events)
    assert len(checks) == 1
    check = checks[0]
    assert check.location == "crane_cliff"
    assert check.dc == 13  # 10 ＋ 6 ÷ 2
    assert check.modifier == perception_modifier(calm, char)
    assert check.success == (check.roll + check.modifier >= 13)
    assert result.char.perception_day("cloud_ridge", "crane_cliff") is not None
    assert result.char.rng_counters.get("reveal") == 1
    assert result.char.has_revealed("cloud_ridge", "crane_cliff") == check.success


def test_sharp_eyes_always_find(calm: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="winter_lake", wis=40)  # 修正 +15：擲 1 也過 13
    result = world_step(calm, make_world(), char, TravelAction(to="north_slope"), NOON)
    assert any(isinstance(e, LocationRevealedEvent) for e in result.events)
    assert result.char.has_revealed("cloud_ridge", "crane_cliff")
    after = world_step(calm, make_world(), result.char, TravelAction(to="crane_cliff"), NOON)
    assert after.char.location == "crane_cliff"


def test_failure_has_no_penalty_and_once_per_day(calm: ContentLibrary, make_char: MakeChar) -> None:
    hard = with_rules(calm, perception={"dc_base": 100})
    char = make_char(location="winter_lake")
    first = world_step(hard, make_world(), char, TravelAction(to="north_slope"), NOON)
    assert not _checks(first.events)[0].success
    assert first.char.hp == char.hp
    assert first.char.supplies == char.supplies
    assert not first.char.has_revealed("cloud_ridge", "crane_cliff")

    # 同一天回到北坡獵場：不再判定。
    back = world_step(hard, make_world(), first.char, TravelAction(to="winter_lake"), NOON + 60)
    again = world_step(hard, make_world(), back.char, TravelAction(to="north_slope"), NOON + 120)
    assert _checks(again.events) == []

    # 隔天（早上 6 點後）再判定一次。
    tomorrow = next_refresh_at(NOON)
    back = world_step(hard, make_world(), again.char, TravelAction(to="winter_lake"), tomorrow)
    next_day = world_step(
        hard, make_world(), back.char, TravelAction(to="north_slope"), tomorrow + 1
    )
    assert len(_checks(next_day.events)) == 1
    assert len(next_day.char.perception_marks) == 1


def test_situation_only_hidden_is_not_checked(calm: ContentLibrary, make_char: MakeChar) -> None:
    # 丹爐洞只有 situation（情境判定）一種發現方式：走到藥師谷不做感知判定。
    char = make_char(location="cliff_gang_fort", wis=40)
    result = world_step(calm, make_world(), char, TravelAction(to="herb_valley"), NOON)
    assert _checks(result.events) == []
    assert not result.char.has_revealed("cloud_ridge", "elixir_cave")


def test_already_revealed_is_not_checked(calm: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="winter_lake", wis=40)
    found = world_step(calm, make_world(), char, TravelAction(to="north_slope"), NOON).char
    back = world_step(calm, make_world(), found, TravelAction(to="winter_lake"), NOON).char
    tomorrow = next_refresh_at(NOON)
    again = world_step(calm, make_world(), back, TravelAction(to="north_slope"), tomorrow)
    assert _checks(again.events) == []
