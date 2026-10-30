"""``trpg`` 指令的進入點。

子命令：

- ``trpg --version``：印出版本。
- ``trpg rng --seed 42 [--count 10] [--sides 20]``：印出亂數序列，每行一個數字
  （未給 ``--sides`` 時印 ``next_u32()``，給了則印擲骰結果）。
- ``trpg content check``：載入並驗證 ``content/`` 下目前所有已知資料檔。
- ``trpg map show <map_id>``：以文字網格印出地圖。
- ``trpg map list``：列出所有地圖的類型、大小與是否有預設遭遇。
- ``trpg battle --map <map_id> --seed <n> [--rounds-max 30] [--log-json <path>]
  [--ai utility|simple] [--weather <id>] [--objective escape|defend]
  [--deploy x,y;x,y] [--allies ...] [--enemies ...]``：
  雙方由效用 AI（預設）自動對戰，印出每輪戰場、環境預告與繁體中文戰鬥紀錄。
- ``trpg skills list`` / ``trpg skills show <id>``：技能的自動摘要。
- ``trpg skills random --seed N [--tier T] [--rarity R] [--skeleton S] [--count C]``：隨機組合器。
- ``trpg sim matrix [--builds a,b] [--maps a,b] [--seeds 20] [--jobs N] [--json out.json]``：
  build × 地圖矩陣（勝率、英雄 DPR、存活率、排名、6.8 標準檢查）。
- ``trpg sim skills [--demo] [--random N] [--seeds 10] [--jobs N]``：技能報表（DPR 分佈、離群）。
- ``trpg sim keywords [--samples 20] [--seed-start 0] [--battles 1] [--maps a,b] [--jobs N]``：
  關鍵字組合抽樣（隨機武器＋2 個關鍵字的測試角色；Phase 3-24b2）。
- ``trpg sim maps [--maps a,b] [--seeds 20] [--seed-start 0] [--jobs N] [--json out.json]
  [--ally-build a,b]``：每張地圖以預設陣容（或指定的 build）批次模擬，印出勝率、輪數、DPR、
  控制回合、技能使用與異常。
- ``trpg sim flash [--policies none,all,mixed] [--seeds 20] [--seed-start 0] [--jobs N]``：
  閃現模擬報表（Phase 3W-8）。
- ``trpg sim completion [--maps a,b] [--seeds 20] [--seed-start 0] [--jobs N]``：完成度檢查
  （9 種指揮官設定 × 地圖 × 種子；exception、max_actions、draw 必須為 0，否則結束碼 1）。
- ``trpg battle`` 與 ``trpg sim maps`` 都可加 ``--ally-commander``／``--enemy-commander <id>``
  （腳本指揮官，見 ``trpg.sim.commanders``）。
- ``trpg battle --ally-build <build_id>[,…]``：我方用 build 英雄（不足 3 人以標準隊友補齊）。
- ``trpg battle replay <path>``：讀取 ``--log-json`` 的輸出，重播並驗證最終狀態一致。
- ``trpg llm ping [--config path]``：檢查本機 LLM（config/llm.toml）是否可用。
- ``trpg llm propose [--tier N] [--rarity R] [--skeleton S] [--keyword K]... [--seed N] [-n N]
  [--mock]``：請 LLM 提議技能（重試＋退回），印出每題結果與統計摘要（Phase 4-L5）。
- ``trpg serve [--host 127.0.0.1] [--port 8000]``：以 uvicorn 啟動本機 API（``trpg.api``）。
- ``trpg run new|auto|show``：roguelite 一輪（``trpg.cli.run``，Phase 3-5a）。
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from trpg import __version__
from trpg.cli.battle import cmd_battle, cmd_map_list, cmd_map_show, cmd_replay
from trpg.cli.budget import cmd_skills_budget, cmd_skills_budget_all, library_violations
from trpg.cli.llm import ProposeArgs, cmd_llm_ping, cmd_llm_propose
from trpg.cli.run import add_run_parser
from trpg.cli.serve import DEFAULT_HOST, DEFAULT_PORT, cmd_serve
from trpg.cli.sim import cmd_sim_keywords, cmd_sim_maps
from trpg.cli.sim_completion import cmd_sim_completion
from trpg.cli.sim_flash import cmd_sim_flash
from trpg.cli.sim_matrix import cmd_sim_matrix, cmd_sim_skills
from trpg.cli.skills import cmd_skills_list, cmd_skills_show
from trpg.cli.skills_random import cmd_skills_random
from trpg.content.library import ContentLibrary
from trpg.content.loader import default_content_dir
from trpg.content.registry import load_all_content
from trpg.content.skills import SKELETON_IDS
from trpg.primitive_coverage import load_checked_library
from trpg.shared.errors import ContentError
from trpg.shared.rng import MASK64, Rng
from trpg.sim.commanders import COMMANDER_IDS

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


def _jobs_arg(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"必須 >= 0，收到 {value}")
    return value


def _resolve_jobs(jobs: int) -> int:
    """``0`` 代表依 CPU 邏輯核心數；報表與 ``jobs`` 無關，只影響速度。"""
    return jobs if jobs > 0 else max(1, os.cpu_count() or 1)


def build_parser() -> argparse.ArgumentParser:  # noqa: PLR0915
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
    content_commands.add_parser("check", help="載入並驗證所有已知的內容資料檔").set_defaults(
        func=_run_content_check
    )

    map_parser = commands.add_parser("map", help="地圖工具")
    map_commands = map_parser.add_subparsers(
        dest="map_command", metavar="<subcommand>", required=True
    )
    show = map_commands.add_parser("show", help="以文字網格印出地圖")
    show.add_argument("map_id", help="地圖 ID（content/maps/<id>.yaml）")
    show.set_defaults(func=_run_map_show)
    map_commands.add_parser("list", help="列出所有地圖的類型、大小與是否有預設遭遇").set_defaults(
        func=_run_map_list
    )

    skills_parser = commands.add_parser("skills", help="技能工具")
    skills_commands = skills_parser.add_subparsers(
        dest="skills_command", metavar="<subcommand>", required=True
    )
    skills_commands.add_parser("list", help="列出所有技能與效果摘要").set_defaults(
        func=_run_skills_list
    )
    skills_show = skills_commands.add_parser("show", help="顯示一個技能的詳細資料")
    skills_show.add_argument("skill_id", help="技能 ID（content/skills/<id>.yaml）")
    skills_show.add_argument(
        "--unit", help="單位範本 ID（content/units/<id>.yaml）；用來標示專精加成目前是否生效"
    )
    skills_budget = skills_commands.add_parser("budget", help="顯示技能的預算明細（或 --all 總表）")
    skills_budget.add_argument("skill_id", nargs="?", help="技能 ID；省略時需加 --all")
    skills_budget.add_argument("--all", action="store_true", help="列出所有技能的預算總表")

    skills_random = skills_commands.add_parser(
        "random", help="隨機組合器：組出合格的隨機技能，印出 YAML 與預算摘要"
    )
    skills_random.add_argument("--seed", type=_non_negative_int, required=True, help="起始種子")
    skills_random.add_argument(
        "--count", type=_positive_int, default=1, help="個數（種子依序 +1，預設 1）"
    )
    skills_random.add_argument("--tier", type=int, choices=range(1, 6), help="階級 1–5")
    skills_random.add_argument(
        "--rarity", choices=("common", "rare", "epic", "legendary"), help="稀有度"
    )
    skills_random.add_argument("--skeleton", choices=SKELETON_IDS, help="骨架")

    sim = commands.add_parser("sim", help="批次模擬與平衡報表")
    sim_commands = sim.add_subparsers(dest="sim_command", metavar="<subcommand>", required=True)
    sim_maps = sim_commands.add_parser(
        "maps", help="每張地圖以預設陣容跑 N 個種子：勝率、輪數、DPR、控制回合、技能使用、異常"
    )
    sim_maps.add_argument(
        "--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部有 encounter 的非測試地圖）"
    )
    sim_maps.add_argument(
        "--seeds", type=_positive_int, default=20, help="每張地圖的場數（預設 20）"
    )
    sim_maps.add_argument(
        "--seed-start", type=_non_negative_int, default=0, help="起始種子（預設 0）"
    )
    sim_maps.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    sim_maps.add_argument("--json", type=Path, default=None, help="另外寫出完整報表 JSON")
    sim_maps.add_argument(
        "--ally-build",
        default=None,
        help="我方改用 build 英雄，以逗號分隔（不足 3 人以標準隊友補齊；預設：地圖的預設陣容）",
    )
    _add_commander_args(sim_maps)

    battle = commands.add_parser(
        "battle",
        help="雙方由 AI 自動對戰（或 battle replay 重播紀錄）",
        description="雙方由 AI 自動對戰。另有子命令：trpg battle replay <path>",
    )
    battle.add_argument("--map", dest="map_id", help="地圖 ID")
    battle.add_argument("--seed", type=_non_negative_int, help="種子（0 <= seed < 2**64）")
    battle.add_argument(
        "--rounds-max", type=_positive_int, default=30, help="輪數上限，超過即平手（預設 30）"
    )
    battle.add_argument(
        "--allies",
        default=None,
        help="我方單位範本，以逗號分隔（預設為地圖的 encounter，沒有時為戰士、弓手、法師）",
    )
    battle.add_argument(
        "--ally-build",
        default=None,
        help=(
            "我方用 content/sim/builds.yaml 的 build 英雄（以逗號分隔；不足 3 人時以標準隊友補齊，"
            "與 sim matrix 相同）；不可與 --allies 同時使用"
        ),
    )
    battle.add_argument(
        "--enemies",
        default=None,
        help="敵方單位範本，以逗號分隔（預設為地圖的 encounter，沒有時為盜賊、盜賊弓手、盜賊頭目）",
    )
    battle.add_argument(
        "--ai", choices=("utility", "simple"), default="utility", help="AI（預設 utility 效用 AI）"
    )
    battle.add_argument("--weather", default=None, help="天氣 ID（預設為地圖的天氣）")
    battle.add_argument(
        "--objective",
        choices=("eliminate", "escape", "defend"),
        default=None,
        help="勝利條件（預設為地圖的 objective；escape／defend 用地圖的 alt_objectives）",
    )
    battle.add_argument(
        "--deploy",
        default=None,
        help="部署：我方單位依序的起始位置，例如 0,6;1,7（必須在起始區內）",
    )
    battle.add_argument(
        "--ally-race",
        default=None,
        help="我方依序的種族（content/races.yaml 的 ID，以逗號分隔；空白＝不指定），例如 orc,,elf",
    )
    battle.add_argument("--enemy-race", default=None, help="敵方依序的種族（格式同 --ally-race）")
    battle.add_argument("--log-json", type=Path, default=None, help="輸出動作列表與事件 JSON")
    _add_commander_args(battle)
    battle_commands = battle.add_subparsers(dest="battle_command", metavar="<subcommand>")
    replay = battle_commands.add_parser("replay", help="重播 --log-json 的輸出並驗證一致")
    replay.add_argument("path", type=Path, help="戰鬥紀錄 JSON")
    _add_sim_report_parsers(sim_commands)
    _add_serve_parser(commands)
    _add_llm_parser(commands)
    add_run_parser(commands, _with_library)
    rng_parser.set_defaults(func=_run_rng)
    skills_show.set_defaults(func=_run_skills_show)
    skills_budget.set_defaults(func=_run_skills_budget)
    skills_random.set_defaults(func=_run_skills_random)
    sim_maps.set_defaults(func=_sim_maps)
    battle.set_defaults(func=_battle)
    replay.set_defaults(func=_run_replay)
    return parser


def _add_sim_report_parsers(
    sim_commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """``trpg sim matrix``（build × 地圖矩陣）與 ``trpg sim skills``（技能報表）。"""
    matrix = sim_commands.add_parser(
        "matrix", help="build × 地圖矩陣：勝率、英雄 DPR、存活率、排名與 6.8 標準檢查"
    )
    matrix.add_argument("--builds", default=None, help="build ID，以逗號分隔（預設：全部）")
    matrix.add_argument(
        "--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部有 encounter 的非測試地圖）"
    )
    matrix.add_argument("--seeds", type=_positive_int, default=20, help="每格的場數（預設 20）")
    matrix.add_argument(
        "--seed-start", type=_non_negative_int, default=0, help="起始種子（預設 0）"
    )
    matrix.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    matrix.add_argument("--json", type=Path, default=None, help="另外寫出完整報表 JSON")
    completion = sim_commands.add_parser(
        "completion",
        help="完成度檢查：9 種指揮官設定 × 地圖 × 種子，確認沒有 exception／max_actions／draw",
    )
    completion.add_argument(
        "--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部有 encounter 的非測試地圖）"
    )
    completion.add_argument("--seeds", type=_positive_int, default=20, help="每格的場數（預設 20）")
    completion.add_argument(
        "--seed-start", type=_non_negative_int, default=0, help="起始種子（預設 0）"
    )
    completion.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    flash = sim_commands.add_parser(
        "flash",
        help="閃現模擬報表（Phase 3W-8）：策略 × 種子各跑一整輪 AI，輸出靈感點、閃現與完整技能摘要",
    )
    flash.add_argument(
        "--policies",
        default=None,
        help="AI 閃現策略，以逗號分隔（none 不指定類別、all 全指定類別、mixed 混合；預設全部）",
    )
    flash.add_argument("--seeds", type=_positive_int, default=20, help="每個策略的輪數（預設 20）")
    flash.add_argument(
        "--economy",
        default=None,
        help=(
            "靈感經濟掃描（BAL-1；只在模擬覆寫，不改 content）：例 "
            '"win=1,2;start=0,2;preboss=0,2"（每勝／開局／Boss 前加給，逗號列出的值取笛卡兒積）'
        ),
    )
    flash.add_argument("--seed-start", type=_non_negative_int, default=0, help="起始種子（預設 0）")
    flash.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    skills = sim_commands.add_parser(
        "skills", help="技能報表：施放者 DPR、勝率、使用率，依階級與骨架彙總，標出 DPR 離群的技能"
    )
    skills.add_argument("--demo", action="store_true", help="測示範技能（content/skills/）")
    skills.add_argument(
        "--random", type=_non_negative_int, default=0, metavar="N", help="測 N 個隨機技能"
    )
    skills.add_argument("--seeds", type=_positive_int, default=10, help="每個技能的場數（預設 10）")
    skills.add_argument(
        "--seed-start", type=_non_negative_int, default=0, help="起始種子（預設 0）"
    )
    skills.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    skills.add_argument("--json", type=Path, default=None, help="另外寫出完整報表 JSON")
    keywords = sim_commands.add_parser(
        "keywords",
        help="關鍵字組合抽樣：隨機武器＋2 個關鍵字組成測試角色，各打一張隨機地圖（Phase 3-24b2）",
    )
    keywords.add_argument("--samples", type=_positive_int, default=20, help="樣本數（預設 20）")
    keywords.add_argument(
        "--seed-start", type=_non_negative_int, default=0, help="起始樣本種子（預設 0）"
    )
    keywords.add_argument(
        "--battles", type=_positive_int, default=1, help="每個樣本的場數（預設 1）"
    )
    keywords.add_argument(
        "--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部有 encounter 的非測試地圖）"
    )
    keywords.add_argument(
        "--jobs", type=_jobs_arg, default=0, help="平行行程數（預設 0＝CPU 邏輯核心數）"
    )
    matrix.set_defaults(func=_sim_matrix)
    completion.set_defaults(func=_sim_completion)
    flash.set_defaults(func=_sim_flash)
    skills.set_defaults(func=_sim_skills)
    keywords.set_defaults(func=_sim_keywords)


def _sim_keywords(args: argparse.Namespace) -> int:
    maps = None if args.maps is None else _split(args.maps)
    if maps == []:
        print("錯誤：--maps 至少要有一張地圖", file=sys.stderr)
        return 2
    return _with_library(
        lambda lib: cmd_sim_keywords(
            lib,
            samples=args.samples,
            seed_start=args.seed_start,
            battles=args.battles,
            maps=maps,
            jobs=_resolve_jobs(args.jobs),
            out=sys.stdout,
            err=sys.stderr,
        )
    )


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
        library = load_checked_library(content_dir)
    except ContentError as exc:
        print(f"內容檢查失敗：\n{exc}", file=sys.stderr)
        return 1
    violations = library_violations(library)
    if violations:
        lines = "\n".join(f"  - {v}" for v in violations)
        print(f"內容檢查失敗：{len(violations)} 項技能違規：\n{lines}", file=sys.stderr)
        return 1
    print(f"內容檢查通過（{content_dir}）：")
    known = {path for path, _ in loaded}
    files = loaded + [(p, m) for p, m in library.files if p not in known]
    for path, model in files:
        print(f"  {path.relative_to(content_dir).as_posix()}：{model.summary()}")
    print(
        f"共 {len(files)} 個檔案；跨檔案檢查（武器引用、地圖地形與連通性）通過；"
        f"{len(library.skills)} 個技能通過預算與結構驗證。"
    )
    # 地圖的 region／look 寫錯只是警告（載入時已丟棄未知值、退回預設畫法），不算失敗
    if library.map_warnings:
        print(f"地圖外觀警告（{len(library.map_warnings)} 項，不影響通過）：")
        for warning in library.map_warnings:
            print(f"  - {warning}")
    return 0


def _add_serve_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    serve = commands.add_parser("serve", help="啟動本機 API 伺服器（FastAPI ＋ uvicorn）")
    serve.add_argument(
        "--host", default=DEFAULT_HOST, help=f"綁定的位址（預設 {DEFAULT_HOST}，只限本機）"
    )
    serve.add_argument(
        "--port", type=_port, default=DEFAULT_PORT, help=f"埠號（預設 {DEFAULT_PORT}）"
    )
    serve.set_defaults(func=_run_serve)


def _add_llm_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    llm = commands.add_parser("llm", help="本機 LLM 工具")
    llm_commands = llm.add_subparsers(dest="llm_command", required=True)
    ping = llm_commands.add_parser("ping", help="送一則最小請求，檢查本機模型（config/llm.toml）")
    ping.add_argument(
        "--config", type=Path, default=None, help="設定檔路徑（預設 config/llm.toml）"
    )
    ping.set_defaults(func=_run_llm_ping)
    propose = llm_commands.add_parser(
        "propose", help="請 LLM 提議技能（重試＋退回），印出每題結果與統計摘要"
    )
    propose.add_argument(
        "--tier",
        type=int,
        choices=range(1, 6),
        default=None,
        help="角色階級（預設 1；--mock 時每題自動選 Mock 答得出的最低階級）",
    )
    propose.add_argument(
        "--rarity",
        choices=("common", "rare", "epic", "legendary"),
        default=None,
        help="稀有度（預設依種子輪替 common／rare／epic）",
    )
    propose.add_argument("--skeleton", choices=SKELETON_IDS, default=None, help="骨架（預設輪替）")
    propose.add_argument(
        "--keyword", action="append", default=None, help="題目關鍵字（可重複，最多 2 個）"
    )
    propose.add_argument("--seed", type=_non_negative_int, default=0, help="種子（預設 0）")
    propose.add_argument("-n", type=_positive_int, default=1, help="題目數（預設 1）")
    propose.add_argument(
        "--mock", action="store_true", help="不連模型：Mock 回傳手寫技能轉成的提議（測試與示範）"
    )
    propose.add_argument(
        "--naming",
        action="store_true",
        help="通過驗證的技能再請模型命名與寫敘事（--mock 用 Mock）；不加則用組合式名稱與模板敘事",
    )
    propose.add_argument(
        "--config", type=Path, default=None, help="設定檔路徑（預設 config/llm.toml）"
    )
    propose.set_defaults(func=_run_llm_propose)


def _run_llm_ping(args: argparse.Namespace) -> int:
    return cmd_llm_ping(sys.stdout, sys.stderr, config_path=args.config)


def _run_llm_propose(args: argparse.Namespace) -> int:
    options = ProposeArgs(
        count=args.n,
        seed=args.seed,
        tier=args.tier,
        rarity=args.rarity,
        skeleton=args.skeleton,
        keywords=tuple(args.keyword or ()),
        mock=args.mock,
        naming=args.naming,
    )
    return _with_library(
        lambda library: cmd_llm_propose(
            library, options, sys.stdout, sys.stderr, config_path=args.config
        )
    )


def _port(text: str) -> int:
    value = int(text)
    if not 0 < value < 65536:  # noqa: PLR2004
        raise argparse.ArgumentTypeError(f"埠號必須介於 1 與 65535，收到 {value}")
    return value


def _run_serve(args: argparse.Namespace) -> int:
    return cmd_serve(args.host, args.port, sys.stdout)


def _with_library(fn: Callable[[ContentLibrary], int]) -> int:
    try:
        library = load_checked_library()
    except ContentError as exc:
        print(f"內容資料錯誤：\n{exc}", file=sys.stderr)
        return 1
    try:
        return fn(library)
    except KeyError as exc:
        print(f"錯誤：{exc.args[0]}", file=sys.stderr)
        return 1


def _add_commander_args(parser: argparse.ArgumentParser) -> None:
    for flag, who in (("--ally-commander", "我方"), ("--enemy-commander", "敵方")):
        parser.add_argument(
            flag,
            choices=COMMANDER_IDS,
            default=None,
            help=f"{who}的腳本指揮官（戰術指令；預設：沒有）",
        )


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _sim_matrix(args: argparse.Namespace) -> int:
    builds = None if args.builds is None else _split(args.builds)
    maps = None if args.maps is None else _split(args.maps)
    if builds == [] or maps == []:
        print("錯誤：--builds 與 --maps 至少要有一個", file=sys.stderr)
        return 2
    return _with_library(
        lambda lib: cmd_sim_matrix(
            lib,
            builds=builds,
            maps=maps,
            seeds=args.seeds,
            seed_start=args.seed_start,
            jobs=_resolve_jobs(args.jobs),
            json_path=args.json,
            out=sys.stdout,
            err=sys.stderr,
        )
    )


def _sim_flash(args: argparse.Namespace) -> int:
    policies = None if args.policies is None else _split(args.policies)
    return _with_library(
        lambda lib: cmd_sim_flash(
            lib,
            policies=policies,
            seeds=args.seeds,
            seed_start=args.seed_start,
            jobs=_resolve_jobs(args.jobs),
            out=sys.stdout,
            err=sys.stderr,
            economy=args.economy,
        )
    )


def _sim_completion(args: argparse.Namespace) -> int:
    maps = None if args.maps is None else _split(args.maps)
    if maps == []:
        print("錯誤：--maps 至少要有一張地圖", file=sys.stderr)
        return 2
    return _with_library(
        lambda lib: cmd_sim_completion(
            lib,
            maps=maps,
            seeds=args.seeds,
            seed_start=args.seed_start,
            jobs=_resolve_jobs(args.jobs),
            out=sys.stdout,
            err=sys.stderr,
        )
    )


def _sim_skills(args: argparse.Namespace) -> int:
    return _with_library(
        lambda lib: cmd_sim_skills(
            lib,
            demo=args.demo or args.random == 0,
            random_count=args.random,
            seeds=args.seeds,
            seed_start=args.seed_start,
            jobs=_resolve_jobs(args.jobs),
            json_path=args.json,
            out=sys.stdout,
            err=sys.stderr,
        )
    )


def _battle(args: argparse.Namespace) -> int:  # noqa: PLR0911
    if args.map_id is None or args.seed is None:
        print(
            "錯誤：trpg battle 需要 --map 與 --seed（或使用 trpg battle replay <path>）",
            file=sys.stderr,
        )
        return 2
    if args.seed > MASK64:
        print(f"錯誤：seed 必須 < 2**64，收到 {args.seed}", file=sys.stderr)
        return 2
    allies = None if args.allies is None else _split(args.allies)
    enemies = None if args.enemies is None else _split(args.enemies)
    if allies == [] or enemies == []:
        print("錯誤：雙方都至少要有一個單位", file=sys.stderr)
        return 2
    ally_builds = None if args.ally_build is None else _split(args.ally_build)
    if ally_builds == []:
        print("錯誤：--ally-build 至少要指定一個 build", file=sys.stderr)
        return 2
    if ally_builds is not None and allies is not None:
        print("錯誤：--ally-build 不可與 --allies 同時使用", file=sys.stderr)
        return 2
    deploy: list[tuple[int, int]] | None = None
    if args.deploy:
        try:
            deploy = [
                (int(a), int(b))
                for a, b in (part.split(",") for part in args.deploy.split(";") if part.strip())
            ]
        except ValueError:
            print(f"錯誤：--deploy 格式應為 x,y;x,y，收到 {args.deploy!r}", file=sys.stderr)
            return 2
    return _with_library(
        lambda lib: cmd_battle(
            lib,
            map_id=args.map_id,
            seed=args.seed,
            rounds_max=args.rounds_max,
            allies=allies,
            enemies=enemies,
            ally_builds=ally_builds,
            log_json=args.log_json,
            out=sys.stdout,
            ai=args.ai,
            weather=args.weather,
            objective=args.objective,
            deploy=deploy,
            ally_commander=args.ally_commander,
            enemy_commander=args.enemy_commander,
            ally_races=_races(args.ally_race),
            enemy_races=_races(args.enemy_race),
        )
    )


def _races(text: str | None) -> list[str] | None:
    """``orc,,elf`` → ``["orc", "", "elf"]``（空白＝不指定；省略＝``None``）。"""
    return None if text is None else [part.strip() for part in text.split(",")]


def _sim_maps(args: argparse.Namespace) -> int:
    maps = None if args.maps is None else _split(args.maps)
    if maps == []:
        print("錯誤：--maps 至少要有一張地圖", file=sys.stderr)
        return 2
    builds = None if args.ally_build is None else _split(args.ally_build)
    if builds == []:
        print("錯誤：--ally-build 至少要指定一個 build", file=sys.stderr)
        return 2
    return _with_library(
        lambda lib: cmd_sim_maps(
            lib,
            ally_builds=builds,
            maps=maps,
            seeds=args.seeds,
            seed_start=args.seed_start,
            jobs=_resolve_jobs(args.jobs),
            json_path=args.json,
            out=sys.stdout,
            err=sys.stderr,
            ally_commander=args.ally_commander,
            enemy_commander=args.enemy_commander,
        )
    )


def _run_rng(args: argparse.Namespace) -> int:
    return _cmd_rng(args.seed, args.count, args.sides)


def _run_content_check(_args: argparse.Namespace) -> int:
    return _cmd_content_check()


def _run_map_list(_args: argparse.Namespace) -> int:
    return _with_library(lambda lib: cmd_map_list(lib, sys.stdout))


def _run_map_show(args: argparse.Namespace) -> int:
    return _with_library(lambda lib: cmd_map_show(lib, args.map_id, sys.stdout))


def _run_skills_list(_args: argparse.Namespace) -> int:
    return _with_library(lambda lib: cmd_skills_list(lib, sys.stdout))


def _run_skills_show(args: argparse.Namespace) -> int:
    return _with_library(
        lambda lib: cmd_skills_show(lib, args.skill_id, sys.stdout, unit_id=args.unit)
    )


def _run_skills_budget(args: argparse.Namespace) -> int:
    if args.all:
        return _with_library(lambda lib: cmd_skills_budget_all(lib, sys.stdout))
    if args.skill_id is None:
        print("錯誤：請指定技能 ID，或使用 --all", file=sys.stderr)
        return 2
    return _with_library(lambda lib: cmd_skills_budget(lib, args.skill_id, sys.stdout))


def _run_skills_random(args: argparse.Namespace) -> int:
    return _with_library(
        lambda lib: cmd_skills_random(
            lib,
            seed=args.seed,
            count=args.count,
            tier=args.tier,
            rarity=args.rarity,
            skeleton=args.skeleton,
            out=sys.stdout,
            err=sys.stderr,
        )
    )


def _run_replay(args: argparse.Namespace) -> int:
    return cmd_replay(args.path, sys.stdout)


def main(argv: list[str] | None = None) -> int:
    """CLI 主程式；回傳結束代碼（方便測試）。各子指令的處理函式由 ``set_defaults`` 指定。"""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --version、--help 與參數錯誤
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    handler = getattr(args, "func", None)
    if handler is None:  # pragma: no cover - 所有子指令都設定了 func
        parser.error(f"未知的指令：{args.command}")
    return int(handler(args))
