"""登入端點（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28.6）。

- ``GET /api/auth/status``：開發模式與目前 token 的帳號。
- ``POST /api/auth/login``：帳號密碼 → token（密碼只在記憶體比對，不寫 log）；失敗次數過多 429
  （5E-2，計畫 29.7）。
- ``POST /api/auth/logout``：讓目前的 token 失效。

帳號由 Discord Bot（5E-2）或開發腳本（``scripts/dev_account.py``）建立，這裡沒有註冊端點。
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from trpg.api.account_schemas import AuthStatus, LoginRequest, LoginResponse
from trpg.api.accounts import AuthError
from trpg.api.auth import (
    account_view,
    accounts_of,
    bearer_token,
    login_limiter_of,
    optional_account,
    settings_of,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def get_status(request: Request) -> AuthStatus:
    store = accounts_of(request)
    record = optional_account(request)
    return AuthStatus(
        dev_mode=settings_of(request).dev_mode,
        account=account_view(store, record) if record is not None else None,
    )


@router.post("/login")
def post_login(body: LoginRequest, request: Request) -> LoginResponse:
    store = accounts_of(request)
    limiter = login_limiter_of(request)
    ip = request.client.host if request.client is not None else None
    limiter.check(body.username, ip)  # 失敗太多次：429，連密碼都不比對（5E-2）
    try:
        token, record = store.login(body.username, body.password)
    except AuthError:
        limiter.failed(body.username, ip)
        raise
    limiter.succeeded(body.username)
    expires = store.session_expires(token)
    assert expires is not None
    return LoginResponse(token=token, expires_at=expires, account=account_view(store, record))


@router.post("/logout", status_code=204)
def post_logout(request: Request) -> Response:
    token = bearer_token(request)
    if token is not None:
        accounts_of(request).logout(token)
    return Response(status_code=204)
