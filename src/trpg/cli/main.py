"""``trpg`` 指令的進入點。

子命令：

- ``trpg --version``：印出版本。
- ``trpg rng --seed 42 [--count 10] [--sides 20]``：印出亂數序列，每行一個數字
  （未給 ``--sides`` 時印 ``next_u32()``，給了則印擲骰結果）。
- ``trpg content check``：載入並驗證 ``content/`` 下目前所有已知資料檔。
- ``trpg map show <map_id>``：以文字網格印出地圖。
- ``trpg battle --map <map_id> --seed <n> [--rounds-max 30] [--log-json <path>]``：
  雙方由簡易 AI 自動對戰，印出每輪戰場與繁體中文戰鬥紀錄。
- ``trpg battle replay <path>``：讀取 ``--log-json`` 的輸出，重播並驗證最終狀態一致。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from trpg import __version__
from trpg.cli.battle import DEFAULT_ALLIES, DEFAULT_ENEMIES, cmd_battle, cmd_map_show, cmd_replay
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import default_content_dir
from trpg.content.registry import load_all_content
from trpg.shared.errors import ContentError
from trpg.shared.rng import MASK64, Rng

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

    map_parser = commands.add_parser("map", help="地圖工具")
    map_commands = map_parser.add_subparsers(
        dest="map_command", metavar="<subcommand>", required=True
    )
    show = map_commands.add_parser("show", help="以文字網格印出地圖")
    show.add_argument("map_id", help="地圖 ID（content/maps/<id>.yaml）")

    battle = commands.add_parser(
        "battle",
        help="雙方由簡易 AI 自動對戰（或 battle replay 重播紀錄）",
        description="雙方由簡易 AI 自動對戰。另有子命令：trpg battle replay <path>",
    )
    battle.add_argument("--map", dest="map_id", help="地圖 ID")
    battle.add_argument("--seed", type=_non_negative_int, help="種子（0 <= seed < 2**64）")
    battle.add_argument(
        "--rounds-max", type=_positive_int, default=30, help="輪數上限，超過即平手（預設 30）"
    )
    battle.add_argument(
        "--allies",
        default=",".join(DEFAULT_ALLIES),
        help=f"我方單位範本，以逗號分隔（預設 {','.join(DEFAULT_ALLIES)}）",
    )
    battle.add_argument(
        "--enemies",
        default=",".join(DEFAULT_ENEMIES),
        help=f"敵方單位範本，以逗號分隔（預設 {','.join(DEFAULT_ENEMIES)}）",
    )
    battle.add_argument("--log-json", type=Path, default=None, help="輸出動作列表與事件 JSON")
    battle_commands = battle.add_subparsers(dest="battle_command", metavar="<subcommand>")
    replay = battle_commands.add_parser("replay", help="重播 --log-json 的輸出並驗證一致")
    replay.add_argument("path", type=Path, help="戰鬥紀錄 JSON")
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
        library = load_library(content_dir)
    except ContentError as exc:
        print(f"內容檢查失敗：\n{exc}", file=sys.stderr)
        return 1
    print(f"內容檢查通過（{content_dir}）：")
    known = {path for path, _ in loaded}
    files = loaded + [(p, m) for p, m in library.files if p not in known]
    for path, model in files:
        print(f"  {path.relative_to(content_dir).as_posix()}：{model.summary()}")
    print(f"共 {len(files)} 個檔案；跨檔案檢查（武器引用、地圖地形與連通性）通過。")
    return 0


def _with_library(fn: Callable[[ContentLibrary], int]) -> int:
    try:
        library = load_library()
    except ContentError as exc:
        print(f"內容資料錯誤：\n{exc}", file=sys.stderr)
        return 1
    try:
        return fn(library)
    except KeyError as exc:
        print(f"錯誤：{exc.args[0]}", file=sys.stderr)
        return 1


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _battle(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.map_id is None or args.seed is None:
        print(
            "錯誤：trpg battle 需要 --map 與 --seed（或使用 trpg battle replay <path>）",
            file=sys.stderr,
        )
        return 2
    if args.seed > MASK64:
        print(f"錯誤：seed 必須 < 2**64，收到 {args.seed}", file=sys.stderr)
        return 2
    allies, enemies = _split(args.allies), _split(args.enemies)
    if not allies or not enemies:
        print("錯誤：雙方都至少要有一個單位", file=sys.stderr)
        return 2
    return _with_library(
        lambda lib: cmd_battle(
            lib,
            map_id=args.map_id,
            seed=args.seed,
            rounds_max=args.rounds_max,
            allies=allies,
            enemies=enemies,
            log_json=args.log_json,
            out=sys.stdout,
        )
    )


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
    if args.command == "map" and args.map_command == "show":
        return _with_library(lambda lib: cmd_map_show(lib, args.map_id, sys.stdout))
    if args.command == "battle":
        if args.battle_command == "replay":
            return cmd_replay(args.path, sys.stdout)
        return _battle(parser, args)
    parser.error(f"未知的指令：{args.command}")  # pragma: no cover - argparse 已限制選項
