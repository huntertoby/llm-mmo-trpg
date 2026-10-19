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
