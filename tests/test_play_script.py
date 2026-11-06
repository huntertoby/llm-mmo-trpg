"""``scripts/play.py``（Phase 3-3 5.4）：判斷是否需要建置前端、啟動 serve（不實際開埠）。"""

from __future__ import annotations

import os
import runpy
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "play.py"


@pytest.fixture(scope="module")
def play() -> dict[str, Any]:
    return runpy.run_path(str(SCRIPT), run_name="play_under_test")


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_needs_build_without_dist(play: dict[str, Any], tmp_path: Path) -> None:
    _touch(tmp_path / "src" / "main.tsx", 1000)
    assert play["needs_build"](tmp_path) is True


def test_needs_build_when_sources_are_newer(play: dict[str, Any], tmp_path: Path) -> None:
    _touch(tmp_path / "dist" / "index.html", 2000)
    _touch(tmp_path / "src" / "battle" / "log.ts", 1000)
    _touch(tmp_path / "package.json", 1000)
    assert play["needs_build"](tmp_path) is False
    _touch(tmp_path / "src" / "battle" / "log.ts", 3000)
    assert play["needs_build"](tmp_path) is True


def test_no_build_starts_serve_without_a_browser(
    play: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    import trpg.cli.main  # noqa: PLC0415

    seen: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        seen.append(argv)
        return 0

    monkeypatch.setattr(trpg.cli.main, "main", fake_main)
    assert play["main"](["--no-build", "--no-browser", "--port", "8123"]) == 0
    assert seen == [["serve", "--port", "8123"]]


def test_build_without_pnpm_exits_with_hint(
    play: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """MAC-1：corepack／pnpm／npx 都找不到時退出並提示安裝 pnpm。"""
    import trpg.cli.frontend  # noqa: PLC0415

    monkeypatch.setitem(play["main"].__globals__, "needs_build", lambda: True)
    monkeypatch.setattr(trpg.cli.frontend, "pnpm_command", lambda: None)
    assert play["main"](["--no-browser"]) == 1
    assert "npm install -g pnpm" in capsys.readouterr().err


def test_build_uses_found_pnpm(play: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """MAC-1：用 ``pnpm_command()`` 找到的指令前綴建置，再啟動 serve。"""
    import trpg.cli.frontend  # noqa: PLC0415
    import trpg.cli.main  # noqa: PLC0415

    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        commands.append(command)
        return type("Done", (), {"returncode": 0})()

    monkeypatch.setitem(play["main"].__globals__, "needs_build", lambda: True)
    monkeypatch.setattr(play["main"].__globals__["subprocess"], "run", fake_run)
    monkeypatch.setattr(trpg.cli.frontend, "pnpm_command", lambda: ["/fake/pnpm"])
    monkeypatch.setattr(trpg.cli.main, "main", lambda argv: 0)
    assert play["main"](["--no-browser"]) == 0
    assert [c[0] for c in commands] == ["/fake/pnpm", "/fake/pnpm"]
    assert [c[-1] for c in commands] == ["install", "build"]
