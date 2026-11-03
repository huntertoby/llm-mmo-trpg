"""帳號服務層（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28）。

- 帳號由之後的 Discord Bot（5E-2）發放；這一層只提供函式（建立、登入、驗證、登出、重設密碼、停用、
  角色歸屬），Bot、API 與開發腳本（``scripts/dev_account.py``）都用它。
- 存檔：``<帳號資料夾>/<account_id>.json``（``trpg-account/1``，一帳號一檔，暫存檔＋原子改名）。
- 密碼：標準函式庫 ``hashlib.scrypt`` 加鹽，**只存雜湊**；只在記憶體比對
  （``hmac.compare_digest``），不寫進 log、錯誤訊息與回應。
- session token：``secrets.token_urlsafe``；檔裡只存 SHA-256 與到期時間。
- 角色之間不共用、不轉移（#100）：已屬於任何帳號的角色不能再歸到別的帳號，沒有轉移函式。
- 帳號不屬於 ``trpg.world`` 的確定性日誌（代決 5E1-2）；時間由注入的時鐘提供。
- 跨程序（Bot 與伺服器）寫入：資料夾鎖檔＋鎖內重讀帳號檔再寫（5D-R2，``AccountStore._update``）。
- 角色上限按賽季算（5D-R2）：``character_seasons`` 記每個角色建立時的賽季，季末清掉的角色不佔上限。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import AccountSettings, load_account_settings
from trpg.server.file_lock import FileLock
from trpg.shared.errors import TrpgError
from trpg.world.save import write_atomic
from trpg.world.season import FIRST_SEASON_ID

__all__ = [
    "ACCOUNT_FORMAT",
    "LOCK_FILE",
    "MAX_SESSIONS",
    "USERNAME_RE",
    "AccountDisabledError",
    "AccountError",
    "AccountLimitError",
    "AccountNotFoundError",
    "AccountRecord",
    "AccountStore",
    "AccountTitle",
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
LOCK_FILE: Final = "accounts.lock"
"""帳號資料夾的鎖檔（跨程序寫入，5D-R2；不是 ``*.json``，不會被當成帳號讀）。"""
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


class AccountTitle(BaseModel):
    """帳號的紀念稱號（Phase 5F-3b：打倒賽季 Boss 的「碎晶的終結者」）。季末保留（紀念類）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    """稱號 ID（``season_boss:<Boss ID>``）；同一季同一個稱號只記一次。"""
    name_zh: str
    season_id: str
    character_id: str
    """第一次拿到這個稱號的角色。"""
    at: int
    """UTC 秒數。"""


class AccountRecord(BaseModel):
    """一個帳號（``trpg-account/1``）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-account/1"] = ACCOUNT_FORMAT
    account_id: str
    username: str
    password: PasswordHash
    disabled: bool = False
    characters: tuple[str, ...] = ()
    """角色 ID（依建立順序；所有賽季，歸屬紀錄不刪）。"""
    character_seasons: dict[str, str] = Field(default_factory=dict)
    """角色 → 建立時的賽季（Phase 5D-R2）。角色上限只算當季的角色：季末清掉的角色不再佔上限。
    沒有記到的角色（舊檔）＝第一季（:data:`~trpg.world.season.FIRST_SEASON_ID`）。"""
    discord_id: str | None = None
    """發帳號的 Discord 使用者 ID（5E-2；有值時全伺服器唯一）。"""
    admin: bool = False
    """管理者：可以改大世界的 LLM 開關（5E-2，計畫 29.8）。有預設值，舊檔照讀。"""
    created_at: int
    sessions: tuple[SessionRecord, ...] = ()
    titles: tuple[AccountTitle, ...] = ()
    """紀念稱號（Phase 5F-3b；依取得順序）。有預設值，舊檔照讀、不升版。"""

    def title_labels(self) -> tuple[str, ...]:
        """顯示用的稱號（「碎晶的終結者（s1）」，依取得順序；5F-3b／5F-3c）。"""
        return tuple(f"{t.name_zh}（{t.season_id}）" for t in self.titles)

    def season_of(self, character_id: str) -> str:
        return self.character_seasons.get(character_id, FIRST_SEASON_ID)

    def characters_in(self, season_id: str) -> tuple[str, ...]:
        """這一季建立的角色（依建立順序）。"""
        return tuple(c for c in self.characters if self.season_of(c) == season_id)


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
    """帳號（記憶體快取＋本機 JSON 存檔）。所有方法執行緒安全，也跨程序安全。

    Bot（5E-2）與遊戲伺服器是兩個程序、共用同一個帳號資料夾：資料夾內檔案（名稱、修改時間、
    大小）變了就重讀快取，所以另一個程序建的帳號、停用立刻看得到（計畫 29.6）。

    跨程序寫入（Phase 5D-R2）：每個操作持有資料夾的鎖檔（:data:`LOCK_FILE`，
    :class:`~trpg.server.file_lock.FileLock`）；改一個帳號時在鎖內**重讀那個帳號檔**，把這次的
    變更套在最新的內容上再寫回（:meth:`_update`），所以 Bot 停用帳號和伺服器發 session 交錯時，
    誰都不會把對方的變更蓋回去。比對密碼（scrypt）在鎖外做。
    """

    def __init__(
        self,
        root: Path,
        *,
        max_characters: int = 3,
        session_ttl_s: int = 168 * 3600,
        clock: Callable[[], int] = _now,
        new_id: Callable[[], str] = _new_account_id,
        season: Callable[[], str] = lambda: FIRST_SEASON_ID,
    ) -> None:
        self.root = root
        self.max_characters = max_characters
        self.session_ttl_s = session_ttl_s
        self.clock = clock
        self.season = season
        """目前的賽季（角色上限按賽季算；遊戲伺服器接到世界存檔的 ``season_id``，5D-R2）。"""
        self._new_id = new_id
        self._lock = threading.RLock()
        self._file_lock = FileLock(root / LOCK_FILE)
        self._depth = 0
        self._accounts: dict[str, AccountRecord] | None = None
        self._signature: tuple[tuple[str, int, int], ...] = ()

    # -- 讀寫 -----------------------------------------------------------------

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """執行緒鎖＋資料夾的鎖檔（同一執行緒可巢狀；只有最外層真的拿鎖檔）。"""
        with self._lock:
            outer = self._depth == 0
            if outer:
                self._file_lock.acquire()
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
                if outer:
                    self._file_lock.release()

    @contextmanager
    def locked(self) -> Iterator[None]:
        """整段持有帳號資料夾的鎖（季末重置 5F-5：期間 Bot 不能同時建角、改帳號）。同一執行緒裡
        照常呼叫其他方法（可巢狀）。"""
        with self._locked():
            yield

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

    def _fresh(self) -> dict[str, AccountRecord]:
        """不管簽章，整個資料夾重讀（鎖內、要檢查全部帳號的寫入前用）。"""
        self._accounts = None
        return self._loaded()

    def _reread(self, account_id: str) -> AccountRecord:
        """鎖內重讀一個帳號檔（不靠修改時間判斷；改那個帳號之前用）。"""
        path = self._path(account_id)
        if not path.is_file():
            raise AccountNotFoundError(f"找不到帳號 {account_id}")
        record = loads_account(path.read_text(encoding="utf-8"))
        self._loaded()[account_id] = record
        return record

    def _save(self, record: AccountRecord) -> AccountRecord:
        accounts = self._loaded()
        write_atomic(self._path(record.account_id), dumps_account(record))
        accounts[record.account_id] = record
        self._signature = self._current_signature()
        return record

    def _update(
        self, account_id: str, change: Callable[[AccountRecord], AccountRecord]
    ) -> AccountRecord:
        """鎖內重讀帳號檔 → 套用 ``change`` → 寫回（跨程序不互相覆蓋，5D-R2）。"""
        with self._locked():
            fresh = self._reread(account_id)
            updated = change(fresh)
            return self._save(updated)

    # -- 查詢 -----------------------------------------------------------------

    def all(self) -> list[AccountRecord]:
        """全部帳號（依帳號名稱排序）。"""
        with self._locked():
            return sorted(self._loaded().values(), key=lambda a: a.username)

    def get(self, account_id: str) -> AccountRecord:
        with self._locked():
            record = self._loaded().get(account_id)
            if record is None:
                raise AccountNotFoundError(f"找不到帳號 {account_id}")
            return record

    def find(self, username: str) -> AccountRecord | None:
        name = normalize_username(username)
        with self._locked():
            return next((a for a in self._loaded().values() if a.username == name), None)

    def by_discord(self, discord_id: str) -> AccountRecord | None:
        with self._locked():
            return next((a for a in self._loaded().values() if a.discord_id == discord_id), None)

    def owner_of(self, character_id: str) -> str | None:
        """角色所屬的帳號 ID（沒有主人＝``None``）。"""
        with self._locked():
            for record in self._loaded().values():
                if character_id in record.characters:
                    return record.account_id
            return None

    def titles_of(self, account_id: str) -> tuple[str, ...]:
        """帳號的顯示用稱號（5F-3c：名片、評分榜、首殺、編年史）；沒有這個帳號＝空。"""
        with self._locked():
            record = self._loaded().get(account_id)
            return () if record is None else record.title_labels()

    # -- 帳號 -----------------------------------------------------------------

    def create(
        self, username: str, password: str, *, discord_id: str | None = None
    ) -> AccountRecord:
        """建帳號（Bot 發帳號、開發腳本用）。"""
        name = normalize_username(username)
        if USERNAME_RE.fullmatch(name) is None:
            raise AccountError("帳號名稱要 3～20 字的英文字母、數字或底線")
        _check_password(password)
        hashed = hash_password(password)
        with self._locked():
            accounts = self._fresh()  # 名稱、Discord ID 唯一：以磁碟上的最新內容為準
            if any(a.username == name for a in accounts.values()):
                raise AccountError(f"帳號名稱 {name} 已經有人用了")
            if discord_id is not None and any(
                a.discord_id == discord_id for a in accounts.values()
            ):
                raise AccountError("這個 Discord 使用者已經有帳號了")
            account_id = self._new_id()
            while account_id in accounts:  # pragma: no cover - 機率極低
                account_id = self._new_id()
            record = AccountRecord(
                account_id=account_id,
                username=name,
                password=hashed,
                discord_id=discord_id,
                created_at=self.clock(),
            )
            return self._save(record)

    def reset_password(self, account_id: str, password: str) -> AccountRecord:
        """換密碼並讓全部 session 失效。"""
        _check_password(password)
        update = {"password": hash_password(password), "sessions": ()}
        return self._update(account_id, lambda r: r.model_copy(update=update))

    def set_disabled(self, account_id: str, disabled: bool) -> AccountRecord:
        """停用（清掉全部 session）或恢復。"""
        update: dict[str, object] = {"disabled": disabled}
        if disabled:
            update["sessions"] = ()
        return self._update(account_id, lambda r: r.model_copy(update=update))

    def grant_title(self, account_id: str, title: AccountTitle) -> AccountRecord:
        """記一個紀念稱號（5F-3b）：鎖內重讀帳號檔再寫回（5D-R2）；同一季已有同一個稱號就不變。"""

        def add(fresh: AccountRecord) -> AccountRecord:
            if any(t.id == title.id and t.season_id == title.season_id for t in fresh.titles):
                return fresh
            return fresh.model_copy(update={"titles": (*fresh.titles, title)})

        return self._update(account_id, add)

    def set_admin(self, account_id: str, admin: bool) -> AccountRecord:
        """設定或取消管理者（開發腳本用；計畫 29.8）。"""
        return self._update(account_id, lambda r: r.model_copy(update={"admin": admin}))

    # -- 登入 -----------------------------------------------------------------

    def login(self, username: str, password: str) -> tuple[str, AccountRecord]:
        """帳號密碼對了就發一個新 token（回傳 token 原文，只此一次）。

        密碼在鎖外比對；發 session 時在鎖內重讀帳號檔，比對之後另一個程序停用帳號或換了密碼 →
        照最新的內容拒絕（5D-R2）。"""
        record = self.find(username)
        if record is None:
            verify_password(password, _DUMMY_HASH)  # 時間一致（5D-R2）
            raise AuthError(_BAD_LOGIN)
        if not verify_password(password, record.password):
            raise AuthError(_BAD_LOGIN)
        token = secrets.token_urlsafe(32)

        def add_session(fresh: AccountRecord) -> AccountRecord:
            if fresh.password != record.password:
                raise AuthError(_BAD_LOGIN)
            if fresh.disabled:
                raise AccountDisabledError("帳號已停用")
            now = self.clock()
            live = [s for s in fresh.sessions if s.expires_at > now]
            expires = now + self.session_ttl_s
            live.append(SessionRecord(token_sha256=_token_sha256(token), expires_at=expires))
            return fresh.model_copy(update={"sessions": tuple(live[-MAX_SESSIONS:])})

        return token, self._update(record.account_id, add_session)

    def _session_owner(self, token: str) -> tuple[AccountRecord, SessionRecord] | None:
        digest = _token_sha256(token)
        for record in self._loaded().values():
            for session in record.sessions:
                if hmac.compare_digest(session.token_sha256, digest):
                    return record, session
        return None

    def authenticate(self, token: str) -> AccountRecord:
        """token → 帳號；無效或過期 :class:`AuthError`、停用 :class:`AccountDisabledError`。"""
        with self._locked():
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
        with self._locked():
            found = self._session_owner(token)
            return found[1].expires_at if found is not None else None

    def logout(self, token: str) -> None:
        with self._locked():
            found = self._session_owner(token)
            if found is not None:
                self._drop_session(*found)

    def _drop_session(self, record: AccountRecord, session: SessionRecord) -> None:
        def drop(fresh: AccountRecord) -> AccountRecord:
            kept = tuple(s for s in fresh.sessions if s.token_sha256 != session.token_sha256)
            return fresh.model_copy(update={"sessions": kept})

        self._update(record.account_id, drop)

    # -- 角色 -----------------------------------------------------------------

    def season_characters(self, record: AccountRecord) -> tuple[str, ...]:
        """這個帳號在目前賽季的角色（角色上限只算這些；5D-R2）。"""
        return record.characters_in(self.season())

    def can_add_character(self, account_id: str) -> bool:
        with self._locked():
            return len(self.season_characters(self.get(account_id))) < self.max_characters

    def check_character_room(self, account_id: str) -> None:
        if not self.can_add_character(account_id):
            raise AccountLimitError(f"角色已達上限（{self.max_characters} 個）")

    def attach_character(self, account_id: str, character_id: str) -> AccountRecord:
        """角色歸到帳號（記下目前賽季）：這一季超過上限、或已屬於任何帳號 →
        :class:`AccountLimitError`（不轉移，#100）。"""
        season = self.season()
        with self._locked():
            accounts = self._fresh()  # 不轉移：以磁碟上的最新歸屬為準
            if account_id not in accounts:
                raise AccountNotFoundError(f"找不到帳號 {account_id}")
            if any(character_id in a.characters for a in accounts.values()):
                raise AccountLimitError("這個角色已經屬於某個帳號，角色不能轉移")
            record = accounts[account_id]
            if len(record.characters_in(season)) >= self.max_characters:
                raise AccountLimitError(f"角色已達上限（{self.max_characters} 個）")
            update = {
                "characters": (*record.characters, character_id),
                "character_seasons": {**record.character_seasons, character_id: season},
            }
            return self._save(record.model_copy(update=update))


def open_account_store(settings: AccountSettings | None = None) -> AccountStore:
    """照 ``config/server.toml`` 開帳號存檔（Bot 與開發腳本共用；計畫 29.6）。"""
    resolved = settings if settings is not None else load_account_settings()
    return AccountStore(
        resolved.accounts_dir(default_save_dir()),
        max_characters=resolved.max_characters,
        session_ttl_s=resolved.session_ttl_s,
    )
