"""``--ally-commander``／``--enemy-commander``（Phase 2C-2 4.5）與戰鬥紀錄中的指令。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_battle_prints_new_orders_each_round(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["battle", "--map", "swamp", "--seed", "3", "--enemy-commander", "focus_lowest_hp"]
    code, out, _ = _run(argv, capsys)
    assert code == 0
    lines = [line for line in out.splitlines() if line.startswith("敵方指令：")]
    assert lines and all(line.startswith("敵方指令：集火 ") for line in lines)
    assert not any(line.startswith("我方指令：") for line in out.splitlines())
    # 指令印在該輪的標題之後、行動者的動作之前
    assert out.index("=== 第 1 輪 ===") < out.index(lines[0])
    _, again, _ = _run(argv, capsys)
    assert again == out


def test_battle_without_commanders_is_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = _run(["battle", "--map", "swamp", "--seed", "3"], capsys)
    assert "指令：" not in out


def test_log_json_contains_orders_and_replay_verifies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "battle.json"
    code, _, _ = _run(
        [
            "battle",
            "--map",
            "swamp",
            "--seed",
            "3",
            "--ally-commander",
            "hold_start",
            "--enemy-commander",
            "focus_lowest_hp",
            "--log-json",
            str(log),
        ],
        capsys,
    )
    assert code == 0
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["orders"] and {r["team"] for r in data["orders"]} == {"ally", "enemy"}
    assert data["orders"][0]["round"] == 1
    kinds = {o["kind"] for r in data["orders"] for o in r["orders"]["team_orders"]}
    assert kinds == {"focus_target"}
    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out
    # 舊格式（沒有 orders 欄位）仍可重播
    del data["orders"]
    old = tmp_path / "old.json"
    old.write_text(json.dumps(data), encoding="utf-8")
    code, out, _ = _run(["battle", "replay", str(old)], capsys)
    assert code == 0 and "重播驗證通過" in out


def test_commander_argument_errors(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(
        ["battle", "--map", "swamp", "--seed", "1", "--enemy-commander", "nope"], capsys
    )
    assert code == 2 and "invalid choice" in err
    code, _, err = _run(
        [
            "battle",
            "--map",
            "swamp",
            "--seed",
            "1",
            "--ai",
            "simple",
            "--ally-commander",
            "use_env",
        ],
        capsys,
    )
    assert code == 2 and "指揮官只能搭配效用 AI" in err


def test_sim_maps_with_a_commander_prints_it_and_stays_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["sim", "maps", "--maps", "oil_depot", "--seeds", "3", "--enemy-commander", "use_env"]
    code, out, _ = _run(argv, capsys)
    assert code == 0
    assert "敵方指揮官：use_env（全隊優先利用環境）" in out
    _, parallel, _ = _run([*argv, "--jobs", "2"], capsys)
    assert parallel == out
    _, plain, _ = _run(["sim", "maps", "--maps", "oil_depot", "--seeds", "3"], capsys)
    assert "指揮官" not in plain
