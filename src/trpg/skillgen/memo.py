"""組合器的純函式快取（PERF-2）。

1. **草稿結果**（:func:`library_memo` ＋ :func:`draft_key`）：隨機組合器對大量種子變體反覆組技能；
   傳說的候選列舉（:mod:`trpg.skillgen.composer_special`）從有限的結構空間抽出，一再對**同樣的
   草稿**（只差 ID 與暫定敘事文字裡的種子）做 schema 驗證、預算計算與驗證器檢查。這些結果只取決於
   草稿內容與內容庫，所以可以快取：

   - 鍵是草稿去掉 ``id`` 與 ``narrative`` 之後的 JSON（``sort_keys``）的 BLAKE2b 摘要（不用內建
     ``hash()``）；兩者不影響驗證、預算與驗證器的結果（ID 只出現在違規訊息裡，敘事文字沒有限制）。
   - 表掛在內容庫上（以物件身分對應、用弱參照確認，內容庫被回收時一起丟掉）；``dataclasses.replace``
     換內容後是新的內容庫、新的空表。
   - 每張表最多 :data:`MEMO_LIMIT` 筆，滿了就清空（只影響速度，不影響結果）。

   快取只記「結果」（是否合格），回傳給呼叫者的技能一律照原本的流程重新驗證建出，所以 ID 與敘事
   文字跟沒有快取時逐字相同。
2. **ID 對照**（:func:`by_id`）：內容表（凍結的 model）的 ``by_id()`` 每次都重建字典；預算與驗證器
   每個效果都要查，改成同一張表只建一次。
"""

from __future__ import annotations

import hashlib
import json
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from trpg.content.library import ContentLibrary

__all__ = ["MEMO_LIMIT", "by_id", "clear_memos", "derived", "draft_key", "library_memo"]

MEMO_LIMIT = 200_000
"""每張快取表的上限（筆）：滿了就清空。"""

_SEED_FIELDS = frozenset({"id", "narrative"})
"""草稿裡帶種子的欄位（不影響驗證與預算），不進鍵。"""


@dataclass
class _Memo:
    ref: weakref.ReferenceType[ContentLibrary]
    tables: dict[str, dict[str, Any]] = field(default_factory=dict)


_MEMOS: dict[int, _Memo] = {}


def _forget(key: int, ref: weakref.ReferenceType[ContentLibrary]) -> None:
    memo = _MEMOS.get(key)
    if memo is not None and memo.ref is ref:
        del _MEMOS[key]


def clear_memos() -> None:
    """清空所有草稿結果快取與 ID 對照（量測最壞情況與測試用；不影響結果）。"""
    _MEMOS.clear()
    _INDEXES.clear()


def library_memo(library: ContentLibrary, table: str) -> dict[str, Any]:
    """``library`` 上名為 ``table`` 的快取表（沒有就建一張空的）。以物件身分對應，並用弱參照
    確認仍是同一個內容庫；內容庫被回收時整組表一起移除。"""
    key = id(library)
    memo = _MEMOS.get(key)
    if memo is None or memo.ref() is not library:
        ref = weakref.ref(library)
        memo = _Memo(ref)
        _MEMOS[key] = memo
        weakref.finalize(library, _forget, key, ref)
    found = memo.tables.get(table)
    if found is None:
        found = memo.tables[table] = {}
    elif len(found) >= MEMO_LIMIT:
        found.clear()
    return found


class _Indexed[T](Protocol):
    def by_id(self) -> dict[str, T]: ...


_INDEX_LIMIT = 256
_INDEXES: dict[tuple[int, str], tuple[object, Any]] = {}


def derived[T](owner: object, name: str, build: Callable[[], T]) -> T:
    """``owner``（凍結的內容 model）上名為 ``name`` 的衍生值，同一個物件只建一次（以物件身分對應，
    並持有該物件確保身分不會被重用）。**回傳值是共用的，呼叫者不可修改。**"""
    key = (id(owner), name)
    found = _INDEXES.get(key)
    if found is not None and found[0] is owner:
        value: T = found[1]
        return value
    if len(_INDEXES) >= _INDEX_LIMIT:
        _INDEXES.clear()
    built = build()
    _INDEXES[key] = (owner, built)
    return built


def by_id[T](table: _Indexed[T]) -> dict[str, T]:
    """``table.by_id()`` 的快取版（:func:`derived`）：內容表是凍結的 model，同一張表的 ID 對照只建
    一次。**回傳的字典是共用的，呼叫者不可修改。**"""
    return derived(table, "by_id", table.by_id)


def draft_key(data: Mapping[str, Any]) -> str | None:
    """草稿 ``data`` 的快取鍵：去掉 ``id`` 與 ``narrative`` 的 JSON（鍵排序）的 BLAKE2b 摘要。內容有
    JSON 表示不了的值時回傳 ``None``（不快取）。"""
    try:
        text = json.dumps(
            {k: v for k, v in data.items() if k not in _SEED_FIELDS},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return None
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()
