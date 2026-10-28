"""``trpg run``：roguelite 一輪（Phase 3-5a）。

- ``trpg run new --seed N --weapon W --keywords a,b [--attrs str=2,con=2] [--save-dir D]``：開新一輪
  並存檔（Phase 3-24b2；也可用 ``--dev-pack P`` 開發者起始包，或 ``--build X`` 回歸範本）。
- ``trpg run auto --seed N [--weapon W --keywords a,b | --dev-pack P | --build X] [--save]
  [--save-dir D]``：AI 代打整輪（測試與模擬用）；都省略時以種子抽武器與關鍵字。``--from <存檔>``
  從存檔接續（含戰鬥中）。
- ``trpg run show <存檔>``：顯示存檔內容。
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_ZH
from trpg.roguelite import (
    ChoiceError,
    RunError,
    RunSave,
    RunState,
    auto_play,
    load_save,
    new_dev_run,
    new_keyword_run,
    new_run,
    restore_battle,
    write_save,
)
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.save import default_save_dir
from trpg.roguelite.start import default_start, with_race
from trpg.roguelite.state import (
    BattleNode,
    BattleRecord,
    CampfireNode,
    GearOfferNode,
    LevelUpNode,
)
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute

__all__ = [
    "StartArgs",
    "add_run_parser",
    "cmd_run_auto",
    "cmd_run_new",
    "cmd_run_show",
    "parse_attrs",
    "parse_keywords",
    "start_run",
    "start_text",
]

type WithLibrary = Callable[[Callable[[ContentLibrary], int]], int]

_NODE_TEXT = {
    "battle": "戰鬥",
    "gear_offer": "裝備三選一",
    "level_up": "升級",
    "campfire": "營火",
    "ended": "結束",
}


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


def parse_equipment(text: str) -> dict[str, str]:
    """``main_hand=iron_sword,ring_1=ring_a`` → 欄位 → 物品 ID（格式錯誤拋出
    ``argparse.ArgumentTypeError``）。"""
    result: dict[str, str] = {}
    for part in (p.strip() for p in text.split(",") if p.strip()):
        slot, sep, item = part.partition("=")
        if not sep or not slot.strip() or not item.strip():
            raise argparse.ArgumentTypeError(
                f"--test-equipment 格式應為 main_hand=物品ID,ring_1=物品ID，收到 {text!r}"
            )
        result[slot.strip()] = item.strip()
    return result


def parse_keywords(text: str) -> tuple[str, ...]:
    """``ignite,prone`` → 關鍵字 ID。"""
    return tuple(p.strip() for p in text.split(",") if p.strip())


def _add_start_args(parser: argparse.ArgumentParser, *, build_help: str) -> None:
    parser.add_argument("--weapon", default=None, help="起始武器（weapons.yaml 的 ID）")
    parser.add_argument(
        "--keywords", type=parse_keywords, default=None, help="選的關鍵字，例如 ignite,prone"
    )
    parser.add_argument(
        "--dev-pack", default=None, help="開發者起始包（content/dev_starters.yaml）"
    )
    parser.add_argument("--build", default=None, help=build_help)
    parser.add_argument(
        "--race", default=None, help="主角的種族（content/races.yaml 的 ID；省略＝無種族）"
    )


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
    _add_start_args(new, build_help="回歸範本 build（content/sim/builds.yaml；開發用）")
    new.add_argument("--attrs", type=parse_attrs, default=None, help="開局配點，例如 str=2,con=2")
    new.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾（預設 saves/）")
    new.add_argument(
        "--test-mode", action="store_true", help="測試模式：戰後 HP、法力回滿；不計入統計"
    )
    new.add_argument(
        "--test-equipment",
        type=parse_equipment,
        default=None,
        help="測試模式挑的裝備（欄位=物品ID，逗號分隔；需 --test-mode）",
    )
    new.set_defaults(
        func=lambda a: with_library(
            lambda lib: cmd_run_new(
                lib,
                seed=a.seed,
                start=_start_of(a),
                attrs=a.attrs,
                save_dir=_dir(a),
                out=sys.stdout,
            )
        )
    )
    auto = sub.add_parser("auto", help="AI 代打整輪（測試與模擬用）")
    auto.add_argument("--seed", type=_seed, default=None, help="一輪的種子（--from 時省略）")
    _add_start_args(auto, build_help="回歸範本 build（開發用）；開局都省略時以種子抽武器與關鍵字")
    auto.add_argument("--from", dest="from_path", type=Path, default=None, help="從存檔接續")
    auto.add_argument("--save", action="store_true", help="結束後把一輪存檔")
    auto.add_argument("--save-dir", type=Path, default=None, help="存檔資料夾（預設 saves/）")
    auto.set_defaults(func=lambda a: with_library(lambda lib: _auto(lib, a)))
    show = sub.add_parser("show", help="顯示存檔內容")
    show.add_argument("path", type=Path, help="存檔路徑（saves/run-<id>.json）")
    show.set_defaults(
        func=lambda a: with_library(lambda lib: cmd_run_show(lib, a.path, sys.stdout))
    )


@dataclass(frozen=True, slots=True)
class StartArgs:
    """命令列的開局選擇（擇一；都沒有時 ``trpg run auto`` 以種子抽武器與關鍵字）。"""

    weapon: str | None = None
    keywords: tuple[str, ...] | None = None
    dev_pack: str | None = None
    build: str | None = None
    test_mode: bool = False
    test_equipment: Mapping[str, str] | None = None
    race: str | None = None
    """主角的種族（Phase 3R-2，``content/races.yaml``）；省略＝無種族。"""


def _start_of(args: argparse.Namespace) -> StartArgs:
    return StartArgs(
        weapon=args.weapon,
        keywords=args.keywords,
        dev_pack=args.dev_pack,
        build=args.build,
        test_mode=getattr(args, "test_mode", False),
        test_equipment=getattr(args, "test_equipment", None),
        race=getattr(args, "race", None),
    )


def start_run(
    library: ContentLibrary,
    seed: int,
    start: StartArgs,
    attrs: Mapping[Attribute, int] | None = None,
) -> RunState:
    """依命令列的開局選擇開新一輪；選擇不合法時拋出 :class:`RunError`。"""
    return with_race(library, _start_base(library, seed, start, attrs), start.race)


def _start_base(
    library: ContentLibrary,
    seed: int,
    start: StartArgs,
    attrs: Mapping[Attribute, int] | None,
) -> RunState:
    given = [
        start.build is not None,
        start.dev_pack is not None,
        start.weapon is not None or start.keywords is not None,
    ]
    if sum(given) > 1:
        raise ChoiceError("--weapon／--keywords、--dev-pack、--build 只能擇一")
    testing = start.test_mode or bool(start.test_equipment)
    if testing and (start.build is not None or start.dev_pack is not None):
        raise ChoiceError("--test-mode／--test-equipment 只能和 --weapon／--keywords 一起用")
    if start.build is not None:
        return new_run(library, start.build, seed, attrs)
    if start.dev_pack is not None:
        return new_dev_run(library, start.dev_pack, seed, attrs)
    weapon, keywords = default_start(library, seed)
    return new_keyword_run(
        library,
        start.weapon if start.weapon is not None else weapon,
        start.keywords if start.keywords is not None else keywords,
        seed,
        attrs,
        test_mode=start.test_mode,
        test_equipment=start.test_equipment,
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
        start=_start_of(args),
        from_path=args.from_path,
        save_dir=_dir(args) if args.save else None,
    )


def _new_run_id() -> str:
    return secrets.token_hex(4)


def cmd_run_new(
    library: ContentLibrary,
    *,
    seed: int,
    start: StartArgs,
    attrs: Mapping[Attribute, int] | None,
    save_dir: Path,
    out: TextIO,
) -> int:
    try:
        run = start_run(library, seed, start, attrs)
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
    start: StartArgs | None = None,
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
            run = start_run(library, seed, start if start is not None else StartArgs())
            run_id, battle = _new_run_id(), None
        _print_header(library, run, out)
        final, _ = auto_play(
            library, run, battle, on_node=lambda a, b: _print_node(library, a, b, out)
        )
    except RunError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    _print_result(library, final, out)
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
    level = run.skill_levels.get(skill_id, 1)
    return f"{skill.name_zh}（{skill_id}）" + (f" Lv.{level}" if level > 1 else "")


def _resources(library: ContentLibrary, run: RunState) -> str:
    core = library.ruleset.core
    max_hp = run.max_hp_in(core)
    return (
        f"HP {run.hp}/{max_hp} 法力 {run.mana}/{run.max_mana_in(core)}"
        f" 耐力 {run.stamina_in(core)}/{run.max_stamina_in(core)} 源力 {run.source}"
        f" 等級 {run.level} 經驗 {run.xp}"
    )


def start_text(library: ContentLibrary, run: RunState) -> str:
    """開局說明：「單手劍（one_handed_sword）＋點燃、倒地」；開發者起始包附上 ID；以回歸範本開局時為
    build ID 與名稱。"""
    if run.start is None:
        build = library.builds.by_id().get(run.build_id or "")
        return f"{run.build_id}（{build.name_zh if build is not None else '?'}）"
    defs = library.keywords.by_id()
    weapon = library.weapons[run.start.weapon].name_zh
    names = "、".join(defs[k].name_zh for k in run.start.keywords)
    pack = f"〔起始包 {run.start.dev_pack}〕" if run.start.dev_pack else ""
    return f"{weapon}（{run.start.weapon}）＋{names}{pack}"


def _print_header(library: ContentLibrary, run: RunState, out: TextIO) -> None:
    print(f"一輪：種子 {run.seed}，{start_text(library, run)}，{_attrs_text(run)}", file=out)
    if run.test_mode:
        gear = "、".join(f"{s}={i}" for s, i in sorted(run.test_equipment.items())) or "無"
        print(f"  〔測試模式：戰後回滿，不計入統計；挑的裝備：{gear}〕", file=out)


def _print_summary(library: ContentLibrary, run: RunState, out: TextIO) -> None:
    _print_header(library, run, out)
    print(f"  {_resources(library, run)}；目前：{_NODE_TEXT[run.node.kind]}", file=out)
    print("  技能：" + "、".join(_skill_name(library, run, s) for s in run.hero.skills), file=out)
    if run.equipment:
        gear = "、".join(f"{SLOT_ZH[s]}={i.name_zh}" for s, i in run.equipment.items())
        print(f"  裝備：{gear}；背包 {len(run.backpack)} 件", file=out)
    if run.bench:
        print("  備用：" + "、".join(_skill_name(library, run, s) for s in run.bench), file=out)
    if run.skill_points:
        print(f"  未花的技能點：{run.skill_points}", file=out)
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
    elif isinstance(node, GearOfferNode):
        print(f"    {_gear_text(node, before, after)}", file=out)
    elif isinstance(node, LevelUpNode):
        gained = [
            f"{a.display_name}+{after.hero.attributes[a] - before.hero.attributes[a]}"
            for a in Attribute
            if after.hero.attributes[a] != before.hero.attributes[a]
        ]
        raised = [
            f"{_skill_name(library, after, s)}"
            for s in sorted(after.skill_levels)
            if after.skill_levels[s] != before.skill_levels.get(s, 1)
        ]
        spent = f"；技能點升級：{'、'.join(raised)}" if raised else ""
        print(
            f"    升級 Lv{node.level}：{' '.join(gained)}；"
            f"{_skill_change(library, before, after)}{spent}",
            file=out,
        )
        for line in _evolution_lines(library, before, after):
            print(f"      {line}", file=out)
    elif isinstance(node, CampfireNode) and isinstance(after.node, CampfireNode):
        print(
            f"    營火重骰：{len(after.node.offer.candidates) if after.node.offer else 0} 個候選",
            file=out,
        )
    elif isinstance(node, CampfireNode):
        print(f"    離開營火：{_skill_change(library, before, after)}", file=out)
    if isinstance(after.node, CampfireNode) and not isinstance(node, CampfireNode):
        print(
            f"    營火（第 {after.node.after_battle} 場後）：HP、法力、耐力回滿，"
            f"源力 {after.source}",
            file=out,
        )


def _gear_text(node: GearOfferNode, before: RunState, after: RunState) -> str:
    """戰後裝備三選一的一行（Phase 3K-2）：候選與 AI 的選擇。"""
    names = "、".join(i.name_zh for i in node.candidates)
    worn = {i.id for i in before.equipment.values()}
    picked = [i for i in after.equipment.values() if i.id not in worn]
    head = f"裝備三選一（第 {node.after_battle} 場後）：{names}"
    return f"{head} → 換上「{picked[0].name_zh}」" if picked else f"{head} → 跳過"


_BRANCH_TEXT = {"deepen": "加深", "bridge": "橋接", "count": "數量"}


def _evolution_lines(library: ContentLibrary, before: RunState, after: RunState) -> list[str]:
    """這次新增的分歧進化（Phase 3-26b）：「分歧進化：火焰箭 → 灼燃・火焰箭（加深）」。"""
    lines = []
    for evolved in sorted(set(after.evolutions) - set(before.evolutions)):
        record = after.evolutions[evolved]
        branch = _BRANCH_TEXT[record.branch] + ("（退回）" if record.fallback else "")
        lines.append(
            f"分歧進化：{record.base_name_zh} → {_skill_name(library, after, evolved)}（{branch}）"
        )
    return lines


def _skill_change(library: ContentLibrary, before: RunState, after: RunState) -> str:
    evolved = {r.base_id for k, r in after.evolutions.items() if k not in before.evolutions}
    added = [
        s
        for s in after.hero.skills
        if s not in before.hero.skills and after.evolutions.get(s) is None
    ]
    removed = [s for s in before.hero.skills if s not in after.hero.skills and s not in evolved]
    if not added:
        return "跳過技能"
    text = "選 " + "、".join(_skill_name(library, after, s) for s in added)
    if removed:
        text += "，替換 " + "、".join(_skill_name(library, before, s) for s in removed)
    return text


def _print_result(library: ContentLibrary, run: RunState, out: TextIO) -> None:
    victory = getattr(run.node, "victory", False)
    won = sum(1 for r in run.history if r.won)
    result = "勝利" if victory else "失敗"
    print(f"結果：{result}（{won}/{len(run.plan)} 場），{_resources(library, run)}", file=out)
