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

import bisect
import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import PathPart, format_path

__all__ = [
    "DICE_TEXT",
    "EXCEPTIONS_KEY",
    "MISSING",
    "PatchError",
    "PatchValue",
    "exception_comment",
    "lookup",
    "patch_exception_list",
    "patch_text",
]

_INT_TAG: Final = "tag:yaml.org,2002:int"
_STR_TAG: Final = "tag:yaml.org,2002:str"
EXCEPTIONS_KEY: Final = "known_budget_exceptions"
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


type PatchValue = int | str | Sequence[str] | None
"""整數、骰子字串（``2d6``）、ID 清單（NW-2a）；``None``＝刪掉。"""

DICE_TEXT: Final = re.compile(r"^\d+d\d+$")
_ID_TEXT: Final = re.compile(r"^[a-z][a-z0-9_]*$")


def _plain(value: PatchValue) -> Any:
    if value is None or isinstance(value, int | str):
        return value
    return list(value)


def _expected(data: Any, parts: Sequence[PathPart], value: PatchValue) -> Any:
    value = _plain(value)
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


def _value_text(value: int | str | Sequence[str], where: str) -> str:
    """值的 YAML 字面（整數、骰子、流式 ID 清單）。"""
    if isinstance(value, bool):
        raise PatchError(f"{where}：不能寫布林值")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        if DICE_TEXT.match(value) is None:
            raise PatchError(f"{where}：骰子要寫成 NdM（例：2d6）")
        return value
    bad = [x for x in value if not isinstance(x, str) or _ID_TEXT.match(x) is None]
    if bad:
        raise PatchError(f"{where}：清單只能放 ID（{bad[0]!r} 不行）")
    return "[" + ", ".join(value) + "]"


def _literal(rest: Sequence[PathPart], value: int | str | Sequence[str]) -> str:
    out = _value_text(value, format_path(rest))
    for key in reversed(rest[1:]):
        out = f"{{{key}: {out}}}"
    return f"{rest[0]}: {out}"


def _insert(
    text: str, mapping: MappingNode, rest: Sequence[PathPart], value: int | str | Sequence[str]
) -> str:
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
    if isinstance(value, SequenceNode | MappingNode) and not value.flow_style:
        end = _last_leaf(value).end_mark.index
    line_start = text.rfind("\n", 0, start) + 1
    line_end = _line_end(text, end)
    if text[line_start:start].strip() or text[end:line_end].strip():
        raise PatchError(f"{where}：這一行還有別的內容（例如註解），不能自動刪除")
    if "#" in text[start:end]:
        raise PatchError(f"{where}：這段有註解，不能自動刪除")
    return text[:line_start] + text[line_end:]


def _scalar_ok(node: Node, value: int | str) -> bool:
    """原本的寫法能不能直接換字面：沒加引號的整數換整數、沒加引號的骰子換骰子。"""
    if not isinstance(node, ScalarNode) or node.style:
        return False
    if isinstance(value, int):
        return node.tag == _INT_TAG
    return node.tag == _STR_TAG and DICE_TEXT.match(node.value) is not None


def _replace_sequence(
    text: str, key: Node | None, node: SequenceNode, value: Sequence[str], where: str
) -> str:
    """整個清單換掉（NW-2a T3）：流式換成新的流式字面；區塊式照原縮排重寫各行；範圍內有註解擋。"""
    literal = _value_text(value, where)
    if node.flow_style or not node.value:
        start, end = node.start_mark.index, node.end_mark.index
        if "#" in text[start:end]:
            raise PatchError(f"{where}：清單裡有註解，不能自動改")
        return text[:start] + literal + text[end:]
    start = text.rfind("\n", 0, node.start_mark.index) + 1
    end = _line_end(text, _last_leaf(node).end_mark.index)
    region = text[start:end]
    if "#" in region:
        raise PatchError(f"{where}：清單裡有註解，不能自動改")
    if any(not isinstance(item, ScalarNode) for item in node.value):
        raise PatchError(f"{where}：清單的項目不是單純的 ID，不能自動改")
    if text[start : node.start_mark.index].strip():
        raise PatchError(f"{where}：清單和別的內容在同一行，不能自動改")
    newline = "\r\n" if "\r\n" in region else "\n"
    if not value:  # 區塊式改成空清單：鍵後面直接寫 []
        if key is None:
            raise PatchError(f"{where}：區塊式清單不能改成空的")
        colon = text.index(":", key.end_mark.index)
        return text[: colon + 1] + " []" + newline + text[end:]
    indent = " " * node.start_mark.column
    lines = "".join(f"{indent}- {item}{newline}" for item in value)
    return text[:start] + lines + text[end:]


def _replace(text: str, node: Node, value: PatchValue, where: str, key: Node | None = None) -> str:
    if value is None:
        raise PatchError(f"{where}：內部錯誤（刪除要從上一層處理）")
    if not isinstance(value, int | str):
        if not isinstance(node, SequenceNode):
            raise PatchError(f"{where}：原本的寫法不是清單，不能自動改")
        return _replace_sequence(text, key, node, value, where)
    if not _scalar_ok(node, value):
        kind = "整數" if isinstance(value, int) else "骰子（NdM）"
        raise PatchError(f"{where}：原本的寫法不是沒加引號的{kind}，不能自動改")
    literal = _value_text(value, where)
    return text[: node.start_mark.index] + literal + text[node.end_mark.index :]


def _uses_anchors(text: str) -> bool:
    return any(
        isinstance(e, yaml.AliasEvent) or getattr(e, "anchor", None)
        for e in yaml.parse(text, Loader=yaml.SafeLoader)
    )


def _patch_one(text: str, parts: Sequence[PathPart], value: PatchValue) -> str:
    where = format_path(parts)
    if _uses_anchors(text):
        raise PatchError(f"{where}：這個檔用了錨點或別名（& / *），不能自動改")
    node: Node = yaml.compose(text, Loader=yaml.SafeLoader)
    key: Node | None = None
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
            plain = isinstance(child, ScalarNode) and (
                _scalar_ok(child, 0) or _scalar_ok(child, "1d1")
            )
            if not (isinstance(child, SequenceNode) or plain):
                raise PatchError(f"{where}：原本的寫法不能自動刪除")
            return _delete(text, node, index, where)
        key, node = node.value[index]
    return _replace(text, node, value, where, key)


def patch_text(text: str, changes: Sequence[tuple[Sequence[PathPart], PatchValue]]) -> str:
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


# ---------------------------------------------------------------------------
# 預算例外清單（NW-2a T5）
# ---------------------------------------------------------------------------


def exception_comment(skill_id: str, ratio_text: str, date: str) -> str:
    """工坊登記例外時寫在清單上方的註解行（不含換行）。"""
    return f"# 數值工坊 {date}：{skill_id} 比例 {ratio_text}（使用者確認）"


def _comment_pattern(skill_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"^# 數值工坊 \d{{4}}-\d{{2}}-\d{{2}}：{re.escape(skill_id)} 比例 [^\s（]+（使用者確認）$"
    )


def patch_exception_list(
    text: str, add: Mapping[str, str], remove: Sequence[str], date: str
) -> str:
    """``skill_budget.yaml`` 的 ``known_budget_exceptions``：加入 ``add``（ID → 比例文字）、移除
    ``remove``。只動那一行與它上方工坊寫的註解行，其他位元組不動：

    - 加入：ID 依字母序插進流式清單（原有的順序不動），清單那一行上方插一行
      :func:`exception_comment`；
    - 移除：從清單拿掉，並刪掉它那一行工坊註解（只刪格式完全相符的；手寫的註解不動）。

    改完重新 parse，結果必須只差那個清單。"""
    if not add and not remove:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    if not isinstance(root, MappingNode):
        raise PatchError(f"{EXCEPTIONS_KEY}：skill_budget.yaml 的最上層不是對照表")
    found = next((item for item in root.value if _key_of(item) == EXCEPTIONS_KEY), None)
    if found is None:
        raise PatchError(f"{EXCEPTIONS_KEY}：skill_budget.yaml 找不到這個鍵")
    key, node = found
    if not isinstance(node, SequenceNode) or not node.flow_style:
        raise PatchError(f"{EXCEPTIONS_KEY}：清單不是流式寫法（[a, b]），不能自動改")
    if text.count("\n", node.start_mark.index, node.end_mark.index):
        raise PatchError(f"{EXCEPTIONS_KEY}：清單跨了好幾行，不能自動改")
    ids: list[str] = [str(item.value) for item in node.value if isinstance(item, ScalarNode)]
    gone = set(remove)
    new_ids = [i for i in ids if i not in gone]
    for skill_id in sorted(add):
        if skill_id not in new_ids:
            bisect.insort(new_ids, skill_id)
    before = parse_yaml(text)
    out = text[: node.start_mark.index] + _value_text(new_ids, EXCEPTIONS_KEY)
    out += text[node.end_mark.index :]
    line_start = text.rfind("\n", 0, key.start_mark.index) + 1
    added = "".join(
        exception_comment(i, add[i], date) + newline for i in sorted(add) if i not in ids
    )
    out = out[:line_start] + added + out[line_start:]
    lines = out.splitlines(keepends=True)
    patterns = [_comment_pattern(i) for i in sorted(gone)]
    lines = [ln for ln in lines if not any(p.match(ln.rstrip("\r\n")) for p in patterns)]
    out = "".join(lines)
    after = parse_yaml(out)
    if after != {**before, EXCEPTIONS_KEY: new_ids}:
        raise PatchError(f"{EXCEPTIONS_KEY}：改完的結果和預期不同，不能自動改")
    return out
