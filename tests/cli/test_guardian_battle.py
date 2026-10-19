"""Phase 2E-2 4.4／4.5：``build_guardian`` 的 AI 戰鬥有攔截紀錄、重播一致；手寫的「還擊」會反擊。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = main(argv)
    return code, capsys.readouterr().out


def test_guardian_battle_logs_intercepts_stances_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "guardian.json"
    argv = ["battle", "--map", "test_flat_6x6", "--ally-build", "build_guardian", "--seed", "1"]
    code, out = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0
    assert "「挺身而出」" in out and "攔截了" in out and "改由 守護者英雄 承受" in out
    assert "姿態" in out
    data = json.loads(log.read_text(encoding="utf-8"))
    entered = [a for a in data["actions"] if a.get("skill_id") == "skill_bulwark_stance"]
    assert entered  # AI 會進入姿態
    types = {e["type"] for e in data["events"]}
    assert {"attack_intercepted", "reaction_triggered"} <= types
    code, replayed = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replayed


def test_a_unit_with_riposte_hits_back_in_an_ai_battle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "duelist.json"
    argv = ["battle", "--map", "test_flat_6x6", "--allies", "sim_duelist,hero_archer,hero_mage"]
    # 種子 2：Phase 3C-3a 加入撞擊傷害後，種子 3 的戰局改變、不再出現還擊
    code, out = _run([*argv, "--seed", "2", "--log-json", str(log)], capsys)
    assert code == 0 and "反應：「還擊」" in out and "以「還擊」攻擊" in out
    code, replayed = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replayed
