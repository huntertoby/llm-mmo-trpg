"""組合器配方盤點的改前改後對照（RC-1）：讀兩份 ``recipe_census.py`` 的 JSON，輸出 Markdown。

- 總表：空格、薄格、正常的數量（全部與「會出題」的），改前 → 改後。
- 逐格：改前是空或薄、或狀態有變的格子，合法數與設計數的前後（依玩家遇到的頻率排序）。

用法::

    uv run python scripts/recipe_census_diff.py docs/phases/RC-0資料/census.json \\
        docs/phases/RC-1資料/census.json --out docs/phases/RC-1資料/對照.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_STATUS_ZH = {"ok": "正常", "thin": "薄", "empty": "空", "by_design": "設計上不存在"}
_ORDER = ("empty", "thin", "ok")


def _key(cell: dict[str, Any]) -> tuple[str, str, int, str]:
    return (cell["keyword"], cell["kind"], int(cell["tier"]), cell["rarity"])


def _cells(path: Path) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {_key(c): c for c in data["cells"]}


def _counts(cells: dict[Any, dict[str, Any]], *, reachable_only: bool) -> Counter[str]:
    return Counter(
        c["status"] for c in cells.values() if not reachable_only or c.get("reachable", True)
    )


def _summary(before: dict[Any, Any], after: dict[Any, Any]) -> list[str]:
    lines = ["| 範圍 | 狀態 | 改前 | 改後 |", "|---|---|---|---|"]
    for label, reach in (("全部格子", False), ("會出題的格子", True)):
        old, new = _counts(before, reachable_only=reach), _counts(after, reachable_only=reach)
        lines += [f"| {label} | {_STATUS_ZH[s]} | {old[s]} | {new[s]} |" for s in _ORDER]
    return lines


def _row(key: tuple[str, str, int, str], old: dict[str, Any], new: dict[str, Any]) -> str:
    keyword, kind, tier, rarity = key
    reach = "是" if new.get("reachable", True) else "否"
    return (
        f"| {keyword} | {kind} | {tier} | {rarity} | {reach} | "
        f"{_STATUS_ZH[old['status']]} → {_STATUS_ZH[new['status']]} | "
        f"{old['legal']} → {new['legal']} | {old['designs']} → {new['designs']} |"
    )


def _changed(before: dict[Any, Any], after: dict[Any, Any]) -> list[str]:
    keys = [
        k
        for k in before
        if k in after
        and (before[k]["status"] in ("empty", "thin") or before[k]["status"] != after[k]["status"])
        and before[k]["status"] != "by_design"
    ]
    keys.sort(key=lambda k: (-int(after[k].get("frequency", 0)), k))
    lines = [
        "| 關鍵字 | 種類 | 階 | 稀有度 | 會出題 | 狀態 | 合法 | 設計 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    return lines + [_row(k, before[k], after[k]) for k in keys]


def render(before_path: Path, after_path: Path) -> str:
    before, after = _cells(before_path), _cells(after_path)
    out = [
        "# 組合器配方盤點：改前改後對照（RC-1）",
        "",
        f"改前 `{before_path.as_posix()}`，改後 `{after_path.as_posix()}`。"
        "格子定義、合法與設計的算法同 RC-0（`scripts/recipe_census.py`）。",
        "",
        "## 總表",
        "",
        *_summary(before, after),
        "",
        "## 改前是空或薄、或狀態有變的格子（依玩家遇到的頻率）",
        "",
        *_changed(before, after),
        "",
    ]
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    text = render(args.before, args.after)
    if args.out is None:
        print(text)
    else:
        args.out.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
