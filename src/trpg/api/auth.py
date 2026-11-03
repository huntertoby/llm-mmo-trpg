"""登入狀態的 FastAPI 依賴（Phase 5E-1；計畫 28.6）。

- token 放 ``Authorization: Bearer <token>``。
- 開發模式關：大世界端點要有效 token（401）；``/characters/{id}…`` 不是自己的角色 → 404
  （不透露存在）。
- 開發模式開：沒帶 token 照 5A-5（不登入、全部角色）；帶了 token 照上一條依帳號存取。
"""

from __future__ import annotations

from fastapi import Request

from trpg.api.account_config import AccountSettings
from trpg.api.account_schemas import AccountView
from trpg.api.accounts import AccountDisabledError, AccountRecord, AccountStore, AuthError
from trpg.api.world import WorldCharacterNotFoundError

__all__ = [
    "account_view",
    "accounts_of",
    "bearer_token",
    "optional_account",
    "require_world_access",
    "settings_of",
    "viewer",
]


def accounts_of(request: Request) -> AccountStore:
    store = request.app.state.accounts
    assert isinstance(store, AccountStore)
    return store


def settings_of(request: Request) -> AccountSettings:
    settings = request.app.state.account_settings
    assert isinstance(settings, AccountSettings)
    return settings


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


def account_view(store: AccountStore, record: AccountRecord) -> AccountView:
    return AccountView(
        account_id=record.account_id,
        username=record.username,
        characters=len(record.characters),
        max_characters=store.max_characters,
        can_create=len(record.characters) < store.max_characters,
    )
