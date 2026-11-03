"""賽季日程、今日目標、懸賞、世界事件的資料（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.4）。"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_map import LocationKind
from trpg.content.world_season import SeasonContent, season_problems


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def season(library: ContentLibrary) -> SeasonContent:
    assert library.world_season is not None
    return library.world_season


def _data(season: SeasonContent) -> dict[str, Any]:
    return season.model_dump(mode="json")


def _problems(library: ContentLibrary, season: SeasonContent) -> list[str]:
    assert library.regions is not None
    return season_problems(
        season,
        world_maps=library.world_maps,
        encounters=library.world_encounters,
        catalog=library.enemy_catalog(),
        weather_ids=set(library.weather),
        region_ids={r.id for r in library.regions.regions},
        location_kinds=get_args(LocationKind.__value__),
    )


def test_first_season_loaded(library: ContentLibrary, season: SeasonContent) -> None:
    assert season.days == 14  # 09 9.7
    assert season.schedule[0].days == (1, 3)
    assert season.phase_on(8) is not None and season.phase_on(8).id == "act3"  # type: ignore[union-attr]
    assert {b.id for b in season.bounties} == {"north_wolf_king", "mist_swordsman", "scarface"}
    assert season.daily_goals is not None and season.daily_goals.count == 3
    event = season.event_by_id()["mist_tide"]
    assert event.goal.weather == ("fog",) and event.goal.count == 30
    assert _problems(library, season) == []
    rel = [p.relative_to(library.root).as_posix() for p, _ in library.files]
    assert "world/season.yaml" in rel


def test_target_formula(season: SeasonContent) -> None:
    event = season.event_by_id()["mist_tide"]
    assert event.target_for(None) == 30
    assert event.target_for(4) == 15
    assert event.target_for(0) == 30  # 沒有上線紀錄：原門檻（5F-1b）
    assert event.target_for(1) == 8  # 30 ÷ 8 ＝ 3 → 下限 1/4 進位 ＝ 8
    assert event.target_for(2) == 8
    assert event.target_for(3) == 11
    assert event.target_for(8) == 30
    assert event.target_for(16) == 60


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (lambda d: d["schedule"].pop(1), "應從第"),
        (lambda d: d.update(days=13), "超過賽季天數|涵蓋"),
        (lambda d: d["daily_goals"].update(newbie=["starter_steps"]), "newbie"),
        (lambda d: d["daily_goals"].update(newbie=["a", "b", "c"]), "未知的目標"),
        (lambda d: d["bounties"].append(dict(d["bounties"][0])), "懸賞的 ID 重複"),
        (
            lambda d: d["daily_goals"]["goals"][0]["goal"].update(weather=["fog"]),
            "不能寫區域",
        ),
    ],
)
def test_schema_rejects(season: SeasonContent, patch: Any, message: str) -> None:
    data = _data(season)
    patch(data)
    with pytest.raises(ValidationError, match=message):
        SeasonContent.model_validate(data)


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (lambda d: d["bounties"][0].update(location="nowhere"), "未知的地點"),
        (lambda d: d["bounties"][0].update(group="nope"), "未知的陣容"),
        (lambda d: d["bounties"][0].update(group="sect_patrol"), "超過 4 名"),
        (lambda d: d["bounties"][0]["elite"].update(affix="nope"), "未知的詞綴"),
        (lambda d: d["world_events"][0]["goal"].update(weather=["snow"]), "未知的天氣"),
        (
            lambda d: d["world_events"][0]["on_failure"]["level_bonus"][0].update(region="mars"),
            "不在區域表",
        ),
    ],
)
def test_cross_file_problems(
    library: ContentLibrary, season: SeasonContent, patch: Any, message: str
) -> None:
    data = _data(season)
    patch(data)
    problems = _problems(library, SeasonContent.model_validate(data))
    assert any(message in p for p in problems), problems


# ---------------------------------------------------------------------------
# 影子循環賽（Phase 5F-4）
# ---------------------------------------------------------------------------


def _league_problems(library: ContentLibrary, season: SeasonContent) -> list[str]:
    assert library.regions is not None
    return season_problems(
        season,
        world_maps=library.world_maps,
        encounters=library.world_encounters,
        catalog=library.enemy_catalog(),
        weather_ids=set(library.weather),
        region_ids={r.id for r in library.regions.regions},
        location_kinds=get_args(LocationKind.__value__),
        battle_maps={k: v.archetype for k, v in library.maps.items()},
    )


def test_league_loaded(library: ContentLibrary, season: SeasonContent) -> None:
    assert season.league is not None
    assert season.league.signup_close_day == 13  # #101
    assert _league_problems(library, season) == []


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"seeds": 0}, "greater than or equal"),
        ({"seeds": 9}, "less than or equal"),
        ({"maps": ["swamp", "swamp"]}, "地圖重複"),
        ({"signup_close_day": 15}, "league.signup_close_day"),
    ],
)
def test_league_schema_rejects(season: SeasonContent, patch: Any, message: str) -> None:
    data = _data(season)
    data["league"] = {**data["league"], **patch}
    with pytest.raises(ValidationError, match=message):
        SeasonContent.model_validate(data)


@pytest.mark.parametrize(
    ("map_id", "message"),
    [("no_such_map", "不存在"), ("cloud_summit", "boss"), ("training_range", "training")],
)
def test_league_map_problems(
    library: ContentLibrary, season: SeasonContent, map_id: str, message: str
) -> None:
    data = _data(season)
    data["league"] = {**data["league"], "maps": [map_id]}
    problems = _league_problems(library, SeasonContent.model_validate(data))
    assert any(message in p for p in problems), problems
