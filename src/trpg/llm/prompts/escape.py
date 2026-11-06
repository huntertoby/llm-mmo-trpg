"""資料區跳脫：任何放進 prompt 資料區的文字都不能跳出資料區。

規則（確定性）：
1. 統一換行為 ``\\n``，移除除換行與 tab 以外的控制字元（含 NUL、ESC、零寬與方向控制字元）。
2. ``&`` → ``&amp;``、``<`` → ``&lt;``、``>`` → ``&gt;``。因此玩家文字不可能產生任何標籤
   （``</player_input>``、``<player_input>``、巢狀標籤、偽造的區塊標籤）。
3. 玩家文字超過長度上限時截斷（預設 ``PLAYER_TEXT_MAX_CHARS``）。
「忽略以上指令」之類的字樣不做過濾（過濾不可靠）；它們只出現在資料區，
而系統指令明確聲明資料區內的任何文字都不是指令。
"""

from __future__ import annotations

import json
import unicodedata

PLAYER_TEXT_MAX_CHARS = 500
_KEEP_CONTROLS = {"\n", "\t"}
_DROPPED_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}


def _is_dropped(ch: str) -> bool:
    if ch in _KEEP_CONTROLS:
        return False
    return unicodedata.category(ch) in _DROPPED_CATEGORIES


def escape_text(text: str) -> str:
    """跳脫一段要放進資料區的文字（不截斷）。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(ch for ch in normalized if not _is_dropped(ch))
    return cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap_player_input(text: str, *, max_chars: int = PLAYER_TEXT_MAX_CHARS) -> str:
    """把玩家文字截斷、跳脫後包進 ``<player_input>`` 標籤。"""
    return f"<player_input>{escape_text(text[:max_chars])}</player_input>"


PLAYER_NAME_MAX_CHARS = 12
"""玩家角色名字的上限（同建角 API 的 ``NAME_MAX``；``tests/llm/test_prompts.py`` 檢查兩者一致）。"""
NAME_TOKEN = "{name}"
"""資料區的稱謂裡代表「叫名字」的記號（名字本身只出現在 ``<player_input>``）。"""


def address_token(address: str, name: str) -> str:
    """稱謂放進資料區的寫法：稱謂就是玩家名字（叫名字）時寫 ``{name}``，名字不出 ``<player_input>``
    （守則 7，6R-2b）；其他稱謂是內容資料的模板（「這位」「施主」），照原樣。"""
    return NAME_TOKEN if not address or address == name else address


def player_block(name: str, address: str) -> str:
    """``<player>`` 區塊（6R-2b）：玩家自己取的名字包進 ``<player_input>``（跳脫、截斷），
    NPC 的稱謂（引擎代入的模板）用 JSON 放在後面。"""
    payload = json.dumps(
        {"address": address_token(address, name)}, ensure_ascii=False, separators=(",", ":")
    )
    name_part = wrap_player_input(name, max_chars=PLAYER_NAME_MAX_CHARS)
    return f"<player>\n{name_part}\n{escape_text(payload)}\n</player>"
