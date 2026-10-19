"""``trpg serve``：以 uvicorn 啟動本機 API（Phase 3-2）。"""

from __future__ import annotations

from typing import TextIO

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "cmd_serve"]

DEFAULT_HOST = "127.0.0.1"
"""預設只綁本機（Phase 3 不部署到網路上）。"""
DEFAULT_PORT = 8000


def cmd_serve(host: str, port: int, out: TextIO) -> int:
    # 延後匯入：其他子指令不需要載入 FastAPI／uvicorn。
    import uvicorn  # noqa: PLC0415

    from trpg.api.app import create_app  # noqa: PLC0415

    app = create_app()
    print(f"本機 API：http://{host}:{port}/api（Ctrl+C 結束）", file=out)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
