"""LB-2：讀 ``scripts/llm_model_compare.py`` 的結果 JSON，統計技能提議各類錯誤（全部嘗試合計），
列出前 N 名並附原文例子（錯誤訊息全文、路徑、pydantic 位置、輸入值）。

用法::

    uv run python scripts/llm_failure_stats.py docs/phases/LB-2資料/gemma_base_t07.json [-n 10]

錯誤的「類別」＝代碼；``value_error`` 等 pydantic 自訂驗證器的代碼另依訊息前段再細分
（``value_error｜<訊息前 24 字>``），因為同一個代碼底下有很多條不同的驗證器。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SPLIT_CODES = frozenset({"value_error", "assertion_error", "reference"})
"""依訊息再細分的代碼（自訂驗證器共用的 pydantic 代碼、引用檢查）。"""
HEAD_CHARS = 24
_NORMALIZE = (
    (re.compile(r"「[^」]*」"), "「…」"),
    (re.compile(r"變奏 [a-z0-9_]+ "), "變奏 X "),
    (re.compile(r"^[A-Za-z_][\w.\[\]]*："), ""),
    (re.compile(r"\d+"), "#"),
)


def error_class(error: dict[str, Any]) -> str:
    """一條錯誤的類別鍵。"""
    code = str(error.get("code", ""))
    if code in SPLIT_CODES:
        head = str(error.get("message", ""))
        for pattern, repl in _NORMALIZE:
            head = pattern.sub(repl, head)
        head = head[:HEAD_CHARS]
        return f"{code}｜{head}"
    return code


def collect(paths: list[Path]) -> tuple[Counter[str], dict[str, dict[str, Any]], int]:
    """所有嘗試的錯誤 → （類別次數、每類第一個例子、嘗試數）。"""
    counts: Counter[str] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    attempts = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows", []):
            for number, detail in enumerate(row.get("attempt_details", []), start=1):
                attempts += 1
                if detail.get("call_error"):
                    key = "llm.call_error"
                    counts[key] += 1
                    examples.setdefault(key, {"message": detail["call_error"]})
                    continue
                for error in detail.get("errors", []):
                    key = error_class(error)
                    counts[key] += 1
                    if key not in examples:
                        examples[key] = {
                            **error,
                            "question": row.get("index"),
                            "attempt": number,
                            "file": path.name,
                        }
    return counts, examples, attempts


def render(
    counts: Counter[str], examples: dict[str, dict[str, Any]], attempts: int, top: int
) -> str:
    total = sum(counts.values())
    lines = [f"嘗試 {attempts} 次，錯誤 {total} 條，類別 {len(counts)} 種", ""]
    lines.append("| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |")
    lines.append("|---|---|---|---|")
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for rank, (key, count) in enumerate(ranked[:top], start=1):
        ex = examples[key]
        parts = [
            f"Q{ex.get('question', '?')}／{ex.get('attempt', '?')}",
            str(ex.get("path", "")),
            str(ex.get("message", "")).replace("|", "／").replace("\n", " "),
        ]
        if ex.get("loc"):
            parts.append(str(ex["loc"]))
        if ex.get("input"):
            parts.append(str(ex["input"]).replace("|", "／")[:80])
        lines.append(f"| {rank} | `{key}` | {count} | {'｜'.join(parts)} |")
    if len(ranked) > top:
        rest = "、".join(f"`{k}` {v}" for k, v in ranked[top:])
        lines.extend(["", f"其餘：{rest}"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("-n", "--top", type=int, default=10)
    args = parser.parse_args(argv)
    counts, examples, attempts = collect(args.paths)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(render(counts, examples, attempts, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
