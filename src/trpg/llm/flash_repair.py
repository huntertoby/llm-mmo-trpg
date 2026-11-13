"""閃現提議的本地修正（Phase LF-2；``docs/phases/PhaseLF計畫.md`` 4.1 第 3 點）。

模型常犯、但意思明確的小錯不送回模型重問，直接在本地改正，每一種修正記一個代碼
（``flash.repaired.*``，評估工具統計）：

- 模板只對應一個類別：類別填錯直接改正（``flash.repaired.category``）。
- 參數選單只有一個值而沒填：補上（``flash.repaired.param_filled``）；模板不用填卻填了：拿掉
  （``flash.repaired.param_dropped``）。
- 代號前後空白、空字串當 null（``flash.repaired.space``）。
- 說明與名稱：前後空白（``note_space``）、半形標點與數字轉全形（``note_width``／``name_width``）、
  尾巴重複的句號（``note_period``）、超過上限時截到最後一個標點（``note_cut``；截完仍要過檢查）。

修正只是改寫「模型說了什麼」，之後照樣走目錄與引擎的驗證（守則 3）。純函式、確定性。
"""

from __future__ import annotations

import re
from typing import Final

from trpg.llm.prompts.flash import NOTE_MAX_CHARS
from trpg.skillgen.flash_catalog import FlashCatalog

__all__ = [
    "PARAM_FIELDS",
    "normalize_name",
    "normalize_note",
    "repair_fields",
]

PARAM_FIELDS: Final = ("keyword", "element", "shape")
_ID_FIELDS: Final = ("category", "template", *PARAM_FIELDS)
_HALF_TO_FULL: Final = str.maketrans(
    {
        ",": "，",
        ".": "。",
        ";": "；",
        ":": "：",
        "!": "！",
        "?": "？",
        "(": "（",
        ")": "）",
        **{str(d): chr(0xFF10 + d) for d in range(10)},
    }
)
_NAME_DOTS: Final = str.maketrans(
    {"·": "・", "•": "・", "‧": "・", "．": "・", "(": "（", ")": "）"}
)
_CUT_MARKS: Final = "。，；！？、"
_SPACES: Final = " \t\r\n　"
_REPEATED_END = re.compile(r"。{2,}$")


def repair_fields(
    fields: dict[str, str | None], catalog: FlashCatalog
) -> tuple[dict[str, str | None], tuple[str, ...]]:
    """修正一個提議項目的代號欄位（``category``、``template``、參數）：回傳修正後的欄位與修正碼。
    模板不在目錄裡時只做空白修正（之後照常被擋）。"""
    out = dict(fields)
    codes: list[str] = []
    for name in _ID_FIELDS:
        value = out.get(name)
        if isinstance(value, str) and value.strip(_SPACES) != value:
            out[name] = value.strip(_SPACES)
            codes.append("flash.repaired.space")
        if name in PARAM_FIELDS and out.get(name) == "":
            out[name] = None
            codes.append("flash.repaired.space")
    template = out.get("template")
    entry = None if template is None else catalog.entry(template)
    if entry is None:
        return out, tuple(dict.fromkeys(codes))
    if out.get("category") != entry.category:
        out["category"] = entry.category
        codes.append("flash.repaired.category")
    for name, choices in zip(
        PARAM_FIELDS, (entry.keywords, entry.elements, entry.shapes), strict=True
    ):
        given = out.get(name)
        if given is None and len(choices) == 1:
            out[name] = choices[0]
            codes.append("flash.repaired.param_filled")
        elif given is not None and not choices:
            out[name] = None
            codes.append("flash.repaired.param_dropped")
    return out, tuple(dict.fromkeys(codes))


def _cut(text: str, limit: int) -> str | None:
    """截到上限內最後一個標點（逗號類換成句號）；上限內沒有標點時回傳 ``None``。"""
    head = text[:limit]
    index = max(head.rfind(mark) for mark in _CUT_MARKS)
    if index < 1:
        return None
    body = head[:index].rstrip(_CUT_MARKS)
    return f"{body}。" if body else None


def normalize_note(note: str) -> tuple[str, tuple[str, ...]]:
    """說明文字的本地修正：前後空白、半形轉全形、尾巴重複的句號、超長截到最後一個標點。回傳修正後的
    文字與修正碼（不保證合格，呼叫者照常檢查）。"""
    codes: list[str] = []
    text = note.strip(_SPACES)
    if text != note:
        codes.append("flash.repaired.note_space")
    wide = text.translate(_HALF_TO_FULL)
    if wide != text:
        codes.append("flash.repaired.note_width")
    text = wide
    single = _REPEATED_END.sub("。", text)
    if single != text:
        codes.append("flash.repaired.note_period")
    text = single
    if len(text) > NOTE_MAX_CHARS:
        cut = _cut(text, NOTE_MAX_CHARS)
        if cut is not None:
            codes.append("flash.repaired.note_cut")
            text = cut
    return text, tuple(codes)


def normalize_name(name: str) -> tuple[str, tuple[str, ...]]:
    """名稱的本地修正：前後空白、間隔號與半形括號換成「・（）」。"""
    codes: list[str] = []
    text = name.strip(_SPACES)
    if text != name:
        codes.append("flash.repaired.name_space")
    wide = text.translate(_NAME_DOTS)
    if wide != text:
        codes.append("flash.repaired.name_width")
    return wide, tuple(codes)
