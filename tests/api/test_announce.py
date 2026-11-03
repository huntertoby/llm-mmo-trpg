"""全服首殺紀錄與公告文字（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.5、31.6）。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.announce import (
    AnnouncementSource,
    AnnouncementTemplates,
    DailyGoal,
    WorldEventProgress,
    daily_digest,
    load_templates,
    location_name,
    region_name,
    safe_text,
)
from trpg.server.first_kills import FirstKillError, FirstKillRegistry, load_first_kills
from trpg.shared.errors import ContentError
from trpg.world.actions import InsightGainedEvent, TravelAction
from trpg.world.clock import REAL_DAY_SECONDS
from trpg.world.replay import WorldLogEntry
from trpg.world.save import dumps_log, dumps_world, write_atomic
from trpg.world.state import ClearedLocation, WorldState

# 2026-11-03 06:00（UTC+8）＝ 2026-11-02 22:00 UTC
DAY0_6AM = 1793656800
ELITE = "mist_wolf+berserk"


def _store(library: ContentLibrary, root: Path) -> WorldStore:
    return WorldStore(library, SessionStore(library), root, prefetch=False, clock=lambda: DAY0_6AM)


def _event(kind: str = ELITE) -> InsightGainedEvent:
    return InsightGainedEvent(source=f"elite:{kind}", amount=1, insight=1)


def test_first_kill_recorded_once_per_kind(library: ContentLibrary, tmp_path: Path) -> None:
    store = _store(library, tmp_path)
    first = store.create("阿霧", "fire_staff", ["ignite", "marked"], seed=0)
    second = store.create("小美", "fire_staff", ["ignite", "marked"], seed=1)
    registry = FirstKillRegistry(library, tmp_path)
    added = registry.record(first, [_event()], seq=3, now=DAY0_6AM)
    assert [k.target for k in added] == [ELITE]
    assert added[0].name == "阿霧" and added[0].kind == "elite" and added[0].seq == 3
    assert "（" in added[0].target_name_zh  # 單位（詞綴）
    assert registry.record(second, [_event()], seq=4, now=DAY0_6AM + 1) == ()
    assert registry.record(second, [_event("other_elite")], seq=5, now=DAY0_6AM + 2)
    kills = load_first_kills(tmp_path / "first_kills.json")
    assert [(k.target, k.character_id) for k in kills] == [
        (ELITE, first.character_id),
        ("other_elite", second.character_id),
    ]
    raw = json.loads((tmp_path / "first_kills.json").read_text(encoding="utf-8"))
    assert raw["format"] == "trpg-firstkills/1"


def test_first_kill_file_format_checked(tmp_path: Path) -> None:
    path = tmp_path / "first_kills.json"
    path.write_text('{"format": "trpg-firstkills/9", "kills": []}', encoding="utf-8")
    with pytest.raises(FirstKillError, match="不認得"):
        load_first_kills(path)


def test_world_store_records_first_kills_from_actions(
    library: ContentLibrary, tmp_path: Path
) -> None:
    """`_apply` 之後才記：沒有精英事件的動作不建檔。"""
    store = _store(library, tmp_path)
    char = store.create("阿霧", "fire_staff", ["ignite", "marked"], seed=0)
    store.act(char.character_id, TravelAction(to=_neighbor(library, char.location)))
    assert not (tmp_path / "first_kills.json").exists()


def test_first_kill_write_failure_does_not_break_the_action(
    library: ContentLibrary,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """首殺紀錄寫入失敗只記 log，世界動作照常完成（5D-R2）。"""
    store = _store(library, tmp_path)
    char = store.create("阿霧", "fire_staff", ["ignite", "marked"], seed=0)

    def boom(*_args: object, **_kwargs: object) -> tuple[object, ...]:
        raise OSError("磁碟滿了")

    monkeypatch.setattr(store.first_kills, "record", boom)
    to = _neighbor(library, char.location)
    outcome = store.act(char.character_id, TravelAction(to=to))
    assert outcome.char.location == to
    assert store.entries()[-1].character_id == char.character_id
    assert "首殺紀錄寫入失敗" in caplog.text


def test_first_kill_season(library: ContentLibrary, tmp_path: Path) -> None:
    """首殺帶賽季；舊檔沒有 season_id＝第一季；按賽季算（下一季的第一個仍是首殺）。"""
    store = _store(library, tmp_path)
    first = store.create("阿霧", "fire_staff", ["ignite", "marked"], seed=0)
    second = store.create("小美", "fire_staff", ["ignite", "marked"], seed=1)
    registry = FirstKillRegistry(library, tmp_path)
    registry.record(first, [_event()], seq=1, now=DAY0_6AM)
    path = tmp_path / "first_kills.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["kills"][0]["season_id"] == "s1"
    del raw["kills"][0]["season_id"]
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_first_kills(path)[0].season_id == "s1"
    assert registry.record(second, [_event()], seq=2, now=DAY0_6AM, season_id="s1") == ()
    added = registry.record(second, [_event()], seq=3, now=DAY0_6AM, season_id="s2")
    assert [(k.season_id, k.character_id) for k in added] == [("s2", second.character_id)]
    assert len(load_first_kills(path)) == 2


def _neighbor(library: ContentLibrary, location: str) -> str:
    world_map = library.world_maps["cloud_ridge"]
    places = world_map.location_by_id()
    return next(
        n
        for n in sorted(world_map.neighbors(location))
        if not places[n].hidden and places[n].unlock_flag is None
    )


def test_templates_load_and_reject_unknown_variables(tmp_path: Path) -> None:
    templates = load_templates()
    assert "$season_day" in templates.daily
    bad = templates.model_dump()
    bad["first_kill"] = "$name 打倒了 $boss"
    with pytest.raises(ValueError, match="boss"):
        AnnouncementTemplates.model_validate(bad)
    folder = tmp_path / "world"
    folder.mkdir()
    (folder / "announcements.yaml").write_text("daily: x\n", encoding="utf-8")
    with pytest.raises(ContentError):
        load_templates(tmp_path)


def test_safe_text_neutralizes_mentions() -> None:
    assert "@everyone" not in safe_text("@everyone 快來")
    assert "<@123>" not in safe_text("<@123>")
    assert safe_text("a\nb") == "a b"
    assert len(safe_text("長" * 100)) == 40


def _world(root: Path, *, entries: Sequence[WorldLogEntry] = ()) -> None:
    world = WorldState(
        season_id="s1",
        season_seed=1,
        season_start=DAY0_6AM - 2 * REAL_DAY_SECONDS + 3600,  # 前天 7 點開季
        cleared=(ClearedLocation(region="cloud_ridge", location="a1", respawn_at=DAY0_6AM + 99),),
    )
    write_atomic(root / "world.json", dumps_world(world))
    write_atomic(root / "log.jsonl", dumps_log(entries))


def _entry(seq: int, now: int, cid: str) -> WorldLogEntry:
    return WorldLogEntry(seq=seq, now=now, character_id=cid, action=TravelAction(to="x1"))


def test_daily_digest_counts(tmp_path: Path) -> None:
    yesterday = DAY0_6AM - 3600
    entries = [
        _entry(1, yesterday, "c1"),
        _entry(2, yesterday + 1, "c1"),
        _entry(3, yesterday + 2, "c2"),
        _entry(4, DAY0_6AM + 10, "c3"),  # 今天的不算
        _entry(5, DAY0_6AM - 2 * REAL_DAY_SECONDS, "c4"),  # 前天的不算
    ]
    _world(tmp_path, entries=entries)
    digest = daily_digest(tmp_path, DAY0_6AM + 60)
    assert digest is not None
    assert digest.date == "2026-11-03" and digest.season_day == 3
    assert digest.active_yesterday == 2 and digest.cleared == 1 and digest.first_kills == 0
    assert digest.goals is None and digest.events is None
    assert daily_digest(tmp_path / "nope", DAY0_6AM) is None


class _Goals:
    def daily_goals(self, world: WorldState, now: int) -> Sequence[DailyGoal]:
        del world, now
        return [DailyGoal("打倒 3 隻霧狼 @here")]


class _Events:
    def world_events(self, world: WorldState, now: int) -> Sequence[WorldEventProgress]:
        del world, now
        return [WorldEventProgress("霧潮入侵", 12, 30)]


def test_daily_text_uses_interfaces_when_available(library: ContentLibrary, tmp_path: Path) -> None:
    _world(tmp_path)
    plain = AnnouncementSource(tmp_path, library=library).daily_text(DAY0_6AM)
    assert plain is not None and plain.count("尚未開放") == 2 and "入口" not in plain
    full = AnnouncementSource(
        tmp_path,
        library=library,
        public_url="https://trpg.example.com",
        goals=_Goals(),
        world_events=_Events(),
    ).daily_text(DAY0_6AM)
    assert full is not None
    assert "霧潮入侵：12／30" in full and "打倒 3 隻霧狼" in full
    assert "@here" not in full and "https://trpg.example.com" in full
    assert "尚未開放" not in full


def test_first_kill_text(library: ContentLibrary, tmp_path: Path) -> None:
    store = _store(library, tmp_path)
    char = store.create("@everyone", "fire_staff", ["ignite", "marked"], seed=0)
    FirstKillRegistry(library, tmp_path).record(char, [_event()], seq=1, now=DAY0_6AM)
    source = AnnouncementSource(tmp_path, library=library)
    (kill,) = source.first_kills()
    text = source.first_kill_text(kill)
    assert "首殺" in text and kill.target_name_zh in text and "@everyone" not in text
    # 不說地點（5E-3b）：區域名、地點名都不在公告裡
    assert region_name(library, kill.region) not in text
    assert location_name(library, kill.region, kill.location) not in text


def test_first_kill_template_rejects_location() -> None:
    bad = load_templates().model_dump()
    for variable in ("$location", "$region"):
        bad["first_kill"] = f"$name 在 {variable} 打倒了 $target"
        with pytest.raises(ValueError, match=variable.removeprefix("$")):
            AnnouncementTemplates.model_validate(bad)
