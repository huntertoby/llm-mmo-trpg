"""FastAPI 應用（Phase 3-2：本機 API；多人 WebSocket 於 Phase 6）。

``create_app()`` 載入內容庫、建立工作階段表並掛上路由。``trpg serve`` 以 uvicorn 啟動，預設只綁
``127.0.0.1``。給了 ``static_dir``（建置好的前端，``client/dist``）時，``/`` 以靜態檔提供前端
（Phase 3-3），``/api/*`` 不受影響。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from trpg import __version__
from trpg.api.gear import GearRequestError
from trpg.api.routes import battles, content, gear, runs, workshop
from trpg.api.runs import RunNotFoundError, RunStore
from trpg.api.sessions import (
    AutoAdvanceLimitError,
    BattleNotFoundError,
    InvalidRequestError,
    SessionConflictError,
    SessionStore,
)
from trpg.api.workshop import WorkshopRequestError
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.runner import DEFAULT_MAX_ACTIONS
from trpg.roguelite.errors import ChoiceError, NodeConflictError, SaveFormatError
from trpg.roguelite.save import default_save_dir
from trpg.shared.errors import IllegalActionError
from trpg.skillgen.draft import DraftError
from trpg.skillgen.random_composer import ComposeError

__all__ = ["ERROR_STATUS", "create_app"]

ERROR_STATUS: dict[type[Exception], int] = {
    BattleNotFoundError: 404,
    IllegalActionError: 400,
    SessionConflictError: 409,
    InvalidRequestError: 422,
    AutoAdvanceLimitError: 500,
    RunNotFoundError: 404,
    NodeConflictError: 409,
    ChoiceError: 422,
    SaveFormatError: 422,
    WorkshopRequestError: 422,
    GearRequestError: 422,
    ComposeError: 422,
    DraftError: 422,
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
    library: ContentLibrary | None = None,
    *,
    max_auto_steps: int = DEFAULT_MAX_ACTIONS,
    static_dir: Path | None = None,
    save_dir: Path | None = None,
) -> FastAPI:
    """建立應用。``library`` 省略時載入 ``content/``。

    ``max_auto_steps`` 是每次請求自動推進的步數上限（超過時 500，工作階段保留）。
    ``save_dir`` 是一輪的存檔資料夾（省略時 :func:`~trpg.roguelite.save.default_save_dir`）。
    ``static_dir`` 是建置好的前端資料夾（含 ``index.html``）；給了就掛在 ``/``（在 API 路由之後，
    所以 ``/api/*`` 優先）。
    """
    app = FastAPI(title="LLM-MMO-TRPG 本機 API", version=__version__)
    lib = library if library is not None else load_library()
    app.state.store = SessionStore(lib, max_auto_steps=max_auto_steps)
    app.state.runs = RunStore(
        lib, app.state.store, save_dir if save_dir is not None else default_save_dir()
    )
    for exc_type, status in ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _error_handler(status))
    app.include_router(content.router)
    app.include_router(battles.router)
    app.include_router(runs.router)
    app.include_router(workshop.router)
    app.include_router(gear.router)
    if static_dir is not None:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="client")
    return app
