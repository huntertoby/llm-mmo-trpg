"""``trpg run new|auto|show``（Phase 3-5a）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.roguelite.helpers import VICTORY, full_run, library
from trpg.cli.main import main
from trpg.roguelite import RunSave, auto_play, new_run, write_save


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_run_new_writes_a_save_and_show_reads_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "4", "--build", "build_push", "--attrs", "str=3,con=1"]
    code, out, _ = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    saves = list(tmp_path.glob("run-*.json"))
    assert len(saves) == 1
    assert str(saves[0]) in out
    assert "力量 13" in out and "體質 11" in out
    assert "第 6 場 Boss" in out
    raw = json.loads(saves[0].read_text(encoding="utf-8"))
    assert raw["format"] == "trpg-run/1"
    assert raw["run"]["seed"] == 4
    code, shown, _ = _run(["run", "show", str(saves[0])], capsys)
    assert code == 0
    assert "trpg-run/1" in shown and "build_push" in shown and "目前：戰鬥" in shown


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--build", "build_nobody"], "未知的 build"),
        (["--build", "build_push", "--attrs", "str=1"], "必須分配 4 點"),
    ],
)
def test_run_new_rejects_bad_input(
    argv: list[str], message: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(["run", "new", "--seed", "1", *argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 2
    assert message in err


def test_bad_attrs_format_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["run", "new", "--seed", "1", "--build", "x", "--attrs", "strong"], capsys)
    assert code == 2
    assert "--attrs" in err


def test_run_auto_is_deterministic_and_matches_the_library_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    build, seed = VICTORY
    argv = ["run", "auto", "--seed", str(seed), "--build", build]
    code, first, _ = _run(argv, capsys)
    assert code == 0
    _, second, _ = _run(argv, capsys)
    assert first == second
    assert "結果：勝利（6/6 場）" in first
    assert first.count("營火（第") == 2
    assert f"經驗 {full_run(*VICTORY).xp}" in first.splitlines()[-1]


def test_run_auto_from_a_mid_battle_save_finishes_the_same(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lib = library()
    run, battle = auto_play(
        lib,
        new_run(lib, *VICTORY),
        stop=lambda r, b: b is not None and b.index == 2 and len(b.steps) >= 10,
    )
    assert battle is not None
    path = write_save(tmp_path, RunSave(run_id="mid", run=run, battle=battle.to_saved()))
    code, out, _ = _run(
        ["run", "auto", "--from", str(path), "--save", "--save-dir", str(tmp_path)], capsys
    )
    assert code == 0
    assert "從存檔接續" in out
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["battle"] is None
    assert saved["run"] == json.loads(full_run(*VICTORY).model_dump_json())


def test_run_auto_needs_exactly_one_of_seed_and_from(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["run", "auto"], capsys)
    assert code == 2
    assert "--seed 或 --from" in err


def test_run_auto_ten_seeds_without_exceptions(capsys: pytest.CaptureFixture[str]) -> None:
    for seed in range(10):
        code, out, err = _run(["run", "auto", "--seed", str(seed)], capsys)
        assert code == 0, err
        assert out.splitlines()[-1].startswith("結果：")
