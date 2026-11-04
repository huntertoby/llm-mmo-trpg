"""情境覆蓋表（Phase 6Q-A）：每區 × 每族能吃種族加值的情境模板數、DC 分布、最好情況成功率。

只讀內容（``content/world/situations/*.yaml``、``situation_rules.yaml``、事件骨架、地點圖），
不跑戰鬥、不呼叫 LLM。計算方式見 ``trpg.world.situation_coverage.best_case``。

用法::

    uv run python scripts/situation_coverage.py           # 完整表格＋被標出的項目
    uv run python scripts/situation_coverage.py --quiet   # 只印摘要與被標出的項目（check.py 用）

被標出的項目只是警告：結束碼 0；加 ``--warn-exit`` 時有被標出的項目回傳 3（``scripts/check.py`` 把它
當「警告」，不影響總結束碼）。內容載入失敗時 1。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.library import load_library
from trpg.shared.errors import ContentError
from trpg.world.situation_coverage import build_coverage, format_report, inputs_from_library

WARN_EXIT = 3


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="情境覆蓋表（只出警告）")
    parser.add_argument("--quiet", action="store_true", help="只印摘要與被標出的項目")
    parser.add_argument(
        "--warn-exit", action="store_true", help=f"有被標出的項目時結束碼 {WARN_EXIT}"
    )
    parser.add_argument("--content", type=Path, default=None, help="內容資料夾（預設 content/）")
    args = parser.parse_args(argv)
    try:
        library = load_library(args.content)
    except ContentError as exc:
        print(f"情境覆蓋表：內容載入失敗：{exc}")
        return 1
    report = build_coverage(inputs_from_library(library))
    print(format_report(report, quiet=args.quiet))
    flagged = bool(report.few() or report.low_dc)
    return WARN_EXIT if args.warn_exit and flagged else 0


if __name__ == "__main__":
    sys.exit(main())
