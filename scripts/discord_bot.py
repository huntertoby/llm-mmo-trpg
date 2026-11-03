"""Discord Bot 啟動腳本（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.10）。

    uv run python scripts/discord_bot.py check   # 檢查設定（缺值列出欄位與環境變數）
    uv run python scripts/discord_bot.py run     # 先 check；真實 Discord 連線還沒做（代決 5E2-1）

Bot 是獨立程序，不碰遊戲伺服器：設定缺值只會讓這個腳本以 exit 2 結束，伺服器照常。
設定範本：``config/bot.example.toml``；真的值放 ``config/bot.local.toml`` 或環境變數。
路徑一律 ``pathlib``，Windows 與 macOS 同一條指令（5E-4 預留）。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from trpg.bot.config import BotConfigError, load_bot_settings

EXIT_CONFIG = 2
EXIT_NO_ADAPTER = 3

NO_ADAPTER = (
    "真實的 Discord 連線（adapter）還沒做：目前只有測試用的假介面。\n"
    "要接上時，實作 trpg.bot.gateway.DiscordGateway（member_roles、send_dm、reply），\n"
    "把 slash 指令與成員事件轉成 CommandEvent／MemberUpdateEvent／MemberRemoveEvent，\n"
    "交給 trpg.bot.service.BotService（啟動時先呼叫 reconcile()）。"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discord Bot")
    parser.add_argument("--config", type=Path, default=None, help="Bot 設定檔（預設照環境變數）")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="檢查設定")
    commands.add_parser("run", help="啟動 Bot")
    return parser


def main(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    env: Mapping[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = load_bot_settings(args.config, env)
    except BotConfigError as exc:
        print(f"錯誤：{exc}", file=err)
        return EXIT_CONFIG
    print(
        f"設定齊全：伺服器 {settings.guild_id}、身分組 {settings.role_id}、"
        f"公告頻道 {settings.announce_channel_id}、token {settings.masked_token()}",
        file=out,
    )
    if args.command == "run":
        print(NO_ADAPTER, file=err)
        return EXIT_NO_ADAPTER
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
