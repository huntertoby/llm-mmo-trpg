"""``season.yaml`` 依季 ID 覆寫與季名模板（Phase 5F-R2）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.world.helpers import NOON, hero, make_world
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_season import SeasonContent, SeasonNaming
from trpg.server.season_reset import season_name_zh
from trpg.shared.errors import ContentError
from trpg.world.actions import CampAction
from trpg.world.layout import WORLD_FILE
from trpg.world.league import league_rules
from trpg.world.save import dumps_world
from trpg.world.season_boss import boss_def
from trpg.world.step import new_character, world_step


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def season(library: ContentLibrary) -> SeasonContent:
    assert library.world_season is not None
    return library.world_season


def _with(season: SeasonContent, overrides: dict[str, Any]) -> SeasonContent:
    data = season.model_dump(mode="json")
    data["seasons"] = overrides
    return SeasonContent.model_validate(data)


# ---------------------------------------------------------------------------
# 覆寫
# ---------------------------------------------------------------------------


def test_first_season_is_the_default(library: ContentLibrary, season: SeasonContent) -> None:
    assert season.seasons == {}
    assert season.for_season("s1") is season
    assert library.for_season("s1") is library  # 第一季：同一個內容庫，行為完全不變
    assert library.for_season("s9") is library


def test_override_replaces_only_listed_items(season: SeasonContent) -> None:
    assert season.season_boss is not None and season.league is not None
    boss = season.season_boss.model_copy(update={"daily_attempts": 5})
    league = season.league.model_copy(update={"seeds": 1})
    events = season.world_events[:1]
    data: dict[str, Any] = {
        "s2": {
            "name_zh": "第二季・餘燼",
            "season_boss": boss.model_dump(mode="json"),
            "league": league.model_dump(mode="json"),
            "world_events": [e.model_dump(mode="json") for e in events],
        },
        "s3": {"league": None},
    }
    # 世界事件只剩第一個時，Boss 的解鎖旗標要另外有事件給：沿用預設的 seal_resonance
    data["s2"]["world_events"].append(
        season.event_by_id()["seal_resonance"].model_dump(mode="json")
    )
    full = _with(season, data)
    s2 = full.for_season("s2")
    assert s2.season_boss is not None and s2.season_boss.daily_attempts == 5
    assert s2.league is not None and s2.league.seeds == 1
    assert [e.id for e in s2.world_events] == ["mist_tide", "seal_resonance"]
    assert s2.days == season.days and s2.bounties == season.bounties  # 沒寫的沿用
    assert s2.seasons == {}
    s3 = full.for_season("s3")
    assert s3.league is None and s3.season_boss == season.season_boss
    assert full.for_season("s1") is full
    assert full.name_of("s2") == "第二季・餘燼" and full.name_of("s3") == "第三季"


def test_override_days(season: SeasonContent) -> None:
    schedule = [p.model_dump(mode="json") for p in season.schedule]
    schedule[-1]["days"] = [14, 15]
    s2 = _with(season, {"s2": {"days": 15, "schedule": schedule}}).for_season("s2")
    assert s2.days == 15 and s2.schedule[-1].days == (14, 15)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"days": 20}, "seasons.s2：.*日程要涵蓋第 1～20 天"),
        ({"days": 10}, "seasons.s2：日程要涵蓋第 1～10 天"),
        ({"days": None}, "seasons.s2"),
        ({"bogus": 1}, "bogus"),
    ],
)
def test_bad_override_rejected(
    season: SeasonContent, override: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _with(season, {"s2": override})


def test_bad_season_id_rejected(season: SeasonContent) -> None:
    with pytest.raises(ValidationError, match="季 ID 格式錯誤"):
        _with(season, {"S-2": {"league": None}})


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def _write_overrides(content: Path, overrides: dict[str, Any]) -> None:
    path = content / "world" / "season.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["seasons"] = overrides
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_library_for_season(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    _write_overrides(content, {"s2": {"league": None, "name_zh": "餘燼之季"}})
    loaded = load_library(content)
    s2 = loaded.for_season("s2")
    assert s2 is not loaded and loaded.for_season("s2") is s2  # 快取
    assert league_rules(s2) is None and league_rules(loaded) is not None
    assert boss_def(s2) == boss_def(loaded)
    assert s2.for_season("s1") is loaded and s2.for_season("s2") is s2
    assert s2.skills is loaded.skills  # 其他內容不變
    assert season_name_zh("s2", s2) == "餘燼之季" == season_name_zh("s2", loaded)
    assert season_name_zh("s1", s2) == "第一季"


def test_override_cross_file_checked(tmp_path: Path, library: ContentLibrary) -> None:
    """每一季套上覆寫後都要通過跨檔案檢查（地圖、狀態、地點……）。"""
    content = _copy_content(tmp_path, library)
    assert library.world_season is not None and library.world_season.league is not None
    league = library.world_season.league.model_dump(mode="json")
    league["maps"] = ["no_such_map"]
    _write_overrides(content, {"s2": {"league": league}})
    with pytest.raises(ContentError, match=r"seasons\.s2：循環賽的地圖 no_such_map 不存在"):
        load_library(content)


def test_world_store_uses_current_season(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    _write_overrides(content, {"s2": {"league": None}})
    loaded = load_library(content)
    root = tmp_path / "world"
    root.mkdir()
    store = WorldStore(loaded, SessionStore(loaded), root, prefetch=False, clock=lambda: NOON)
    assert store.library is loaded  # 還沒有世界存檔：原本的內容庫，不建立世界
    assert not (root / WORLD_FILE).exists()
    (root / WORLD_FILE).write_text(dumps_world(make_world(season_id="s2")), encoding="utf-8")
    assert league_rules(store.library) is None
    assert league_rules(store.league.library) is None


# ---------------------------------------------------------------------------
# 季名模板
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "text"),
    [
        (0, "零"),
        (1, "一"),
        (10, "十"),
        (11, "十一"),
        (23, "二十三"),
        (99, "九十九"),
        (100, "一百"),
        (101, "一百零一"),
        (110, "一百一十"),
        (1001, "一千零一"),
        (1010, "一千零一十"),
        (9999, "九千九百九十九"),
        (10000, "10000"),
    ],
)
def test_number_zh(number: int, text: str) -> None:
    assert SeasonNaming().number_zh(number) == text


def test_naming_from_yaml(season: SeasonContent) -> None:
    assert season.naming == SeasonNaming()  # season.yaml 寫的＝原本程式裡的寫法
    assert season.name_of("s1") == "第一季"
    assert season.name_of("s100") == "第一百季"  # 原本只支援到 99
    assert season.name_of("beta") == "賽季 beta"
    custom = SeasonNaming(template="Season {number}", fallback="{id}", digits="0123456789")
    assert custom.name_of("s3") == "Season 3" and custom.name_of("x") == "x"


@pytest.mark.parametrize(
    "update", [{"template": "第季"}, {"template": "{number}{id}"}, {"fallback": "賽季"}]
)
def test_naming_rejects(update: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="季名模板"):
        SeasonNaming(**update)


def test_world_step_follows_season(tmp_path: Path, library: ContentLibrary) -> None:
    """世界規則（換日、世界事件）照世界的季 ID 用那一季的覆寫。"""
    assert library.world_season is not None
    keep = library.world_season.event_by_id()["seal_resonance"].model_dump(mode="json")
    content = _copy_content(tmp_path, library)
    _write_overrides(content, {"s2": {"world_events": [keep]}})
    loaded = load_library(content)
    char = new_character(loaded, "alice", hero(loaded), region="cloud_ridge")
    char = char.model_copy(update={"location": "hunter_hut", "supplies": 5})
    for season_id, has_mist in (("s1", True), ("s2", False)):
        world = make_world(season_id=season_id)
        result = world_step(loaded, world, char, CampAction(), NOON, actor="acc")
        assert (result.world.world_event("mist_tide") is not None) is has_mist
