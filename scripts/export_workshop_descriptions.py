"""匯出工坊裡「含英文代號或開發者語氣」的說明（Phase 3-48c；交給玩法 PM 改寫）。

用法::

    uv run python scripts/export_workshop_descriptions.py [輸出檔]

預設寫到共用筆記資料夾的 ``workshop_descriptions.csv``（UTF-8 with BOM，兩欄 ``id,原文``）。
來源有兩類：

- 內容資料（原語、形狀、條件、觸發、骨架、狀態、層數）的 ``description_zh``，連同各參數的說明：
  ``原語.zone.anchor``、``形狀.line`` 這種 id；
- 程式組出的欄位說明（``工坊.<步驟>.<欄位>=<選項>``），用每個骨架各一個隨機技能的各種截斷草稿展開。

玩家模式不顯示這些原文（顯示程式產生的版本，或空白）；``?dev=1`` 仍顯示原文。可重複執行。
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.skillgen.option_models import FieldSpec
from trpg.skillgen.option_player import content_dev_texts, option_dev_texts
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill

DEFAULT_OUTPUT = Path(
    r"C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes"
    r"\local_46ffc72c-28dd-48aa-9eb7-f1724ef32432\workshop_descriptions.csv"
)
TRUNCATE: tuple[tuple[str, ...], ...] = (
    (),
    ("effects", "cost", "rarity", "condition", "followup"),
    ("shape", "effects", "cost", "rarity", "condition", "followup"),
    ("cost", "rarity"),
)


def _drafts(library: ContentLibrary) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = [{}]
    for seed, skeleton in enumerate(sorted(library.skeletons), start=1):
        try:
            skill = compose_random_skill(seed, skeleton=skeleton, library=library)
        except Exception:
            continue
        full = skill.model_dump(mode="json", exclude_none=True)
        for drop in TRUNCATE:
            drafts.append({k: v for k, v in full.items() if k not in drop})
    return drafts


def collect(library: ContentLibrary) -> list[tuple[str, str]]:
    """``(id, 原文)``，依 id 排序、不重複。"""
    rows: dict[str, str] = dict(content_dev_texts(library))
    steps: dict[str, tuple[FieldSpec, ...]] = {}
    for draft in _drafts(library):
        for step in draft_options(draft, library).steps:
            steps.setdefault(step.id, step.fields)
            for key, text in option_dev_texts({step.id: step.fields}):
                rows.setdefault(key, text)
    return sorted(rows.items())


def main(argv: list[str]) -> int:
    output = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUTPUT
    rows = collect(load_library())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "原文"])
        writer.writerows(rows)
    print(f"已寫入 {output}（{len(rows)} 筆）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
