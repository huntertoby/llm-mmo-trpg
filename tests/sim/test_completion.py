"""完成度檢查 ``trpg sim completion``（Phase 2C-4 3.4）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.cli.sim import default_sim_maps
from trpg.sim.commanders import COMMANDER_IDS
from trpg.sim.completion import (
    COMPLETION_ANOMALY_KINDS,
    CompletionConfig,
    completion_configs,
    format_completion,
    run_completion,
)

FAST_MAPS = ("open_plain", "lava_crossing")


def test_nine_configs_cover_no_commander_and_every_commander_on_each_side() -> None:
    configs = completion_configs()
    assert len(configs) == 9
    assert configs[0] == CompletionConfig()
    assert {c.ally for c in configs[1:]} == {*COMMANDER_IDS, None}
    assert {c.enemy for c in configs[1:]} == {*COMMANDER_IDS, None}
    assert all((c.ally is None) or (c.enemy is None) for c in configs)
    assert len({c.label for c in configs}) == 9


@pytest.mark.slow
def test_fast_completion_run_has_the_expected_shape_and_no_anomalies() -> None:
    report = run_completion(library(), FAST_MAPS, [0])
    assert len(report.cells) == 9 * len(FAST_MAPS)
    assert report.clean, report.anomalies
    text = format_completion(report)
    lines = text.splitlines()
    assert lines[0].startswith("完成度檢查：9 種設定 × 2 張地圖 × 1 個種子（0–0）＝ 18 場")
    assert "| 設定 | open_plain | lava_crossing |" in lines
    rows = [line for line in lines if line.startswith("| ") and "／" in line]
    assert len(rows) == 9
    assert rows[0].startswith("| 無指揮官 | ")
    assert all(row.count("／") == 4 for row in rows)  # 2 格 × 每格 2 個分隔
    assert "異常合計：exception 0、max_actions 0、draw 0 —— 通過" in text
    assert COMPLETION_ANOMALY_KINDS == ("exception", "max_actions", "draw")


@pytest.mark.slow
def test_completion_output_is_identical_between_runs_and_jobs() -> None:
    lib = library()
    maps = FAST_MAPS[:1]
    first = format_completion(run_completion(lib, maps, [0, 1], jobs=1))
    again = format_completion(run_completion(lib, maps, [0, 1], jobs=1))
    parallel = format_completion(run_completion(lib, maps, [0, 1], jobs=2))
    assert first == again == parallel


def test_anomalies_are_listed_with_config_map_and_seed() -> None:
    # max_rounds=1 讓每場戰鬥都以平手結束：確認 draw 會被列出
    report = run_completion(
        library(), ("open_plain",), [0], configs=[CompletionConfig()], max_rounds=1
    )
    assert not report.clean
    assert [(a.kind, a.map_id, a.seed) for a in report.anomalies] == [("draw", "open_plain", 0)]
    text = format_completion(report)
    assert "- draw (無指揮官, open_plain, 0)" in text and "—— 未通過" in text


def test_cli_returns_nonzero_on_unknown_map(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sim", "completion", "--maps", "no_such_map", "--seeds", "1"]) == 2
    assert "沒有這些地圖" in capsys.readouterr().err


@pytest.mark.slow
def test_cli_prints_the_report_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["sim", "completion", "--maps", "open_plain", "--seeds", "1"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("完成度檢查：9 種設定 × 1 張地圖 × 1 個種子")
    assert "執行時間" in captured.err and "執行時間" not in captured.out


@pytest.mark.slow
def test_every_map_and_config_completes_without_exception_max_actions_or_draw() -> None:
    maps = default_sim_maps(library())
    assert len(maps) == 10
    report = run_completion(library(), maps, range(3), jobs=2)
    assert len(report.cells) == 9 * 10
    assert report.anomalies == (), format_completion(report)
