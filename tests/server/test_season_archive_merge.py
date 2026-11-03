"""封存中斷後重跑（Phase 5F-R1）：併入既有的 ``archive/<季>/``，不另開 ``-2`` 資料夾。"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from trpg.server.season_archive import (
    ArchiveManifest,
    SeasonArchiveError,
    archive_season,
    season_archive_dir,
)
from trpg.world.layout import FIRST_KILL_DIR, LEAGUE_DIR, LEAGUE_FILE, LEAGUE_MATCHES_DIR, LOG_FILE
from trpg.world.save import write_atomic

NOW = 1_800_000_000


def _world(save_dir: Path) -> Path:
    world = save_dir / "world"
    write_atomic(world / LOG_FILE, '{"seq": 1}\n')
    write_atomic(world / LEAGUE_DIR / LEAGUE_FILE, '{"league": 1}\n')
    write_atomic(world / LEAGUE_DIR / LEAGUE_MATCHES_DIR / "m1.json", '{"m": 1}\n')
    write_atomic(world / LEAGUE_DIR / LEAGUE_MATCHES_DIR / "m2.json", '{"m": 2}\n')
    write_atomic(world / FIRST_KILL_DIR / "s1-first-kill.json", '{"log": 1}\n')
    return world


def _tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _manifest(folder: Path) -> ArchiveManifest:
    return ArchiveManifest.model_validate_json((folder / "manifest.json").read_text("utf-8"))


def _writable(folder: Path) -> None:
    """tmp_path 清理用：封存是唯讀的。"""
    for p in folder.rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)


def test_rerun_merges_into_existing_archive(tmp_path: Path) -> None:
    """第一次只搬了一部分（世界日誌、一場循環賽）就中斷；重跑時剩下的併進同一個資料夾。"""
    save = tmp_path / "saves"
    world = _world(save)
    full = _tree(world)
    target = season_archive_dir(save, "s1")
    # 模擬中斷：日誌與 m1 已搬進封存（唯讀），m1 在世界資料夾還有同一份（rename 前複製的情況）
    for relative in (LOG_FILE, f"{LEAGUE_DIR}/{LEAGUE_MATCHES_DIR}/m1.json"):
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((world / relative).read_bytes())
        os.chmod(dest, stat.S_IRUSR)
    (world / LOG_FILE).unlink()
    try:
        archived = archive_season(save, world, "s1", NOW)
        assert archived == target
        assert not (save / "archive" / "s1-2").exists()
        assert not any((target / name).exists() for name in ("log-2.jsonl", "league-2"))
        tree = _tree(target)
        assert {k: v for k, v in tree.items() if k != "manifest.json"} == full
        assert [f.path for f in _manifest(target).files] == sorted(full)
        assert not any(world.iterdir())  # 世界資料夾的 ARCHIVED 全部搬空
        # 再跑一次（什麼都沒剩）：封存不變
        archive_season(save, world, "s1", NOW)
        assert {k: v for k, v in _tree(target).items() if k != "manifest.json"} == full
    finally:
        _writable(target)


def test_rerun_with_different_content_is_refused(tmp_path: Path) -> None:
    save = tmp_path / "saves"
    world = _world(save)
    target = season_archive_dir(save, "s1")
    dest = target / LEAGUE_DIR / LEAGUE_MATCHES_DIR / "m2.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text('{"m": "不同"}\n', encoding="utf-8")
    before_world, before_archive = _tree(world), _tree(target)
    with pytest.raises(SeasonArchiveError, match=r"m2.json"):
        archive_season(save, world, "s1", NOW)
    assert _tree(world) == before_world  # 什麼都不動
    assert _tree(target) == before_archive
