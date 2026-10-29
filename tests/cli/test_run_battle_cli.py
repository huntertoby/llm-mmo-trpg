"""跑步（Phase 3-20）的 CLI 驗收：AI 對戰的紀錄含跑步，重播一致。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


@pytest.mark.parametrize(("map_id", "seed"), [("open_plain", 0), ("dark_forest", 2)])
def test_battle_log_contains_runs_and_replays(
    map_id: str, seed: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "run.json"
    argv = ["battle", "--map", map_id, "--seed", str(seed), "--log-json", str(log)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "跑步（本回合移動 +3" in out  # 戰鬥紀錄有一行
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["format"] == "trpg-battle-log/88"
    assert any(a.get("type") == "run" for a in data["actions"])
    assert any(e["type"] == "unit_ran" for e in data["events"])
    assert main(["battle", "replay", str(log)]) == 0
    assert "重播驗證通過" in capsys.readouterr().out
