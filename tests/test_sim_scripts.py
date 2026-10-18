"""``scripts/sim_demo_maps.py`` 是 ``trpg sim maps`` 的薄包裝（Phase 2C-1 3.2）。

技能使用統計的收集與歸屬規則在 ``trpg.sim.metrics``，測試見 ``tests/sim/test_metrics.py``。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sim_demo_maps.py"


def test_sim_demo_maps_forwards_its_arguments_to_trpg_sim_maps(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--maps", "oil_depot", "--seeds", "2"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "## oil_depot（2 場" in out and "技能使用：" in out
