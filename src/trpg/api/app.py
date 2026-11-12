"""FastAPI 應用（Phase 3-2：本機 API；多人 WebSocket 於 Phase 6）。

``create_app()`` 載入內容庫、建立工作階段表並掛上路由。``trpg serve`` 以 uvicorn 啟動，預設只綁
``127.0.0.1``。給了 ``static_dir``（建置好的前端，``client/dist``）時，``/`` 以靜態檔提供前端
（Phase 3-3），``/api/*`` 不受影響。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from trpg import __version__
from trpg.api.auth import AdminRequiredError, DevModeRequiredError, require_login
from trpg.api.gear import GearRequestError
from trpg.api.llm_health import LlmHealth
from trpg.api.llm_source import LlmProvider, LocalLlmProvider
from trpg.api.login_limit import LoginLimiter, LoginRateLimitError
from trpg.api.primitive_coverage import check_primitive_coverage
from trpg.api.routes import auth, battles, content, gear, mail, runs, workshop, world
from trpg.api.runs import RunNotFoundError, RunStore
from trpg.api.server_config import ServerSettings, load_server_settings
from trpg.api.sessions import (
    AutoAdvanceLimitError,
    BattleNotFoundError,
    InvalidRequestError,
    SessionConflictError,
    SessionStore,
)
from trpg.api.tuning import routes as tuning_routes
from trpg.api.tuning.service import TuningService, tuning_enabled
from trpg.api.workshop import WorkshopRequestError
from trpg.api.world import WorldCharacterNotFoundError, WorldConflictError, WorldStore
from trpg.api.world_flow import WorldLlm
from trpg.api.world_pregen import WorldPregen, provider_generators
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.runner import DEFAULT_MAX_ACTIONS
from trpg.roguelite.errors import ChoiceError, NodeConflictError, SaveFormatError
from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import AccountSettings, load_account_settings
from trpg.server.accounts import (
    AccountDisabledError,
    AccountError,
    AccountLimitError,
    AccountNotFoundError,
    AccountStore,
    AuthError,
)
from trpg.server.league import LeagueError, LeagueMatchNotFoundError
from trpg.server.notes import NoteError, NoteNotFoundError
from trpg.server.season_archive import ArchiveRecordNotFoundError
from trpg.server.season_reset import SeasonResetError
from trpg.server.server_presence import ServerPresence
from trpg.shared.errors import IllegalActionError
from trpg.skillgen.draft import DraftError
from trpg.skillgen.random_composer import ComposeError
from trpg.world.calendar import season_start_at
from trpg.world.errors import WorldActionError, WorldError, WorldSaveFormatError
from trpg.world.layout import world_dir_of

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
    WorldCharacterNotFoundError: 404,
    WorldConflictError: 409,
    WorldActionError: 422,
    WorldSaveFormatError: 422,
    WorldError: 422,
    AuthError: 401,
    AccountDisabledError: 403,
    AccountNotFoundError: 404,
    AccountLimitError: 409,
    AccountError: 422,
    LoginRateLimitError: 429,
    AdminRequiredError: 403,
    DevModeRequiredError: 403,  # 6S-1 開發用欄位
    NoteNotFoundError: 404,
    NoteError: 422,
    LeagueError: 409,  # 5F-4 循環賽還不能開跑
    LeagueMatchNotFoundError: 404,
    SeasonResetError: 409,  # 5F-5 季末重置的檢查沒過
    ArchiveRecordNotFoundError: 404,  # 5F-5c 查證的首殺或場次不存在
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


def _include_routers(app: FastAPI, *, dev_mode: bool, tuning: bool = False) -> None:
    app.include_router(content.router)
    # 5D-R2（保守代決，待使用者確認）：開發模式關時一輪、戰鬥、工坊、裝備測試要登入；開發用端點與
    # 存檔列表、讀檔不掛（開發模式開照舊）。
    login = [Depends(require_login)]
    app.include_router(battles.router, dependencies=login)
    if dev_mode:
        app.include_router(runs.dev_router)  # 在 runs.router 之前：/saves 不能被 /{run_id} 吃掉
    app.include_router(runs.router, dependencies=login)
    app.include_router(workshop.router, dependencies=login)
    app.include_router(gear.router, dependencies=login)
    if dev_mode:
        app.include_router(world.dev_router)  # 6F-3：開發用 Boss 戰入口（另要 TRPG_DEV_ROUTES=1）
    app.include_router(world.router)
    app.include_router(mail.router)  # 6T-1a 郵寄
    app.include_router(auth.router)
    if dev_mode and tuning:  # NW-1a 數值工坊：另要 TRPG_TUNING=1；轉發標頭一律 403（tuning.routes）
        app.include_router(tuning_routes.router)


def create_app(
    library: ContentLibrary | None = None,
    *,
    max_auto_steps: int = DEFAULT_MAX_ACTIONS,
    static_dir: Path | None = None,
    save_dir: Path | None = None,
    llm: LlmProvider | None = None,
    accounts: AccountSettings | None = None,
    server: ServerSettings | None = None,
    hold_presence: bool = False,
    tuning: bool | None = None,
) -> FastAPI:
    """建立應用。``library`` 省略時載入 ``content/``；兩種情況都先檢查效果原語的對應項
    （:func:`~trpg.api.primitive_coverage.check_primitive_coverage`，缺了拋出 ``ContentError``）。

    ``max_auto_steps`` 是每次請求自動推進的步數上限（超過時 500，工作階段保留）。
    ``save_dir`` 是一輪的存檔資料夾（省略時 :func:`~trpg.roguelite.save.default_save_dir`）；
    大世界存在它底下的 ``world/``（5A-5）。
    ``llm`` 是網頁版 LLM 開關的模型來源（4-L6b；省略時讀 ``config/llm.toml`` 連本機模型，連不到就
    把那一輪當作關閉）；測試傳 :class:`~trpg.api.llm_source.MockLlmProvider`。
    ``accounts`` 是帳號與登入的設定（5E-1；省略時讀 ``config/server.toml`` 的 ``[accounts]``，
    開發模式預設開）。帳號存在 ``accounts.dir``，空字串時 ``<save_dir>/accounts``。
    ``server`` 是網路與健康檢查的設定（5E-3；省略時讀 ``config/server.toml`` 的 ``[network]``、
    ``[llm_health]``）：``trusted_proxies`` 決定登入限制讀不讀轉發標頭，``llm_health_interval_s`` 是
    本機模型的 ping 間隔（啟動時 ping 一次；0＝只在啟動時）。
    ``hold_presence``（5F-R1；``trpg serve`` 傳 ``True``）：啟動時在世界資料夾寫心跳檔
    ``server.lock``、關閉時移除（:mod:`trpg.server.server_presence`），命令列的季末重置看到就拒絕。
    測試預設不寫，免得動到真正的存檔資料夾。
    ``tuning``（NW-1a 數值工坊）：省略時看環境變數 ``TRPG_TUNING=1``；開發模式關時一律不掛。
    ``static_dir`` 是建置好的前端資料夾（含 ``index.html``）；給了就掛在 ``/``（在 API 路由之後，
    所以 ``/api/*`` 優先）。
    """
    app = FastAPI(title="LLM-MMO-TRPG 本機 API", version=__version__)
    lib = library if library is not None else load_library()
    check_primitive_coverage(lib)
    app.state.store = SessionStore(lib, max_auto_steps=max_auto_steps)
    saves = save_dir if save_dir is not None else default_save_dir()
    provider = llm if llm is not None else LocalLlmProvider()
    app.state.runs = RunStore(lib, app.state.store, saves, llm=provider)
    network = server if server is not None else load_server_settings()
    start_date = network.season_start_date  # 開賽日（5F-1）；沒設定＝建立世界的當下
    app.state.world = WorldStore(  # 大世界（5A-5）
        lib,
        app.state.store,
        world_dir_of(saves),
        season_start=None if start_date is None else season_start_at(lib, start_date),
    )
    app.router.on_shutdown.append(app.state.world.offers.shutdown)  # PERF-3 背景執行緒
    app.router.on_shutdown.append(app.state.world.league_runner.shutdown)  # 5F-4 循環賽
    if hold_presence:  # 5F-R1：心跳檔，命令列重置看得到伺服器開著
        presence = ServerPresence(world_dir_of(saves))
        app.router.on_startup.append(presence.start)
        app.router.on_shutdown.append(presence.stop)
    app.state.server_settings = network  # 網路與健康檢查（5E-3）
    health = LlmHealth(provider, interval_s=network.llm_health_interval_s)
    world_llm = WorldLlm(provider, health)  # 大世界自己的 LLM 開關（5B-5）
    health.active = lambda: world_llm.enabled
    app.state.world_llm = world_llm
    pregen = WorldPregen(provider_generators(provider), enabled=world_llm.usable)  # 6L-2
    app.state.world.pregen = pregen
    app.router.on_shutdown.append(pregen.shutdown)
    app.state.llm_health = health
    app.router.on_startup.append(health.start)  # 啟動時與定期 ping（5E-3）
    app.router.on_shutdown.append(health.stop)
    settings = accounts if accounts is not None else load_account_settings()
    app.state.account_settings = settings  # 帳號與登入（5E-1）
    app.state.accounts = AccountStore(
        settings.accounts_dir(saves),
        max_characters=settings.max_characters,
        session_ttl_s=settings.session_ttl_s,
        season=app.state.world.current_season,  # 角色上限按賽季算（5D-R2）
    )
    app.state.world.actor_of = app.state.accounts.owner_of  # 世界日誌記帳號（5F-1，Q15）
    app.state.world.grant_title = app.state.accounts.grant_title  # 紀念稱號（5F-3b）
    app.state.world.account_titles = app.state.accounts.titles_of  # 稱號顯示（5F-3c）
    app.state.login_limiter = LoginLimiter(  # 登入嘗試次數限制（5E-2）
        max_failures=settings.login_max_failures,
        ip_max_failures=settings.login_ip_max_failures,
        window_s=settings.login_window_s,
    )
    for exc_type, status in ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _error_handler(status))
    use_tuning = settings.dev_mode and tuning_enabled(tuning)
    if use_tuning:  # NW-1a：寫回的是內容庫所在的資料夾；草稿、備份、模擬放 <save_dir>/tuning/
        app.state.tuning = TuningService(lib.root, saves, lib)
        app.router.on_shutdown.append(app.state.tuning.shutdown)
    _include_routers(app, dev_mode=settings.dev_mode, tuning=use_tuning)
    if static_dir is not None:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="client")
    return app
