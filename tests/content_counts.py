"""內容數量的快照（Phase WL-1）：測試裡「骨架有幾種、詞條有幾條」不再寫死，改讀
``tests/content_counts.json``。

加內容（骨架、詞條、技能、關鍵字……）之後重產快照、看 diff：

    uv run python -m tests.content_counts

``tests/test_content_counts.py`` 檢查快照沒過期（數字和正式內容算出來的一樣）。幾何、骰子、結算
結果的數字不是內容計數，不放這裡。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.skillgen.random_composer import default_library

SNAPSHOT = Path(__file__).with_name("content_counts.json")
"""快照檔（鍵照字母排序）。"""


def _skill_files(library: ContentLibrary) -> int:
    """``content/skills/`` 裡不是裝備附帶技能（``skill_gear_*``）的檔：數值工坊的技能對象。"""
    del library
    return sum(
        1
        for p in (bundled_content_dir() / "skills").glob("*.yaml")
        if not p.stem.startswith("skill_gear_")
    )


COUNTERS: dict[str, Callable[[ContentLibrary], int]] = {
    "affixes": lambda lib: len(lib.affixes),
    "keywords": lambda lib: len(lib.keywords.ids()),
    "map_archetypes": lambda lib: len(lib.map_archetypes.archetypes),
    "skeletons": lambda lib: len(lib.skeletons),
    "skill_files_without_gear": _skill_files,
    "skill_triggers": lambda lib: len(lib.ruleset.skill_triggers.triggers),
    "skills": lambda lib: len(lib.skills),
    "statuses": lambda lib: len(lib.ruleset.statuses.statuses),
}
"""快照的每一項怎麼數（正式內容）。"""


def compute(library: ContentLibrary) -> dict[str, int]:
    return {name: COUNTERS[name](library) for name in sorted(COUNTERS)}


def load() -> dict[str, int]:
    """快照內容（還沒有快照檔時是空的，``main`` 才能第一次產生）。"""
    if not SNAPSHOT.is_file():
        return {}
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in data.items()}


COUNTS: dict[str, int] = load()
"""快照內容；測試用 ``COUNTS["skeletons"]`` 代替寫死的數字。"""


def main() -> None:
    counts = compute(default_library())
    text = json.dumps(counts, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    SNAPSHOT.write_text(text, encoding="utf-8", newline="")
    print(f"已寫入 {SNAPSHOT}：" + "、".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
