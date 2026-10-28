"""``trpg battle --ally-race``、``trpg run new --race``（Phase 3R-2）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_battle_with_ally_races_uses_race_skills_and_logs_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "log.json"
    argv = ["battle", "--map", "dark_forest", "--seed", "1", "--rounds-max", "10"]
    code, out, _ = _run([*argv, "--ally-race", "fox,fox,fox", "--log-json", str(log)], capsys)
    assert code == 0
    assert "發動種族技「狐火誘餌」" in out
    data = json.loads(log.read_text(encoding="utf-8"))
    assert any(a["type"] == "use_race_skill" for a in data["actions"])
    code, replayed, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "最終狀態一致" in replayed


def test_battle_without_race_args_has_no_race_skills(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        ["battle", "--map", "dark_forest", "--seed", "1", "--rounds-max", "6"], capsys
    )
    assert code == 0 and "種族技" not in out


def test_battle_rejects_unknown_races(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(
        ["battle", "--map", "dark_forest", "--seed", "1", "--ally-race", "elfin"], capsys
    )
    assert code == 2 and "未知的種族" in err


def test_run_new_race_is_saved(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["run", "new", "--seed", "4", "--build", "build_push", "--race", "orc"]
    code, _, _ = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    (save,) = tmp_path.glob("run-*.json")
    assert json.loads(save.read_text(encoding="utf-8"))["run"]["hero"]["race"] == "orc"
    code, _, err = _run(
        ["run", "new", "--seed", "4", "--build", "build_push", "--race", "elfin"], capsys
    )
    assert code == 2 and "未知的種族" in err
