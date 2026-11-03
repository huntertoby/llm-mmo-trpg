"""影子循環賽的賽果存檔與背景執行（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.5～36.6）。"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.runner import log_replay_problem, replay
from trpg.server.league import (
    LeagueError,
    LeagueMatch,
    LeagueMatchNotFoundError,
    LeagueRecord,
    LeagueRunner,
    LeagueStore,
    standings,
)
from trpg.world.league_actions import LeagueEnterAction
from trpg.world.state import WorldState
from trpg.world.step import new_character, world_step

NOON = 1_793_592_000
DAY = 24 * 3600
AFTER = NOON + 13 * DAY  # 第 14 天（截止後）


@pytest.fixture(scope="module")
def small() -> ContentLibrary:
    """循環賽只有 1 張地圖 × 1 個種子（每對 2 場）的內容庫（測試快）。"""
    library = load_library()
    season = library.world_season
    assert season is not None and season.league is not None
    league = season.league.model_copy(update={"maps": ("open_plain",), "seeds": 1, "batch_size": 1})
    return dataclasses.replace(library, world_season=season.model_copy(update={"league": league}))


def _world(library: ContentLibrary, builds: tuple[str, ...]) -> WorldState:
    world = WorldState(season_id="s1", season_seed=20261102, season_start=NOON)
    heroes = {b.id: b.hero for b in library.builds.builds}
    for index, build in enumerate(builds):
        cid = f"c{index}"
        char = new_character(library, cid, heroes[build], region="cloud_ridge")
        world = world_step(
            library, world, char, LeagueEnterAction(), NOON + index, actor=f"acc{index}"
        ).world
    return world


def test_start_conditions(small: ContentLibrary, tmp_path: Path) -> None:
    store = LeagueStore(small, tmp_path)
    world = _world(small, ("build_support", "build_charger"))
    with pytest.raises(LeagueError, match="還沒截止"):
        store.start(world, NOON + 12 * DAY)  # 第 13 天
    with pytest.raises(LeagueError, match="不到 2 位"):
        store.start(_world(small, ("build_support",)), AFTER)
    assert store.record() is None


def test_run_all_and_resume(small: ContentLibrary, tmp_path: Path) -> None:
    world = _world(small, ("build_support", "build_charger", "build_storm"))
    store = LeagueStore(small, tmp_path)
    record = store.start(world, AFTER)
    assert len(record.matches) == 3 * 2  # C(3,2) 組合 × 1 地圖 × 1 種子 × 先後手
    assert record.entries == world.league_entries
    assert all(m.status == "pending" for m in record.matches)
    runner = LeagueRunner(store)
    assert runner.run_pending(limit=2) == 2
    # 重啟：新的 store 從檔案讀，只接續 pending
    again = LeagueStore(small, tmp_path)
    loaded = again.record()
    assert loaded is not None and loaded.done == 2
    assert again.start(world.model_copy(update={"league_entries": ()}), AFTER) == loaded  # 沿用
    second = LeagueRunner(again)
    assert second.start() is True
    second.join(120)
    final = again.record()
    assert final is not None and final.done == 6
    assert all(m.status == "done" for m in final.matches)
    # 每場可重播：紀錄檔的步驟重播出相同的最終狀態
    for match in final.matches:
        log = again.log(match.id)
        assert log_replay_problem(log) is None
        assert log.seed == match.seed
        assert replay(log.setup, log.seed, log.actions).state == log.final_state
    table = standings(final)
    assert sum(r.wins for r in table) == sum(1 for m in final.matches if m.winner is not None)
    assert all(r.played == 4 for r in table)
    assert [r.rank for r in table] == sorted(r.rank for r in table)


def test_same_inputs_same_results(small: ContentLibrary, tmp_path: Path) -> None:
    world = _world(small, ("build_support", "build_charger"))
    results = []
    for folder in ("a", "b"):
        store = LeagueStore(small, tmp_path / folder)
        store.start(world, AFTER)
        LeagueRunner(store).run_pending()
        record = store.record()
        assert record is not None
        results.append([(m.id, m.winner, m.rounds) for m in record.matches])
    assert results[0] == results[1]


def test_match_error_is_recorded(small: ContentLibrary, tmp_path: Path) -> None:
    world = _world(small, ("build_support", "build_charger"))
    store = LeagueStore(small, tmp_path)
    record = store.start(world, AFTER)
    broken = record.matches[0].model_copy(update={"map": "no_such_map"})
    store._save(record.with_match(broken))  # 模擬壞掉的賽程
    LeagueRunner(store).run_pending()
    final = store.record()
    assert final is not None
    first, second = final.matches
    assert first.status == "error" and first.error
    assert second.status == "done"
    with pytest.raises(LeagueMatchNotFoundError):
        store.log(first.id)


def test_standings_order_and_ties() -> None:
    def entry(account: str, at: int) -> object:
        return {
            "account": account,
            "character_id": account,
            "name": account,
            "snapshot": {
                "owner": account,
                "hero": load_library().builds.builds[0].hero.model_dump(mode="json"),
                "level": 1,
                "region": "cloud_ridge",
                "location": "mist_ferry",
                "saved_at": 0,
            },
            "entered_at": at,
        }

    def match(n: int, a: str, b: str, winner: str | None) -> LeagueMatch:
        return LeagueMatch(
            id=f"m{n:04d}",
            a=a,
            b=b,
            map="swamp",
            seed_index=0,
            seed=n,
            ally=a,
            status="done",
            winner=winner,
        )

    record = LeagueRecord.model_validate(
        {
            "season_id": "s1",
            "started_at": 0,
            "entries": [entry("x", 3), entry("y", 1), entry("z", 2)],
            "matches": [
                match(1, "x", "y", "x").model_dump(),
                match(2, "x", "z", "z").model_dump(),
                match(3, "y", "z", None).model_dump(),
            ],
        }
    )
    table = standings(record)
    # z 1 勝 0 負 1 和、x 1 勝 1 負、y 0 勝 1 負 1 和
    assert [(r.account, r.rank, r.wins, r.losses, r.draws) for r in table] == [
        ("z", 1, 1, 0, 1),
        ("x", 2, 1, 1, 0),
        ("y", 3, 0, 1, 1),
    ]
    # 三人都 1 勝 1 負：同名次第 1，依報名先後排（代決 5F4-8）
    tied = record.with_match(match(3, "y", "z", "y"))
    assert [(r.account, r.rank) for r in standings(tied)] == [("y", 1), ("z", 1), ("x", 1)]
