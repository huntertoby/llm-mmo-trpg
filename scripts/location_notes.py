"""地點留言的管理腳本（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.7；#105「使用者手動刪」）。

    uv run python scripts/location_notes.py list [--location <地點 ID>]
    uv run python scripts/location_notes.py delete <note_id>

世界資料夾預設 ``<存檔資料夾>/world``（``TRPG_SAVE_DIR`` 或專案的 ``saves/``），
可用 ``--world-dir`` 指定。
伺服器開著也可以刪：伺服器每次都重讀留言檔。路徑一律 ``pathlib``，Windows 與 macOS 同一條指令。
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from trpg.roguelite.save import default_save_dir
from trpg.server.notes import LocationNoteStore, NoteError, NoteNotFoundError
from trpg.world.layout import world_dir_of

EXIT_ERROR = 2
TZ = dt.timezone(dt.timedelta(hours=8))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="地點留言（管理者）")
    parser.add_argument("--world-dir", type=Path, default=None, help="世界存檔資料夾")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="列出留言（新的在前）")
    listing.add_argument("--location", default=None, help="只列這個地點")
    delete = commands.add_parser("delete", help="刪一則留言")
    delete.add_argument("note_id")
    return parser


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr
) -> int:
    args = _parser().parse_args(argv)
    root = args.world_dir if args.world_dir is not None else world_dir_of(default_save_dir())
    store = LocationNoteStore(root)
    try:
        if args.command == "delete":
            note = store.delete(args.note_id)
            print(f"已刪除 {note.note_id}（{note.name}：{note.text}）", file=out)
            return 0
        notes = sorted(store.all(), key=lambda n: (n.at, n.note_id), reverse=True)
        if args.location is not None:
            notes = [n for n in notes if n.location == args.location]
        for note in notes:
            when = dt.datetime.fromtimestamp(note.at, TZ).strftime("%Y-%m-%d %H:%M")
            print(
                f"{note.note_id}  {when}  {note.region}/{note.location}  {note.name}：{note.text}",
                file=out,
            )
        if not notes:
            print("（沒有留言）", file=out)
        return 0
    except (NoteError, NoteNotFoundError) as exc:
        print(f"錯誤：{exc}", file=err)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
