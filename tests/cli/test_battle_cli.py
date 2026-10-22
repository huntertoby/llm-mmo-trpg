"""``trpg map show``、``trpg battle``、``trpg battle replay`` 的測試（驗收條件 10）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_map_show(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["map", "show", "test_heights_8x8"], capsys)
    assert code == 0
    lines = out.splitlines()
    assert lines[0].startswith("測試高台")
    assert lines[1].split() == [str(x) for x in range(8)]
    assert lines[4].split() == ["2", "0.", "0.", "1.", "2#", "2#", "1.", "0.", "0."]
    assert "0a" in lines[8] and "0e" in lines[2]
    assert "深淵" in out and "石地" in out


def test_the_unit_table_shows_each_units_facing(capsys: pytest.CaptureFixture[str]) -> None:
    """Phase 3D-8d：單位列有朝向（開場我方面向敵方起始區、敵方面向我方）。"""
    code, out, _ = _run(["battle", "--map", "open_plain", "--seed", "2"], capsys)
    assert code == 0
    first = out.split("=== 第 1 輪 ===")[1].split("— ")[0]
    rows = [line for line in first.splitlines() if "位置" in line]
    assert rows and all("面向" in line for line in rows)
    assert any("我方" in r and "面向東→" in r for r in rows)
    assert any("敵方" in r and "面向西←" in r for r in rows)


def test_map_show_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["map", "show", "atlantis"], capsys)
    assert code == 1 and "未知的地圖" in err


def test_battle_runs_to_a_winner(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["battle", "--map", "test_heights_8x8", "--seed", "42"], capsys)
    assert code == 0
    assert "=== 第 1 輪 ===" in out
    assert "戰鬥結束：" in out and "勝方：" in out
    assert "勝利" in out.split("勝方：")[1].splitlines()[0]
    assert "攻擊" in out and "命中" in out
    # 同一種子輸出完全相同
    _, again, _ = _run(["battle", "--map", "test_heights_8x8", "--seed", "42"], capsys)
    assert again == out


def test_battle_rounds_max_draw(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        ["battle", "--map", "test_heights_8x8", "--seed", "1", "--rounds-max", "1"], capsys
    )
    assert code == 0
    assert "達到輪數上限，平手" in out and "勝方：平手" in out


def test_battle_log_and_replay(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "battle.json"
    code, out, _ = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "7", "--log-json", str(log)], capsys
    )
    assert code == 0 and log.is_file() and str(log) in out
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["format"] == "trpg-battle-log/55"
    assert data["seed"] == 7 and data["actions"] and data["events"]
    assert data["events"][0]["type"] == "battle_started"

    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out

    data["final_state"]["units"]["unit_0001"]["hp"] = 999
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(data), encoding="utf-8")
    code, _, err = _run(["battle", "replay", str(tampered)], capsys)
    assert code == 1 and "最終狀態不一致" in err

    data = json.loads(log.read_text(encoding="utf-8"))
    data["events"][5]["seq"] = 12345
    tampered.write_text(json.dumps(data), encoding="utf-8")
    code, _, err = _run(["battle", "replay", str(tampered)], capsys)
    assert code == 1 and "事件不一致（第 5 個事件開始不同）" in err

    data = json.loads(log.read_text(encoding="utf-8"))
    data["format"] = "other/9"
    tampered.write_text(json.dumps(data), encoding="utf-8")
    code, _, err = _run(["battle", "replay", str(tampered)], capsys)
    assert code == 1 and "不支援的紀錄格式" in err


def test_replay_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["battle", "replay", str(tmp_path / "none.json")], capsys)
    assert code == 1 and "找不到檔案" in err
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    code, _, err = _run(["battle", "replay", str(bad)], capsys)
    assert code == 1 and "不是有效的戰鬥紀錄" in err


@pytest.mark.parametrize(
    ("argv", "code", "fragment"),
    [
        (["battle"], 2, "需要 --map 與 --seed"),
        (["battle", "--map", "test_flat_6x6"], 2, "需要 --map 與 --seed"),
        (["battle", "--map", "nowhere", "--seed", "1"], 1, "未知的地圖"),
        (["battle", "--map", "test_flat_6x6", "--seed", "1", "--enemies", "dragon"], 1, "dragon"),
        (["battle", "--map", "test_flat_6x6", "--seed", "1", "--allies", ","], 2, "至少"),
        (["battle", "--map", "test_flat_6x6", "--seed", str(2**64)], 2, "seed"),
    ],
)
def test_battle_argument_errors(
    argv: list[str], code: int, fragment: str, capsys: pytest.CaptureFixture[str]
) -> None:
    got, _, err = _run(argv, capsys)
    assert got == code and fragment in err


def test_custom_lineup(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        [
            "battle",
            "--map",
            "test_flat_6x6",
            "--seed",
            "3",
            "--allies",
            "hero_fighter",
            "--enemies",
            "bandit,bandit",
        ],
        capsys,
    )
    assert code == 0 and "盜賊1" in out and "盜賊2" in out


def test_ally_build_uses_build_heroes_and_fills_with_companions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--ally-build``：build 英雄 ＋ 標準隊友（與 sim matrix 相同），紀錄可重播。"""
    log = tmp_path / "build.json"
    argv = ["battle", "--map", "test_flat_6x6", "--seed", "3", "--ally-build", "build_warlock"]
    code, out, _ = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0 and "術士英雄" in out and "勝方：" in out
    units = json.loads(log.read_text(encoding="utf-8"))["setup"]["units"]
    allies = [u["template"]["id"] for u in units if u["team"] == "ally"]
    assert allies == ["build_warlock", "sim_companion_fighter", "sim_companion_archer"]
    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out


def test_ally_build_rejects_unknown_builds_and_allies_together(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--ally-build", "build_nope"], capsys
    )
    assert code == 2 and "未知的 build" in err
    code, _, err = _run(
        [
            "battle", "--map", "test_flat_6x6", "--seed", "1",
            "--ally-build", "build_tank", "--allies", "hero_mage",
        ],
        capsys,
    )  # fmt: skip
    assert code == 2 and "--allies" in err


@pytest.mark.parametrize(
    ("map_id", "objective", "reasons"),
    [
        ("bridge_chasm", "escape", ("escaped", "escape_failed", "eliminate")),
        ("swamp", "defend", ("defended", "point_lost", "eliminate")),
    ],
)
def test_objective_battle_log_and_replay(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    map_id: str,
    objective: str,
    reasons: tuple[str, ...],
) -> None:
    """Phase 3-22：``--objective escape|defend`` 用地圖的 alt_objectives；紀錄可重播且一致。"""
    log = tmp_path / f"{objective}.json"
    argv = ["battle", "--map", map_id, "--seed", "5", "--objective", objective]
    code, _, _ = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0
    setup = json.loads(log.read_text(encoding="utf-8"))["setup"]
    assert setup["objective"]["kind"] == objective
    assert setup["objective"]["tiles"]
    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out


def test_objective_option_rejects_maps_without_the_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--objective", "escape"], capsys
    )
    assert code == 2 and "沒有 escape" in err
