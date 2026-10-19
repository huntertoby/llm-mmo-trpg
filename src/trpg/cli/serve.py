"""``trpg serve``：以 uvicorn 啟動本機 API（Phase 3-2），前端已建置時一併提供網頁（3-3）。"""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

__all__ = ["CLIENT_DIST", "DEFAULT_HOST", "DEFAULT_PORT", "cmd_serve", "find_client_dist"]

DEFAULT_HOST = "127.0.0.1"
"""預設只綁本機（Phase 3 不部署到網路上）。"""
DEFAULT_PORT = 8000

CLIENT_DIST = Path(__file__).resolve().parents[3] / "client" / "dist"
"""建置好的前端（``corepack pnpm -C client build`` 的輸出）。"""


def find_client_dist(path: Path = CLIENT_DIST) -> Path | None:
    """``path`` 內有 ``index.html`` 時回傳 ``path``，否則 ``None``（前端尚未建置）。"""
    return path if (path / "index.html").is_file() else None


def cmd_serve(host: str, port: int, out: TextIO, *, client_dist: Path = CLIENT_DIST) -> int:
    # 延後匯入：其他子指令不需要載入 FastAPI／uvicorn。
    import uvicorn  # noqa: PLC0415

    from trpg.api.app import create_app  # noqa: PLC0415

    static_dir = find_client_dist(client_dist)
    app = create_app(static_dir=static_dir)
    if static_dir is None:
        print(
            f"找不到建置好的前端（{client_dist}）；只提供 API。"
            "要玩網頁版請先執行 `corepack pnpm -C client install` 與 "
            "`corepack pnpm -C client build`，或用 `uv run python scripts/play.py`。",
            file=out,
        )
    else:
        print(f"網頁：http://{host}:{port}/", file=out)
    print(f"本機 API：http://{host}:{port}/api（Ctrl+C 結束）", file=out)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
