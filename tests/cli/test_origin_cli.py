"""``trpg run new --origin``（Phase 3R-3a）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.cli.test_race_cli import _run


def test_run_new_origin_is_saved_and_unknown_origins_are_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "4", "--build", "build_push", "--race", "elf"]
    code, _, _ = _run(
        [*argv, "--origin", "origin_cloud_ridge", "--save-dir", str(tmp_path)], capsys
    )
    assert code == 0
    (save,) = tmp_path.glob("run-*.json")
    run = json.loads(save.read_text(encoding="utf-8"))["run"]
    assert run["origin"] == "origin_cloud_ridge" and run["hero"]["race"] == "elf"
    code, _, err = _run([*argv, "--origin", "origin_nowhere"], capsys)
    assert code == 2 and "未知的出身" in err
