"""內容資料檔（YAML／JSON）的讀取與驗證。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from trpg.shared.errors import ContentError

__all__ = ["CONTENT_DIR_ENV", "bundled_content_dir", "default_content_dir", "load_content_file"]

CONTENT_DIR_ENV = "TRPG_CONTENT_DIR"
"""可覆寫內容資料夾位置的環境變數名稱。"""

_YAML_SUFFIXES = frozenset({".yaml", ".yml"})
_JSON_SUFFIXES = frozenset({".json"})
_MAX_REPORTED_ERRORS = 10


def bundled_content_dir() -> Path:
    """專案內建的 ``content/`` 資料夾（不受 ``TRPG_CONTENT_DIR`` 影響；schema 匯入時讀清單用）。"""
    return Path(__file__).resolve().parents[3] / "content"


def default_content_dir() -> Path:
    """專案頂層 ``content/`` 資料夾的路徑。

    預設以本檔位置推算（``src/trpg/content/loader.py`` → 專案根目錄 / ``content``），
    可用環境變數 ``TRPG_CONTENT_DIR`` 覆寫。
    """
    override = os.environ.get(CONTENT_DIR_ENV)
    if override:
        return Path(override)
    return bundled_content_dir()


def _read_raw(path: Path) -> object:
    suffix = path.suffix.lower()
    if suffix not in _YAML_SUFFIXES | _JSON_SUFFIXES:
        raise ContentError(path, f"不支援的副檔名 {path.suffix!r}（只接受 .yaml、.yml、.json）")
    try:
        # utf-8-sig：容許 Windows 編輯器加上的 BOM
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ContentError(path, "找不到檔案") from None
    except UnicodeDecodeError as exc:
        raise ContentError(path, f"檔案不是有效的 UTF-8：{exc}") from exc
    except OSError as exc:
        raise ContentError(path, f"無法讀取檔案：{exc}") from exc

    try:
        if suffix in _YAML_SUFFIXES:
            data: object = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except yaml.YAMLError as exc:
        raise ContentError(path, f"YAML 格式錯誤：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContentError(path, f"JSON 格式錯誤：{exc}") from exc
    return data


def _summarize_validation_error(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False)
    lines = []
    for err in errors[:_MAX_REPORTED_ERRORS]:
        loc = ".".join(str(part) for part in err["loc"]) or "（根）"
        msg = err["msg"].removeprefix("Value error, ")  # 自訂驗證訊息已是中文，不需要英文前綴
        lines.append(f"  - {loc}: {msg}")
    if len(errors) > _MAX_REPORTED_ERRORS:
        lines.append(f"  - ……另有 {len(errors) - _MAX_REPORTED_ERRORS} 個錯誤")
    return f"驗證失敗（{len(errors)} 個錯誤）：\n" + "\n".join(lines)


def load_content_file[M: BaseModel](path: str | Path, model: type[M]) -> M:
    """讀取 ``.yaml``／``.yml``／``.json`` 並以 ``model`` 驗證。

    YAML 一律使用 ``yaml.safe_load``。任何讀取、解析或驗證錯誤都轉成
    :class:`~trpg.shared.errors.ContentError`，訊息包含檔案路徑與錯誤摘要。
    """
    path = Path(path)
    data = _read_raw(path)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ContentError(path, _summarize_validation_error(exc)) from exc
