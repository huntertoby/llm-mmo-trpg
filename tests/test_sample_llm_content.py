"""``scripts/sample_llm_content.py`` 的極小測試（只用 Mock，不需網路）。"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sample_llm_content.py"


def test_sample_llm_content_mock_renders_report(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = [str(SCRIPT), "--mock", "--pool", "6", "--nature", "2", "--want", "3", "--flashes", "2"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "## 升級技能" in out and "## 名稱重複統計" in out and "## 閃現大變化" in out
