"""從舊季的唯讀封存重播查證首殺或循環賽場次（Phase 5F-5c；09 9.7 季末重置細節）。

    uv run python scripts/season_verify.py --season-id s1 --first-kill rift_shard_lord
    uv run python scripts/season_verify.py --season-id s1 --match <場次 ID>

舊季讀 ``<存檔資料夾>/archive/<季>/``（季末重置搬進去的世界日誌、循環賽、Boss 首殺的戰鬥紀錄），
目前這一季讀世界資料夾。只讀不寫，伺服器開著也可以跑。存檔資料夾預設 ``TRPG_SAVE_DIR`` 或專案的
``saves/``；路徑一律 ``pathlib``，Windows 與 macOS 同一條指令。

結束碼：0＝一致、1＝不一致、2＝找不到或參數錯。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from trpg.roguelite.save import default_save_dir
from trpg.server.season_archive import (
    ArchiveRecordNotFoundError,
    ReplayCheck,
    verify_first_kill,
    verify_league_match,
)
from trpg.world.layout import world_dir_of

EXIT_MISMATCH = 1
EXIT_ERROR = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="從唯讀封存重播查證首殺或循環賽場次（只讀）")
    parser.add_argument("--season-id", required=True, help="哪一季（例 s1）")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--first-kill", metavar="TARGET", help="首殺的目標（精英種類或 Boss ID）")
    which.add_argument("--match", metavar="MATCH_ID", help="循環賽的場次 ID")
    parser.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾")
    return parser


def print_check(check: ReplayCheck, out: TextIO) -> None:
    where = "封存" if check.source == "archive" else "世界資料夾（目前這一季）"
    head = "一致" if check.ok else "不一致"
    print(f"{head}：{check.season_id} {check.subject_zh}（讀{where}）", file=out)
    for line in check.passed:
        print(f"  通過：{line}", file=out)
    for line in check.problems:
        print(f"  不符：{line}", file=out)


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr
) -> int:
    args = _parser().parse_args(argv)
    save_dir = args.save_dir if args.save_dir is not None else default_save_dir()
    world_dir = world_dir_of(save_dir)
    try:
        if args.first_kill is not None:
            check = verify_first_kill(save_dir, world_dir, args.season_id, args.first_kill)
        else:
            check = verify_league_match(save_dir, world_dir, args.season_id, args.match)
    except ArchiveRecordNotFoundError as exc:
        print(f"找不到：{exc}", file=err)
        return EXIT_ERROR
    print_check(check, out)
    return 0 if check.ok else EXIT_MISMATCH


if __name__ == "__main__":
    sys.exit(main())
