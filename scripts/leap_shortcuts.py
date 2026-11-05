"""獸躍捷徑檢查（Phase 6R-1 驗收 C，#138）：每張戰鬥地圖與實地地圖輸出摘要表。

計算方式見 :mod:`trpg.sim.leap_check`。不跑戰鬥、不呼叫 LLM。用法::

    uv run python scripts/leap_shortcuts.py                 # 全部地圖
    uv run python scripts/leap_shortcuts.py --out scratchpad/leap.md
    uv run python scripts/leap_shortcuts.py --maps north_slope,cloud_summit

有被標出的路徑或格子時結束碼 1。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.library import load_library
from trpg.sim.leap_check import LeapReport, battle_map_report, field_map_report, format_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="", help="只查這些地圖 ID（逗號分隔）")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    library = load_library()
    wanted = {m for m in args.maps.split(",") if m}
    reports: list[LeapReport] = []
    for map_id in sorted(library.maps):
        if not wanted or map_id in wanted:
            reports.append(battle_map_report(library, library.maps[map_id]))
    for map_id in sorted(library.field_maps):
        field_map = library.field_maps[map_id]
        if field_map.region == "capital" or (wanted and map_id not in wanted):
            continue
        reports.append(field_map_report(library, field_map))
    text = format_reports(reports)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
