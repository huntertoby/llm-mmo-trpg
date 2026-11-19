"""量類 ×10 換算（X10-1；``docs/design/05-戰鬥.md`` 5.4.1，#169 題 10）：欄位清單的檢查。

``scripts/x10/fields.yaml`` 列出 ``content/`` 每個數字欄位是 ×10、不變或待定。

用法::

    uv run python scripts/x10/rescale.py --check          # 檢查清單（有問題時結束碼 1）
    uv run python scripts/x10/rescale.py --unclassified   # 列出清單沒涵蓋的數字欄位
    uv run python scripts/x10/rescale.py --stats          # 清單統計

欄位清單的路徑語法（每段用 ``.`` 分開）：

- ``name``：mapping 的鍵（可含 ``*`` 萬用字元，例 ``*_permille``）；``*``：任一個鍵；
  ``**``：零到多段任意路徑。
- 鍵後面接 ``{k=v}``：這個鍵的值（mapping）裡 ``k`` 等於 ``v`` 才算。
- 鍵後面接 ``[]``：清單的任一項；``[k=v]``：清單裡 ``k`` 等於 ``v`` 的那幾項。
  ``v`` 可用 ``|`` 列多個，``~`` 代表沒寫這個鍵；``k!=v`` 是「不等於」；多個條件用 ``,`` 分開；
  值裡有 ``.``、``[`` 等符號時用雙引號包起來。可以連續接（``tiles[][]``）。
- 每個數字欄位只能落在一類：``scale``（×10）、``keep``（不變）、``pending``（待定，暫不 ×10）、
  ``unit_change``（不 ×10，但 X10-2 要改單位，例如預算係數）。
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

ROOT: Final = Path(__file__).resolve().parents[2]
CONTENT_DIR: Final = ROOT / "content"
FIELDS_PATH: Final = Path(__file__).resolve().parent / "fields.yaml"
CATEGORIES: Final = ("scale", "keep", "pending", "unit_change")
_INT_TAG: Final = "tag:yaml.org,2002:int"
_FLOAT_TAG: Final = "tag:yaml.org,2002:float"
_BOM: Final = "﻿"
_ABSENT: Final = "~"
_QUOTE: Final = '"'


class RescaleError(ValueError):
    """清單或內容有問題，整批不寫。"""


# ---------------------------------------------------------------------------
# 掃描 content/ 的數字欄位


@dataclass(frozen=True, slots=True)
class Step:
    """具體路徑的一段：mapping 的鍵（``key``），或清單的第 ``index`` 項。``item`` 是這一段的值
    （mapping 時）的純量欄位，給 ``{k=v}``／``[k=v]`` 篩選用。"""

    key: str | None = None
    index: int = -1
    item: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Leaf:
    file: str  # 相對 content/ 的 posix 路徑
    steps: tuple[Step, ...]
    node: ScalarNode

    @property
    def value(self) -> str:
        return str(self.node.value)

    @property
    def start(self) -> int:
        return int(self.node.start_mark.index)

    def display(self) -> str:
        """給人看的路徑：清單項有 ``id``（或 ``path``）時寫 ``[id=…]``，否則寫索引。"""
        out = ""
        for step in self.steps:
            if step.key is not None:
                out += ("." if out else "") + step.key
                continue
            fields = dict(step.item)
            name = next((k for k in ("id", "path") if k in fields), None)
            out += f"[{name}={fields[name]}]" if name is not None else f"[{step.index}]"
        return out


def _item_fields(node: Node) -> tuple[tuple[str, str], ...]:
    if not isinstance(node, MappingNode):
        return ()
    return tuple(
        (str(k.value), str(v.value))
        for k, v in node.value
        if isinstance(k, ScalarNode) and isinstance(v, ScalarNode)
    )


def _walk(node: Node, file: str, steps: tuple[Step, ...]) -> Iterator[Leaf]:
    if isinstance(node, MappingNode):
        for key, value in node.value:
            step = Step(key=str(key.value), item=_item_fields(value))
            yield from _walk(value, file, (*steps, step))
    elif isinstance(node, SequenceNode):
        for index, item in enumerate(node.value):
            yield from _walk(item, file, (*steps, Step(index=index, item=_item_fields(item))))
    elif isinstance(node, ScalarNode) and node.tag in (_INT_TAG, _FLOAT_TAG):
        yield Leaf(file, steps, node)


def content_files(content_dir: Path = CONTENT_DIR) -> list[Path]:
    return sorted(p for p in content_dir.rglob("*") if p.suffix in (".yaml", ".yml", ".json"))


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def compose(text: str) -> Node | None:
    node: Node | None = yaml.compose(text.removeprefix(_BOM), Loader=yaml.SafeLoader)
    return node


def scan_file(path: Path, content_dir: Path = CONTENT_DIR) -> list[Leaf]:
    rel = path.relative_to(content_dir).as_posix()
    node = compose(_read(path))
    return [] if node is None else list(_walk(node, rel, ()))


# ---------------------------------------------------------------------------
# 路徑樣式


@dataclass(frozen=True, slots=True)
class _Tok:
    kind: str  # "key" | "any_key" | "item" | "deep"
    name: str = ""
    filters: tuple[tuple[str, frozenset[str], bool], ...] = ()  # (鍵, 值, 是否為 !=)


def _split_top(text: str, sep: str) -> list[str]:
    """在括號與雙引號之外，用 ``sep`` 切開。"""
    parts: list[str] = []
    depth = 0
    quoted = False
    current = ""
    for ch in text:
        if ch == _QUOTE:
            quoted = not quoted
        elif not quoted and ch in "[{":
            depth += 1
        elif not quoted and ch in "]}":
            depth -= 1
        if ch == sep and depth == 0 and not quoted:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return parts


def _unquote(text: str) -> str:
    text = text.strip()
    quoted = text.startswith(_QUOTE) and text.endswith(_QUOTE) and len(text) > 1
    return text[1:-1] if quoted else text


def _parse_filters(body: str, pattern: str) -> tuple[tuple[str, frozenset[str], bool], ...]:
    if not body:
        return ()
    out: list[tuple[str, frozenset[str], bool]] = []
    for part in _split_top(body, ","):
        if "=" not in part:
            raise RescaleError(f"樣式 {pattern!r}：篩選要寫成 k=v 或 k!=v")
        key, _, values = part.partition("=")
        negate = key.endswith("!")
        key = key.removesuffix("!").strip()
        out.append((key, frozenset(_unquote(v) for v in _split_top(values, "|")), negate))
    return tuple(out)


def _closing(text: str, close: str) -> int:
    """``text[0]`` 是開括號；回傳對應的關括號位置（略過雙引號內），找不到時 −1。"""
    quoted = False
    for i, ch in enumerate(text[1:], start=1):
        if ch == _QUOTE:
            quoted = not quoted
        elif ch == close and not quoted:
            return i
    return -1


def _segment(part: str, pattern: str) -> tuple[str, str | None, list[str]]:
    """一段拆成（鍵名, ``{}`` 內文或 None, ``[]`` 內文清單）。"""
    i = 0
    while i < len(part) and part[i] not in "[{":
        i += 1
    name, rest = part[:i], part[i:]
    braces: str | None = None
    brackets: list[str] = []
    while rest:
        close = "}" if rest[0] == "{" else "]"
        end = _closing(rest, close)
        if end < 0 or (close == "}" and (braces is not None or brackets)):
            raise RescaleError(f"樣式 {pattern!r} 的 {part!r} 寫錯")
        body = rest[1:end]
        rest = rest[end + 1 :]
        if close == "}":
            braces = body
        else:
            brackets.append(body)
        if rest and rest[0] not in "[{":
            raise RescaleError(f"樣式 {pattern!r} 的 {part!r} 寫錯")
    return name, braces, brackets


def parse_pattern(pattern: str) -> tuple[_Tok, ...]:
    toks: list[_Tok] = []
    for part in _split_top(pattern, "."):
        name, braces, brackets = _segment(part, pattern)
        if name == "**":
            if brackets or braces is not None:
                raise RescaleError(f"樣式 {pattern!r}：** 後面不能接 [] 或 {{}}")
            toks.append(_Tok("deep"))
            continue
        key_filters = _parse_filters(braces or "", pattern)
        if name == "*":
            toks.append(_Tok("any_key", filters=key_filters))
        elif name:
            toks.append(_Tok("key", name=name, filters=key_filters))
        elif braces is not None:
            raise RescaleError(f"樣式 {pattern!r}：{{k=v}} 要接在鍵名後面")
        elif not brackets:
            raise RescaleError(f"樣式 {pattern!r} 有空的一段")
        toks.extend(_Tok("item", filters=_parse_filters(body, pattern)) for body in brackets)
    return tuple(toks)


def _step_ok(tok: _Tok, step: Step) -> bool:
    if tok.kind == "key":
        if step.key is None or not fnmatch.fnmatchcase(step.key, tok.name):
            return False
    elif tok.kind == "any_key":
        if step.key is None:
            return False
    elif step.key is not None:
        return False
    fields = dict(step.item)
    return all(
        (fields.get(key, _ABSENT) in values) != negate for key, values, negate in tok.filters
    )


def matches(toks: Sequence[_Tok], steps: Sequence[Step]) -> bool:
    if not toks:
        return not steps
    head = toks[0]
    if head.kind == "deep":
        return any(matches(toks[1:], steps[i:]) for i in range(len(steps) + 1))
    return bool(steps) and _step_ok(head, steps[0]) and matches(toks[1:], steps[1:])


# ---------------------------------------------------------------------------
# 欄位清單


@dataclass(slots=True)
class Rule:
    category: str
    pattern: str
    toks: tuple[_Tok, ...]
    hits: int = 0


@dataclass(slots=True)
class Group:
    files: tuple[str, ...]
    rules: list[Rule] = field(default_factory=list)
    file_hits: int = 0

    def owns(self, rel: str) -> bool:
        return any(_glob(rel, g) for g in self.files)


def _glob(rel: str, pattern: str) -> bool:
    """``*`` 不跨 ``/``，``**`` 跨。"""
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, rel) is not None


def load_fields(path: Path = FIELDS_PATH) -> list[Group]:
    raw = yaml.safe_load(_read(path))
    groups: list[Group] = []
    for entry in raw["groups"]:
        files = entry["files"]
        group = Group(tuple([files] if isinstance(files, str) else files))
        unknown = set(entry) - {"files", *CATEGORIES}
        if unknown:
            raise RescaleError(f"{group.files}：不認得的欄位 {sorted(unknown)}")
        for category in CATEGORIES:
            for pattern in entry.get(category) or ():
                group.rules.append(Rule(category, str(pattern), parse_pattern(str(pattern))))
        groups.append(group)
    return groups


@dataclass(slots=True)
class Classified:
    groups: Sequence[Group]
    by_category: dict[str, list[Leaf]]
    unclassified: list[Leaf] = field(default_factory=list)
    conflicts: list[tuple[Leaf, list[str]]] = field(default_factory=list)
    multi_group_files: list[tuple[str, list[str]]] = field(default_factory=list)


def _classify_leaf(group: Group, leaf: Leaf, out: Classified) -> None:
    hit = [r for r in group.rules if matches(r.toks, leaf.steps)]
    for rule in hit:
        rule.hits += 1
    cats = sorted({r.category for r in hit})
    if not cats:
        out.unclassified.append(leaf)
    elif len(cats) > 1:
        out.conflicts.append((leaf, [f"{r.category}:{r.pattern}" for r in hit]))
    else:
        out.by_category[cats[0]].append(leaf)


def classify(groups: Sequence[Group] | None = None, content_dir: Path = CONTENT_DIR) -> Classified:
    groups = load_fields() if groups is None else groups
    for group in groups:
        group.file_hits = 0
        for rule in group.rules:
            rule.hits = 0
    out = Classified(groups, {c: [] for c in CATEGORIES})
    for path in content_files(content_dir):
        rel = path.relative_to(content_dir).as_posix()
        owners = [g for g in groups if g.owns(rel)]
        for owner in owners:
            owner.file_hits += 1
        leaves = scan_file(path, content_dir)
        if len(owners) > 1:
            out.multi_group_files.append((rel, [",".join(g.files) for g in owners]))
        elif not owners:
            out.unclassified.extend(leaves)
        else:
            for leaf in leaves:
                _classify_leaf(owners[0], leaf, out)
    return out


def problems(result: Classified) -> list[str]:
    """清單的問題：多個 group 搶同一個檔、同一個欄位落在兩類、沒列到的欄位、過時的 group 或樣式。"""
    msgs = [f"{f}：同時符合多個 group {gs}" for f, gs in result.multi_group_files]
    msgs += [f"{leaf.file} {leaf.display()}：同時符合 {c}" for leaf, c in result.conflicts]
    msgs += [
        f"{leaf.file} {leaf.display()} = {leaf.value}：清單沒列" for leaf in result.unclassified
    ]
    for group in result.groups:
        if group.file_hits == 0:
            msgs.append(f"group {group.files}：沒有對到任何檔")
        msgs += [
            f"{group.files} {r.category}:{r.pattern}：沒有對到任何欄位"
            for r in group.rules
            if r.hits == 0
        ]
    return msgs


# ---------------------------------------------------------------------------
# CLI


def stats(result: Classified) -> str:
    files = {leaf.file for leaves in result.by_category.values() for leaf in leaves}
    lines = [f"有數字欄位的檔：{len(files)}；清單 group：{len(result.groups)}"]
    for category in CATEGORIES:
        leaves = result.by_category[category]
        rules = sum(1 for g in result.groups for r in g.rules if r.category == category)
        nodes = {(leaf.file, leaf.start) for leaf in leaves}  # 錨點共用的算一個
        touched = len({leaf.file for leaf in leaves})
        lines.append(f"{category}：{rules} 條樣式，{len(nodes)} 個數值，分布在 {touched} 個檔")
    return "\n".join(lines)


def _unclassified_summary(result: Classified) -> str:
    """把沒列的欄位依檔群與路徑（索引換成 ``[]``）彙整。"""
    seen: dict[tuple[str, str], list[str]] = {}
    for leaf in result.unclassified:
        parent = leaf.file.rsplit("/", 1)[0] + "/*" if "/" in leaf.file else leaf.file
        path = ""
        for step in leaf.steps:
            if step.key is not None:
                path += ("." if path else "") + step.key
            else:
                kind = dict(step.item).get("type")
                path += f"[type={kind}]" if kind is not None else "[]"
        seen.setdefault((parent, path), []).append(leaf.value)
    return "\n".join(
        f"{g}  {p}  n={len(v)}  {sorted(set(v), key=float)[:8]}"
        for (g, p), v in sorted(seen.items())
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="量類 ×10 換算（scripts/x10/fields.yaml）")
    parser.add_argument("--check", action="store_true", help="檢查清單，有問題時結束碼 1")
    parser.add_argument("--unclassified", action="store_true", help="列出清單沒涵蓋的數字欄位")
    parser.add_argument("--stats", action="store_true", help="清單統計")
    args = parser.parse_args(argv)

    try:
        result = classify()
        found = problems(result)
        if args.unclassified:
            print(_unclassified_summary(result))
        if args.check:
            print("\n".join(found) if found else "欄位清單沒有問題")
        if args.stats:
            print(stats(result))
        return 1 if args.check and found else 0
    except RescaleError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
