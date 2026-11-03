"""登入狀態的 FastAPI 依賴（Phase 5E-1；計畫 28.6）。

- token 放 ``Authorization: Bearer <token>``。
- 開發模式關：大世界端點要有效 token（401）；``/characters/{id}…`` 不是自己的角色 → 404
  （不透露存在）。
- 開發模式開：沒帶 token 照 5A-5（不登入、全部角色）；帶了 token 照上一條依帳號存取。
- LLM 開關只給管理者改（5E-2，計畫 29.8）：:func:`require_admin`。
"""

from __future__ import annotations

from fastapi import Request

from trpg.api.account_schemas import AccountView
from trpg.api.login_limit import LoginLimiter
from trpg.api.server_config import ServerSettings
from trpg.api.world import WorldCharacterNotFoundError
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountDisabledError, AccountRecord, AccountStore, AuthError
from trpg.shared.errors import TrpgError

__all__ = [
    "AdminRequiredError",
    "account_view",
    "accounts_of",
    "bearer_token",
    "login_limiter_of",
    "optional_account",
    "require_admin",
    "require_note_admin",
    "require_world_access",
    "server_settings_of",
    "settings_of",
    "viewer",
]


class AdminRequiredError(TrpgError):
    """需要管理者帳號（403）。"""


def accounts_of(request: Request) -> AccountStore:
    store = request.app.state.accounts
    assert isinstance(store, AccountStore)
    return store


def settings_of(request: Request) -> AccountSettings:
    settings = request.app.state.account_settings
    assert isinstance(settings, AccountSettings)
    return settings


def server_settings_of(request: Request) -> ServerSettings:
    settings = request.app.state.server_settings
    assert isinstance(settings, ServerSettings)
    return settings


def login_limiter_of(request: Request) -> LoginLimiter:
    limiter = request.app.state.login_limiter
    assert isinstance(limiter, LoginLimiter)
    return limiter


def bearer_token(request: Request) -> str | None:
    """``Authorization: Bearer <token>`` 的 token（沒有或格式不對＝``None``）。"""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def optional_account(request: Request) -> AccountRecord | None:
    """目前 token 的帳號；沒帶、無效、過期或停用＝``None``（不拋錯，``/api/auth/status`` 用）。"""
    token = bearer_token(request)
    if token is None:
        return None
    try:
        return accounts_of(request).authenticate(token)
    except (AuthError, AccountDisabledError):
        return None


def viewer(request: Request) -> AccountRecord | None:
    """大世界端點的存取者：帳號，或開發模式下沒帶 token 的 ``None``（＝不限帳號）。"""
    token = bearer_token(request)
    if token is not None:
        return accounts_of(request).authenticate(token)
    if settings_of(request).dev_mode:
        return None
    raise AuthError("請先登入")


def require_world_access(request: Request) -> None:
    """``/api/world`` 路由的共用依賴：檢查登入；路徑有 ``character_id`` 時檢查是不是自己的角色。"""
    account = viewer(request)
    character_id = request.path_params.get("character_id")
    if account is not None and character_id is not None and character_id not in account.characters:
        raise WorldCharacterNotFoundError(f"找不到角色 {character_id}")


def _check_admin(request: Request, message: str) -> None:
    account = viewer(request)
    if account is not None and not account.admin:
        raise AdminRequiredError(message)


def require_admin(request: Request) -> None:
    """伺服器全域設定（LLM 開關）：帶了 token 的非管理者 → 403；開發模式開、沒帶 token 照舊可改
    （代決 5E2-6）；開發模式關、沒 token → 401（:func:`viewer`）。"""
    _check_admin(request, "只有管理者能改 LLM 開關")


def require_note_admin(request: Request) -> None:
    """刪地點留言（5E-3，#105「使用者手動刪」）：規則同 :func:`require_admin`。"""
    _check_admin(request, "只有管理者能刪留言")


def account_view(store: AccountStore, record: AccountRecord) -> AccountView:
    return AccountView(
        account_id=record.account_id,
        username=record.username,
        characters=len(store.season_characters(record)),  # 當季的角色（5D-R2）
        max_characters=store.max_characters,
        can_create=len(store.season_characters(record)) < store.max_characters,
    )
