"""三張示範地圖與 1B 的 CLI 選項（6.1-14、6.2-7）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from trpg.cli.main import main

DEMOS = {
    # 地圖：戰鬥紀錄中應出現的環境互動
    "oil_depot": ("爆炸了", "的油變成了火焰"),
    "bridge_chasm": ("木橋", "掉進了深淵"),
    "swamp": ("傳導雷電", "天氣 ×"),
}


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize("map_id", sorted(DEMOS))
def test_demo_map_battle_has_winner_and_interactions(
    map_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(["battle", "--map", map_id, "--seed", "42"], capsys)
    assert code == 0
    verdict = out.split("勝方：")[1].splitlines()[0]
    assert "勝利" in verdict
    for fragment in DEMOS[map_id]:
        assert fragment in out, fragment
    assert "～ 環境回合 ～" in out and "環境預告：" in out


def test_demo_map_show(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["map", "show", "oil_depot"], capsys)
    assert code == 0
    assert "& 油桶" in out and "o 油" in out and "地圖事件：第 3 輪結束時 援軍" in out
    code, out, _ = _run(["map", "show", "swamp"], capsys)
    assert "天氣：rain" in out and "預設陣容：我方 hero_fighter,hero_archer,hero_stormcaller" in out


def test_demo_log_replays(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "depot.json"
    code, _, _ = _run(
        ["battle", "--map", "oil_depot", "--seed", "42", "--log-json", str(log)], capsys
    )
    assert code == 0
    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out


def test_simple_ai_weather_and_deploy_options(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        [
            "battle",
            "--map",
            "test_flat_6x6",
            "--seed",
            "1",
            "--ai",
            "simple",
            "--weather",
            "fog",
            "--deploy",
            "1,5;0,4",
        ],
        capsys,
    )
    assert code == 0 and "勝方：" in out
    assert "戰士：HP 60/60 耐力 30 位置 (1, 5)" in out
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--deploy", "5,5"], capsys
    )
    assert code == 2 and "不在我方起始區" in err
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--deploy", "x"], capsys
    )
    assert code == 2 and "--deploy" in err
