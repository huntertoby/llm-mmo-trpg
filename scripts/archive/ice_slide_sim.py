"""Phase 6E-2：冰面滑倒並滑行（#123）前後對照——冰湖地圖與冰系 build 的勝率（只量不調）。

用法::

    uv run python scripts/archive/ice_slide_sim.py --seeds 60 --jobs 8 --out <報表.md>

「舊」＝ 同一份程式把冰面檢定的 ``slide_max`` 覆寫成 0（等於 #123 之前：每格檢定、失敗倒地停在
那格；AI 也不估滑行代價）；「新」＝ content 現況（3：第一格擲一次、失敗滑行最多 3 格）。
地圖：冰湖（``frozen_lake``，地圖上原本就有冰）與沼澤（``swamp``，冰系技能把水凍成冰）。
build：冰系（``build_storm``、``build_support``、``build_healer``）與兩個對照（``build_tank``、
``build_fire``）。另記每場的冰面檢定次數、滑倒次數（我方／敵方）與滑行格數。
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import CheckRolled, UnitSlid
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.shared.errors import TrpgError
from trpg.shared.types import Surface, Team
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, UtilityPolicyFactory
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks

MAPS = ("frozen_lake", "swamp")
BUILDS = ("build_storm", "build_support", "build_healer", "build_tank", "build_fire")
MODES = {0: "舊（每格檢定、不滑）", 3: "新（滑倒並滑行）"}


@dataclass(slots=True)
class Sample:
    mode: int
    build: str
    map_id: str
    ok: bool = True
    won: bool = False
    rounds: int = 0
    checks: int = 0
    ally_falls: int = 0
    enemy_falls: int = 0
    slid_tiles: int = 0


_CACHE: dict[str, object] = {}


def _lib(mode: int) -> ContentLibrary:
    key = f"lib/{mode}"
    if key not in _CACHE:
        base = library_with_builds(load_library())
        table = base.ruleset.surfaces
        defs = []
        for original in table.surfaces:
            d = original
            check = d.on_enter.check if d.on_enter is not None else None
            if d.id is Surface.ICE and d.on_enter is not None and check is not None:
                on_enter = d.on_enter.model_copy(
                    update={"check": check.model_copy(update={"slide_max": mode})}
                )
                d = d.model_copy(update={"on_enter": on_enter})
            defs.append(d)
        surfaces = table.model_copy(update={"surfaces": tuple(defs)})
        surfaces.model_post_init(None)
        ruleset = base.ruleset.model_copy(update={"surfaces": surfaces})
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


type Task = tuple[int, str, str, int]


def work(_ctx: None, task: Task) -> Sample:
    mode, build, map_id, seed = task
    lib = _lib(mode)
    s = Sample(mode, build, map_id)

    def on_step(step: object, result: ResolveResult) -> None:
        for e in result.events:
            if isinstance(e, UnitSlid):
                s.slid_tiles += len(e.path) - 1
            if not isinstance(e, CheckRolled) or e.reason != "surface:ice":
                continue
            s.checks += 1
            if e.success:
                continue
            unit = result.state.units.get(e.unit_id)
            if unit is not None and unit.team is Team.ALLY:
                s.ally_falls += 1
            else:
                s.enemy_falls += 1

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


def _cell(sel: list[Sample]) -> str:
    if not sel:
        return "—"
    win = 100 * statistics.mean(x.won for x in sel)
    return f"{win:.1f}%"


def _row(label: str, sel: list[Sample]) -> str:
    n = len(sel)
    mean = statistics.mean
    return (
        f"| {label} | {_cell(sel)}（n={n}） | {mean(x.rounds for x in sel):.2f} "
        f"| {mean(x.checks for x in sel):.2f} | {mean(x.ally_falls for x in sel):.2f} "
        f"| {mean(x.enemy_falls for x in sel):.2f} | {mean(x.slid_tiles for x in sel):.2f} |"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=60)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    tasks: list[Task] = [
        (mode, b, m, sd) for mode in MODES for b in BUILDS for m in MAPS for sd in range(args.seeds)
    ]
    print(f"任務 {len(tasks)}", file=sys.stderr, flush=True)
    samples = list(run_tasks(work, None, tasks, jobs=args.jobs))
    errors = sum(not s.ok for s in samples)
    samples = [s for s in samples if s.ok]
    lines = [
        f"地圖 {'、'.join(MAPS)}；build {'、'.join(BUILDS)}；每格 {args.seeds} 種子"
        f"（種子 1000～{999 + args.seeds}，新舊同一批）；例外 {errors} 場",
        "",
        "| 地圖・規則 | 勝率 | 輪數 | 冰面檢定／場 | 我方滑倒／場 | 敵方滑倒／場 | 滑行格數／場 |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in MAPS:
        for mode, label in MODES.items():
            lines.append(
                _row(f"{m} {label}", [s for s in samples if s.map_id == m and s.mode == mode])
            )
    lines += ["", "| build | " + " | ".join(f"{m} 舊／新" for m in MAPS) + " |", "|---|---|---|"]
    for b in BUILDS:
        cells = []
        for m in MAPS:
            old, new = (
                _cell([s for s in samples if s.build == b and s.map_id == m and s.mode == mode])
                for mode in MODES
            )
            cells.append(f"{old}／{new}")
        lines.append(f"| {b} | " + " | ".join(cells) + " |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
