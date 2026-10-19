"""FastAPI 應用（Phase 3-2：本機 API；多人 WebSocket 於 Phase 6）。

``create_app()`` 載入內容庫、建立工作階段表並掛上路由。``trpg serve`` 以 uvicorn 啟動，預設只綁
``127.0.0.1``。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from trpg import __version__
from trpg.api.routes import battles, content
from trpg.api.sessions import (
    AutoAdvanceLimitError,
    BattleNotFoundError,
    InvalidRequestError,
    SessionConflictError,
    SessionStore,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.runner import DEFAULT_MAX_ACTIONS
from trpg.shared.errors import IllegalActionError

__all__ = ["ERROR_STATUS", "create_app"]

ERROR_STATUS: dict[type[Exception], int] = {
    BattleNotFoundError: 404,
    IllegalActionError: 400,
    SessionConflictError: 409,
    InvalidRequestError: 422,
    AutoAdvanceLimitError: 500,
}
"""引擎與工作階段的錯誤 → HTTP 狀態碼（回應為 ``{"detail": "<中文訊息>"}``）。

:class:`AutoAdvanceLimitError` 的回應多一個 ``battle_id``（工作階段保留）。"""


def _error_handler(status: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(_request: Request, exc: Exception) -> JSONResponse:
        content: dict[str, str] = {"detail": str(exc)}
        if isinstance(exc, AutoAdvanceLimitError):
            content["battle_id"] = exc.battle_id
        return JSONResponse(status_code=status, content=content)

    return handle


def create_app(
    library: ContentLibrary | None = None, *, max_auto_steps: int = DEFAULT_MAX_ACTIONS
) -> FastAPI:
    """建立應用。``library`` 省略時載入 ``content/``。

    ``max_auto_steps`` 是每次請求自動推進的步數上限（超過時 500，工作階段保留）。
    """
    app = FastAPI(title="LLM-MMO-TRPG 本機 API", version=__version__)
    app.state.store = SessionStore(
        library if library is not None else load_library(), max_auto_steps=max_auto_steps
    )
    for exc_type, status in ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _error_handler(status))
    app.include_router(content.router)
    app.include_router(battles.router)
    return app
