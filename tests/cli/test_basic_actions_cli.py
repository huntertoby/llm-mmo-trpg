"""基本動作守護、換位、瞄準（Phase 3-21a）的 CLI 驗收：AI 對戰的紀錄含這些動作，重播一致。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from trpg.cli.main import main


def _log(
    map_id: str, seed: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[dict[str, Any], str]:
    log = tmp_path / "basic.json"
    assert main(["battle", "--map", map_id, "--seed", str(seed), "--log-json", str(log)]) == 0
    out = capsys.readouterr().out
    return json.loads(log.read_text(encoding="utf-8")), out


def _replays(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["battle", "replay", str(tmp_path / "basic.json")]) == 0
    assert "重播驗證通過" in capsys.readouterr().out


def test_open_plain_battle_uses_guard_swap_and_aim_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data, out = _log(
        "open_plain", 98, tmp_path, capsys
    )  # 3-24a1：弓有拋射，AI 軌跡改變，種子 3 → 98；3H-1 常駐數值後 → 222；3H-2 武器技花耐力後 → 98
    assert data["format"] == "trpg-battle-log/89"
    kinds = {a["type"] for a in data["actions"]}
    assert {"swap", "aim"} <= kinds
    assert any(a["type"] == "defend" and a.get("target_id") for a in data["actions"])
    assert any(e["type"] == "attack_intercepted" and e.get("guard") for e in data["events"])
    assert "守護" in out and "瞄準" in out
    _replays(tmp_path, capsys)


@pytest.mark.parametrize(("map_id", "seed"), [("ruined_fort", 6), ("bridge_chasm", 0)])
def test_other_maps_replay_with_basic_actions(
    map_id: str, seed: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data, _ = _log(map_id, seed, tmp_path, capsys)
    kinds = {a["type"] for a in data["actions"]}
    assert kinds & {"swap", "aim"} or any(
        a["type"] == "defend" and a.get("target_id") for a in data["actions"]
    )
    _replays(tmp_path, capsys)
