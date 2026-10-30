"""BAL-9c：Boss 戰頭目 HP 700‰ 下，只調弱弓手護衛傷害（弓手護衛專用弓的骰面降階；只在模擬覆寫）。

用法::

    uv run python scripts/bal9c_boss.py --dice 1d8,1d6,1d5,1d4,1d3 --seeds 60 --jobs 8 \
        --out docs/phases/BAL-9c/archer.md [--hp 700] [--approach 10]

每個骰面、每個起始包（有召喚 3 包＋無召喚 3 包）、每個種子一場 Boss 戰。
``--approach`` 覆寫所有行為模式的 ``boss_approach``（-1 ＝ 不改）。
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from bal9_sweep import with_boss_approach, with_boss_hp  # type: ignore[import-not-found]
from bal9b_boss import Rec, run_one, summarize  # type: ignore[import-not-found]
from trpg.content.battle import Dice
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.attrition import PLAIN_PACKS, SUMMON_PACKS
from trpg.sim.parallel import run_tasks

ARCHER = "bandit_archer_guard"


def with_archer_dice(library: ContentLibrary, dice: str) -> ContentLibrary:
    """弓手護衛改用骰面 ``dice`` 的弓複本 ``bow_guard``（其餘不動）。"""
    bow = library.weapons["bow"].model_copy(
        update={"id": "bow_guard", "dice": Dice.model_validate(dice)}
    )
    weapons = {**library.weapons, "bow_guard": bow}
    tpl = library.units[ARCHER].model_copy(update={"weapon": "bow_guard"})
    return dataclasses.replace(library, weapons=weapons, units={**library.units, ARCHER: tpl})


def dead_but_lost(recs: list[Rec]) -> int:
    return sum(1 for r in recs if r.boss_dead_round is not None and not r.win)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dice", default="1d8,1d6,1d5,1d4,1d3")
    p.add_argument("--hp", type=int, default=700)
    p.add_argument("--approach", type=int, default=-1)
    p.add_argument("--seeds", type=int, default=60)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = with_boss_hp(load_library(), args.hp)
    if args.approach >= 0:
        base = with_boss_approach(base, args.approach)
    dices = args.dice.split(",")
    libs = {i: with_archer_dice(base, d) for i, d in enumerate(dices)}
    tasks = [
        (pack, s, i)
        for i in libs
        for pack in (*SUMMON_PACKS, *PLAIN_PACKS)
        for s in range(args.seed_start, args.seed_start + args.seeds)
    ]
    recs = run_tasks(run_one, libs, tasks, jobs=args.jobs)
    appr = args.approach if args.approach >= 0 else "現況"
    lines = [
        f"頭目 HP {args.hp}‰，boss_approach={appr}，每格每類 {3 * args.seeds} 場",
        "",
        "| 弓手護衛骰面 | 有召喚 勝率／輪數 | 無召喚 勝率／輪數 "
        "| 有召喚 打死頭目仍輸 | 無召喚 打死頭目仍輸 |",
        "|---|---|---|---|---|",
    ]
    for i, d in enumerate(dices):
        s = [r for r in recs if r.mult == i and r.summon]
        pl = [r for r in recs if r.mult == i and not r.summon]
        lines.append(
            f"| {d} | {summarize(s)} | {summarize(pl)} | {dead_but_lost(s)}/{len(s)} "
            f"| {dead_but_lost(pl)}/{len(pl)} |"
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
