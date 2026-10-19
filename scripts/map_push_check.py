"""地圖卡路檢查（Phase 3C-1）：可推動物件會不會擋住我方到敵方的通路。

用法::

    uv run python scripts/map_push_check.py [--maps oil_depot,dark_forest]

預設檢查所有正式地圖（不含 ``test_`` 開頭者），輸出 Markdown 摘要表。邏輯在
``trpg.sim.push_check``。
"""

from __future__ import annotations

import argparse

from trpg.content.library import load_library
from trpg.sim.push_check import check_map, render_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部正式地圖）")
    args = parser.parse_args()
    library = load_library()
    ids = (
        args.maps.split(",")
        if args.maps
        else sorted(m for m in library.maps if not m.startswith("test_"))
    )
    print(render_report([check_map(library, m) for m in ids]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
