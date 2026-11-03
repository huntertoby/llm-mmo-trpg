"""開發用：在本機建立與管理大世界帳號（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28.7）。

正式的帳號由 Discord Bot（5E-2）發放；這個腳本只給本機測試用，呼叫同一個服務層
（:class:`trpg.server.accounts.AccountStore`）。

    uv run python scripts/dev_account.py create alice            # 產生密碼並只印一次
    uv run python scripts/dev_account.py create alice --password-stdin < pw.txt
    uv run python scripts/dev_account.py list
    uv run python scripts/dev_account.py disable alice
    uv run python scripts/dev_account.py enable alice
    uv run python scripts/dev_account.py reset-password alice
    uv run python scripts/dev_account.py attach alice c1a2b3c4d  # 開發模式建的角色歸到帳號
    uv run python scripts/dev_account.py admin alice on          # 管理者（可改 LLM 開關，5E-2）
    uv run python scripts/dev_account.py create root --admin

``attach`` 先檢查角色檔 ``<世界資料夾>/chars/<character_id>.json`` 存在（5E-2，計畫 29.9）；
世界資料夾預設 ``<存檔資料夾>/world``，可用 ``--world-dir`` 指定。

帳號資料夾照 ``config/server.toml`` 的 ``[accounts] dir``
（空字串＝存檔資料夾底下的 ``accounts/``），
可用 ``--dir`` 指定。路徑一律 ``pathlib``，Windows 與 macOS 同一條指令（5E-4 預留）。
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import load_account_settings
from trpg.server.accounts import AccountRecord, AccountStore, open_account_store
from trpg.shared.errors import TrpgError

GENERATED_PASSWORD_BYTES = 12


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="開發用：管理大世界帳號")
    parser.add_argument("--dir", type=Path, default=None, help="帳號資料夾（預設照設定檔）")
    parser.add_argument(
        "--world-dir", type=Path, default=None, help="世界資料夾（預設 <存檔資料夾>/world）"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="建立帳號")
    create.add_argument("username")
    create.add_argument("--password-stdin", action="store_true", help="從標準輸入讀密碼")
    create.add_argument("--discord-id", default=None)
    create.add_argument("--admin", action="store_true", help="設為管理者")
    commands.add_parser("list", help="列出帳號")
    for name in ("disable", "enable"):
        commands.add_parser(name, help=f"{name} 帳號").add_argument("username")
    reset = commands.add_parser("reset-password", help="重設密碼（清掉全部登入）")
    reset.add_argument("username")
    reset.add_argument("--password-stdin", action="store_true")
    attach = commands.add_parser("attach", help="把沒有主人的角色歸到帳號")
    attach.add_argument("username")
    attach.add_argument("character_id")
    admin = commands.add_parser("admin", help="設定或取消管理者（可改 LLM 開關）")
    admin.add_argument("username")
    admin.add_argument("state", choices=("on", "off"))
    return parser


def _store(folder: Path | None) -> AccountStore:
    if folder is None:
        return open_account_store()
    settings = load_account_settings()
    return AccountStore(
        folder, max_characters=settings.max_characters, session_ttl_s=settings.session_ttl_s
    )


def _check_character_file(world_dir: Path | None, character_id: str) -> None:
    root = world_dir if world_dir is not None else default_save_dir() / "world"
    path = root / "chars" / f"{character_id}.json"
    if not path.is_file():
        raise TrpgError(
            f"找不到角色檔 {path}（角色 ID 打錯，或世界資料夾不對：用 --world-dir 指定）"
        )


def _password(from_stdin: bool, stdin: TextIO) -> tuple[str, bool]:
    """（密碼, 是不是腳本產生的）。"""
    if from_stdin:
        return stdin.readline().rstrip("\r\n"), False
    return secrets.token_urlsafe(GENERATED_PASSWORD_BYTES), True


def _account(store: AccountStore, username: str) -> AccountRecord:
    record = store.find(username)
    if record is None:
        raise TrpgError(f"找不到帳號 {username}")
    return record


def _line(record: AccountRecord) -> str:
    state = ("停用" if record.disabled else "正常") + ("・管理者" if record.admin else "")
    chars = "、".join(record.characters) or "（沒有角色）"
    return f"{record.username}\t{record.account_id}\t{state}\t{chars}"


def run(args: argparse.Namespace, out: TextIO, stdin: TextIO) -> None:
    store = _store(args.dir)
    if args.command == "create":
        password, generated = _password(args.password_stdin, stdin)
        record = store.create(args.username, password, discord_id=args.discord_id)
        if args.admin:
            record = store.set_admin(record.account_id, True)
        print(f"已建立 {record.username}（{record.account_id}）", file=out)
        if generated:
            print(f"密碼（只顯示這一次）：{password}", file=out)
    elif args.command == "list":
        for record in store.all():
            print(_line(record), file=out)
    elif args.command in ("disable", "enable"):
        record = store.set_disabled(
            _account(store, args.username).account_id, args.command == "disable"
        )
        print(_line(record), file=out)
    elif args.command == "reset-password":
        password, generated = _password(args.password_stdin, stdin)
        record = store.reset_password(_account(store, args.username).account_id, password)
        print(f"已重設 {record.username} 的密碼", file=out)
        if generated:
            print(f"新密碼（只顯示這一次）：{password}", file=out)
    elif args.command == "attach":
        account_id = _account(store, args.username).account_id
        _check_character_file(args.world_dir, args.character_id)
        record = store.attach_character(account_id, args.character_id)
        print(_line(record), file=out)
    elif args.command == "admin":
        account_id = _account(store, args.username).account_id
        record = store.set_admin(account_id, args.state == "on")
        print(_line(record), file=out)


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, stdin: TextIO = sys.stdin
) -> int:
    args = _parser().parse_args(argv)
    try:
        run(args, out, stdin)
    except TrpgError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
