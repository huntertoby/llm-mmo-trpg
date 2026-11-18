"""「誰在等誰」掃描：找出交接文件裡「等…」「待…」的句子，依「在等誰」分組。

用法::

    uv run python scripts/wait_scan.py                     # 掃 docs/*PM交接.md，輸出 markdown
    uv run python scripts/wait_scan.py --json              # 輸出 JSON
    uv run python scripts/wait_scan.py docs/開發PM交接.md   # 指定檔案或 glob（可多個）
    uv run python scripts/wait_scan.py --show-closed       # 連「看起來已結案」的也列出

判斷全靠下面幾張關鍵字表（只用標準庫，沒有語意理解）：

- ``WAIT_PATTERNS``：哪些字算「在等」。
- ``NOISE_PHRASES``：命中位置落在這些詞裡就丟掉（「待辦」「待查」等清單標題字）。
- ``CLOSED_MARKERS``：同一句（或同一列開頭）有這些字就標成「已結案？」，預設不列入分組。
- ``OWNER_PATTERNS``：命中處往後一小段裡先出現誰，就算在等誰；都沒有就是「未知」。
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = "docs/*PM交接.md"

# ---------------------------------------------------------------------------
# 規則表（要調整誤判就改這裡）
# ---------------------------------------------------------------------------

# (規則名, 正規表示式)。命中任何一條就算「在等」。
WAIT_PATTERNS: list[tuple[str, str]] = [
    ("在等", r"(?:還在|仍在|正在|在|仍|還)等"),
    ("等待", r"等待"),
    ("等某人", r"等(?:使用者|專案|玩法|開發|美術|設計|總 ?PM|PM|對方|裁判|你們?|他們?)"),
    ("等某事", r"等(?:試玩|答覆|回覆|回話|交件|結論|結果|決定|確認|定案|裁定|通知)"),
    ("等某段", r"等 ?(?:#\d+|[A-Z]{1,4}-?\d)"),
    ("待某人", r"待 ?(?:使用者|專案|玩法|開發|美術|設計|PM)"),
    # 「待決 3」這種帶編號的是條目代號，多半出現在「待決 3：照現況」這類答覆裡，不單獨算；
    # 「待決 2～6 轉玩法」這種後面接「轉某人」的才算。
    ("待決轉某人", r"待決[^，。；]{0,8}?轉 ?(?:給 ?)?(?:使用者|專案|玩法|開發|美術)"),
    ("待某事", r"待(?:決(?!\s*\d)|定|確認|回|答覆|回覆|轉|送|驗|過目|裁定)"),
]

# 命中位置落在這些詞裡就不算（清單標題字、流程用語）。
NOISE_PHRASES: list[str] = [
    "待辦",
    "待查",
    "待排",
    "待量",
    "待 PM 決定",
    "待PM決定",
    "待決定事項",
    "等通知",  # 流程守則「等通知，不要輪詢」
    "等待動畫",  # 美術名詞
    "練等",  # 「打不過就練等」
    "誰在等誰",  # 本腳本自己的名字
]

# 命中處前面 NEGATION_WINDOW 個字（去掉 ** 與空白後）以這些字結尾，就當成「沒有在等」而標成已結案。
NEGATION_SUFFIXES: list[str] = ["沒有", "沒", "無", "不用", "不必"]
NEGATION_WINDOW = 6

# 「等」緊接在這些字後面時多半是「……等（等等）」，不算在等。例：「傷害（第 1 段）」等玩法 PM 定字。
ETC_PREV_CHARS = "」"

# markdown 輸出時小節標題最多幾個字。
SECTION_WIDTH = 30

# 同一句或同一列開頭（前 LINE_HEAD_CHARS 個字）有這些字，就標成「已結案？」。
CLOSED_MARKERS: list[str] = [
    "已 push",
    "已push",
    "已做",
    "已完成",
    "已合併",
    "已上 main",
    "結案",
    "已結",
    "已刪",
    "已答覆",
    "已回覆",
    "已定案",
    "已處理",
    "已裁定",
    "✅",
    "~~",
]
# 只看列開頭的標記：「(e3y) 已完成（GB-4d）。原：……」這種整列都是舊紀錄。
# 列開頭的「結案」不算整列，因為交接常把「X 結案；Y 等開發」寫在同一列。
LINE_HEAD_MARKERS: list[str] = ["已完成", "~~", "✅"]
LINE_HEAD_CHARS = 24

# (誰, 正規表示式)，依序比對；命中處往後 OWNER_WINDOW 個字內最先出現的那個勝出。
OWNER_PATTERNS: list[tuple[str, str]] = [
    ("使用者", r"使用者"),
    ("專案 PM", r"專案 ?PM|總 ?PM|專案(?!計畫)"),
    ("玩法 PM", r"玩法|設計 ?PM"),
    # 「等 PB-1e」這種直接等某一段的，段由開發 PM 派，算開發 PM。
    ("開發 PM", r"開發 ?PM|開發(?!頁|中|環境|伺服器|流程)|^等 ?[A-Z]{1,4}-?\d"),
    ("美術 PM", r"美術"),
]
OWNER_WINDOW = 25
UNKNOWN = "未知"
OWNER_ORDER = [name for name, _ in OWNER_PATTERNS] + [UNKNOWN]

# 斷句：句號、問號、驚嘆號、分號、箭頭、表格直線。
SENTENCE_SPLIT = re.compile(r"[。！？；|→]")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")

_WAIT_RES = [(name, re.compile(rx)) for name, rx in WAIT_PATTERNS]
_OWNER_RES = [(name, re.compile(rx)) for name, rx in OWNER_PATTERNS]


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    section: str
    snippet: str
    owner: str
    rule: str
    closed: bool


# ---------------------------------------------------------------------------
# 判斷
# ---------------------------------------------------------------------------


def _in_noise(text: str, start: int, end: int) -> bool:
    for phrase in NOISE_PHRASES:
        for m in re.finditer(re.escape(phrase), text):
            if m.start() <= start and end <= m.end():
                return True
            if m.start() <= start < m.end():
                return True
    return False


def _has_closed_marker(text: str) -> bool:
    return any(marker in text for marker in CLOSED_MARKERS)


def _looks_like_etc(sentence: str, start: int) -> bool:
    return sentence[start] == "等" and start > 0 and sentence[start - 1] in ETC_PREV_CHARS


def _negated(before: str) -> bool:
    tail = before.replace("*", "").replace(" ", "")[-NEGATION_WINDOW:]
    return any(tail.endswith(word) for word in NEGATION_SUFFIXES)


def guess_owner(text: str) -> str:
    """命中處之後一小段文字裡最先出現的角色；沒有就回「未知」。"""
    best: tuple[int, str] | None = None
    for name, rx in _OWNER_RES:
        m = rx.search(text[:OWNER_WINDOW])
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), name)
    return best[1] if best else UNKNOWN


def _snippet(sentence: str, pos: int, width: int) -> str:
    s = sentence.strip()
    offset = len(sentence) - len(sentence.lstrip())
    pos = max(0, pos - offset)
    if len(s) <= width:
        return s
    start = max(0, min(pos - width // 3, len(s) - width))
    cut = s[start : start + width]
    return ("…" if start > 0 else "") + cut + ("…" if start + width < len(s) else "")


def _sentences(line: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    start = 0
    for m in SENTENCE_SPLIT.finditer(line):
        out.append((start, line[start : m.start()]))
        start = m.end()
    out.append((start, line[start:]))
    return out


def scan_line(line: str) -> list[tuple[str, str, bool, int, str]]:
    """回傳 (規則, 誰, 是否已結案, 句內位置, 句子)；同一句只算一筆。"""
    head = line.lstrip(" -*|>")[:LINE_HEAD_CHARS]
    head_closed = any(marker in head for marker in LINE_HEAD_MARKERS)
    results: list[tuple[str, str, bool, int, str]] = []
    for _, sentence in _sentences(line):
        for rule, rx in _WAIT_RES:
            found = None
            for m in rx.finditer(sentence):
                if _in_noise(sentence, m.start(), m.end()) or _looks_like_etc(sentence, m.start()):
                    continue
                found = m
                break
            if found is None:
                continue
            owner = guess_owner(sentence[found.start() :])
            closed = (
                head_closed or _has_closed_marker(sentence) or _negated(sentence[: found.start()])
            )
            results.append((rule, owner, closed, found.start(), sentence))
            break
    return results


def scan_text(text: str, file: str, width: int = 60) -> list[Hit]:
    hits: list[Hit] = []
    section = ""
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = HEADING.match(raw)
        if heading:
            section = heading.group(2)
            continue  # 標題本身不算（「待辦」「待 PM 決定」這類標題字）
        for rule, owner, closed, pos, sentence in scan_line(raw):
            hits.append(
                Hit(
                    file=file,
                    line=lineno,
                    section=section,
                    snippet=_snippet(sentence, pos, width),
                    owner=owner,
                    rule=rule,
                    closed=closed,
                )
            )
    return hits


# ---------------------------------------------------------------------------
# 輸入輸出
# ---------------------------------------------------------------------------


def resolve_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches and not Path(pattern).is_absolute():
            matches = sorted(glob.glob(str(ROOT / pattern)))
        for m in matches:
            p = Path(m)
            if p.is_file() and p not in paths:
                paths.append(p)
    return paths


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scan_paths(paths: list[Path], width: int = 60) -> list[Hit]:
    hits: list[Hit] = []
    for p in paths:
        hits.extend(scan_text(p.read_text(encoding="utf-8"), _display(p), width))
    return hits


def group_by_owner(hits: list[Hit]) -> dict[str, list[Hit]]:
    groups: dict[str, list[Hit]] = {name: [] for name in OWNER_ORDER}
    for h in hits:
        groups[h.owner].append(h)
    return {k: v for k, v in groups.items() if v}


def _md_line(h: Hit) -> str:
    title = h.section if len(h.section) <= SECTION_WIDTH else h.section[:SECTION_WIDTH] + "…"
    section = f" §{title}" if title else ""
    return f"- `{h.file}:{h.line}`{section} — {h.snippet}"


def render_markdown(hits: list[Hit], show_closed: bool = False) -> str:
    open_hits = [h for h in hits if not h.closed]
    closed_hits = [h for h in hits if h.closed]
    lines = [
        f"# 誰在等誰（未結 {len(open_hits)} 筆；看起來已結案 {len(closed_hits)} 筆"
        + ("，列在最後）" if show_closed else "，未列出，加 --show-closed 顯示）"),
        "",
    ]
    groups = group_by_owner(open_hits)
    if groups:
        lines.append("| 在等誰 | 筆數 |")
        lines.append("|---|---|")
        lines.extend(f"| {owner} | {len(items)} |" for owner, items in groups.items())
        lines.append("")
    for owner, items in groups.items():
        lines.append(f"## 等{owner}（{len(items)}）")
        lines.append("")
        lines.extend(_md_line(h) for h in items)
        lines.append("")
    if show_closed and closed_hits:
        lines.append(f"## 看起來已結案（{len(closed_hits)}）")
        lines.append("")
        lines.extend(f"{_md_line(h)}（{h.owner}）" for h in closed_hits)
        lines.append("")
    return "\n".join(lines)


def render_json(hits: list[Hit], show_closed: bool = False) -> str:
    chosen = hits if show_closed else [h for h in hits if not h.closed]
    payload = {
        "total": len(hits),
        "open": sum(1 for h in hits if not h.closed),
        "closed": sum(1 for h in hits if h.closed),
        "groups": {k: len(v) for k, v in group_by_owner([h for h in hits if not h.closed]).items()},
        "hits": [asdict(h) for h in chosen],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="掃交接文件裡的「等…」「待…」，依在等誰分組")
    parser.add_argument("paths", nargs="*", help=f"檔案或 glob（預設 {DEFAULT_GLOB}）")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--show-closed", action="store_true", help="連看起來已結案的也列出")
    parser.add_argument("--width", type=int, default=60, help="句子片段最多幾個字（預設 60）")
    args = parser.parse_args(argv)

    paths = resolve_paths(args.paths or [DEFAULT_GLOB])
    if not paths:
        print("找不到檔案：" + "、".join(args.paths or [DEFAULT_GLOB]), file=sys.stderr)
        return 2
    hits = scan_paths(paths, args.width)
    out = (
        render_json(hits, args.show_closed)
        if args.json
        else render_markdown(hits, args.show_closed)
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
