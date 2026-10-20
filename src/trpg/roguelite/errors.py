"""一輪流程的錯誤。"""

from __future__ import annotations

from trpg.shared.errors import TrpgError

__all__ = ["ChoiceError", "NodeConflictError", "RunError", "SaveFormatError"]


class RunError(TrpgError):
    """一輪流程的錯誤（基底）。"""


class ChoiceError(RunError):
    """選擇或建立一輪的內容不合法（未知的 build、配點不對、候選索引錯、技能欄位超過上限）。"""


class NodeConflictError(RunError):
    """請求與一輪目前的節點不符（例如不在升級節點卻送升級選擇、一輪已結束）。"""


class SaveFormatError(RunError):
    """存檔格式不對、版本不符，或存檔的戰鬥紀錄無法由這一版程式重播。"""
