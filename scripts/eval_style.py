"""文字風格分區的驗收（Phase 6L-1 C9）：讀評估輸出，判斷三項驗收是否通過。

用法::

    uv run python scripts/eval_style.py --names <skills.csv> [--dialogues <dialogues.json>]

- ``--names``：``eval_llm_skills.py --suites region`` 的 CSV（欄位 ``region``、``skill_name``、
  ``name_source``；也接受 ``source`` 為 ``llm`` 才算的列）。
- ``--dialogues``：NPC 對白 ``[{"region": ..., "npc": ..., "text": ...}]``（說書人聊天的輸出）。

標準在 ``content/llm/style_eval.yaml``，古風詞在 ``content/llm/world_shattered.yaml`` 的
``naming.archaic``。三項都通過時結束碼 0，否則 1。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from trpg.content.world import load_style_eval, load_world_style
from trpg.llm.style_eval import DialogueRow, NameRow, report_lines, style_report


def read_names(path: Path) -> list[NameRow]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        NameRow(
            r.get("region") or None,
            r["skill_name"],
            r.get("name_source") or "",
            r.get("concept") or "",
            r.get("cast_flavor") or "",
        )
        for r in rows
        if r.get("skill_name")
    ]


def read_dialogues(path: Path) -> list[DialogueRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [DialogueRow(d["region"], d["npc"], d["text"]) for d in data]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--dialogues", type=Path, default=None)
    args = parser.parse_args(argv)
    names = read_names(args.names)
    dialogues = read_dialogues(args.dialogues) if args.dialogues is not None else []
    report = style_report(names, dialogues, load_style_eval(), load_world_style().naming.archaic)
    print("\n".join(report_lines(report)))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
