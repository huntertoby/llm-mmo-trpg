"""遊戲伺服器的心跳檔（Phase 5F-R1）：命令列季末重置偵測到伺服器開著就拒絕 ``--execute``。"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from tests.server.test_season_reset import _fake_season, _script, _tree
from trpg.api.app import create_app
from trpg.api.llm_source import MockLlmProvider
from trpg.content.library import ContentLibrary
from trpg.server.server_presence import (
    PRESENCE_FORMAT,
    STALE_AFTER_S,
    ServerPresence,
    running_server,
)
from trpg.world.layout import SERVER_LOCK_FILE

NOW = 1_800_000_000


def test_start_writes_and_stop_removes(tmp_path: Path) -> None:
    clock = iter(range(NOW, NOW + 100))
    presence = ServerPresence(tmp_path, interval_s=0, clock=lambda: next(clock))
    assert running_server(tmp_path, NOW) is None
    presence.start()
    info = running_server(tmp_path, NOW + 5)
    assert info is not None and info.pid == os.getpid() and info.started_at == NOW
    presence.beat()
    beat = running_server(tmp_path, NOW + 5)
    assert beat is not None and beat.heartbeat_at > info.heartbeat_at
    presence.stop()
    assert not (tmp_path / SERVER_LOCK_FILE).exists()
    assert running_server(tmp_path, NOW + 5) is None


def test_stale_heartbeat_is_not_running(tmp_path: Path) -> None:
    presence = ServerPresence(tmp_path, interval_s=0, clock=lambda: NOW)
    presence.start()  # 不呼叫 stop：模擬伺服器當掉、檔案留著
    assert running_server(tmp_path, NOW + STALE_AFTER_S) is not None
    assert running_server(tmp_path, NOW + STALE_AFTER_S + 1) is None


def test_bad_file_is_not_running(tmp_path: Path) -> None:
    path = tmp_path / SERVER_LOCK_FILE
    path.write_text("不是 JSON", encoding="utf-8")
    assert running_server(tmp_path, NOW) is None
    path.write_text(json.dumps({"format": "x", "pid": 1, "heartbeat_at": NOW}), encoding="utf-8")
    assert running_server(tmp_path, NOW) is None


def test_stop_keeps_other_process_file(tmp_path: Path) -> None:
    presence = ServerPresence(tmp_path, interval_s=0, clock=lambda: NOW)
    presence.start()
    other = {"format": PRESENCE_FORMAT, "pid": -1, "started_at": NOW, "heartbeat_at": NOW}
    (tmp_path / SERVER_LOCK_FILE).write_text(json.dumps(other), encoding="utf-8")
    presence.stop()
    assert (tmp_path / SERVER_LOCK_FILE).exists()


def test_app_lifespan_holds_presence(tmp_path: Path, library: ContentLibrary) -> None:
    app = create_app(library, save_dir=tmp_path, llm=MockLlmProvider(), hold_presence=True)
    world_dir = tmp_path / "world"
    with TestClient(app):
        assert (world_dir / SERVER_LOCK_FILE).is_file()
        data = json.loads((world_dir / SERVER_LOCK_FILE).read_text(encoding="utf-8"))
        assert data["format"] == PRESENCE_FORMAT and data["pid"] == os.getpid()
    assert not (world_dir / SERVER_LOCK_FILE).exists()


def test_app_without_presence_writes_nothing(tmp_path: Path, library: ContentLibrary) -> None:
    """測試與其他呼叫端預設不寫心跳檔（不動真正的存檔資料夾）。"""
    with TestClient(create_app(library, save_dir=tmp_path, llm=MockLlmProvider())):
        assert not (tmp_path / "world" / SERVER_LOCK_FILE).exists()


def test_script_refuses_execute_while_server_runs(tmp_path: Path, library: ContentLibrary) -> None:
    season = _fake_season(library, tmp_path)
    script = _script()
    base = [
        "--start-date",
        "2027-01-01",
        "--save-dir",
        str(season.save_dir),
        "--accounts-dir",
        str(season.save_dir / "accounts"),
        "--backup-root",
        str(tmp_path / "backups"),
        "--execute",
    ]
    presence = ServerPresence(season.world_dir, interval_s=0)
    presence.start()
    try:
        before = _tree(season.save_dir)
        out, err = io.StringIO(), io.StringIO()
        assert script.main(base, out, err) == script.EXIT_ERROR
        assert "遊戲伺服器還開著" in err.getvalue() and "--force-server" in err.getvalue()
        # 5F-R2：--force 拆成兩個各自獨立的旗標；--force-season 不略過伺服器心跳
        out, err = io.StringIO(), io.StringIO()
        assert script.main([*base, "--force-season"], out, err) == script.EXIT_ERROR
        assert "遊戲伺服器還開著" in err.getvalue()
        out, err = io.StringIO(), io.StringIO()
        assert script.main([*base, "--force"], out, err) == script.EXIT_ERROR  # 舊旗標：說明怎麼改
        assert "--force-season" in err.getvalue() and "--force-server" in err.getvalue()
        assert _tree(season.save_dir) == before
        out, err = io.StringIO(), io.StringIO()
        both = [*base, "--force-server", "--force-season"]  # 真實時間：假賽季可能還沒結束
        assert script.main(both, out, err) == 0
        assert "已重置：s1 → s2" in out.getvalue()
        assert "似乎還開著" in err.getvalue()
        assert (season.world_dir / SERVER_LOCK_FILE).is_file()  # 重置不動心跳檔
    finally:
        presence.stop()


def test_force_server_does_not_skip_unfinished_season(
    tmp_path: Path, library: ContentLibrary
) -> None:
    """5F-R2：--force-server 只略過伺服器心跳；賽季沒結束照樣要 --force-season。"""
    season = _fake_season(library, tmp_path)
    script = _script()
    world = season.world_dir / "world.json"
    data = json.loads(world.read_text(encoding="utf-8"))
    data["season_start"] = 4_102_444_800  # 2100 年才開賽：一定還沒結束
    world.write_text(json.dumps(data), encoding="utf-8")
    base = ["--start-date", "2027-01-01", "--save-dir", str(season.save_dir)]
    base += ["--accounts-dir", str(season.save_dir / "accounts"), "--force-server"]
    out, err = io.StringIO(), io.StringIO()
    assert script.main(base, out, err) == script.EXIT_ERROR
    assert "還沒結束" in err.getvalue() and "--force-season" in err.getvalue()
    out, err = io.StringIO(), io.StringIO()
    assert script.main([*base, "--force-season"], out, err) == 0
    assert "dry-run" in out.getvalue()
