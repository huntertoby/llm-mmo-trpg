"""模擬報表共用的 Markdown 表格（CODE-3，整理提案 I3）。"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["markdown_table"]


def markdown_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """表頭、分隔列、資料列，各一行（不含結尾換行）。"""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines
