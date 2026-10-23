"""``trpg run new --test-mode --test-equipment``（Phase 3-39）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main

_START = ["--seed", "4", "--weapon", "one_handed_sword", "--keywords", "ignite,prone"]


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_run_new_test_mode_marks_the_save(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gear = "body=item_test_armor,ring_1=item_test_ring_hp"
    argv = ["run", "new", *_START, "--test-mode", "--test-equipment", gear]
    code, out, _ = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    assert "測試模式" in out and "body=item_test_armor" in out
    raw = json.loads(next(tmp_path.glob("run-*.json")).read_text(encoding="utf-8"))
    assert raw["run"]["test_mode"] is True
    assert raw["run"]["test_equipment"] == {
        "body": "item_test_armor",
        "ring_1": "item_test_ring_hp",
    }


def test_run_new_without_test_mode_prints_no_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(["run", "new", *_START, "--save-dir", str(tmp_path)], capsys)
    assert code == 0 and "測試模式" not in out
    raw = json.loads(next(tmp_path.glob("run-*.json")).read_text(encoding="utf-8"))
    assert raw["run"]["test_mode"] is False


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (["--test-equipment", "body=item_test_armor"], "只能在測試模式"),
        (["--test-mode", "--test-equipment", "body=item_nope"], "未知的物品"),
        (["--test-mode", "--test-equipment", "body"], "格式應為"),
    ],
)
def test_run_new_test_mode_rejects_bad_input(
    extra: list[str], message: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(["run", "new", *_START, *extra, "--save-dir", str(tmp_path)], capsys)
    assert code != 0 and message in err


def test_run_new_test_mode_rejects_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "1", "--build", "build_push", "--test-mode"]
    code, _, err = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code != 0 and "只能和" in err
