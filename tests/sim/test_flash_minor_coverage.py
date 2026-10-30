"""``scripts/flash_minor_coverage.py``（BAL-10a）：小規模能跑，而且輸出確定。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "flash_minor_coverage.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flash_minor_coverage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(capsys: pytest.CaptureFixture[str], csv_path: Path | None = None) -> str:
    module = _load()
    argv = ["--skills", "skill_bloodlust,skill_attack_mastery", "--seeds", "1"]
    if csv_path is not None:
        argv += ["--csv", str(csv_path)]
    assert module.main(argv) == 0
    return capsys.readouterr().out


def test_coverage_scan_runs_and_is_deterministic(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = tmp_path / "out.csv"
    first = _run(capsys, csv_path)
    assert "## 1." in first and "## 2." in first and "## 3." in first
    assert "skill_bloodlust" in first
    assert csv_path.read_text(encoding="utf-8").splitlines()[0].startswith("origin,skill_id")
    assert _run(capsys) == first
