"""Phase 3-25a：戰場變奏的 CLI——``trpg skills budget`` 逐型態列出、整場戰鬥 ``--log-json`` ＋
``replay`` 一致、戰鬥紀錄文字標出型態名。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main

ALLIES = "variant_vanguard,variant_tidecaller,variant_slinger"


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = main(argv)
    return code, capsys.readouterr().out


def test_budget_lists_every_form(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _run(["skills", "budget", "skill_tidal_spear"], capsys)
    assert code == 0
    assert "變奏加價 200" in out and "戰場變奏 2 個" in out
    assert "【型態：水中貫穿】（tide_pierce）" in out and "【型態：居高投矛】（high_tide）" in out
    assert "驗證：通過" in out
    code, table = _run(["skills", "budget", "--all"], capsys)
    assert "└ tide_pierce" in table and "└ high_tide" in table


def test_a_variant_battle_logs_the_form_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "variant.json"
    argv = ["battle", "--map", "swamp", "--allies", ALLIES, "--seed", "0"]
    code, out = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0 and log.is_file()
    assert "（借牆猛撞）" in out or "（寒霜刃）" in out
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["format"] == "trpg-battle-log/91"
    variants = [e["variant"] for e in data["events"] if e["type"] == "skill_used"]
    assert any(v is not None for v in variants)
    code, replay = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replay
    again = tmp_path / "again.json"
    _run([*argv, "--log-json", str(again)], capsys)
    second = json.loads(again.read_text(encoding="utf-8"))
    assert data["events"] == second["events"] and data["actions"] == second["actions"]
