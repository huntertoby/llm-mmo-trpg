"""Discord Bot 啟動腳本（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.10）。

    uv run python scripts/discord_bot.py check   # 檢查設定（缺值列出欄位與環境變數）
    uv run python scripts/discord_bot.py run     # 先 check；真實 Discord 連線還沒做（代決 5E2-1）
    uv run python scripts/discord_bot.py preview # 印出今日公告與還沒貼的首殺公告（不連網，5E-3）

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

from trpg.api.announce import AnnouncementSource, default_bot_state_path
from trpg.api.server_config import ServerConfigError, load_server_settings
from trpg.bot.announcer import kill_key, read_state
from trpg.bot.config import BotConfigError, load_announce_settings, load_bot_settings

EXIT_CONFIG = 2
EXIT_NO_ADAPTER = 3

NO_ADAPTER = (
    "真實的 Discord 連線（adapter）還沒做：目前只有測試用的假介面。\n"
    "要接上時，實作 trpg.bot.gateway.DiscordGateway（member_roles、send_dm、reply），\n"
    "把 slash 指令與成員事件轉成 CommandEvent／MemberUpdateEvent／MemberRemoveEvent，\n"
    "交給 trpg.bot.service.BotService（啟動時先呼叫 reconcile()）。\n"
    "公告（5E-3）：實作 send_channel，再建 trpg.bot.announcer.Announcer，\n"
    "每分鐘呼叫一次 tick(現在時間)。現在可以先用 `preview` 看公告文字。"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discord Bot")
    parser.add_argument("--config", type=Path, default=None, help="Bot 設定檔（預設照環境變數）")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="檢查設定")
    commands.add_parser("run", help="啟動 Bot")
    preview = commands.add_parser("preview", help="印出現在的公告文字（不連網、不需要 token）")
    preview.add_argument("--world-dir", type=Path, default=None, help="世界存檔資料夾")
    preview.add_argument("--now", type=int, default=None, help="時間（UTC 秒；預設現在）")
    return parser


def _preview(args: argparse.Namespace, out: TextIO, env: Mapping[str, str] | None) -> int:
    """不貼、不寫狀態：今日公告（不管今天貼過沒）＋還沒貼的首殺公告。"""
    import time  # noqa: PLC0415

    schedule = load_announce_settings(args.config, env)
    server = load_server_settings(env=env)
    source = AnnouncementSource(args.world_dir, public_url=server.public_url)
    now = args.now if args.now is not None else int(time.time())
    print(f"（每天 {schedule.hour} 點，{schedule.timezone}；時區 {schedule.tzinfo()}）", file=out)
    daily = source.daily_text(now)
    print(daily if daily is not None else "（世界還沒建立，今日公告不會貼）", file=out)
    state = read_state(default_bot_state_path())
    # 狀態檔還沒建立：Bot 第一次啟動會把現有首殺當作已貼（不洗版），所以沒有待貼的
    posted = set(state.posted_kills) if state is not None else None
    kills = source.first_kills()
    pending = [k for k in kills if posted is not None and kill_key(k) not in posted]
    for kill in pending:
        print(source.first_kill_text(kill), file=out)
    if not pending:
        print("（沒有還沒貼的首殺）", file=out)
    return 0


def main(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    env: Mapping[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preview":
        try:
            return _preview(args, out, env)
        except (BotConfigError, ServerConfigError) as exc:
            print(f"錯誤：{exc}", file=err)
            return EXIT_CONFIG
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
