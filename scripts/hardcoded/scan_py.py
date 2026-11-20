"""後端寫死數值掃描（HC-1；``docs/phases/PhaseHC-1計畫.md`` 第 1 項）。

用 AST 列出 ``src/trpg/`` 裡的：

- 數字字面值（``number``）：不列 0、1、-1（含 0.0、1.0），不列 ``range()`` 的參數和 True／False。
- 含數字的中文字串（``text``）：同時有中日韓文字和數字（0-9、全形０-９）。docstring 和獨立成一句的
  字串（欄位、常數下一行的說明）記成 ``docstring``。f-string 只看固定的部分，``{...}`` 的
  運算式照原樣保留在值裡。

每一筆附：檔、行、所在函式或類別（``scope``，例 ``Foo.bar``，模組層是 ``<module>``）、值、
「位置」（``slot``，見 ``_slot``）、所在敘述的指派目標（``owner``）和型別註記（``ann``）、那一行
原文（``context``）。歸類用 ``scripts/hardcoded/classes.yaml``，不靠行號。

用法::

    uv run python scripts/hardcoded/scan_py.py              # 印出全部（tsv）
    uv run python scripts/hardcoded/scan_py.py --count      # 只印筆數
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
SRC_DIR: Final = ROOT / "src" / "trpg"
CJK: Final = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")
_CJK_LETTER: Final = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
DIGIT: Final = re.compile(r"[0-9\uff10-\uff19]")
_SKIP_NUMBERS: Final = frozenset({0, 1, -1})
_CONTEXT_MAX: Final = 160
_SHORT_MAX: Final = 40
_PASS_THROUGH: Final = (
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.IfExp,
    ast.Tuple,
    ast.List,
    ast.Set,
    ast.Starred,
)


@dataclass(frozen=True)
class Hit:
    """一筆掃描結果。``value`` 是正規化後的字面值（數字用 repr，字串用原字串）。"""

    lang: str
    file: str
    line: int
    scope: str
    kind: str
    value: str
    slot: str
    context: str
    owner: str = ""
    ann: str = ""


def has_cjk_digit(text: str) -> bool:
    return bool(_CJK_LETTER.search(text)) and bool(DIGIT.search(text))


def _name_of(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _name_of(node.value)
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return ""


def _short(node: ast.AST) -> str:
    text = ast.unparse(node)
    return text if len(text) <= _SHORT_MAX else text[: _SHORT_MAX - 3] + "..."


class _Scanner(ast.NodeVisitor):
    def __init__(self, rel: str, source: str) -> None:
        self.rel = rel
        self.lines = source.splitlines()
        self.parents: dict[ast.AST, ast.AST] = {}
        self.scope: list[str] = []
        self.hits: list[Hit] = []
        self.docstrings: set[int] = set()
        self.fstring_parts: set[int] = set()

    # ---------------------------------------------------------------- 走訪
    def scan(self, tree: ast.Module) -> list[Hit]:
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self.parents[child] = parent
            if isinstance(parent, ast.Expr):
                doc = parent.value
                if isinstance(doc, ast.Constant) and isinstance(doc.value, str):
                    # 模組、類別、函式的 docstring，以及欄位、常數下一行的「屬性 docstring」。
                    self.docstrings.add(id(doc))
            if isinstance(parent, ast.JoinedStr):
                for part in parent.values:
                    self.fstring_parts.add(id(part))
        self.visit(tree)
        return self.hits

    def _scoped(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for deco in node.decorator_list:
            self.visit(deco)
        if not isinstance(node, ast.ClassDef):
            self.visit(node.args)
            if node.returns is not None:
                self.visit(node.returns)
        else:
            for base in node.bases:
                self.visit(base)
            for kw in node.keywords:
                self.visit(kw)
        self.scope.append(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scoped(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scoped(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scoped(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        value = node.value
        if isinstance(value, bool):
            return
        if isinstance(value, int | float):
            self._number(node, value)
        elif isinstance(value, str) and id(node) not in self.fstring_parts and has_cjk_digit(value):
            kind = "docstring" if id(node) in self.docstrings else "text"
            self._add(node, kind, value)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        fixed: list[str] = []
        whole: list[str] = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                fixed.append(part.value)
                whole.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                whole.append("{" + ast.unparse(part.value) + "}")
        if has_cjk_digit("".join(fixed)):
            self._add(node, "text", "".join(whole))
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        operand = node.operand
        if (
            isinstance(node.op, ast.USub)
            and isinstance(operand, ast.Constant)
            and isinstance(operand.value, int | float)
            and not isinstance(operand.value, bool)
        ):
            self._number(node, -operand.value)
            return
        self.generic_visit(node)

    # ---------------------------------------------------------------- 紀錄
    def _number(self, node: ast.expr, value: float) -> None:
        if value in _SKIP_NUMBERS:
            return
        if self._in_range_call(node):
            return
        self._add(node, "number", repr(value))

    def _in_range_call(self, node: ast.AST) -> bool:
        parent = self.parents.get(node)
        return (
            isinstance(parent, ast.Call)
            and node in parent.args
            and isinstance(parent.func, ast.Name)
            and parent.func.id == "range"
        )

    def _add(self, node: ast.expr, kind: str, value: str) -> None:
        line = node.lineno
        context = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        if len(context) > _CONTEXT_MAX:
            context = context[: _CONTEXT_MAX - 3] + "..."
        scope = ".".join(self.scope) or "<module>"
        owner, ann = self._owner(node)
        self.hits.append(
            Hit("py", self.rel, line, scope, kind, value, self._slot(node), context, owner, ann)
        )

    def _owner(self, node: ast.AST) -> tuple[str, str]:
        """所在敘述的指派目標（欄位、常數名）與型別註記；函式預設值是參數名。"""
        cur: ast.AST | None = node
        while cur is not None and not isinstance(cur, ast.stmt):
            parent = self.parents.get(cur)
            if isinstance(parent, ast.arguments):
                return _default_param(parent, cur), ""
            cur = parent
        if isinstance(cur, ast.AnnAssign):
            return _name_of(cur.target), _short(cur.annotation)
        if isinstance(cur, ast.Assign):
            return ",".join(_name_of(t) for t in cur.targets), ""
        if isinstance(cur, ast.AugAssign):
            return _name_of(cur.target), ""
        return "", ""

    def _slot(self, node: ast.AST) -> str:  # noqa: PLR0911, PLR0912 -- 單一節點種類分派
        """往上找第一個「有名字的位置」。

        ``Call(kw)`` 關鍵字參數、``Call(#i)`` 第 i 個位置參數、``=name`` 指派、``{key}`` dict 的值、
        ``def:param`` 函式預設值、``cmp:左邊`` 比較、``return``、``index`` 下標、空字串（其他）。
        """
        child = node
        parent = self.parents.get(child)
        while isinstance(parent, _PASS_THROUGH):
            child, parent = parent, self.parents.get(parent)
        if isinstance(parent, ast.keyword):
            call = self.parents.get(parent)
            name = _name_of(call.func) if isinstance(call, ast.Call) else ""
            return f"{name}({parent.arg or '**'})"
        if isinstance(parent, ast.Call):
            if child in parent.args:
                return f"{_name_of(parent.func)}(#{parent.args.index(child)})"
            return "call"
        if isinstance(parent, ast.Assign | ast.AugAssign | ast.AnnAssign):
            targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
            return "=" + ",".join(_name_of(t) for t in targets)
        if isinstance(parent, ast.Dict):
            for key, val in zip(parent.keys, parent.values, strict=True):
                if val is child:
                    if isinstance(key, ast.Constant):
                        return "{" + str(key.value) + "}"
                    return "{" + (_short(key) if key is not None else "**") + "}"
            return "{key}"
        if isinstance(parent, ast.arguments):
            return "def:" + _default_param(parent, child)
        if isinstance(parent, ast.Compare):
            other = parent.left if parent.left is not child else parent.comparators[0]
            return "cmp:" + _short(other)
        if isinstance(parent, ast.Return):
            return "return"
        if isinstance(parent, ast.Subscript):
            return "index"
        return ""


def _default_param(args: ast.arguments, default: ast.AST) -> str:
    positional = args.posonlyargs + args.args
    if default in args.defaults:
        offset = len(positional) - len(args.defaults)
        return positional[offset + args.defaults.index(default)].arg
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        if kw_default is default:
            return arg.arg
    return "?"


def iter_files() -> Iterator[Path]:
    yield from sorted(SRC_DIR.rglob("*.py"))


def scan_file(path: Path) -> list[Hit]:
    source = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    return _Scanner(rel, source).scan(ast.parse(source, filename=rel))


def scan() -> list[Hit]:
    hits: list[Hit] = []
    for path in iter_files():
        hits.extend(scan_file(path))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--count", action="store_true", help="只印筆數")
    args = parser.parse_args(argv)
    hits = scan()
    if args.count:
        print(len(hits))
        return 0
    for hit in hits:
        value = hit.value.replace("\n", "\\n").replace("\t", " ")
        print(
            f"{hit.file}:{hit.line}\t{hit.scope}\t{hit.kind}\t{hit.slot}\t{hit.owner}\t{hit.ann}\t"
            f"{value[:80]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
