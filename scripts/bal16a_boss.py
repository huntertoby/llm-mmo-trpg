"""BAL-16a：Boss 戰「頭目倒下、護衛撤退」（#86）前後對照（只量不調；頭目 HP 維持 content 的 700‰）。

用法::

    uv run python scripts/bal16a_boss.py --seeds 60 --jobs 6 --out docs/phases/BAL-16/boss.md

「前」＝ 同一份程式把 Boss 地圖的 ``leader_retreat`` 關掉（關掉時判定與 BAL-16a 之前完全相同）；
「後」＝ content 現況（開啟）。每個起始包（有召喚 3 包＋無召喚 3 包）、每個種子一場 Boss 戰
（``bal9b_boss.run_one``，與 BAL-9b／9c 同一套跑法與種子）。另記撤退時剩幾名敵人。
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
from dataclasses import dataclass
from pathlib import Path

from bal9b_boss import Rec, run_one, summarize  # type: ignore[import-not-found]
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.attrition import PLAIN_PACKS, SUMMON_PACKS
from trpg.sim.parallel import run_tasks

MODES = {0: "前（無撤退）", 1: "後（頭目倒下即勝）"}


@dataclass
class Out:
    rec: Rec
    enemies_left: int


def with_retreat(library: ContentLibrary, on: bool) -> ContentLibrary:
    map_id = library.roguelite.boss.map
    m = library.maps[map_id]
    objective = m.objective.model_copy(update={"leader_retreat": on})
    maps = {**library.maps, map_id: m.model_copy(update={"objective": objective})}
    return dataclasses.replace(library, maps=maps)


def run_mode(libs: dict[int, ContentLibrary], task: tuple[str, int, int]) -> Out:
    rec = run_one(libs, task)
    return Out(rec, rec.enemies_alive_end)


def dead_but_lost(recs: list[Rec]) -> int:
    return sum(1 for r in recs if r.boss_dead_round is not None and not r.win)


def _row(label: str, outs: list[Out]) -> str:
    recs = [o.rec for o in outs]
    retreat = [o for o in outs if o.rec.win and o.enemies_left > 0]
    left = statistics.mean(o.enemies_left for o in retreat) if retreat else 0.0
    killed = [r for r in recs if r.boss_dead_round is not None]
    kill_round = statistics.mean(r.boss_dead_round for r in killed) if killed else 0.0
    return (
        f"| {label} | {summarize(recs)} | {len(killed)}/{len(recs)}（{kill_round:.1f}） "
        f"| {dead_but_lost(recs)}/{len(recs)} | {len(retreat)}（{left:.1f}） |"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=60)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = load_library()
    libs = {mode: with_retreat(base, bool(mode)) for mode in MODES}
    tasks = [
        (pack, s, mode)
        for mode in MODES
        for pack in (*SUMMON_PACKS, *PLAIN_PACKS)
        for s in range(args.seed_start, args.seed_start + args.seeds)
    ]
    outs = run_tasks(run_mode, libs, tasks, jobs=args.jobs)
    lines = [
        f"Boss 戰，頭目 HP 700‰（content），種子 {args.seed_start}–"
        f"{args.seed_start + args.seeds - 1}，每格 {3 * args.seeds} 場",
        "",
        "| 設定 | 勝率／輪數 | 打死頭目場數（平均輪） | 打死頭目仍輸 | 撤退勝場（平均撤退敵數） |",
        "|---|---|---|---|---|",
    ]
    for summon, name in ((True, "有召喚"), (False, "無召喚")):
        for mode, label in MODES.items():
            sel = [o for o in outs if o.rec.mult == mode and o.rec.summon is summon]
            lines.append(_row(f"{name} {label}", sel))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
