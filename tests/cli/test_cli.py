"""trpg.cli.main 的測試。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from trpg import __version__
from trpg.cli.main import main
from trpg.content.loader import CONTENT_DIR_ENV
from trpg.shared.rng import Rng

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"trpg {__version__}"


def test_no_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_rng_u32_matches_rng(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rng", "--seed", "42", "--count", "5"]) == 0
    lines = capsys.readouterr().out.split()
    rng = Rng(42)
    assert [int(x) for x in lines] == [rng.next_u32() for _ in range(5)]


def test_rng_sides_matches_roll(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rng", "--seed", "42", "--count", "8", "--sides", "20"]) == 0
    lines = capsys.readouterr().out.split()
    rng = Rng(42)
    assert [int(x) for x in lines] == [rng.roll(20) for _ in range(8)]


def test_rng_default_count(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rng", "--seed", "1"]) == 0
    assert len(capsys.readouterr().out.split()) == 10


@pytest.mark.parametrize(
    "argv",
    [
        ["rng"],
        ["rng", "--seed", "abc"],
        ["rng", "--seed", "1", "--count", "-1"],
        ["rng", "--seed", "1", "--sides", "0"],
    ],
)
def test_rng_bad_arguments(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 2
    capsys.readouterr()


def test_rng_seed_out_of_range(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rng", "--seed", "-1"]) == 2
    assert "seed" in capsys.readouterr().err


def test_content_check_success(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CONTENT_DIR_ENV, raising=False)
    assert main(["content", "check"]) == 0
    out = capsys.readouterr().out
    assert "內容檢查通過" in out
    assert "elements.yaml：9 種元素" in out


def test_content_check_prints_map_warnings_without_failing(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    path = content / "maps" / "open_plain.yaml"
    extra = "\nregion: nowhere\nlook: {wall: marble}\n"
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    monkeypatch.setenv(CONTENT_DIR_ENV, str(content))
    assert main(["content", "check"]) == 0  # 警告不算失敗
    out = capsys.readouterr().out
    assert "內容檢查通過" in out
    assert "地圖外觀警告（2 項" in out
    assert "nowhere" in out
    assert "marble" in out


def test_content_check_failure(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    broken = tmp_path / "elements.yaml"
    original = (PROJECT_ROOT / "content" / "elements.yaml").read_text(encoding="utf-8")
    broken.write_text(original.replace("id: shadow", "id: shad0w"), encoding="utf-8")
    monkeypatch.setenv(CONTENT_DIR_ENV, str(tmp_path))
    assert main(["content", "check"]) == 1
    err = capsys.readouterr().err
    assert "內容檢查失敗" in err
    assert str(broken) in err


def test_content_check_missing_file(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(CONTENT_DIR_ENV, str(tmp_path))
    assert main(["content", "check"]) == 1
    assert str(tmp_path / "elements.yaml") in capsys.readouterr().err


def test_content_without_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["content"]) == 2
    capsys.readouterr()


def test_python_dash_m_trpg() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(PROJECT_ROOT / "src"), env.get("PYTHONPATH", "")) if p
    )
    completed = subprocess.run(
        [sys.executable, "-m", "trpg", "--version"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == f"trpg {__version__}"
