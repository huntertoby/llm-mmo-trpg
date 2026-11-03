"""季末重置（管理者；Phase 5F-5，``docs/phases/Phase5計畫.md`` 第 40 節）。

    uv run python scripts/season_reset.py --start-date 2026-12-01            # dry-run：只列出清／留
    uv run python scripts/season_reset.py --start-date 2026-12-01 --execute  # 真的執行

**先停遊戲伺服器**（伺服器有記憶體快取；伺服器開著時請用管理者介面或
``POST /api/world/season/reset``）。執行前會把整個存檔資料夾備份到 ``--backup-root``（預設存檔資料夾
旁邊的 ``saves-backups/``）。存檔資料夾預設 ``TRPG_SAVE_DIR`` 或專案的 ``saves/``；帳號資料夾預設照
``config/server.toml`` 的 ``[accounts] dir``。路徑一律 ``pathlib``，Windows 與 macOS 同一條指令。
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from trpg.content.library import load_library
from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import load_account_settings
from trpg.server.accounts import AccountStore
from trpg.server.season_reset import SeasonResetError, SeasonResetReport, season_reset
from trpg.world.calendar import season_start_at

EXIT_ERROR = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="季末重置（管理者；沒加 --execute 只做 dry-run）")
    parser.add_argument(
        "--start-date", required=True, type=dt.date.fromisoformat, help="新一季的開賽日 YYYY-MM-DD"
    )
    parser.add_argument("--season-id", default=None, help="新一季的 ID（省略＝s<N+1>）")
    parser.add_argument("--seed", type=int, default=None, help="新一季的種子（省略＝由舊種子推）")
    parser.add_argument("--force", action="store_true", help="賽季還沒結束、循環賽沒跑完也重置")
    parser.add_argument("--execute", action="store_true", help="真的執行（沒加＝dry-run）")
    parser.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾")
    parser.add_argument("--accounts-dir", type=Path, default=None, help="帳號資料夾")
    parser.add_argument("--backup-root", type=Path, default=None, help="備份放在哪裡")
    return parser


def print_report(report: SeasonResetReport, out: TextIO) -> None:
    head = "dry-run（沒有寫任何檔）" if report.dry_run else "已重置"
    print(
        f"{head}：{report.old_season} → {report.new_season}（{report.new_season_name_zh}）",
        file=out,
    )
    for warning in report.warnings:
        print(f"  ! 已略過：{warning}", file=out)
    print("會清掉：" if report.dry_run else "清掉了：", file=out)
    for line in report.cleared:
        detail = f"（{line.detail_zh}）" if line.detail_zh else ""
        print(f"  - {line.label_zh} {line.count}{detail}", file=out)
    print("保留：", file=out)
    for line in report.kept:
        detail = f"（{line.detail_zh}）" if line.detail_zh else ""
        print(f"  - {line.label_zh} {line.count}{detail}", file=out)
    print("編年史：", file=out)
    for text in report.chronicle or ("（這一季沒有角色）",):
        print(f"  {text}", file=out)
    if report.backup is not None:
        print(f"備份：{report.backup}", file=out)


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr
) -> int:
    args = _parser().parse_args(argv)
    save_dir = args.save_dir if args.save_dir is not None else default_save_dir()
    accounts_dir = (
        args.accounts_dir
        if args.accounts_dir is not None
        else load_account_settings().accounts_dir(save_dir)
    )
    library = load_library()
    try:
        report = season_reset(
            library,
            save_dir,
            start=season_start_at(library, args.start_date),
            now=int(time.time()),
            accounts=AccountStore(accounts_dir),
            season_id=args.season_id,
            seed=args.seed,
            force=args.force,
            dry_run=not args.execute,
            backup_root=args.backup_root,
        )
    except SeasonResetError as exc:
        print(f"不能重置：{exc}", file=err)
        return EXIT_ERROR
    print_report(report, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
