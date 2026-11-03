"""帳號與登入的 API 型別（Phase 5E-1；計畫 28.6）。密碼只出現在請求裡，回應不帶。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["AccountView", "AuthStatus", "LoginRequest", "LoginResponse"]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AccountView(BaseModel):
    """目前登入的帳號（不含密碼雜湊與 session）。"""

    account_id: str
    username: str
    characters: int
    """已有幾個角色。"""
    max_characters: int
    can_create: bool
    """還能不能建角色（沒到上限）。"""
    admin: bool = False
    """管理者（5F-5：前端顯示季末重置等管理介面；權限仍由伺服器檢查）。"""


class AuthStatus(BaseModel):
    dev_mode: bool
    """開發模式：開著時大世界不用登入（代決 5E1-1）。"""
    account: AccountView | None = None
    """目前 token 的帳號；沒帶、無效或過期＝``None``。"""


class LoginResponse(BaseModel):
    token: str
    """之後的請求放在 ``Authorization: Bearer <token>``。"""
    expires_at: int
    """UTC 秒數。"""
    account: AccountView
