"""伺服器層的牆上時鐘（CODE-3，整理提案 I3）。

``AccountStore``、``LeagueStore``、``WorldStore``、``LlmHealth`` 的 ``clock`` 參數預設都用這個；
測試改傳自己的 ``clock``。引擎與世界規則不讀時間，時間一律由這一層傳入。
"""

from __future__ import annotations

import time

__all__ = ["unix_now"]


def unix_now() -> int:
    """現在的 Unix 時間（整數秒）。"""
    return int(time.time())
