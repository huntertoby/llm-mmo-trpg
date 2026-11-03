"""BAL-16b：潮濕 × 治療（#93）前後對照——有治療技能的 build 勝率（只量不調）。

用法::

    uv run python scripts/bal16b_heal.py --normal-seeds 6 --boss-seeds 20 --jobs 6 \\
        --out docs/phases/BAL-16/heal.md

「前」＝ 同一份程式把 ``wet_heal_permille`` 覆寫成 1000（等於 BAL-16b 之前）；「後」＝ content 現況
（1200）。build：具名 build 中英雄或標準隊友以外、英雄自己帶「治療」效果技能的。情境同
``bal15a_resources``：一般戰（每張示範地圖預設陣容）與 Boss 戰（bandit_lair）。
另記我方受到的治療總量，以及其中站在水上（被放大）的部分。
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import Healed
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, UtilityPolicyFactory
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks

BOSS_MAP = "bandit_lair"
MODES = {1000: "前（×1.0）", 1200: "後（×1.2）"}


@dataclass(slots=True)
class Sample:
    mode: int
    build: str
    kind: str
    ok: bool = True
    won: bool = False
    rounds: int = 0
    healed: int = 0
    healed_wet: int = 0
    heals_wet: int = 0


_CACHE: dict[str, object] = {}


def _lib(mode: int) -> ContentLibrary:
    key = f"lib/{mode}"
    if key not in _CACHE:
        base = library_with_builds(load_library())
        core = base.ruleset.core.model_copy(update={"wet_heal_permille": mode})
        ruleset = base.ruleset.model_copy(update={"core": core})
        ruleset.model_post_init(None)
        _CACHE[key] = dataclasses.replace(base, ruleset=ruleset)
    lib = _CACHE[key]
    assert isinstance(lib, ContentLibrary)
    return lib


def _setup(mode: int, build: str, map_id: str) -> BattleSetup:
    key = f"setup/{mode}/{build}/{map_id}"
    if key not in _CACHE:
        lib = _lib(mode)
        enc = lib.map(map_id).encounter
        assert enc is not None
        _CACHE[key] = build_setup(
            lib,
            map_id,
            (build, *lib.builds.companions),
            tuple(enc.enemies),
            max_rounds=DEFAULT_MAX_ROUNDS,
        )
    setup = _CACHE[key]
    assert isinstance(setup, BattleSetup)
    return setup


type Task = tuple[int, str, str, int, str]


def work(_ctx: None, task: Task) -> Sample:
    mode, build, kind, seed, map_id = task
    lib = _lib(mode)
    s = Sample(mode, build, kind)

    def on_step(step: object, result: ResolveResult) -> None:
        for e in result.events:
            if not isinstance(e, Healed):
                continue
            unit = result.state.units.get(e.target_id)
            if unit is None or unit.team is not Team.ALLY:
                continue
            s.healed += e.amount
            if result.state.tile(unit.pos.x, unit.pos.y).surface.value == "water":
                s.healed_wet += e.amount
                s.heals_wet += 1

    try:
        run = run_battle(
            _setup(mode, build, map_id),
            1000 + seed,
            UtilityPolicyFactory(lib.ai_profiles)(),
            on_step=on_step,
        )
    except TrpgError:
        s.ok = False
        return s
    s.won = run.state.winner is Team.ALLY
    s.rounds = run.state.round
    return s


def heal_builds(library: ContentLibrary) -> list[str]:
    out = []
    for b in library.builds.builds:
        if "blank" in b.id or "tester" in b.id or b.id.startswith("build_form"):
            continue
        hero = library.units[b.id]
        if any(
            e.type == "heal" for sid in hero.skills for e in library.ruleset.skill_def(sid).effects
        ):
            out.append(b.id)
    return out


def _row(label: str, sel: list[Sample]) -> str:
    n = len(sel)
    win = 100 * statistics.mean(s.won for s in sel)
    rounds = statistics.mean(s.rounds for s in sel)
    healed = sum(s.healed for s in sel)
    wet = sum(s.healed_wet for s in sel)
    share = 100 * wet / healed if healed else 0.0
    return (
        f"| {label} | {win:.1f}%（n={n}）／{rounds:.2f} | {healed / n:.1f} "
        f"| {wet / n:.1f}（{share:.1f}%） | {sum(s.heals_wet for s in sel) / n:.2f} |"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--normal-seeds", type=int, default=6)
    p.add_argument("--boss-seeds", type=int, default=20)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = library_with_builds(load_library())
    builds = heal_builds(base)
    maps = tuple(default_sim_maps(base))
    tasks: list[Task] = []
    for mode in MODES:
        for b in builds:
            for m in maps:
                tasks += [(mode, b, "normal", sd, m) for sd in range(args.normal_seeds)]
            tasks += [(mode, b, "boss", sd, BOSS_MAP) for sd in range(args.boss_seeds)]
    print(f"任務 {len(tasks)}；build {builds}", file=sys.stderr, flush=True)
    samples = [s for s in run_tasks(work, None, tasks, jobs=args.jobs) if s.ok]
    lines = [
        f"有治療技能的 build {len(builds)} 個：{'、'.join(builds)}；一般戰 {len(maps)} 圖 × "
        f"{args.normal_seeds} 種子、Boss {args.boss_seeds} 種子（同一批種子）",
        "",
        "| 設定 | 勝率／輪數 | 我方受治療／場 | 其中站在水上／場（占比） | 水上治療次數／場 |",
        "|---|---|---|---|---|",
    ]
    for kind, name in (("normal", "一般戰"), ("boss", "Boss 戰")):
        for mode, label in MODES.items():
            sel = [s for s in samples if s.kind == kind and s.mode == mode]
            lines.append(_row(f"{name} {label}", sel))
    lines += ["", "| build | 一般戰 前／後 | Boss 前／後 |", "|---|---|---|"]
    for b in builds:
        cells = []
        for kind in ("normal", "boss"):
            w = [
                100
                * statistics.mean(
                    s.won for s in samples if s.build == b and s.kind == kind and s.mode == m
                )
                for m in MODES
            ]
            cells.append(f"{w[0]:.1f}%／{w[1]:.1f}%")
        lines.append(f"| {b} | {cells[0]} | {cells[1]} |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
