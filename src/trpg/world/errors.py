"""大世界的錯誤。"""

from __future__ import annotations

from trpg.shared.errors import TrpgError

__all__ = ["WorldActionError", "WorldError", "WorldReplayError", "WorldSaveFormatError"]


class WorldError(TrpgError):
    """大世界的錯誤（基底）。"""


class WorldActionError(WorldError):
    """世界動作不合法（不相鄰、補給不足、有未處理的遭遇、不能紮營的地點…）；狀態不變。"""


class WorldReplayError(WorldError):
    """世界動作日誌無法重播（序號不遞增、時間倒退、找不到角色）。"""


class WorldSaveFormatError(WorldError):
    """世界、角色或日誌的存檔格式不對。"""
