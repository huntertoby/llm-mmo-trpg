"""專案共用的錯誤類別。"""

from __future__ import annotations

from pathlib import Path

__all__ = ["ContentError", "IllegalActionError", "TrpgError"]


class TrpgError(Exception):
    """本專案所有自訂錯誤的基底類別。"""


class ContentError(TrpgError):
    """內容資料（``content/`` 下的 YAML／JSON）讀取或驗證失敗。

    一律帶有出錯的檔案路徑與原因，訊息格式為 ``"<路徑>: <原因>"``。
    """

    def __init__(self, path: str | Path, reason: str) -> None:
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"{self.path}: {reason}")


class IllegalActionError(TrpgError):
    """玩家或 AI 提出的行動不合法（Phase 1 起由規則引擎使用，本階段只定義）。"""
