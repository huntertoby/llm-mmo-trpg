"""登入狀態的 FastAPI 依賴（Phase 5E-1；計畫 28.6）。

- token 放 ``Authorization: Bearer <token>``。
- 開發模式關：大世界端點要有效 token（401）；``/characters/{id}…`` 不是自己的角色 → 404
  （不透露存在）。
- 開發模式開：沒帶 token 照 5A-5（不登入、全部角色）；帶了 token 照上一條依帳號存取。
- LLM 開關只給管理者改（5E-2，計畫 29.8）：:func:`require_admin`。
- 開發模式關：runs／battles／workshop／gear 也要登入（:func:`require_login`，5D-R2）。
- 6S-1（使用者「當然擋」）：開發模式關時開發用欄位一律 403（:func:`reject_dev_fields`）；戰鬥、
  一輪只給建立它的帳號（:func:`check_owner`，別人的 404，不透露存在）。開發模式開都不檢查。
"""

from __future__ import annotations

from collections.abc import Iterable

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
    "DevModeRequiredError",
    "account_view",
    "accounts_of",
    "bearer_token",
    "check_owner",
    "login_limiter_of",
    "optional_account",
    "owner_id",
    "reject_dev_fields",
    "require_admin",
    "require_league_admin",
    "require_login",
    "require_note_admin",
    "require_season_admin",
    "require_world_access",
    "server_settings_of",
    "settings_of",
    "viewer",
]


class AdminRequiredError(TrpgError):
    """需要管理者帳號（403）。"""


class DevModeRequiredError(TrpgError):
    """開發用欄位在開發模式關時送來（403，6S-1）。"""


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


def require_login(request: Request) -> None:
    """runs／battles／workshop／gear 路由的共用依賴（5D-R2，保守代決）：開發模式關時要有效 token
    （沒有或無效 401、停用 403）；開發模式開照舊不檢查。"""
    if not settings_of(request).dev_mode:
        viewer(request)


def require_world_access(request: Request) -> None:
    """``/api/world`` 路由的共用依賴：檢查登入；路徑有 ``character_id`` 時檢查是不是自己的角色。"""
    account = viewer(request)
    character_id = request.path_params.get("character_id")
    if account is not None and character_id is not None and character_id not in account.characters:
        raise WorldCharacterNotFoundError(f"找不到角色 {character_id}")


def owner_id(request: Request) -> str | None:
    """建立戰鬥或一輪時記下的主人：登入的帳號 ID（6S-1）。開發模式開照舊不擋（token 沒帶或無效＝
    ``None``，不 401）；開發模式關照 :func:`viewer`。"""
    dev = settings_of(request).dev_mode
    account = optional_account(request) if dev else viewer(request)
    return None if account is None else account.account_id


def check_owner(request: Request, owner: str | None, missing: Exception) -> None:
    """開發模式關：不是自己帳號建立的（含沒有主人的）→ 拋 ``missing``（404 那一類，訊息與真的
    不存在相同，不透露存在與否）；沒登入照 :func:`viewer` 401。開發模式開照舊不檢查（6S-1）。"""
    if settings_of(request).dev_mode:
        return
    account = viewer(request)
    if account is None or owner != account.account_id:
        raise missing


def reject_dev_fields(request: Request, fields: Iterable[str]) -> None:
    """開發模式關時，請求裡有開發用欄位（``fields``＝有填的欄位名）→ 403（6S-1）。"""
    used = sorted(fields)
    if used and not settings_of(request).dev_mode:
        raise DevModeRequiredError(f"{'、'.join(used)} 是開發用欄位，開發模式才能用")


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


def require_league_admin(request: Request) -> None:
    """開始影子循環賽（5F-4，代決 5F4-1 只由管理者觸發）：規則同 :func:`require_admin`。"""
    _check_admin(request, "只有管理者能開始循環賽")


def require_season_admin(request: Request) -> None:
    """季末重置（5F-5，代決 5F5-6）：規則同 :func:`require_admin`；真的執行另外要輸入目前季 ID。"""
    _check_admin(request, "只有管理者能季末重置")


def account_view(store: AccountStore, record: AccountRecord) -> AccountView:
    return AccountView(
        account_id=record.account_id,
        username=record.username,
        characters=len(store.season_characters(record)),  # 當季的角色（5D-R2）
        max_characters=store.max_characters,
        can_create=len(store.season_characters(record)) < store.max_characters,
        admin=record.admin,
        titles=list(record.title_labels()),
    )
