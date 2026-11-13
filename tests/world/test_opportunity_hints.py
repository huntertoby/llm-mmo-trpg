"""機遇的提示（Phase 5B-4e；18.7.6「5B-4d 代決」）：第 4 天起酒館傳聞一定有古松祭壇、第 6 天起
還沒遇過機遇的角色在霧渡鎮聽到說書人順口提一句。"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_quests import SocialTable
from trpg.world.actions import (
    OpportunityHintEvent,
    RumorsHeardEvent,
    TavernAction,
    TravelAction,
    WorldEvent,
)
from trpg.world.clock import refresh_day
from trpg.world.save import dumps_char, loads_char
from trpg.world.social import opportunity_hint, week_rumors
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

DAY = 86_400
ALTAR_RUMOR = "rumor_storm_altar"
HINT = "酒館的說書人順口提了一句：「古松那邊最近不太平。」"


def _day(n: int) -> int:
    return NOON + (n - 1) * DAY


def test_storm_altar_rumor_from_day_4(library: ContentLibrary) -> None:
    missing_before = 0
    for seed in range(40):
        world = make_world(season_seed=seed)
        for day in range(1, 22):
            _, rumors = week_rumors(library, world, "cloud_ridge", _day(day))
            ids = [r.id for r in rumors]
            assert len(ids) == 3 and ids == sorted(ids)
            if day >= 4:
                assert ALTAR_RUMOR in ids, (seed, day)
            elif ALTAR_RUMOR not in ids:
                missing_before += 1
        # 同一週第 4 天起只換掉一條（其餘照原本的洗牌）
        _, early = week_rumors(library, world, "cloud_ridge", _day(3))
        _, late = week_rumors(library, world, "cloud_ridge", _day(4))
        assert len({r.id for r in early} - {r.id for r in late}) <= 1
    assert missing_before > 0  # 第 1～3 天照舊隨機


def test_hint_on_arrival_at_ferry_from_day_6(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    away = make_char(location="ferry_steps")
    before = world_step(library, world, away, TravelAction(to="mist_ferry"), _day(5))
    assert not any(isinstance(e, OpportunityHintEvent) for e in before.events)
    after = world_step(library, world, away, TravelAction(to="mist_ferry"), _day(6))
    hints = [e for e in after.events if isinstance(e, OpportunityHintEvent)]
    assert [(h.location, h.text_zh) for h in hints] == [("mist_ferry", HINT)]
    # 只記下聽到提示的日子（5B-4f）
    assert after.char.met_opportunities == ()
    # 遇過或拿過機遇就不提
    met = away.model_copy(update={"met_opportunities": ("storm_altar",)})
    result = world_step(library, world, met, TravelAction(to="mist_ferry"), _day(6))
    assert not any(isinstance(e, OpportunityHintEvent) for e in result.events)
    taken = away.model_copy(update={"opportunities": ("storm_altar",)})
    assert (
        opportunity_hint(
            library, world, taken.model_copy(update={"location": "mist_ferry"}), _day(6)
        )
        is None
    )


def test_hint_in_ferry_tavern(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="mist_ferry")
    early = world_step(library, world, char, TavernAction(), _day(5)).events
    assert [type(e) for e in early] == [RumorsHeardEvent]
    late = world_step(library, world, char, TavernAction(), _day(6)).events
    assert [type(e) for e in late] == [RumorsHeardEvent, OpportunityHintEvent]
    heard = late[0]
    assert isinstance(heard, RumorsHeardEvent) and ALTAR_RUMOR in heard.rumors
    # 別的地點沒有提示
    assert (
        opportunity_hint(
            library, world, char.model_copy(update={"location": "ferry_steps"}), _day(6)
        )
        is None
    )


def test_pinned_rumor_must_exist() -> None:
    with pytest.raises(ValidationError, match="rumor_nope"):
        SocialTable.model_validate(
            {"region": "cloud_ridge", "pinned_rumors": [{"rumor": "rumor_nope", "from_day": 4}]}
        )


def test_hint_once_per_refresh_day(library: ContentLibrary, make_char: MakeChar) -> None:
    """5B-4f（玩法 PM 2026-11-03 代決）：每個角色一天只提一次（6 點刷新為界），抵達與酒館共用。"""
    world = make_world()
    away = make_char(location="ferry_steps")
    first = world_step(library, world, away, TravelAction(to="mist_ferry"), _day(6))
    assert _hints(first.events) == [HINT]
    assert first.char.opportunity_hint_day == refresh_day(_day(6))
    # 同一天：酒館、再抵達都不再提
    tavern = world_step(library, world, first.char, TavernAction(), _day(6) + 60)
    assert [type(e) for e in tavern.events] == [RumorsHeardEvent]
    assert tavern.char == first.char
    back = tavern.char.model_copy(update={"location": "ferry_steps"})
    again = world_step(library, world, back, TravelAction(to="mist_ferry"), _day(6) + 120)
    assert _hints(again.events) == []
    # 過了午夜、還沒到 6 點仍是同一天
    late_night = _day(6) + 15 * 3600
    assert refresh_day(late_night) == refresh_day(_day(6))
    night = world_step(library, world, again.char, TavernAction(), late_night)
    assert _hints(night.events) == []
    # 6 點刷新後再提一次（酒館先聽到，記下新的一天）
    next_day = world_step(library, world, night.char, TavernAction(), _day(7))
    assert _hints(next_day.events) == [HINT]
    assert next_day.char.opportunity_hint_day == refresh_day(_day(7))


def test_hint_day_absent_in_old_save(library: ContentLibrary, make_char: MakeChar) -> None:
    """5B-4f：新欄位有預設值，舊存檔（沒有 ``opportunity_hint_day``）照讀；不升版號。"""
    char = make_char(location="mist_ferry")
    data = json.loads(dumps_char(char))
    data.pop("opportunity_hint_day")
    old = loads_char(json.dumps(data, ensure_ascii=False))
    assert data["format"] == "trpg-char/15"
    assert old.opportunity_hint_day is None
    result = world_step(library, make_world(), old, TavernAction(), _day(6))
    assert _hints(result.events) == [HINT]


def _hints(events: Sequence[WorldEvent]) -> list[str]:
    return [e.text_zh for e in events if isinstance(e, OpportunityHintEvent)]
