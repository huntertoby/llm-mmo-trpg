"""``trpg`` 指令的進入點。

子命令：

- ``trpg --version``：印出版本。
- ``trpg rng --seed 42 [--count 10] [--sides 20]``：印出亂數序列，每行一個數字
  （未給 ``--sides`` 時印 ``next_u32()``，給了則印擲骰結果）。
- ``trpg content check``：載入並驗證 ``content/`` 下目前所有已知資料檔。
"""

from __future__ import annotations

import argparse
import sys

from trpg import __version__
from trpg.content.loader import default_content_dir
from trpg.content.registry import load_all_content
from trpg.shared.errors import ContentError
from trpg.shared.rng import Rng

__all__ = ["build_parser", "main"]


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"必須 >= 0，收到 {value}")
    return value


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"必須 >= 1，收到 {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trpg", description="LLM-MMO-TRPG 開發工具")
    parser.add_argument("--version", action="version", version=f"trpg {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    rng_parser = commands.add_parser("rng", help="印出可重現的亂數序列")
    rng_parser.add_argument("--seed", type=int, required=True, help="種子（0 <= seed < 2**64）")
    rng_parser.add_argument(
        "--count", type=_non_negative_int, default=10, help="要印出的數量（預設 10）"
    )
    rng_parser.add_argument(
        "--sides", type=_positive_int, default=None, help="骰子面數；未給時印 32 位元無號整數"
    )

    content_parser = commands.add_parser("content", help="內容資料工具")
    content_commands = content_parser.add_subparsers(
        dest="content_command", metavar="<subcommand>", required=True
    )
    content_commands.add_parser("check", help="載入並驗證所有已知的內容資料檔")
    return parser


def _cmd_rng(seed: int, count: int, sides: int | None) -> int:
    try:
        rng = Rng(seed)
    except ValueError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    for _ in range(count):
        print(rng.next_u32() if sides is None else rng.roll(sides))
    return 0


def _cmd_content_check() -> int:
    content_dir = default_content_dir()
    try:
        loaded = load_all_content(content_dir)
    except ContentError as exc:
        print(f"內容檢查失敗：\n{exc}", file=sys.stderr)
        return 1
    print(f"內容檢查通過（{content_dir}）：")
    for path, model in loaded:
        print(f"  {path.relative_to(content_dir).as_posix()}：{model.summary()}")
    print(f"共 {len(loaded)} 個檔案。")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 主程式；回傳結束代碼（方便測試）。"""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --version、--help 與參數錯誤
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)

    if args.command == "rng":
        return _cmd_rng(args.seed, args.count, args.sides)
    if args.command == "content" and args.content_command == "check":
        return _cmd_content_check()
    parser.error(f"未知的指令：{args.command}")  # pragma: no cover - argparse 已限制選項
