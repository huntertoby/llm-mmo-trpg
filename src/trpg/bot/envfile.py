"""極小的 ``.env`` 解析器（Phase 5E-2b；``docs/phases/Phase5計畫.md`` 32.3）。

使用者把 Bot token 放在 repo 根目錄的 ``.env``（原話「到時候我會放.env然後 放token」）；不加
python-dotenv，只支援：

- 一行一個 ``KEY=VALUE``；``KEY`` 是 ``[A-Za-z_][A-Za-z0-9_]*``，前後空白去掉。
- ``#`` 開頭的行與空行略過；沒引號的值遇到「空白＋``#``」之後當註解。
- 值前後空白去掉；可包在成對的 ``"`` 或 ``'`` 裡（去掉引號、不處理跳脫）。
- 同名後面的蓋前面；檔頭 BOM 略過。

不合法的行 → :class:`EnvFileError`，**只報行號、不印那行內容**（可能含 token）。
不支援 ``export``、多行值、變數展開。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from trpg.shared.errors import TrpgError

__all__ = ["EnvFileError", "parse_env_text", "read_env_file"]

_KEY_RE: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INLINE_COMMENT_RE: Final = re.compile(r"\s#")
_QUOTES: Final = ('"', "'")


class EnvFileError(TrpgError):
    """``.env`` 格式不對（訊息只有檔名與行號）。"""


def _value(raw: str) -> str | None:
    """``=`` 右邊 → 值；引號沒有成對＝``None``（不合法）。"""
    value = raw.strip()
    if value[:1] in _QUOTES:
        quote = value[0]
        end = value.find(quote, 1)
        if end < 0:
            return None
        rest = value[end + 1 :].strip()
        if rest and not rest.startswith("#"):
            return None
        return value[1:end]
    match = _INLINE_COMMENT_RE.search(value)
    return value[: match.start()].rstrip() if match else value


def parse_env_text(text: str, *, source: str = ".env") -> dict[str, str]:
    """``.env`` 的內容 → ``{KEY: VALUE}``。"""
    result: dict[str, str] = {}
    for lineno, line in enumerate(text.removeprefix("﻿").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, raw = stripped.partition("=")
        key = key.strip()
        value = _value(raw) if sep else None
        if not sep or _KEY_RE.fullmatch(key) is None or value is None:
            raise EnvFileError(
                f"{source} 第 {lineno} 行格式不對：要寫成 KEY=VALUE（值可以用引號包起來）"
            )
        result[key] = value
    return result


def read_env_file(path: Path) -> dict[str, str]:
    """讀 ``.env``；檔案不存在＝空的（``.env`` 是選用的）。"""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EnvFileError(f"無法讀取 {path}：{type(exc).__name__}") from exc
    return parse_env_text(text, source=str(path))
