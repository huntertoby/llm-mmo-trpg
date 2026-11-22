"""worker 掛掉時的補排與留證（QF-3a）。

在暫存資料夾跑小測試組（``tests/infra/stuck_suite/`` 裡不會被收集的示範檔）：

- ``crash_case.py``：一個測試讓 worker 直接結束。``tests/xdist_loadgroup.py`` 修正前，xdist 3.8 的
  ``--dist loadgroup`` 會在補上新 worker 後永遠卡住。
- ``crash_twice_case.py``：兩個 worker 接連掛掉；修正前 master 會 INTERNALERROR（``KeyError`` 或
  對死掉的 worker 送工作的 ``OSError``）。
- ``timeout_case.py``：一個測試超過 pytest-timeout（thread 方式）的逾時，worker 被 ``os._exit``；
  ``tests/pytest_trace.py`` 要在那之前把 stack 寫進 ``.stacks``，``.trace`` 留下沒結束的測試。

子程序限 :data:`CASE_LIMIT_SECONDS` 秒（全量時機器很忙，小測試組平常 4～8 秒）；worker 掛掉的兩題
限 :data:`CRASH_LIMIT_SECONDS` 秒。超過就用 PID 結束整棵程序樹並判失敗，失敗訊息附上到那時為止的
輸出。子程序的主行程（xdist master）在時限前 :data:`MASTER_STACKS_LEAD_SECONDS` 秒把所有執行緒的
stack 寫進 ``master-hang.stacks``，逾時時也附在失敗訊息裡（TS-1：兩次逾時都是子測試全部回報了、
主行程卻沒收尾，下次再發生就看得到卡在哪裡）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.infra.test_run_pytest import run_pytest

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests" / "infra" / "stuck_suite"
MASTER_STACKS_ENV = "TRPG_CASE_MASTER_STACKS_AFTER"
MASTER_STACKS_FILE = "master-hang.stacks"
CONFTEST = f"""\
import faulthandler
import os

from tests.pytest_trace import pytest_runtest_protocol  # noqa: F401
from tests.xdist_loadgroup import pytest_xdist_make_scheduler  # noqa: F401

if "PYTEST_XDIST_WORKER" not in os.environ and os.environ.get("{MASTER_STACKS_ENV}"):
    # 只在主行程（xdist master）：時限前把 stack 寫下來，卡在收尾時看得到卡在哪裡。
    _HANG = open("{MASTER_STACKS_FILE}", "w", encoding="utf-8")
    faulthandler.dump_traceback_later(float(os.environ["{MASTER_STACKS_ENV}"]), file=_HANG)
"""
INI = "[pytest]\ntimeout = 300\ntimeout_method = thread\n"
CASE_LIMIT_SECONDS = 240
TEST_TIMEOUT_SECONDS = 290  # 比 CASE_LIMIT_SECONDS 長，讓子程序逾時時由本測試收樹、印輸出
CRASH_LIMIT_SECONDS = 540
"""worker 掛掉、要補開 worker 的兩題：負載重時 240 秒不夠。QF-4b 先放寬兩個一起掛的那題；
TS-1 把只掛一個的那題也放寬到一樣（2026-11-22 的全量在 240 秒逾時）。"""
CRASH_TIMEOUT_SECONDS = 600  # 比 CRASH_LIMIT_SECONDS 長，讓子程序逾時時由本測試收樹、印輸出
MASTER_STACKS_LEAD_SECONDS = 20


def _run_case(tmp_path: Path, case: str, limit: int = CASE_LIMIT_SECONDS) -> tuple[int, str, Path]:
    """把示範檔複製成 ``test_<case>`` 跑 ``-n 2 --dist loadgroup``（最多 ``limit`` 秒）。

    回傳（結束碼、輸出、留證資料夾）。"""
    shutil.copy(SUITE / case, tmp_path / f"test_{case}")
    (tmp_path / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(INI, encoding="utf-8")
    trace_dir = tmp_path / "trace"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT / "src")]),
        "TRPG_WATCHDOG_DEMO": "1",
        run_pytest.TRACE_DIR_ENV: str(trace_dir),
        MASTER_STACKS_ENV: str(max(limit - MASTER_STACKS_LEAD_SECONDS, 1)),
    }
    env.pop("PYTEST_XDIST_WORKER", None)
    env.pop("PYTEST_ADDOPTS", None)
    command = [sys.executable, "-m", "pytest", "-v", "-n", "2", "--dist", "loadgroup"]
    command += ["-p", "no:cacheprovider", "--rootdir", str(tmp_path), str(tmp_path)]
    output_path = tmp_path / "output.log"
    with output_path.open("wb") as output:
        proc = subprocess.Popen(
            command,
            cwd=tmp_path,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=sys.platform != "win32",
        )
        try:
            proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            run_pytest.kill_tree(proc)
            partial = output_path.read_text(encoding="utf-8", errors="replace")
            note = _hang_note(tmp_path, partial)
            pytest.fail(f"{case}：{limit} 秒內沒跑完。{note}輸出：\n{partial}")
    return proc.returncode, output_path.read_text(encoding="utf-8", errors="replace"), trace_dir


def _hang_note(tmp_path: Path, partial: str) -> str:
    """逾時時的補充：子測試是不是都回報了（卡在收尾），以及主行程的 stack。"""
    note = "子測試都回報了（[100%]），卡在主行程收尾。" if "[100%]" in partial else ""
    stacks = tmp_path / MASTER_STACKS_FILE
    text = stacks.read_text(encoding="utf-8", errors="replace") if stacks.is_file() else ""
    return f"{note}主行程 stack：\n{text}\n" if text.strip() else note


def _crash_runs(tmp_path: Path) -> list[str]:
    """示範檔每次讓 worker 結束前寫的檔（``<名稱>.<pid>``），只取名稱並排序。"""
    return sorted(path.name.split(".")[0] for path in (tmp_path / "crash_runs").iterdir())


@pytest.mark.timeout(CRASH_TIMEOUT_SECONDS)
def test_loadgroup_finishes_after_a_worker_crash(tmp_path: Path) -> None:
    returncode, text, trace_dir = _run_case(tmp_path, "crash_case.py", CRASH_LIMIT_SECONDS)
    assert "SafeLoadGroupScheduling" in text, text
    assert "INTERNALERROR" not in text, text
    assert "1 failed, 3 passed" in text, text
    assert returncode == 1, text
    # 掛掉時那個測試不重跑。
    assert _crash_runs(tmp_path) == ["once"], text
    summary = run_pytest.read_traces(trace_dir)
    assert [t.nodeid for t in summary.running] == ["test_crash_case.py::test_crash_once"]


@pytest.mark.timeout(CRASH_TIMEOUT_SECONDS)
def test_loadgroup_survives_two_workers_crashing_together(tmp_path: Path) -> None:
    returncode, text, trace_dir = _run_case(tmp_path, "crash_twice_case.py", CRASH_LIMIT_SECONDS)
    assert "INTERNALERROR" not in text, text
    assert "2 failed, 3 passed" in text, text
    assert returncode == 1, text
    assert _crash_runs(tmp_path) == ["first", "second"], text
    assert sorted(t.nodeid for t in run_pytest.read_traces(trace_dir).running) == [
        "test_crash_twice_case.py::test_crash_first",
        "test_crash_twice_case.py::test_crash_second",
    ]


@pytest.mark.timeout(TEST_TIMEOUT_SECONDS)
def test_timed_out_worker_leaves_its_stack_in_a_file(tmp_path: Path) -> None:
    returncode, text, trace_dir = _run_case(tmp_path, "timeout_case.py")
    assert "1 failed, 1 passed" in text, text
    assert returncode == 1, text
    summary = run_pytest.read_traces(trace_dir)
    assert [(t.nodeid, t.timeout) for t in summary.running] == [
        ("test_timeout_case.py::test_sleeps_past_timeout", 4.0)
    ]
    stacks = "".join(p.read_text(encoding="utf-8") for p in trace_dir.glob("*.stacks"))
    assert "_sleep_somewhere_recognizable" in stacks, stacks
    assert "test_sleeps_past_timeout" in stacks, stacks
