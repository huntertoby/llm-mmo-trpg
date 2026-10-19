"""一鍵試玩（Phase 3-3）：必要時建置前端，啟動 ``trpg serve`` 並開瀏覽器。

用法::

    uv run python scripts/play.py              # 預設 http://127.0.0.1:8000/
    uv run python scripts/play.py --port 8123
    uv run python scripts/play.py --no-browser --no-build

``client/dist`` 不存在或比前端原始碼舊時，先執行 ``corepack pnpm -C client install`` 與
``corepack pnpm -C client build``（需要 Node；``corepack`` 隨 Node 附帶）。Ctrl+C 結束。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIENT = PROJECT_ROOT / "client"
DIST_INDEX = CLIENT / "dist" / "index.html"

# 影響建置結果的檔案與資料夾（相對於 client/）。
BUILD_INPUTS = (
    "src",
    "index.html",
    "package.json",
    "pnpm-lock.yaml",
    "vite.config.ts",
    "tsconfig.json",
)


def _files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from (p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            yield path


def needs_build(client: Path = CLIENT) -> bool:
    """``dist/index.html`` 不存在，或任何建置輸入比它新時為真。"""
    index = client / "dist" / "index.html"
    if not index.is_file():
        return True
    built = index.stat().st_mtime
    return any(f.stat().st_mtime > built for f in _files(client / p for p in BUILD_INPUTS))


def build_client(corepack: str) -> int:
    for args in (["install"], ["build"]):
        command = [corepack, "pnpm", "-C", str(CLIENT), *args]
        print("$ corepack pnpm -C client " + " ".join(args), flush=True)
        code = subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode
        if code != 0:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="建置前端（必要時）並啟動本機試玩伺服器")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="不自動開瀏覽器")
    parser.add_argument("--no-build", action="store_true", help="不檢查、不建置前端")
    args = parser.parse_args(argv)

    if not args.no_build and needs_build():
        corepack = shutil.which("corepack")
        if corepack is None:
            print("錯誤：找不到 corepack，請先安裝 Node.js（20.19 以上）。", file=sys.stderr)
            return 1
        print("前端需要建置……", flush=True)
        code = build_client(corepack)
        if code != 0:
            print(f"錯誤：前端建置失敗（結束碼 {code}）。", file=sys.stderr)
            return code

    from trpg.cli.main import main as trpg_main  # noqa: PLC0415  只在真的要啟動時載入

    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    return trpg_main(["serve", "--port", str(args.port)])


if __name__ == "__main__":
    sys.exit(main())
