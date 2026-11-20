"""worker 掛掉時的補排與留證（QF-3a）。

在暫存資料夾跑小測試組（``tests/infra/stuck_suite/`` 裡不會被收集的示範檔）：

- ``crash_case.py``：一個測試讓 worker 直接結束。``tests/xdist_loadgroup.py`` 修正前，xdist 3.8 的
  ``--dist loadgroup`` 會在補上新 worker 後永遠卡住；這裡限 90 秒，超過就用 PID 結束整棵程序樹
  並判失敗。
- ``timeout_case.py``：一個測試超過 pytest-timeout（thread 方式）的逾時，worker 被 ``os._exit``；
  ``tests/pytest_trace.py`` 要在那之前把 stack 寫進 ``.stacks``，``.trace`` 留下沒結束的測試。
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
CONFTEST = """\
from tests.pytest_trace import pytest_runtest_protocol  # noqa: F401
from tests.xdist_loadgroup import pytest_xdist_make_scheduler  # noqa: F401
"""
INI = "[pytest]\ntimeout = 300\ntimeout_method = thread\n"


def _run_case(tmp_path: Path, case: str) -> tuple[int, str, Path]:
    """把示範檔複製成 ``test_<case>`` 跑 ``-n 2 --dist loadgroup``。

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
    }
    env.pop("PYTEST_XDIST_WORKER", None)
    env.pop("PYTEST_ADDOPTS", None)
    command = [sys.executable, "-m", "pytest", "-v", "-n", "2", "--dist", "loadgroup"]
    command += ["-p", "no:cacheprovider", "--rootdir", str(tmp_path), str(tmp_path)]
    proc = subprocess.Popen(
        command,
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=sys.platform != "win32",
    )
    try:
        output, _ = proc.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        run_pytest.kill_tree(proc)
        pytest.fail(f"{case}：worker 掛掉後卡住（90 秒內沒跑完）")
    return proc.returncode, output.decode("utf-8", errors="replace"), trace_dir


@pytest.mark.timeout(150)
def test_loadgroup_finishes_after_a_worker_crash(tmp_path: Path) -> None:
    returncode, text, trace_dir = _run_case(tmp_path, "crash_case.py")
    assert "SafeLoadGroupScheduling" in text, text
    assert "1 failed, 3 passed" in text, text
    assert returncode == 1, text
    # 掛掉時那個測試不重跑。
    runs = (tmp_path / "crash_runs.txt").read_text(encoding="utf-8").splitlines()
    assert runs == ["run"]
    summary = run_pytest.read_traces(trace_dir)
    assert [t.nodeid for t in summary.running] == ["test_crash_case.py::test_crash_once"]


@pytest.mark.timeout(150)
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
