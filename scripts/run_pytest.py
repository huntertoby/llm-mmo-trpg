"""pytest 看門狗（QF-3a）：卡住時只結束自己開的那棵程序樹，自動重跑一次；再卡住就判失敗。

用法（所有跑測試的地方都用這支，包括 ``scripts/check.py`` 和 agent 自己跑的 pytest）::

    uv run python scripts/run_pytest.py tests/api -x -n 8          # 其餘參數原樣交給 pytest
    uv run python scripts/run_pytest.py --stall-minutes 5 tests/engine/test_turns.py

看門狗自己的選項要放在最前面：

- ``--stall-minutes N``：多久沒有進展算卡住，預設 10（或環境變數 ``TRPG_PYTEST_STALL_MINUTES``）。
- ``--retries N``：卡住後重跑幾次，預設 1。
- ``--log-dir DIR``：留證資料夾，預設 ``.claude/pm-logs/pytest/<時間>-<pid>/``。
- ``--keep-logs``：全部通過也保留留證資料夾（預設通過、沒有 worker 掛掉時刪掉）。

**進展**：任何一個測試跑完（``tests/pytest_trace.py`` 寫的 ``END`` 行數增加）。還沒有任何測試
開始前（收集階段），pytest 有輸出就算進展。逾時設得比卡住門檻長的測試（標 slow 的 1800 秒）
正在跑時，等到它自己的逾時加 60 秒才算卡住，不會誤殺。

**卡住時**：用 PID 結束自己開的 pytest 和它底下的所有子程序（Windows ``taskkill /T /F /PID``；
其他系統用自己開的 session 的 process group），**不用程序名稱**；把「只有開始、沒有結束」的
測試和 worker 留下的 stack 寫進留證資料夾的 ``stuck.txt``，印出來，再重跑。

**結束碼**：pytest 的結束碼原樣傳回；連續卡住判失敗時是 :data:`STALL_EXIT_CODE`（124）；
被 Ctrl+C 中斷是 130（中斷時同樣先結束整棵樹）。看門狗的父程序（``TRPG_WATCHDOG_PARENT_PID``，
``scripts/check.py`` 會設）消失時也會結束整棵樹、回 130。

既有的單一測試逾時（``pyproject.toml`` 的 ``timeout = 300``，slow 1800）照舊由 pytest-timeout 管。
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = PROJECT_ROOT / ".claude" / "pm-logs" / "pytest"
TRACE_DIR_ENV = "TRPG_PYTEST_TRACE_DIR"  # 與 tests/pytest_trace.py 一致
STALL_ENV = "TRPG_PYTEST_STALL_MINUTES"
PARENT_PID_ENV = "TRPG_WATCHDOG_PARENT_PID"
DEFAULT_STALL_MINUTES = 10.0
DEFAULT_RETRIES = 1
STALL_EXIT_CODE = 124
INTERRUPT_EXIT_CODE = 130
LONG_TEST_GRACE_SECONDS = 60.0
POLL_SECONDS = 2.0
CRASH_MARKERS = (b"node down", b"replacing crashed worker", b"crashed while running")


# ---------------------------------------------------------------------------
# 留證檔解析
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunningTest:
    worker: str  # 檔名（``<worker>-<pid>``）
    nodeid: str
    started: float  # epoch 秒
    timeout: float  # 這個測試自己的逾時秒數（0＝不限）


@dataclass
class TraceSummary:
    started: int = 0
    finished: int = 0
    running: list[RunningTest] = field(default_factory=list)


def read_traces(directory: Path) -> TraceSummary:
    """讀 ``*.trace``：算開始、結束的測試數，列出每個行程最後「有開始、沒結束」的測試。"""
    summary = TraceSummary()
    if not directory.is_dir():
        return summary
    for path in sorted(directory.glob("*.trace")):
        current: RunningTest | None = None
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            parts = line.split("\t")
            if parts[0] == "START" and len(parts) >= 4:  # noqa: PLR2004
                summary.started += 1
                current = RunningTest(path.stem, parts[3], float(parts[1]), float(parts[2]))
            elif parts[0] == "END" and len(parts) >= 3:  # noqa: PLR2004
                summary.finished += 1
                current = None
        if current is not None:
            summary.running.append(current)
    return summary


def stall_deadline(
    last_progress: float, stall_seconds: float, running: Sequence[RunningTest]
) -> float:
    """卡住的判定時間：最後進展＋門檻；正在跑、逾時比門檻長的測試，延到它的逾時＋60 秒。"""
    deadline = last_progress + stall_seconds
    for test in running:
        if test.timeout > stall_seconds:
            deadline = max(deadline, test.started + test.timeout + LONG_TEST_GRACE_SECONDS)
    return deadline


def describe_stuck(trace_dir: Path, now: float) -> str:
    """卡住時的說明：每個行程最後沒結束的測試（含已跑秒數），以及非空的 stack 檔。"""
    summary = read_traces(trace_dir)
    lines = [f"已開始 {summary.started} 個測試、跑完 {summary.finished} 個。"]
    if summary.running:
        lines.append("最後開始、還沒結束的測試（行程被結束的也會列出）：")
        for test in sorted(summary.running, key=lambda t: t.started):
            elapsed = now - test.started
            lines.append(f"  [{test.worker}] {test.nodeid}（已 {elapsed:.0f} 秒）")
    else:
        lines.append("沒有正在跑的測試（卡在收集、排程或結束階段）。")
    for path in sorted(trace_dir.glob("*.stacks")) if trace_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            lines.append(f"\n--- {path.name} ---\n{text}")
    return "\n".join(lines)


def has_stack_dumps(trace_dir: Path) -> bool:
    if not trace_dir.is_dir():
        return False
    return any(path.stat().st_size > 0 for path in trace_dir.glob("*.stacks"))


# ---------------------------------------------------------------------------
# 程序樹
# ---------------------------------------------------------------------------


def popen_tree(command: Sequence[str], env: dict[str, str]) -> subprocess.Popen[bytes]:
    """開一個子程序；非 Windows 時放進自己的 session，之後可以整組結束。"""
    return subprocess.Popen(
        list(command),
        cwd=PROJECT_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=sys.platform != "win32",
    )


def kill_tree(proc: subprocess.Popen[bytes]) -> None:
    """用 PID 結束自己開的程序和它底下的所有子程序（不用程序名稱）。"""
    if proc.poll() is None:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)


class ParentWatch:
    """看門狗的父程序還在不在（父程序被結束時，看門狗收掉自己的樹再離開）。

    看的是環境變數 ``TRPG_WATCHDOG_PARENT_PID``（``scripts/check.py`` 設成自己的 PID），沒設時看
    ``os.getppid()``。Windows 上 ``uv run`` 與 venv 的 ``python.exe`` 會多一層轉接程序，直接父程序
    不一定是呼叫者，所以 check.py 明確傳 PID。開始時就取得程序 handle，PID 之後被重用也不會誤判。
    """

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        env = os.environ if environ is None else environ
        given = env.get(PARENT_PID_ENV, "").strip()
        self._explicit = given.isdigit()
        self._pid = int(given) if self._explicit else os.getppid()
        self._handle: int | None = None
        if sys.platform == "win32":
            synchronize = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, self._pid)
            self._handle = int(handle) if handle else None

    def alive(self) -> bool:
        if sys.platform == "win32":
            if self._handle is None:
                return True
            wait_timeout = 0x102
            return bool(ctypes.windll.kernel32.WaitForSingleObject(self._handle, 0) == wait_timeout)
        if self._explicit:
            try:
                os.kill(self._pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True
        return os.getppid() == self._pid


# ---------------------------------------------------------------------------
# 單次執行
# ---------------------------------------------------------------------------


@dataclass
class AttemptResult:
    returncode: int | None  # None：卡住（已結束整棵樹）或父程序消失
    stalled: bool
    crashed: bool  # 輸出裡有 worker 掛掉的訊息
    parent_gone: bool = False


class _Pump(threading.Thread):
    """把子程序輸出同時寫到自己的 stdout 和紀錄檔，記下最後一次輸出的時間。"""

    def __init__(self, source: IO[bytes], log: IO[bytes]) -> None:
        super().__init__(daemon=True)
        self.source = source
        self.log = log
        self.bytes_seen = 0
        self.crashed = False
        self._tail = b""

    def run(self) -> None:
        out = sys.stdout.buffer
        read = getattr(self.source, "read1", self.source.read)
        while chunk := read(65536):
            self.bytes_seen += len(chunk)
            window = self._tail + chunk
            if any(marker in window for marker in CRASH_MARKERS):
                self.crashed = True
            self._tail = window[-64:]
            out.write(chunk)
            out.flush()
            self.log.write(chunk)
            self.log.flush()


def run_attempt(
    command: Sequence[str], attempt_dir: Path, stall_seconds: float, parent: ParentWatch
) -> AttemptResult:
    trace_dir = attempt_dir / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, TRACE_DIR_ENV: str(trace_dir), "PYTHONUNBUFFERED": "1"}
    env.pop(PARENT_PID_ENV, None)
    with (attempt_dir / "output.log").open("wb") as log:
        proc = popen_tree(command, env)
        assert proc.stdout is not None
        pump = _Pump(proc.stdout, log)
        pump.start()
        try:
            stalled, parent_gone = _watch(proc, pump, trace_dir, stall_seconds, parent)
        except BaseException:
            kill_tree(proc)
            raise
        if stalled or parent_gone:
            kill_tree(proc)
        else:
            proc.wait()
        pump.join(timeout=10)
    returncode = None if stalled or parent_gone else proc.returncode
    return AttemptResult(returncode, stalled, pump.crashed, parent_gone)


def _watch(
    proc: subprocess.Popen[bytes],
    pump: _Pump,
    trace_dir: Path,
    stall_seconds: float,
    parent: ParentWatch,
) -> tuple[bool, bool]:
    """等子程序結束；回傳（是否卡住、父程序是否消失）。"""
    last_progress = time.time()
    last_marker: tuple[int, int] = (-1, -1)
    while proc.poll() is None:
        time.sleep(POLL_SECONDS)
        if not parent.alive():
            return False, True
        summary = read_traces(trace_dir)
        # 有測試開始後只看「跑完的測試數」；之前（收集階段）看輸出位元組。
        marker = (summary.finished, 0) if summary.started else (0, pump.bytes_seen)
        now = time.time()
        if marker != last_marker:
            last_marker = marker
            last_progress = now
        elif now > stall_deadline(last_progress, stall_seconds, summary.running):
            return True, False
    return False, False


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------


@dataclass
class Options:
    stall_minutes: float
    retries: int
    log_dir: Path | None
    keep_logs: bool
    pytest_args: list[str]


def parse_args(argv: Sequence[str], environ: dict[str, str] | None = None) -> Options:
    """看門狗自己的選項放最前面；第一個不認得的參數（或 ``--``）起全部交給 pytest。"""
    env = os.environ if environ is None else environ
    stall = float(env.get(STALL_ENV, "").strip() or DEFAULT_STALL_MINUTES)
    options = Options(stall, DEFAULT_RETRIES, None, False, [])
    args = list(argv)
    while args:
        name, _, inline = args[0].partition("=")
        if name == "--":
            args.pop(0)
            break
        if name == "--keep-logs":
            options.keep_logs = True
            args.pop(0)
            continue
        if name not in ("--stall-minutes", "--retries", "--log-dir"):
            break
        args.pop(0)
        if not inline:
            if not args:
                raise SystemExit(f"{name} 需要一個值")
            inline = args.pop(0)
        if name == "--stall-minutes":
            options.stall_minutes = float(inline)
        elif name == "--retries":
            options.retries = int(inline)
        else:
            options.log_dir = Path(inline)
    options.pytest_args = args
    if options.stall_minutes <= 0 or options.retries < 0:
        raise SystemExit("--stall-minutes 必須大於 0，--retries 不能是負數")
    return options


def _default_log_dir() -> Path:
    return LOG_ROOT / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


def _say(message: str) -> None:
    print(f"\n[看門狗] {message}", file=sys.stderr, flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")
    options = parse_args(sys.argv[1:] if argv is None else argv)
    log_dir = options.log_dir or _default_log_dir()
    command = [sys.executable, "-m", "pytest", *options.pytest_args]
    stall_seconds = options.stall_minutes * 60
    parent = ParentWatch()
    attempts = options.retries + 1
    keep = options.keep_logs
    for number in range(1, attempts + 1):
        attempt_dir = log_dir / f"attempt-{number}"
        try:
            result = run_attempt(command, attempt_dir, stall_seconds, parent)
        except KeyboardInterrupt:
            _say(f"中斷：已結束整棵 pytest 程序樹。留證在 {attempt_dir}")
            return INTERRUPT_EXIT_CODE
        if result.parent_gone:
            _say(f"父程序已結束：已結束整棵 pytest 程序樹。留證在 {attempt_dir}")
            return INTERRUPT_EXIT_CODE
        trace_dir = attempt_dir / "trace"
        if result.crashed or has_stack_dumps(trace_dir):
            keep = True
            _say(f"有 worker 掛掉或留下 stack，留證在 {trace_dir}")
        if not result.stalled:
            assert result.returncode is not None
            if result.returncode != 0:
                keep = True
            if keep:
                _say(f"留證資料夾：{log_dir}")
            else:
                shutil.rmtree(log_dir, ignore_errors=True)
            return result.returncode
        keep = True
        report = describe_stuck(trace_dir, time.time())
        (attempt_dir / "stuck.txt").write_text(report + "\n", encoding="utf-8")
        _say(
            f"第 {number}/{attempts} 次：超過 {options.stall_minutes:g} 分鐘沒有進展，"
            f"已結束自己開的整棵程序樹（PID）。\n{report}\n（存在 {attempt_dir / 'stuck.txt'}）"
        )
        if number < attempts:
            _say("自動重跑一次。")
    _say(f"連續 {attempts} 次卡住，判失敗。留證資料夾：{log_dir}")
    return STALL_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
