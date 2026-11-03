"""帳號服務層（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28）。

- 帳號由之後的 Discord Bot（5E-2）發放；這一層只提供函式（建立、登入、驗證、登出、重設密碼、停用、
  角色歸屬），Bot、API 與開發腳本（``scripts/dev_account.py``）都用它。
- 存檔：``<帳號資料夾>/<account_id>.json``（``trpg-account/1``，一帳號一檔，暫存檔＋原子改名）。
- 密碼：標準函式庫 ``hashlib.scrypt`` 加鹽，**只存雜湊**；只在記憶體比對
  （``hmac.compare_digest``），不寫進 log、錯誤訊息與回應。
- session token：``secrets.token_urlsafe``；檔裡只存 SHA-256 與到期時間。
- 角色之間不共用、不轉移（#100）：已屬於任何帳號的角色不能再歸到別的帳號，沒有轉移函式。
- 帳號不屬於 ``trpg.world`` 的確定性日誌（代決 5E1-2）；時間由注入的時鐘提供。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import AccountSettings, load_account_settings
from trpg.shared.errors import TrpgError
from trpg.world.save import write_atomic

__all__ = [
    "ACCOUNT_FORMAT",
    "MAX_SESSIONS",
    "USERNAME_RE",
    "AccountDisabledError",
    "AccountError",
    "AccountLimitError",
    "AccountNotFoundError",
    "AccountRecord",
    "AccountStore",
    "AuthError",
    "PasswordHash",
    "SessionRecord",
    "hash_password",
    "normalize_username",
    "open_account_store",
    "verify_password",
]

ACCOUNT_FORMAT: Final = "trpg-account/1"
ACCOUNT_ID_PREFIX: Final = "a"
MAX_SESSIONS: Final = 5
"""每個帳號同時有效的 session 上限（新登入擠掉最舊的，代決 5E1-5）。"""
PASSWORD_MIN: Final = 8
PASSWORD_MAX: Final = 128
USERNAME_RE: Final = re.compile(r"^[a-z0-9_]{3,20}$")
"""帳號名稱：3～20 字英數與底線，存小寫（代決 5E1-8）。"""

SCRYPT_N: Final = 2**14
SCRYPT_R: Final = 8
SCRYPT_P: Final = 1
SCRYPT_DKLEN: Final = 32
SALT_BYTES: Final = 16
_BAD_LOGIN: Final = "帳號或密碼錯誤"


class AccountError(TrpgError):
    """帳號資料不合法：名稱或 Discord ID 重複、格式不合、密碼長度不對、存檔格式不認得（422）。"""


class AccountNotFoundError(TrpgError):
    """找不到帳號（404；服務層與開發腳本用）。"""


class AuthError(TrpgError):
    """沒有登入、token 無效或過期、帳號或密碼錯誤（401）。"""


class AccountDisabledError(TrpgError):
    """帳號已停用（403）。"""


class AccountLimitError(TrpgError):
    """角色已達上限，或角色已屬於某個帳號（不轉移，#100）（409）。"""


class PasswordHash(BaseModel):
    """密碼雜湊（不含原文）。參數存在檔裡，之後調高時舊檔照讀。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: Literal["scrypt"] = "scrypt"
    n: int = Field(ge=2)
    r: int = Field(ge=1)
    p: int = Field(ge=1)
    salt: str
    """十六進位。"""
    hash: str
    """十六進位。"""


class SessionRecord(BaseModel):
    """一個有效的 session：只存 token 的 SHA-256（十六進位）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_sha256: str
    expires_at: int


class AccountRecord(BaseModel):
    """一個帳號（``trpg-account/1``）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-account/1"] = ACCOUNT_FORMAT
    account_id: str
    username: str
    password: PasswordHash
    disabled: bool = False
    characters: tuple[str, ...] = ()
    """角色 ID（依建立順序）。"""
    discord_id: str | None = None
    """發帳號的 Discord 使用者 ID（5E-2；有值時全伺服器唯一）。"""
    admin: bool = False
    """管理者：可以改大世界的 LLM 開關（5E-2，計畫 29.8）。有預設值，舊檔照讀。"""
    created_at: int
    sessions: tuple[SessionRecord, ...] = ()


def _scrypt(password: str, salt: bytes, params: tuple[int, int, int], dklen: int) -> bytes:
    n, r, p = params
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=128 * n * r * 2
    )


def hash_password(password: str) -> PasswordHash:
    """加鹽的 scrypt 雜湊（每次呼叫不同鹽）。"""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, (SCRYPT_N, SCRYPT_R, SCRYPT_P), SCRYPT_DKLEN)
    return PasswordHash(n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, salt=salt.hex(), hash=digest.hex())


def verify_password(password: str, stored: PasswordHash) -> bool:
    """在記憶體比對（常數時間）。"""
    expected = bytes.fromhex(stored.hash)
    params = (stored.n, stored.r, stored.p)
    digest = _scrypt(password, bytes.fromhex(stored.salt), params, len(expected))
    return hmac.compare_digest(digest, expected)


_DUMMY_HASH: Final = PasswordHash(
    algorithm="scrypt",
    n=SCRYPT_N,
    r=SCRYPT_R,
    p=SCRYPT_P,
    salt="00" * SALT_BYTES,
    hash="00" * SCRYPT_DKLEN,
)
"""帳號不存在時拿來比對的假雜湊（5D-R2）：照樣跑一次 scrypt，讓回應時間和帳號存在時一致，
不能從時間猜出哪些帳號名稱存在。沒有任何密碼會對上（比對結果一律丟掉）。"""


def _token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _check_password(password: str) -> None:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise AccountError(f"密碼長度要 {PASSWORD_MIN}～{PASSWORD_MAX} 字")


def _new_account_id() -> str:
    return ACCOUNT_ID_PREFIX + secrets.token_hex(4)


def _now() -> int:
    return int(time.time())


def loads_account(text: str) -> AccountRecord:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AccountError(f"帳號存檔不是合法的 JSON：{exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") != ACCOUNT_FORMAT:
        found = raw.get("format") if isinstance(raw, dict) else None
        raise AccountError(f"不認得的帳號存檔格式：{found!r}（需要 {ACCOUNT_FORMAT}）")
    try:
        return AccountRecord.model_validate(raw)
    except ValidationError as exc:
        raise AccountError(f"帳號存檔不合法：{exc}") from exc


def dumps_account(record: AccountRecord) -> str:
    return json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=1)


class AccountStore:
    """帳號（記憶體快取＋本機 JSON 存檔）。所有方法執行緒安全。

    Bot（5E-2）與遊戲伺服器是兩個程序、共用同一個帳號資料夾：資料夾內檔案（名稱、修改時間、
    大小）變了就重讀快取，所以另一個程序建的帳號、停用立刻看得到（計畫 29.6）。
    """

    def __init__(
        self,
        root: Path,
        *,
        max_characters: int = 3,
        session_ttl_s: int = 168 * 3600,
        clock: Callable[[], int] = _now,
        new_id: Callable[[], str] = _new_account_id,
    ) -> None:
        self.root = root
        self.max_characters = max_characters
        self.session_ttl_s = session_ttl_s
        self.clock = clock
        self._new_id = new_id
        self._lock = threading.RLock()
        self._accounts: dict[str, AccountRecord] | None = None
        self._signature: tuple[tuple[str, int, int], ...] = ()

    # -- 讀寫 -----------------------------------------------------------------

    def _path(self, account_id: str) -> Path:
        return self.root / f"{account_id}.json"

    def _files(self) -> list[Path]:
        return sorted(self.root.glob("*.json")) if self.root.is_dir() else []

    def _current_signature(self) -> tuple[tuple[str, int, int], ...]:
        entries: list[tuple[str, int, int]] = []
        for path in self._files():
            try:
                stat = path.stat()
            except OSError:  # pragma: no cover - 另一個程序剛好在換檔
                continue
            entries.append((path.name, stat.st_mtime_ns, stat.st_size))
        return tuple(entries)

    def _loaded(self) -> dict[str, AccountRecord]:
        signature = self._current_signature()
        if self._accounts is None or signature != self._signature:
            found: dict[str, AccountRecord] = {}
            for path in self._files():
                record = loads_account(path.read_text(encoding="utf-8"))
                found[record.account_id] = record
            self._accounts = found
            self._signature = signature
        return self._accounts

    def _save(self, record: AccountRecord) -> AccountRecord:
        accounts = self._loaded()
        write_atomic(self._path(record.account_id), dumps_account(record))
        accounts[record.account_id] = record
        self._signature = self._current_signature()
        return record

    # -- 查詢 -----------------------------------------------------------------

    def all(self) -> list[AccountRecord]:
        """全部帳號（依帳號名稱排序）。"""
        with self._lock:
            return sorted(self._loaded().values(), key=lambda a: a.username)

    def get(self, account_id: str) -> AccountRecord:
        with self._lock:
            record = self._loaded().get(account_id)
            if record is None:
                raise AccountNotFoundError(f"找不到帳號 {account_id}")
            return record

    def find(self, username: str) -> AccountRecord | None:
        name = normalize_username(username)
        with self._lock:
            return next((a for a in self._loaded().values() if a.username == name), None)

    def by_discord(self, discord_id: str) -> AccountRecord | None:
        with self._lock:
            return next((a for a in self._loaded().values() if a.discord_id == discord_id), None)

    def owner_of(self, character_id: str) -> str | None:
        """角色所屬的帳號 ID（沒有主人＝``None``）。"""
        with self._lock:
            for record in self._loaded().values():
                if character_id in record.characters:
                    return record.account_id
            return None

    # -- 帳號 -----------------------------------------------------------------

    def create(
        self, username: str, password: str, *, discord_id: str | None = None
    ) -> AccountRecord:
        """建帳號（Bot 發帳號、開發腳本用）。"""
        name = normalize_username(username)
        if USERNAME_RE.fullmatch(name) is None:
            raise AccountError("帳號名稱要 3～20 字的英文字母、數字或底線")
        _check_password(password)
        with self._lock:
            if self.find(name) is not None:
                raise AccountError(f"帳號名稱 {name} 已經有人用了")
            if discord_id is not None and self.by_discord(discord_id) is not None:
                raise AccountError("這個 Discord 使用者已經有帳號了")
            taken = set(self._loaded())
            account_id = self._new_id()
            while account_id in taken:  # pragma: no cover - 機率極低
                account_id = self._new_id()
            record = AccountRecord(
                account_id=account_id,
                username=name,
                password=hash_password(password),
                discord_id=discord_id,
                created_at=self.clock(),
            )
            return self._save(record)

    def reset_password(self, account_id: str, password: str) -> AccountRecord:
        """換密碼並讓全部 session 失效。"""
        _check_password(password)
        with self._lock:
            record = self.get(account_id)
            update = {"password": hash_password(password), "sessions": ()}
            return self._save(record.model_copy(update=update))

    def set_disabled(self, account_id: str, disabled: bool) -> AccountRecord:
        """停用（清掉全部 session）或恢復。"""
        with self._lock:
            record = self.get(account_id)
            update: dict[str, object] = {"disabled": disabled}
            if disabled:
                update["sessions"] = ()
            return self._save(record.model_copy(update=update))

    def set_admin(self, account_id: str, admin: bool) -> AccountRecord:
        """設定或取消管理者（開發腳本用；計畫 29.8）。"""
        with self._lock:
            record = self.get(account_id)
            return self._save(record.model_copy(update={"admin": admin}))

    # -- 登入 -----------------------------------------------------------------

    def login(self, username: str, password: str) -> tuple[str, AccountRecord]:
        """帳號密碼對了就發一個新 token（回傳 token 原文，只此一次）。"""
        with self._lock:
            record = self.find(username)
            if record is None:
                verify_password(password, _DUMMY_HASH)  # 時間一致（5D-R2）
                raise AuthError(_BAD_LOGIN)
            if not verify_password(password, record.password):
                raise AuthError(_BAD_LOGIN)
            if record.disabled:
                raise AccountDisabledError("帳號已停用")
            now = self.clock()
            token = secrets.token_urlsafe(32)
            live = [s for s in record.sessions if s.expires_at > now]
            expires = now + self.session_ttl_s
            live.append(SessionRecord(token_sha256=_token_sha256(token), expires_at=expires))
            record = self._save(record.model_copy(update={"sessions": tuple(live[-MAX_SESSIONS:])}))
            return token, record

    def _session_owner(self, token: str) -> tuple[AccountRecord, SessionRecord] | None:
        digest = _token_sha256(token)
        for record in self._loaded().values():
            for session in record.sessions:
                if hmac.compare_digest(session.token_sha256, digest):
                    return record, session
        return None

    def authenticate(self, token: str) -> AccountRecord:
        """token → 帳號；無效或過期 :class:`AuthError`、停用 :class:`AccountDisabledError`。"""
        with self._lock:
            found = self._session_owner(token)
            if found is None:
                raise AuthError("請先登入")
            record, session = found
            if session.expires_at <= self.clock():
                self._drop_session(record, session)
                raise AuthError("登入已過期，請重新登入")
            if record.disabled:
                raise AccountDisabledError("帳號已停用")
            return record

    def session_expires(self, token: str) -> int | None:
        with self._lock:
            found = self._session_owner(token)
            return found[1].expires_at if found is not None else None

    def logout(self, token: str) -> None:
        with self._lock:
            found = self._session_owner(token)
            if found is not None:
                self._drop_session(*found)

    def _drop_session(self, record: AccountRecord, session: SessionRecord) -> None:
        kept = tuple(s for s in record.sessions if s != session)
        self._save(record.model_copy(update={"sessions": kept}))

    # -- 角色 -----------------------------------------------------------------

    def can_add_character(self, account_id: str) -> bool:
        with self._lock:
            return len(self.get(account_id).characters) < self.max_characters

    def check_character_room(self, account_id: str) -> None:
        if not self.can_add_character(account_id):
            raise AccountLimitError(f"角色已達上限（{self.max_characters} 個）")

    def attach_character(self, account_id: str, character_id: str) -> AccountRecord:
        """角色歸到帳號：超過上限、或已屬於任何帳號 → :class:`AccountLimitError`
        （不轉移，#100）。"""
        with self._lock:
            record = self.get(account_id)
            owner = self.owner_of(character_id)
            if owner is not None:
                raise AccountLimitError("這個角色已經屬於某個帳號，角色不能轉移")
            self.check_character_room(account_id)
            update = {"characters": (*record.characters, character_id)}
            return self._save(record.model_copy(update=update))


def open_account_store(settings: AccountSettings | None = None) -> AccountStore:
    """照 ``config/server.toml`` 開帳號存檔（Bot 與開發腳本共用；計畫 29.6）。"""
    resolved = settings if settings is not None else load_account_settings()
    return AccountStore(
        resolved.accounts_dir(default_save_dir()),
        max_characters=resolved.max_characters,
        session_ttl_s=resolved.session_ttl_s,
    )
