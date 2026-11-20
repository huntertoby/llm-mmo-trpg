"""前端寫死數值掃描（HC-1；``docs/phases/PhaseHC-1計畫.md`` 第 2 項）。

列出 ``client/src/`` 的 .ts／.tsx（不含 ``*.test.*``、``*.spec.*``、``*.d.ts``、``fixtures/``、
``client/src/test/``）裡的：

- 數字字面值（``number``）：不列 0、1、-1。字串裡的數字（``"12px"``、``"#fff"``）不算字面值。
- 含數字的中文字串（``text``）：一般字串、樣板字串（``${...}`` 照原樣保留在值裡）、JSX 裡的文字。

沒有 Node 相依：用一個小型的 tokenizer 處理註解、字串、樣板字串、正規表示式和 JSX 文字。每一筆附
所在函式或常數（``scope``）、「位置」（``slot``：``{key}`` 物件鍵、``=name`` 指派、``attr=name`` JSX
屬性、``name()`` 呼叫參數、``[]`` 陣列、``cmp`` 比較、``op:*`` 運算、``return``、``?:`` 三元）、
所在宣告或物件鍵（``owner``）與那一行原文。歸類用 ``scripts/hardcoded/classes.yaml``，不靠行號。

用法::

    uv run python scripts/hardcoded/scan_ts.py              # 印出全部（tsv）
    uv run python scripts/hardcoded/scan_ts.py --count      # 只印筆數
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
CLIENT_SRC: Final = ROOT / "client" / "src"
_CJK_LETTER: Final = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_DIGIT: Final = re.compile(r"[0-9\uff10-\uff19]")
_NUMBER: Final = re.compile(
    r"0[xX][0-9a-fA-F_]+n?|0[bB][01_]+n?|0[oO][0-7_]+n?|"
    r"(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9][0-9_]*)(?:[eE][+-]?[0-9]+)?n?"
)
_IDENT: Final = re.compile(r"[A-Za-z_$][\w$]*")
_PUNCT3: Final = ("===", "!==", "**=", "...", ">>>", "<<=", ">>=", "&&=", "||=", "??=")
_PUNCT2: Final = (
    "=>", "==", "!=", "<=", ">=", "&&", "||", "??", "?.", "++", "--", "+=", "-=", "*=", "/=",
    "%=", "&=", "|=", "^=", "**", "<<", ">>",
)  # fmt: skip
_REGEX_AFTER_PUNCT: Final = frozenset("(,=:[!&|?{;+-*%<>~^") | {
    "=>", "==", "!=", "===", "!==", "<=", ">=", "&&", "||", "??", "+=", "-=", "*=", "/=", "%=",
}  # fmt: skip
_REGEX_AFTER_WORD: Final = frozenset(
    {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw",
     "yield", "await"}
)  # fmt: skip
_BLOCK_KEYWORDS: Final = frozenset(
    {"if", "for", "while", "switch", "catch", "with", "function", "return", "typeof"}
)
_DECL_KEYWORDS: Final = frozenset(
    {"const", "let", "var", "function", "class", "interface", "type", "enum"}
)
_CMP: Final = frozenset({"<", ">", "<=", ">=", "==", "===", "!=", "!=="})
_ARITH: Final = frozenset({"*", "/", "+", "-", "%", "**"})
_JSX_STOP: Final = frozenset("<>{}\n")
_SKIP_NUMBERS: Final = frozenset({0.0, 1.0, -1.0})
_CONTEXT_MAX: Final = 160


@dataclass(frozen=True)
class Hit:
    """一筆掃描結果（欄位與 ``scan_py.Hit`` 相同；``ann`` 前端不用）。"""

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


@dataclass
class _Tok:
    kind: str  # num, str, tmpl, ident, punct, jsx
    text: str
    pos: int
    value: str = ""
    fixed: str = ""


@dataclass
class _Frame:
    char: str
    name: str
    owner: str
    scoped: bool


@dataclass
class _State:
    stack: list[_Frame] = field(default_factory=list)
    pending: str = ""


def has_cjk_digit(text: str) -> bool:
    return bool(_CJK_LETTER.search(text)) and bool(_DIGIT.search(text))


def _numeric(text: str) -> float | None:
    raw = text.replace("_", "").rstrip("n").lower()
    try:
        if raw.startswith(("0x", "0b", "0o")):
            return float(int(raw, 0))
        return float(raw)
    except ValueError:
        return None


class _Lexer:
    def __init__(self, src: str) -> None:
        self.src = src
        self.toks: list[_Tok] = []

    # ------------------------------------------------------------------ 主迴圈
    def run(self, start: int = 0, stop_brace: bool = False) -> int:  # noqa: PLR0912 -- 字元分派
        src, n, i, depth = self.src, len(self.src), start, 0
        while i < n:
            ch = src[i]
            if ch in " \t\r\n":
                i += 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = n if j < 0 else j + 2
            elif ch in "'\"":
                i = self._string(i, ch)
            elif ch == "`":
                i = self._template(i)
            elif ch == "/" and self._regex_allowed():
                i = self._regex(i)
            elif ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
                m = _NUMBER.match(src, i)
                end = m.end() if m else i + 1
                self.toks.append(_Tok("num", src[i:end], i))
                i = end
            elif ch.isalpha() or ch in "_$":
                m = _IDENT.match(src, i)
                if m is None or _CJK_LETTER.match(ch):
                    i = self._jsx_text(i)
                else:
                    self.toks.append(_Tok("ident", m.group(), i))
                    i = m.end()
            elif _CJK_LETTER.match(ch):
                i = self._jsx_text(i)
            else:
                if stop_brace and ch == "}" and depth == 0:
                    return i + 1
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                text = next((p for p in _PUNCT3 if src.startswith(p, i)), "") or next(
                    (p for p in _PUNCT2 if src.startswith(p, i)), ch
                )
                self.toks.append(_Tok("punct", text, i))
                i += len(text)
        return i

    def _prev(self) -> _Tok | None:
        return self.toks[-1] if self.toks else None

    def _regex_allowed(self) -> bool:
        prev = self._prev()
        if prev is None:
            return True
        if prev.kind == "punct":
            # ``</div>`` 的 ``/`` 是 JSX 結束標籤，不是正規表示式。
            return prev.text in _REGEX_AFTER_PUNCT and prev.text != "<"
        return prev.kind == "ident" and prev.text in _REGEX_AFTER_WORD

    def _string(self, i: int, quote: str) -> int:
        src, j = self.src, i + 1
        out: list[str] = []
        while j < len(src) and src[j] != quote and src[j] != "\n":
            if src[j] == "\\" and j + 1 < len(src):
                out.append(src[j : j + 2])
                j += 2
            else:
                out.append(src[j])
                j += 1
        text = "".join(out)
        self.toks.append(_Tok("str", src[i : j + 1], i, value=text, fixed=text))
        return j + 1

    def _template(self, i: int) -> int:
        src, j = self.src, i + 1
        whole: list[str] = []
        fixed: list[str] = []
        while j < len(src) and src[j] != "`":
            if src[j] == "\\" and j + 1 < len(src):
                whole.append(src[j : j + 2])
                fixed.append(src[j : j + 2])
                j += 2
            elif src.startswith("${", j):
                end = self.run(j + 2, stop_brace=True)
                whole.append(src[j:end])
                j = end
            else:
                whole.append(src[j])
                fixed.append(src[j])
                j += 1
        tok = _Tok("tmpl", src[i : j + 1], i, value="".join(whole), fixed="".join(fixed))
        self.toks.append(tok)
        return j + 1

    def _regex(self, i: int) -> int:
        src, j, in_class = self.src, i + 1, False
        while j < len(src) and src[j] != "\n":
            ch = src[j]
            if ch == "\\":
                j += 2
                continue
            if ch == "[":
                in_class = True
            elif ch == "]":
                in_class = False
            elif ch == "/" and not in_class:
                break
            j += 1
        j += 1
        while j < len(src) and (src[j].isalpha()):
            j += 1
        self.toks.append(_Tok("str", src[i:j], i, value="", fixed=""))
        return j

    def _jsx_text(self, i: int) -> int:
        """JSX 文字：從這個中文字往前、往後擴到 ``< > { }`` 或換行，吞掉中間已經切出的 token。"""
        src = self.src
        start = i
        while start > 0 and src[start - 1] not in _JSX_STOP:
            start -= 1
        end = i
        while end < len(src) and src[end] not in _JSX_STOP:
            end += 1
        while self.toks and self.toks[-1].pos >= start:
            self.toks.pop()
        text = src[start:end].strip()
        self.toks.append(_Tok("jsx", text, start, value=text, fixed=text))
        return end


def _at(toks: list[_Tok], k: int) -> _Tok:
    """第 ``k`` 個 token；超出範圍時給空的 token（比對都不會成立）。"""
    return toks[k] if 0 <= k < len(toks) else _Tok("none", "", -1)


def _slot(toks: list[_Tok], k: int, frame: _Frame | None) -> str:  # noqa: PLR0911 -- 分派
    prev, prev2, prev3 = _at(toks, k - 1), _at(toks, k - 2), _at(toks, k - 3)
    if prev.text == ":" and prev2.kind in ("ident", "str") and prev3.text in ("{", ",", "?"):
        return "{" + prev2.text.strip("'\"") + "}"
    if prev.text == "=" and prev2.kind == "ident":
        return "=" + prev2.text
    if prev.text == "{" and prev2.text == "=" and prev3.kind == "ident":
        return "attr=" + prev3.text
    if prev.text in ("(", ",") and frame is not None and frame.char in "([":
        return (frame.name + "()") if frame.char == "(" else "[]"
    if prev.text == "[":
        return "[]"
    if prev.text in _CMP:
        return "cmp"
    if prev.text in _ARITH:
        return "op:" + prev.text
    if prev.text == "return":
        return "return"
    return "?:" if prev.text in ("?", ":") else ""


class _Walker:
    """走一遍 token：追蹤所在函式或常數（scope）、宣告名或物件鍵（owner），記下要列的項目。"""

    def __init__(self, rel: str, src: str, toks: list[_Tok]) -> None:
        self.rel = rel
        self.toks = toks
        self.lines = src.splitlines()
        self.line_starts = [0] + [idx + 1 for idx, ch in enumerate(src) if ch == "\n"]
        self.state = _State()
        self.hits: list[Hit] = []
        self.last_paren_name = ""

    def line_of(self, pos: int) -> int:
        return bisect.bisect_right(self.line_starts, pos)

    def scope(self) -> str:
        names: list[str] = []
        for fr in self.state.stack:
            if fr.scoped and fr.name and (not names or names[-1] != fr.name):
                names.append(fr.name)
        return ".".join(names) or "<module>"

    def owner(self) -> str:
        if self.state.pending:
            return self.state.pending
        return next((fr.owner for fr in reversed(self.state.stack) if fr.owner), "")

    def add(self, tok: _Tok, kind: str, value: str, k: int) -> None:
        """``k``：用來看前文（slot）的 token 位置。"""
        line = self.line_of(tok.pos)
        context = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        if len(context) > _CONTEXT_MAX:
            context = context[: _CONTEXT_MAX - 3] + "..."
        frame = self.state.stack[-1] if self.state.stack else None
        slot = _slot(self.toks, k, frame)
        own = slot[1:-1] if slot.startswith("{") else self.owner()
        self.hits.append(Hit("ts", self.rel, line, self.scope(), kind, value, slot, context, own))

    def walk(self) -> list[Hit]:
        for k, tok in enumerate(self.toks):
            if tok.kind == "num":
                self.number(tok, k)
            elif tok.kind in ("str", "tmpl", "jsx"):
                if has_cjk_digit(tok.fixed):
                    self.add(tok, "text", tok.value, k)
            elif tok.kind == "ident":
                prev = _at(self.toks, k - 1)
                if prev.kind == "ident" and prev.text in _DECL_KEYWORDS:
                    self.state.pending = tok.text
            elif tok.kind == "punct":
                self.punct(tok, k)
        return self.hits

    def number(self, tok: _Tok, k: int) -> None:
        number = _numeric(tok.text)
        if number is None:
            return
        before = _at(self.toks, k - 2)
        negative = _at(self.toks, k - 1).text == "-" and (
            before.kind == "none" or (before.kind == "punct" and before.text not in (")", "]"))
        )
        if negative:
            number = -number
        if number in _SKIP_NUMBERS:
            return
        shown = tok.text.replace("_", "").lower()
        self.add(tok, "number", ("-" if negative else "") + shown, k - 1 if negative else k)

    def punct(self, tok: _Tok, k: int) -> None:
        stack, prev = self.state.stack, _at(self.toks, k - 1)
        if tok.text == "{":
            key = _at(self.toks, k - 2).text.strip("'\"") if prev.text == ":" else ""
            if self.state.pending:
                stack.append(_Frame("{", self.state.pending, self.state.pending, True))
                self.state.pending = ""
            elif prev.text in (")", "=>") and self.last_paren_name:
                stack.append(_Frame("{", self.last_paren_name, "", True))
            else:
                stack.append(_Frame("{", "", key, False))
        elif tok.text in ("(", "["):
            name = prev.text if prev.kind == "ident" and prev.text not in _BLOCK_KEYWORDS else ""
            stack.append(_Frame(tok.text, name, "", False))
        elif tok.text in (")", "]", "}"):
            if stack:
                frame = stack.pop()
                if tok.text == ")":
                    self.last_paren_name = frame.name
        elif tok.text == ";":
            self.state.pending = ""


def iter_files() -> Iterator[Path]:
    for path in sorted(CLIENT_SRC.rglob("*")):
        rel = path.relative_to(CLIENT_SRC).as_posix()
        if path.suffix not in (".ts", ".tsx") or rel.endswith(".d.ts"):
            continue
        if ".test." in path.name or ".spec." in path.name:
            continue
        if rel.startswith("test/") or "/fixtures/" in f"/{rel}" or "/__tests__/" in f"/{rel}":
            continue
        yield path


def scan_source(rel: str, src: str) -> list[Hit]:
    """掃一段原始碼（``rel`` 是要記在結果裡的路徑）。"""
    lexer = _Lexer(src)
    lexer.run()
    return _Walker(rel, src, lexer.toks).walk()


def scan_file(path: Path) -> list[Hit]:
    return scan_source(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8"))


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
            f"{hit.file}:{hit.line}\t{hit.scope}\t{hit.kind}\t{hit.slot}\t{hit.owner}\t\t{value[:80]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
