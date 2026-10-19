"""本機完整檢查：ruff、格式、mypy、import-linter、pytest 依序執行。

通常用法（Windows、macOS、Linux 皆同）::

    uv run python scripts/check.py

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


def _client_step(title: str, *args: str) -> Step:
    """``corepack pnpm -C client <args>``；找不到 corepack 時略過（不算失敗）。"""
    return Step(title, None, "corepack", ("pnpm", "-C", "client", *args), optional=True)


STEPS: tuple[Step, ...] = (
    Step("ruff check", "ruff", "ruff", ("check", ".")),
    Step("ruff format --check", "ruff", "ruff", ("format", "--check", ".")),
    Step("mypy", "mypy", "mypy", ()),
    Step("lint-imports", None, "lint-imports", (), optional=True),
    Step("pytest", "pytest", "pytest", ("-q", "-n", "auto")),
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


def run_step(step: Step) -> str:
    """執行一個步驟，回傳 ``"通過"``、``"失敗"`` 或 ``"略過"``。"""
    print(f"\n=== {step.title} ===", flush=True)
    command = find_command(step)
    if command is None:
        if step.optional:
            print(yellow(f"警告：找不到 {step.executable}，略過此步驟（不算失敗）。"), flush=True)
            return "略過"
        print(red(f"錯誤：找不到 {step.executable}，請先執行 `uv sync`。"), flush=True)
        return "失敗"
    completed = subprocess.run([*command, *step.args], cwd=PROJECT_ROOT, check=False)
    return "通過" if completed.returncode == 0 else "失敗"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    results = [(step.title, run_step(step)) for step in STEPS]

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
