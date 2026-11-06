"""BAL-16 追加量測：近戰 build 的格擋 vs 還擊（玩法 PM 2026-11-02，BAL-15c 驗收）。

用法::

    uv run python scripts/archive/bal16_block_riposte.py --normal-seeds 3 --boss-seeds 10 --jobs 6 \\
        --out docs/phases/BAL-16/block_riposte.md

近戰武器的具名 build（``bal15a_resources`` 的 ``riposte`` 覆寫：反應技換成「還擊」）各跑兩種設定：

- ``riposte+blockon``（格擋優先，#83 之前的預設）：量 **格擋每次省下的傷害**——英雄受到的傷害事件
  ``block_permille`` ≠ 1000 時，省下 ＝ 未格擋傷害 − 實際傷害（護盾前）。
- ``riposte``（反應技優先，BAL-15c 起的預設）：量 **還擊每次觸發的傷害**——英雄的「還擊」反應觸發後、
  英雄的下一個反應、他人施放技能或回合交接前，英雄造成的傷害（沒命中算 0）。

兩者都另以「英雄存活的輪數」平均（每輪最多一次反應，所以每輪的值是兩者直接可比的量）。
情境同 ``bal15a_resources``：一般戰（每張示範地圖預設陣容）與 Boss 戰（bandit_lair）。
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bal15a_resources import BOSS_MAP, _hero, _lib, _setup  # type: ignore[import-not-found]
from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import (
    DamageDealt,
    ReactionTriggered,
    SkillUsed,
    TurnEnded,
    TurnStarted,
)
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.batch import UtilityPolicyFactory
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks

RIPOSTE = "skill_riposte"
VARIANTS = ("riposte+blockon", "riposte")
PERMILLE = 1000


@dataclass(slots=True)
class Sample:
    variant: str
    build: str
    kind: str
    ok: bool = True
    won: bool = False
    hero_rounds: int = 0
    blocks: int = 0
    block_saved: int = 0
    ripostes: int = 0
    riposte_dmg: int = 0


class Tracker:
    def __init__(self, build: str, sample: Sample) -> None:
        self.build = build
        self.s = sample
        self.rounds: set[int] = set()
        self.open = False

    def __call__(self, step: object, result: ResolveResult) -> None:
        state = result.state
        hero = _hero(state, self.build)
        if hero is None:
            return
        for e in result.events:
            if isinstance(e, ReactionTriggered) and e.unit_id == hero.id:
                self.open = e.reaction == RIPOSTE
                self.s.blocks += e.reaction == "block"
                self.s.ripostes += self.open
            elif isinstance(e, TurnStarted | TurnEnded):
                self.open = False
                if isinstance(e, TurnStarted) and e.unit_id == hero.id:
                    self.rounds.add(state.round)
            elif isinstance(e, SkillUsed) and e.unit_id != hero.id:
                self.open = False
            elif isinstance(e, DamageDealt):
                if e.target_id == hero.id and e.block_permille not in (0, PERMILLE):
                    self.s.block_saved += e.amount * PERMILLE // e.block_permille - e.amount
                if self.open and e.source_id == hero.id:
                    self.s.riposte_dmg += e.amount
        self.s.hero_rounds = len(self.rounds)


type Task = tuple[str, str, str, int, str]


def work(_ctx: None, task: Task) -> Sample:
    variant, build, kind, seed, map_id = task
    lib = _lib(variant)
    s = Sample(variant, build, kind)
    setup = _setup(variant, build, map_id, None)
    try:
        run = run_battle(
            setup, 1000 + seed, UtilityPolicyFactory(lib.ai_profiles)(), on_step=Tracker(build, s)
        )
    except TrpgError:
        s.ok = False
        return s
    s.won = run.state.winner is Team.ALLY
    return s


def melee_builds(library: ContentLibrary) -> list[str]:
    return [
        b.id
        for b in library.builds.builds
        if library.weapons[b.hero.weapon].is_melee
        and "blank" not in b.id
        and "tester" not in b.id
        and not b.id.startswith("build_form")
    ]


def _ratio(a: int, b: int) -> str:
    return "—" if b == 0 else f"{a / b:.2f}"


def table(samples: list[Sample], builds: list[str]) -> list[str]:
    lines = [
        "| build | 情境 | 格擋／場 | 格擋每次省下 | 格擋每輪省下 "
        "| 還擊／場 | 還擊每次傷害 | 還擊每輪傷害 "
        "| 勝率（格擋優先／還擊優先） |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for build in [*builds, "合計"]:
        for kind in ("normal", "boss"):
            sel = [s for s in samples if s.ok and s.kind == kind]
            if build != "合計":
                sel = [s for s in sel if s.build == build]
            blk = [s for s in sel if s.variant == VARIANTS[0]]
            rip = [s for s in sel if s.variant == VARIANTS[1]]
            if not blk or not rip:
                continue
            b_n, b_saved = sum(s.blocks for s in blk), sum(s.block_saved for s in blk)
            r_n, r_dmg = sum(s.ripostes for s in rip), sum(s.riposte_dmg for s in rip)
            b_rounds, r_rounds = sum(s.hero_rounds for s in blk), sum(s.hero_rounds for s in rip)
            win_b = 100 * statistics.mean(s.won for s in blk)
            win_r = 100 * statistics.mean(s.won for s in rip)
            label = "一般" if kind == "normal" else "Boss"
            lines.append(
                f"| {build} | {label} | {b_n / len(blk):.2f} | {_ratio(b_saved, b_n)} "
                f"| {_ratio(b_saved, b_rounds)} | {r_n / len(rip):.2f} | {_ratio(r_dmg, r_n)} "
                f"| {_ratio(r_dmg, r_rounds)} | {win_b:.1f}%／{win_r:.1f}%"
                f"（n={len(blk)}／{len(rip)}） |"
            )
    return lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--normal-seeds", type=int, default=3)
    p.add_argument("--boss-seeds", type=int, default=10)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = library_with_builds(load_library())
    builds = melee_builds(base)
    maps = tuple(default_sim_maps(base))
    tasks: list[Task] = []
    for v in VARIANTS:
        for b in builds:
            for m in maps:
                tasks += [(v, b, "normal", sd, m) for sd in range(args.normal_seeds)]
            tasks += [(v, b, "boss", sd, BOSS_MAP) for sd in range(args.boss_seeds)]
    print(f"任務 {len(tasks)}；build {builds}", file=sys.stderr, flush=True)
    samples = run_tasks(work, None, tasks, jobs=args.jobs)
    counts: dict[str, int] = defaultdict(int)
    for s in samples:
        counts[s.variant] += not s.ok
    lines = [
        f"近戰 build {len(builds)} 個；一般戰 {len(maps)} 圖 × {args.normal_seeds} 種子、"
        f"Boss {args.boss_seeds} 種子；失敗樣本 {dict(counts)}",
        "",
        *table(samples, builds),
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
