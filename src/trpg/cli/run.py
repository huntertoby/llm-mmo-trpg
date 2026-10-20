"""``trpg run``：roguelite 一輪（Phase 3-5a）。

- ``trpg run new --seed N --build X [--attrs str=2,con=2] [--save-dir D]``：開新一輪並存檔。
- ``trpg run auto --seed N [--build X] [--save] [--save-dir D]``：AI 代打整輪（測試與模擬用）；
  ``--from <存檔>`` 從存檔接續（含戰鬥中）。
- ``trpg run show <存檔>``：顯示存檔內容。
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.roguelite import (
    RunError,
    RunSave,
    RunState,
    auto_play,
    load_save,
    new_run,
    restore_battle,
    write_save,
)
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.save import default_save_dir
from trpg.roguelite.start import default_build
from trpg.roguelite.state import BattleNode, BattleRecord, CampfireNode, LevelUpNode
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute

__all__ = ["add_run_parser", "cmd_run_auto", "cmd_run_new", "cmd_run_show", "parse_attrs"]

type WithLibrary = Callable[[Callable[[ContentLibrary], int]], int]

_NODE_TEXT = {"battle": "戰鬥", "level_up": "升級", "campfire": "營火", "ended": "結束"}


def parse_attrs(text: str) -> dict[Attribute, int]:
    """``str=2,con=2`` → 配點（格式錯誤拋出 ``argparse.ArgumentTypeError``）。"""
    result: dict[Attribute, int] = {}
    try:
        for part in (p.strip() for p in text.split(",") if p.strip()):
            key, value = part.split("=")
            attr = Attribute(key.strip())
            result[attr] = result.get(attr, 0) + int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--attrs 格式應為 str=2,con=2，收到 {text!r}") from exc
    return result


def _seed(text: str) -> int:
    value = int(text)
    if not 0 <= value <= MASK64:
        raise argparse.ArgumentTypeError(f"seed 必須在 0～2**64−1，收到 {value}")
    return value


def add_run_parser(
    commands: argparse._SubParsersAction[argparse.ArgumentParser], with_library: WithLibrary
) -> None:
    run = commands.add_parser("run", help="roguelite 一輪：開新一輪、AI 代打、顯示存檔")
    sub = run.add_subparsers(dest="run_command", metavar="<subcommand>", required=True)
    new = sub.add_parser("new", help="開新一輪並存檔")
    new.add_argument("--seed", type=_seed, required=True, help="一輪的種子")
    new.add_argument("--build", required=True, help="起始 build（content/sim/builds.yaml）")
    new.add_argument("--attrs", type=parse_attrs, default=None, help="開局配點，例如 str=2,con=2")
    new.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾（預設 saves/）")
    new.set_defaults(
        func=lambda a: with_library(
            lambda lib: cmd_run_new(
                lib, seed=a.seed, build=a.build, attrs=a.attrs, save_dir=_dir(a), out=sys.stdout
            )
        )
    )
    auto = sub.add_parser("auto", help="AI 代打整輪（測試與模擬用）")
    auto.add_argument("--seed", type=_seed, default=None, help="一輪的種子（--from 時省略）")
    auto.add_argument("--build", default=None, help="起始 build；省略時以種子抽一個")
    auto.add_argument("--from", dest="from_path", type=Path, default=None, help="從存檔接續")
    auto.add_argument("--save", action="store_true", help="結束後把一輪存檔")
    auto.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾（預設 saves/）")
    auto.set_defaults(func=lambda a: with_library(lambda lib: _auto(lib, a)))
    show = sub.add_parser("show", help="顯示存檔內容")
    show.add_argument("path", type=Path, help="存檔路徑（saves/run-<id>.json）")
    show.set_defaults(
        func=lambda a: with_library(lambda lib: cmd_run_show(lib, a.path, sys.stdout))
    )


def _dir(args: argparse.Namespace) -> Path:
    return args.save_dir if args.save_dir is not None else default_save_dir()


def _auto(library: ContentLibrary, args: argparse.Namespace) -> int:
    if (args.seed is None) == (args.from_path is None):
        print("錯誤：trpg run auto 需要 --seed 或 --from（擇一）", file=sys.stderr)
        return 2
    return cmd_run_auto(
        library,
        sys.stdout,
        seed=args.seed,
        build=args.build,
        from_path=args.from_path,
        save_dir=_dir(args) if args.save else None,
    )


def _new_run_id() -> str:
    return secrets.token_hex(4)


def cmd_run_new(
    library: ContentLibrary,
    *,
    seed: int,
    build: str,
    attrs: Mapping[Attribute, int] | None,
    save_dir: Path,
    out: TextIO,
) -> int:
    try:
        run = new_run(library, build, seed, attrs)
    except RunError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    run_id = _new_run_id()
    path = write_save(save_dir, RunSave(run_id=run_id, run=run))
    _print_summary(library, run, out)
    print(f"已存檔：{path}（run id {run_id}）", file=out)
    return 0


def cmd_run_auto(
    library: ContentLibrary,
    out: TextIO,
    *,
    seed: int | None = None,
    build: str | None = None,
    from_path: Path | None = None,
    save_dir: Path | None = None,
) -> int:
    try:
        if from_path is not None:
            save = load_save(from_path)
            run, run_id = save.run, save.run_id
            battle = restore_battle(library, save)
            print(f"從存檔接續：{from_path}", file=out)
        else:
            assert seed is not None
            run = new_run(library, build or default_build(library, seed), seed)
            run_id, battle = _new_run_id(), None
        _print_header(library, run, out)
        final, _ = auto_play(
            library, run, battle, on_node=lambda a, b: _print_node(library, a, b, out)
        )
    except RunError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    _print_result(final, out)
    if save_dir is not None:
        print(f"已存檔：{write_save(save_dir, RunSave(run_id=run_id, run=final))}", file=out)
    return 0


def cmd_run_show(library: ContentLibrary, path: Path, out: TextIO) -> int:
    try:
        save = load_save(path)
    except RunError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    print(f"存檔 {path}（{save.format}，run id {save.run_id}）", file=out)
    _print_summary(library, save.run, out)
    if save.battle is not None:
        print(
            f"進行中的戰鬥：第 {save.battle.index} 場，已結算 {len(save.battle.steps)} 步", file=out
        )
    for record in save.run.history:
        print(f"  {_record_text(library, record)}", file=out)
    return 0


# ---------------------------------------------------------------------------
# 文字
# ---------------------------------------------------------------------------


def _attrs_text(run: RunState) -> str:
    return " ".join(f"{a.display_name} {run.hero.attributes[a]}" for a in Attribute)


def _skill_name(library: ContentLibrary, run: RunState, skill_id: str) -> str:
    skill = skill_defs(library, run, [skill_id])[0]
    return f"{skill.name_zh}（{skill_id}）"


def _resources(run: RunState) -> str:
    return (
        f"HP {run.hp}/{run.max_hp} 法力 {run.mana}/{run.max_mana} 源力 {run.source}"
        f" 等級 {run.level} 經驗 {run.xp}"
    )


def _print_header(library: ContentLibrary, run: RunState, out: TextIO) -> None:
    build = library.builds.by_id()[run.build_id]
    print(f"一輪：種子 {run.seed}，{run.build_id}（{build.name_zh}），{_attrs_text(run)}", file=out)


def _print_summary(library: ContentLibrary, run: RunState, out: TextIO) -> None:
    _print_header(library, run, out)
    print(f"  {_resources(run)}；目前：{_NODE_TEXT[run.node.kind]}", file=out)
    print("  技能：" + "、".join(_skill_name(library, run, s) for s in run.hero.skills), file=out)
    for plan in run.plan:
        enemies = "、".join(library.unit(t).name_zh for t in plan.enemies)
        mark = "Boss " if plan.boss else ""
        done = "✓" if plan.index <= run.battles_done else " "
        map_name = library.map(plan.map_id).name_zh
        print(f"  {done} 第 {plan.index} 場 {mark}{map_name}（{plan.map_id}）：{enemies}", file=out)


def _record_text(library: ContentLibrary, record: BattleRecord) -> str:
    title = "Boss 戰" if record.boss else f"第 {record.index} 場"
    outcome = "勝利" if record.won else f"失敗（{record.end_reason}）"
    downed = "（主角曾倒下）" if record.hero_downed else ""
    return (
        f"{title} {library.map(record.map_id).name_zh}：{outcome}，{record.rounds} 輪 "
        f"{record.steps} 步；HP {record.hp} 法力 {record.mana} 源力 {record.source}{downed}"
    )


def _print_node(library: ContentLibrary, before: RunState, after: RunState, out: TextIO) -> None:
    """一個節點完成後的一行（或幾行）進度。"""
    node = before.node
    if isinstance(node, BattleNode):
        level = f"；等級 {after.level} 經驗 {after.xp}" if after.history[-1].won else ""
        print(f"  {_record_text(library, after.history[-1])}{level}", file=out)
    elif isinstance(node, LevelUpNode):
        gained = [
            f"{a.display_name}+{after.hero.attributes[a] - before.hero.attributes[a]}"
            for a in Attribute
            if after.hero.attributes[a] != before.hero.attributes[a]
        ]
        print(
            f"    升級 Lv{node.level}：{' '.join(gained)}；{_skill_change(library, before, after)}",
            file=out,
        )
    elif isinstance(node, CampfireNode) and isinstance(after.node, CampfireNode):
        print(
            f"    營火重骰：{len(after.node.offer.candidates) if after.node.offer else 0} 個候選",
            file=out,
        )
    elif isinstance(node, CampfireNode):
        print(f"    離開營火：{_skill_change(library, before, after)}", file=out)
    if isinstance(after.node, CampfireNode) and not isinstance(node, CampfireNode):
        print(
            f"    營火（第 {after.node.after_battle} 場後）：HP、法力回滿，源力 {after.source}",
            file=out,
        )


def _skill_change(library: ContentLibrary, before: RunState, after: RunState) -> str:
    added = [s for s in after.hero.skills if s not in before.hero.skills]
    removed = [s for s in before.hero.skills if s not in after.hero.skills]
    if not added:
        return "跳過技能"
    text = "選 " + "、".join(_skill_name(library, after, s) for s in added)
    if removed:
        text += "，替換 " + "、".join(_skill_name(library, before, s) for s in removed)
    return text


def _print_result(run: RunState, out: TextIO) -> None:
    victory = getattr(run.node, "victory", False)
    won = sum(1 for r in run.history if r.won)
    result = "勝利" if victory else "失敗"
    print(f"結果：{result}（{won}/{len(run.plan)} 場），{_resources(run)}", file=out)
