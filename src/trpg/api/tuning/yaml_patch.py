"""YAML 字面替換（數值工坊 NW-1a，規格 5.2）：只改一個純量的文字，其他位元組不動、註解保留。

沒有能保留註解的 round-trip 套件，所以用 ``yaml.compose``（純 Python 的 ``SafeLoader``）拿到節點的
位置（``start_mark.index``／``end_mark.index``），直接替換那段文字：

- 欄位存在：替換純量的字面（只接受沒加引號的整數）。
- 欄位沒寫（用預設值）：區塊式 mapping 在最後一項之後插一行同縮排的 ``key: value``；流式 mapping
  （``{…}``）在最後一項之後插 ``, key: value``（空的 ``{}`` 插 ``key: value``）；中間層也沒寫時一次
  插整段（例 ``resist: {physical: 100}``）。
- 改成「沒寫」（``None``，反向改動單用）：刪掉那一項（區塊式刪整行；那行有註解或是唯一一項時擋下）。

每一筆改完都重新 parse，結果必須等於「原資料只改那一個值」，否則丟 :class:`PatchError`
（說明哪一筆）；呼叫端整張改動單不寫。行尾照原檔（LF／CRLF），UTF-8 BOM 保留。
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any, Final

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import PathPart, format_path

__all__ = ["MISSING", "PatchError", "lookup", "patch_text"]

_INT_TAG: Final = "tag:yaml.org,2002:int"
_BOM: Final = "﻿"


class PatchError(ValueError):
    """這筆改動沒辦法安全地改寫成文字（訊息是中文、帶欄位路徑）。"""


class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


MISSING: Final = _Missing()
""":func:`lookup` 的「沒寫」。"""


def lookup(data: Any, parts: Sequence[PathPart]) -> Any:
    """照路徑取值；中途沒有這個鍵回 :data:`MISSING`；清單索引超出或型別不對丟
    :class:`PatchError`。"""
    node = data
    for part in parts:
        if isinstance(part, int):
            if not isinstance(node, list) or not 0 <= part < len(node):
                raise PatchError(f"{format_path(parts)}：清單沒有第 {part} 項")
            node = node[part]
        elif isinstance(node, dict):
            if part not in node:
                return MISSING
            node = node[part]
        elif node is None:
            return MISSING
        else:
            raise PatchError(f"{format_path(parts)}：{part} 的上一層不是對照表")
    return node


def _expected(data: Any, parts: Sequence[PathPart], value: int | None) -> Any:
    out = copy.deepcopy(data)
    node = out
    for part in parts[:-1]:
        if isinstance(part, int):
            node = node[part]
        else:
            if node.get(part) is None:
                node[part] = {}
            node = node[part]
    last = parts[-1]
    if value is None:
        node.pop(last, None)
    else:
        node[last] = value
    return out


def _key_of(item: tuple[Node, Node]) -> str | None:
    key = item[0]
    return key.value if isinstance(key, ScalarNode) else None


def _last_leaf(node: Node) -> Node:
    """區塊式集合的最後一個葉節點（純量或流式集合）：它的 ``end_mark`` 是精確的。"""
    while isinstance(node, (MappingNode, SequenceNode)) and not node.flow_style and node.value:
        last = node.value[-1]
        node = last[1] if isinstance(node, MappingNode) else last
    return node


def _line_end(text: str, index: int) -> int:
    """``index`` 所在行的下一行開頭（沒有換行時是檔尾）。"""
    if index > 0 and text[index - 1] == "\n":
        return index
    found = text.find("\n", index)
    return len(text) if found < 0 else found + 1


def _literal(rest: Sequence[PathPart], value: int) -> str:
    out = str(value)
    for key in reversed(rest[1:]):
        out = f"{{{key}: {out}}}"
    return f"{rest[0]}: {out}"


def _insert(text: str, mapping: MappingNode, rest: Sequence[PathPart], value: int) -> str:
    where = format_path(rest)
    if any(isinstance(p, int) for p in rest):
        raise PatchError(f"{where}：清單沒有這一項，不能自動新增")
    item = _literal(rest, value)
    if mapping.flow_style:
        close = mapping.end_mark.index - 1
        if text[close] != "}":
            raise PatchError(f"{where}：找不到流式寫法的右括號")
        if not mapping.value:
            return text[:close] + item + text[close:]
        at = mapping.value[-1][1].end_mark.index
        return text[:at] + ", " + item + text[at:]
    if not mapping.value:
        raise PatchError(f"{where}：上一層是空的區塊寫法，不能自動新增")
    newline = "\r\n" if "\r\n" in text else "\n"
    column: int = mapping.value[0][0].start_mark.column
    indent = " " * column
    at = _line_end(text, _last_leaf(mapping).end_mark.index)
    prefix = "" if at == 0 or text[at - 1] == "\n" else newline
    return text[:at] + prefix + indent + item + newline + text[at:]


def _delete(text: str, mapping: MappingNode, index: int, where: str) -> str:
    key, value = mapping.value[index]
    start, end = key.start_mark.index, value.end_mark.index
    if mapping.flow_style:
        if index > 0:
            start = mapping.value[index - 1][1].end_mark.index
        elif len(mapping.value) > 1:
            end = mapping.value[1][0].start_mark.index
        return text[:start] + text[end:]
    if len(mapping.value) == 1:
        raise PatchError(f"{where}：是這一層唯一的一項，不能自動刪除")
    line_start = text.rfind("\n", 0, start) + 1
    line_end = _line_end(text, end)
    if text[line_start:start].strip() or text[end:line_end].strip():
        raise PatchError(f"{where}：這一行還有別的內容（例如註解），不能自動刪除")
    return text[:line_start] + text[line_end:]


def _replace(text: str, node: Node, value: int | None, where: str) -> str:
    if not isinstance(node, ScalarNode) or node.tag != _INT_TAG or node.style:
        raise PatchError(f"{where}：原本的寫法不是沒加引號的整數，不能自動改")
    if value is None:
        raise PatchError(f"{where}：內部錯誤（刪除要從上一層處理）")
    return text[: node.start_mark.index] + str(value) + text[node.end_mark.index :]


def _uses_anchors(text: str) -> bool:
    return any(
        isinstance(e, yaml.AliasEvent) or getattr(e, "anchor", None)
        for e in yaml.parse(text, Loader=yaml.SafeLoader)
    )


def _patch_one(text: str, parts: Sequence[PathPart], value: int | None) -> str:
    where = format_path(parts)
    if _uses_anchors(text):
        raise PatchError(f"{where}：這個檔用了錨點或別名（& / *），不能自動改")
    node: Node = yaml.compose(text, Loader=yaml.SafeLoader)
    for depth, part in enumerate(parts):
        last = depth == len(parts) - 1
        if isinstance(part, int):
            if not isinstance(node, SequenceNode) or not 0 <= part < len(node.value):
                raise PatchError(f"{where}：清單沒有第 {part} 項")
            node = node.value[part]
            continue
        if not isinstance(node, MappingNode):
            raise PatchError(f"{where}：{part} 的上一層不是對照表")
        index = next((i for i, item in enumerate(node.value) if _key_of(item) == part), None)
        if index is None:
            return text if value is None else _insert(text, node, parts[depth:], value)
        if last and value is None:
            child = node.value[index][1]
            if not isinstance(child, ScalarNode) or child.tag != _INT_TAG or child.style:
                raise PatchError(f"{where}：原本的寫法不是沒加引號的整數，不能自動刪除")
            return _delete(text, node, index, where)
        node = node.value[index][1]
    return _replace(text, node, value, where)


def patch_text(text: str, changes: Sequence[tuple[Sequence[PathPart], int | None]]) -> str:
    """依序套用 ``(路徑, 新值)``（``None``＝刪掉、改回沒寫），每筆改完都驗證。"""
    bom = text.startswith(_BOM)
    body = text.removeprefix(_BOM)
    for parts, value in changes:
        where = format_path(parts)
        try:
            before = parse_yaml(body)
        except yaml.YAMLError as exc:
            raise PatchError(f"{where}：原檔的 YAML 讀不懂：{exc}") from exc
        if lookup(before, parts) is MISSING and value is None:  # 清單索引不對也在這裡先擋
            continue
        try:
            after_text = _patch_one(body, parts, value)
            after = parse_yaml(after_text)
        except yaml.YAMLError as exc:
            raise PatchError(f"{where}：改完的 YAML 讀不懂：{exc}") from exc
        if after != _expected(before, parts, value):
            raise PatchError(f"{where}：改完的結果和預期不同（特殊寫法），不能自動改")
        body = after_text
    return _BOM + body if bom else body
