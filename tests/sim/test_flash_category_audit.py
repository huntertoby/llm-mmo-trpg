"""``scripts/flash_category_audit.py``（BAL-2）：小規模能跑，而且輸出確定。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "flash_category_audit.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flash_category_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 要從 sys.modules 找到模組
    spec.loader.exec_module(module)
    return module


def _run(capsys: pytest.CaptureFixture[str], *extra: str) -> str:
    module = _load()
    code = module.main(
        ["--skills", "skill_bloodlust,skill_attack_mastery", "--seeds", "1", "--no-sim", *extra]
    )
    assert code == 0
    return capsys.readouterr().out


def test_audit_runs_on_two_skills_and_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = _run(capsys)
    assert "## A1." in first and "## A2." in first and "## B." in first
    assert "trigger_potency" in first and "mod_potency" in first
    assert _run(capsys) == first
