"""本機完整檢查：ruff、格式、mypy、import-linter、pytest 依序執行。

通常用法（Windows、macOS、Linux 皆同）::

    uv run python scripts/check.py          # 快速版（不跑標 slow 的測試、前端抽樣）
    uv run python scripts/check.py --full   # 完整版（pytest -m ""、TRPG_FULL=1）

pytest 平行數預設 8，可用環境變數 ``TRPG_PYTEST_WORKERS`` 覆寫（數字或 ``auto``）。
單一測試預設逾時 300 秒（標 slow 的 1800 秒），見 ``pyproject.toml`` 的 ``timeout``。

多個 agent 同時工作時：每個 agent 在自己的 worktree 執行本腳本（不要共用同一個 checkout），
並設 ``UV_NO_SYNC=1``（或用 ``uv run --frozen``）避免 ``uv run`` 自動同步、重裝套件。
跑 pytest 前會清掉 ``tests/**/__pycache__`` 中多個行程同時寫入留下的 ``*.pyc.<pid>`` 暫存檔。

每個步驟都會執行（方便一次看到全部問題），最後印出各步驟結果摘要；
任一步失敗時以非零代碼結束。``lint-imports`` 未安裝時只印出警告並略過，不算失敗
（``tests/test_architecture.py`` 提供等效的依賴方向檢查）。前端檢查（``corepack pnpm -C client``
的 ``install --frozen-lockfile``、``typecheck``、``test``）在找不到 ``corepack`` 時同樣略過。

工具的尋找順序：目前 Python 環境的模組（``sys.executable -m <tool>``）→
與 ``sys.executable`` 同一資料夾的執行檔 → ``PATH`` 上的執行檔（``shutil.which``）。
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Step:
    title: str
    module: str | None  # 可用 ``python -m`` 執行的模組名稱
    executable: str  # 對應的指令名稱
    args: tuple[str, ...]
    optional: bool = False


def pytest_workers() -> str:
    """pytest 的平行數：環境變數 ``TRPG_PYTEST_WORKERS``（數字或 ``auto``），預設 8。"""
    value = os.environ.get("TRPG_PYTEST_WORKERS", "").strip() or "8"
    if value != "auto" and not (value.isdigit() and int(value) >= 0):
        raise SystemExit(f"TRPG_PYTEST_WORKERS 必須是非負整數或 auto，收到：{value!r}")
    return value


def _client_step(title: str, *args: str) -> Step:
    """``corepack pnpm -C client <args>``；找不到 corepack 時略過（不算失敗）。"""
    return Step(title, None, "corepack", ("pnpm", "-C", "client", *args), optional=True)


STEPS: tuple[Step, ...] = (
    Step("ruff check", "ruff", "ruff", ("check", ".")),
    Step("ruff format --check", "ruff", "ruff", ("format", "--check", ".")),
    Step("mypy", "mypy", "mypy", ()),
    Step("lint-imports", None, "lint-imports", (), optional=True),
    Step("pytest", "pytest", "pytest", ("-q", "-n", pytest_workers())),
    # 前端（Phase 3-3）：找不到 corepack（沒有安裝 Node）時印出警告並略過，不算失敗。
    _client_step("client install", "install", "--frozen-lockfile"),
    _client_step("client typecheck", "typecheck"),
    _client_step("client test", "test"),
)


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        # 讓舊版 Windows 主控台啟用 ANSI 色碼（無副作用的慣用做法）。
        os.system("")
    return sys.stdout.isatty()


COLOR = _use_color()


def _paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def green(text: str) -> str:
    return _paint(text, "32")


def red(text: str) -> str:
    return _paint(text, "31")


def yellow(text: str) -> str:
    return _paint(text, "33")


def find_command(step: Step) -> list[str] | None:
    """找出執行此步驟的指令；找不到時回傳 None。"""
    if step.module is not None and importlib.util.find_spec(step.module) is not None:
        return [sys.executable, "-m", step.module]
    bin_dir = Path(sys.executable).parent
    for name in (step.executable, f"{step.executable}.exe"):
        candidate = bin_dir / name
        if candidate.is_file():
            return [str(candidate)]
    found = shutil.which(step.executable)
    return [found] if found else None


def _full_step(step: Step) -> Step:
    if step.title != "pytest":
        return step
    return Step(step.title, step.module, step.executable, (*step.args, "-m", ""), step.optional)


def clean_stale_pyc() -> int:
    """刪除 ``tests/**/__pycache__/*.pyc.<pid>``（並行寫入中斷留下的暫存檔）；回傳刪除數。"""
    count = 0
    for path in (PROJECT_ROOT / "tests").glob("**/__pycache__/*.pyc.*"):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count


def run_step(step: Step) -> str:
    """執行一個步驟，回傳 ``"通過"``、``"失敗"`` 或 ``"略過"``。"""
    print(f"\n=== {step.title} ===", flush=True)
    if step.title == "pytest" and (removed := clean_stale_pyc()):
        print(f"已清除 {removed} 個殘留的 .pyc 暫存檔。", flush=True)
    command = find_command(step)
    if command is None:
        if step.optional:
            print(yellow(f"警告：找不到 {step.executable}，略過此步驟（不算失敗）。"), flush=True)
            return "略過"
        print(red(f"錯誤：找不到 {step.executable}，請先執行 `uv sync`。"), flush=True)
        return "失敗"
    completed = subprocess.run([*command, *step.args], cwd=PROJECT_ROOT, check=False)
    return "通過" if completed.returncode == 0 else "失敗"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = sys.argv[1:] if argv is None else argv
    if any(a not in ("--full",) for a in args):
        print("用法：scripts/check.py [--full]")
        return 2
    full = "--full" in args
    if full:
        # 完整版：包含標 slow 的測試（後面的 -m "" 覆蓋 addopts 的 -m 'not slow'）與前端完整組合。
        os.environ["TRPG_FULL"] = "1"
    results = [(step.title, run_step(_full_step(step) if full else step)) for step in STEPS]

    print("\n=== 檢查結果摘要 ===")
    for title, result in results:
        painted = {"通過": green, "失敗": red, "略過": yellow}[result](result)
        print(f"  {title:<22} {painted}")

    failed = [title for title, result in results if result == "失敗"]
    if failed:
        print(red(f"\n失敗：{len(failed)} 個步驟（{'、'.join(failed)}）"))
        return 1
    print(green("\n全部檢查通過。"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
