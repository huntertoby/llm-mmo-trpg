"""刻印的整場戰鬥（Phase 3-23 驗收 2）：刻印流 build 的 AI 對戰紀錄中有刻印與讀取，重播一致。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_runeweaver_battle_has_inscribe_and_read_events_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "rune.json"
    argv = ["battle", "--map", "training_range", "--seed", "0", "--ally-build", "build_runeweaver"]
    code, out, _ = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0 and log.is_file()
    assert "刻下" in out  # 刻印
    assert "被引爆了" in out or "「咒雷」" in out  # 讀取：引爆或條件追加傷害
    events = json.loads(log.read_text(encoding="utf-8"))["events"]
    kinds = {e["type"] for e in events}
    assert {"rune_inscribed", "rune_removed"} <= kinds
    assert any(e["type"] == "rune_removed" and e["reason"] == "detonated" for e in events) or any(
        e["type"] == "skill_used" and e["skill_id"] == "skill_rune_thunderbolt" for e in events
    )
    code, replay, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replay
    # 同種子同輸入 → 同樣的紀錄
    again = tmp_path / "again.json"
    _run([*argv, "--log-json", str(again)], capsys)
    first, second = (json.loads(p.read_text(encoding="utf-8")) for p in (log, again))
    assert first["events"] == second["events"] and first["actions"] == second["actions"]
