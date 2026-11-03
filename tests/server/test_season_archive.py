"""舊季的唯讀封存與重播查證（Phase 5F-5c；玩法 PM 2026-11-03 代決）。

真的跑一場循環賽（1 張地圖 × 1 個種子、2 人＝2 場），季末重置把世界日誌、循環賽與賽季 Boss 首殺的
戰鬥紀錄搬進 ``archive/<季>/`` 之後，從封存確定性重播查證；封存檔被改過要查得出來。
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.runner import BattleLog
from trpg.engine.state import BattleState
from trpg.server.first_kills import FIRST_KILLS_FILE, FirstKill
from trpg.server.league import LeagueRunner, LeagueStore
from trpg.server.season_archive import (
    ArchiveManifest,
    ArchiveRecordNotFoundError,
    season_archive_dir,
    verify_first_kill,
    verify_league_match,
)
from trpg.server.season_reset import season_reset
from trpg.shared.types import Team
from trpg.world.league_actions import LeagueEnterAction
from trpg.world.save import dumps_world, write_atomic
from trpg.world.state import WorldState
from trpg.world.step import new_character, world_step

NOON = 1_793_592_000
DAY = 24 * 3600
AFTER = NOON + 13 * DAY
ENDED = NOON + 15 * DAY
BOSS = "rift_shard_lord"


@pytest.fixture(scope="module")
def small() -> ContentLibrary:
    library = load_library()
    season = library.world_season
    assert season is not None and season.league is not None
    league = season.league.model_copy(update={"maps": ("open_plain",), "seeds": 1})
    return dataclasses.replace(library, world_season=season.model_copy(update={"league": league}))


@dataclasses.dataclass
class Played:
    save_dir: Path
    world_dir: Path
    match_ids: tuple[str, ...]


def _won_by_ally(path: Path) -> bool:
    log = BattleLog.model_validate_json(path.read_text(encoding="utf-8"))
    state: BattleState = log.final_state
    return state.winner is Team.ALLY


@pytest.fixture(scope="module")
def played(small: ContentLibrary, tmp_path_factory: pytest.TempPathFactory) -> Played:
    """跑完一季（循環賽 2 場＋一筆用其中一場當戰鬥紀錄的賽季 Boss 首殺），留一份沒重置的範本。"""
    save_dir = tmp_path_factory.mktemp("season") / "saves"
    world_dir = save_dir / "world"
    world = WorldState(season_id="s1", season_seed=20261102, season_start=NOON)
    heroes = {b.id: b.hero for b in small.builds.builds}
    for index, build in enumerate(("build_support", "build_charger")):
        char = new_character(small, f"c{index}", heroes[build], region="cloud_ridge")
        world = world_step(
            small, world, char, LeagueEnterAction(), NOON + index, actor=f"acc{index}"
        ).world
    write_atomic(world_dir / "world.json", dumps_world(world))
    store = LeagueStore(small, world_dir)
    record = store.start(world, AFTER)
    LeagueRunner(store).run_pending()
    matches = world_dir / "league" / "matches"
    won = next(m.id for m in record.matches if _won_by_ally(matches / f"{m.id}.json"))
    boss_log = world_dir / "season_boss" / "s1-first-kill.json"
    boss_log.parent.mkdir(parents=True)
    shutil.copyfile(matches / f"{won}.json", boss_log)
    kill = FirstKill(
        kind="season_boss",
        target=BOSS,
        target_name_zh="碎晶之主",
        character_id="c0",
        name="勇者c0",
        region="cloud_ridge",
        location="rift_gate",
        seq=1,
        at=NOON + 9 * DAY,
        battle_log="season_boss/s1-first-kill.json",
    )
    data = {"format": "trpg-firstkills/1", "kills": [kill.model_dump(mode="json")]}
    write_atomic(world_dir / FIRST_KILLS_FILE, json.dumps(data, ensure_ascii=False))
    entries = [
        {"seq": 0, "now": NOON, "character_id": "c1", "action": {"kind": "rest"}},
        {"seq": 1, "now": NOON + 9 * DAY, "character_id": "c0", "action": {"kind": "rest"}},
    ]
    write_atomic(world_dir / "log.jsonl", "".join(json.dumps(e) + "\n" for e in entries))
    return Played(save_dir, world_dir, tuple(m.id for m in record.matches))


def _copy(played: Played, root: Path) -> Played:
    save_dir = root / "saves"
    shutil.copytree(played.save_dir, save_dir)
    return Played(save_dir, save_dir / "world", played.match_ids)


def _reset(library: ContentLibrary, played: Played) -> None:
    season_reset(
        library,
        played.save_dir,
        start=ENDED + 5 * DAY,
        now=ENDED,
        backup_root=played.save_dir.parent / "backups",
        dry_run=False,
    )


def test_current_season_verifies_from_the_world_folder(played: Played) -> None:
    check = verify_league_match(played.save_dir, played.world_dir, "s1", played.match_ids[0])
    assert check.source == "world" and check.ok, check.problems


def test_archived_season_replays_and_matches_the_records(
    small: ContentLibrary, played: Played, tmp_path: Path
) -> None:
    season = _copy(played, tmp_path)
    _reset(small, season)
    archived = season_archive_dir(season.save_dir, "s1")
    assert not (season.world_dir / "league").exists()
    for match_id in season.match_ids:
        check = verify_league_match(season.save_dir, season.world_dir, "s1", match_id)
        assert check.source == "archive" and check.ok, check.problems
        assert any("重播一致" in p for p in check.passed)
    kill = verify_first_kill(season.save_dir, season.world_dir, "s1", BOSS)
    assert kill.source == "archive" and kill.ok, kill.problems
    actions = len(_actions(archived / "season_boss" / "s1-first-kill.json"))
    assert kill.passed == (
        "世界日誌序號 1 是 勇者c0 的動作",
        f"戰鬥紀錄重播一致（{actions} 個動作）",
        "那一場是我方勝",
    )
    manifest = ArchiveManifest.model_validate_json(
        (archived / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.season_id == "s1" and manifest.archived_at == ENDED
    with pytest.raises(ArchiveRecordNotFoundError):
        verify_league_match(season.save_dir, season.world_dir, "s1", "no_such_match")
    with pytest.raises(ArchiveRecordNotFoundError):
        verify_first_kill(season.save_dir, season.world_dir, "s0", BOSS)


def _actions(path: Path) -> list[object]:
    return list(BattleLog.model_validate_json(path.read_text(encoding="utf-8")).actions)


def test_a_tampered_archive_is_caught(
    small: ContentLibrary, played: Played, tmp_path: Path
) -> None:
    season = _copy(played, tmp_path)
    _reset(small, season)
    archived = season_archive_dir(season.save_dir, "s1")
    match_id = season.match_ids[0]
    path = archived / "league" / "matches" / f"{match_id}.json"
    assert not os.access(path, os.W_OK)  # 封存是唯讀
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["seed"] = data["seed"] + 1
    path.write_text(json.dumps(data), encoding="utf-8")
    check = verify_league_match(season.save_dir, season.world_dir, "s1", match_id)
    assert not check.ok
    assert any("sha256" in p for p in check.problems)
    assert any("重播" in p for p in check.problems)


def _script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "season_verify.py"
    spec = importlib.util.spec_from_file_location("season_verify_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["season_verify_script"] = module
    spec.loader.exec_module(module)
    return module


def test_script_verifies_from_the_archive(
    small: ContentLibrary, played: Played, tmp_path: Path
) -> None:
    season = _copy(played, tmp_path)
    _reset(small, season)
    script = _script()
    out, err = io.StringIO(), io.StringIO()
    base = ["--season-id", "s1", "--save-dir", str(season.save_dir)]
    assert script.main([*base, "--first-kill", BOSS], out=out, err=err) == 0
    assert out.getvalue().startswith("一致：s1 碎晶之主的首殺：勇者c0（讀封存）")
    assert script.main([*base, "--match", season.match_ids[1]], out=out, err=err) == 0
    assert script.main([*base, "--match", "nope"], out=out, err=err) == script.EXIT_ERROR
    assert "找不到" in err.getvalue()
