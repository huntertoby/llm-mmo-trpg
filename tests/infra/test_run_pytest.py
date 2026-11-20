"""``scripts/run_pytest.py`` 看門狗的判定邏輯（QF-3a）。

真的卡住、結束程序樹的驗證是手動跑 ``tests/infra/stuck_suite/hang_case.py``（不進推送前檢查），
結果記在 ``docs/phases/PhaseQF-3a報告.md``。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests import pytest_trace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_pytest.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_pytest_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_pytest = _load()


def test_trace_env_name_matches_the_plugin() -> None:
    assert run_pytest.TRACE_DIR_ENV == pytest_trace.TRACE_DIR_ENV


def test_read_traces_lists_tests_started_but_not_ended(tmp_path: Path) -> None:
    (tmp_path / "gw0-11.trace").write_text(
        "START\t100.0\t300\ta.py::t1\nEND\t101.0\ta.py::t1\nSTART\t102.0\t300\ta.py::t2\n",
        encoding="utf-8",
    )
    (tmp_path / "gw1-12.trace").write_text(
        "START\t100.0\t1800\tb.py::slow\nEND\t200.0\tb.py::slow\n", encoding="utf-8"
    )
    summary = run_pytest.read_traces(tmp_path)
    assert (summary.started, summary.finished) == (3, 2)
    assert [(t.worker, t.nodeid, t.timeout) for t in summary.running] == [
        ("gw0-11", "a.py::t2", 300.0)
    ]
    report = run_pytest.describe_stuck(tmp_path, now=162.0)
    assert "[gw0-11] a.py::t2（已 60 秒）" in report


def test_stall_deadline_waits_for_tests_with_longer_timeouts() -> None:
    running = run_pytest.RunningTest
    normal = [running("gw0", "a::t", 1000.0, 300.0)]
    assert run_pytest.stall_deadline(1000.0, 600.0, normal) == 1600.0
    slow = [running("gw0", "a::slow", 1000.0, 1800.0)]
    assert run_pytest.stall_deadline(1000.0, 600.0, slow) == 1000.0 + 1800.0 + 60.0


def test_parse_args_splits_watchdog_options_from_pytest_args() -> None:
    options = run_pytest.parse_args(
        ["--stall-minutes=2.5", "--retries", "0", "--keep-logs", "tests/api", "-n", "8"], {}
    )
    assert (options.stall_minutes, options.retries, options.keep_logs) == (2.5, 0, True)
    assert options.pytest_args == ["tests/api", "-n", "8"]
    # 第一個不認得的參數起全部交給 pytest（後面同名的也照樣交出去）。
    options = run_pytest.parse_args(["-x", "--retries", "3"], {"TRPG_PYTEST_STALL_MINUTES": "4"})
    assert (options.stall_minutes, options.retries) == (4.0, 1)
    assert options.pytest_args == ["-x", "--retries", "3"]
    assert run_pytest.parse_args(["--", "--keep-logs"], {}).pytest_args == ["--keep-logs"]
    with pytest.raises(SystemExit):
        run_pytest.parse_args(["--stall-minutes", "0"], {})


@pytest.mark.timeout(7)
def test_item_timeout_reads_the_marker(request: pytest.FixtureRequest) -> None:
    assert pytest_trace.item_timeout(request.node) == 7.0
    assert pytest_trace.dump_lead_seconds(300.0) == 5.0
    assert pytest_trace.dump_lead_seconds(4.0) == 1.0
