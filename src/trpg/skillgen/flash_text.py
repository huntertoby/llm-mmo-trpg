"""閃現變化的名稱與描述（Phase LF-1；``docs/design/06-技能.md`` 6.34.3、6.34.7）。

LLM 提議的文字（名稱 ``name_zh``、一句話描述 ``note_zh``）和變化的**結構**分開存
（:class:`VariationText`，以 :meth:`~trpg.skillgen.flash_state.Variation.key` 對應）。出題時
:func:`clean_text` 把**合格的**文字掛到變化上，之後跟著變化歷程存下來，所以下一次閃現、升階重配都
留得住名稱。

引擎照樣驗證（守則 3）：文字只影響顯示，從日誌或暫存讀進來也要再檢查一次；不合格的欄位當作沒有
（名稱退回「{前綴}・{原名}」、描述退回模板說明），**不會**讓變化本身不合格。

- 名稱只給大變化與轉型（6.34.3：小變化不改名稱）；全形中文與「・（）」，最多
  :data:`NAME_MAX_CHARS` 字（同 ``content/llm/world_*.yaml`` 的 ``naming.name_max_chars``）。
- 描述給任何變化；全形中文與全形標點，最多 :data:`NOTE_MAX_CHARS` 字（同 LLM 閃現 prompt 的上限）。

LLM 端更嚴的檢查（禁字、重名、敘事與效果一致、古風詞）在 :mod:`trpg.llm` 做；這裡只做不需要讀檔的
字元與長度檢查，當最後一道防線。純函式。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from trpg.skillgen.flash_state import Variation

__all__ = [
    "NAME_MAX_CHARS",
    "NOTE_MAX_CHARS",
    "VariationText",
    "clean_name",
    "clean_note",
    "clean_text",
    "text_map",
]

NAME_MAX_CHARS: Final = 12
NOTE_MAX_CHARS: Final = 40
_NAME_CHARS = re.compile(r"^[一-鿿・（）]+$")
_NOTE_CHARS = re.compile(r"^[一-鿿　-〿＀-￯・—…‘-”、。，；：！？（）「」『』《》]+$")


class VariationText(BaseModel):
    """一個變化的文字（以變化的穩定鍵 ``key`` 對應；沒有的欄位不輸出）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    name_zh: str | None = Field(default=None, exclude_if=lambda v: v is None)
    note_zh: str | None = Field(default=None, exclude_if=lambda v: v is None)


def clean_name(name: str | None) -> str | None:
    """合格的名稱原樣回傳，否則 ``None``。"""
    if name is None or not 0 < len(name) <= NAME_MAX_CHARS:
        return None
    return name if _NAME_CHARS.match(name) else None


def clean_note(note: str | None) -> str | None:
    """合格的描述原樣回傳，否則 ``None``。"""
    if note is None or not 0 < len(note) <= NOTE_MAX_CHARS:
        return None
    return note if _NOTE_CHARS.match(note) else None


def clean_text(variation: Variation, text: VariationText | None) -> Variation:
    """把 ``text`` 裡合格的欄位掛到 ``variation`` 上（鍵不對、不合格的欄位當作沒有）。小變化不掛
    名稱。原本就帶的文字一律先拿掉，只認這一次給的。"""
    bare = variation.model_copy(update={"name_zh": None, "note_zh": None})
    if text is None or text.key != variation.key():
        return bare
    name = None if variation.source == "minor" else clean_name(text.name_zh)
    note = clean_note(text.note_zh)
    if name is None and note is None:
        return bare
    return bare.model_copy(update={"name_zh": name, "note_zh": note})


def text_map(texts: Iterable[VariationText]) -> Mapping[str, VariationText]:
    """依鍵查文字（同一個鍵有多筆時取最後一筆）。"""
    return {t.key: t for t in texts}
