"""近戰能否摸到 Boss（BAL-8b；只量不調）。

用法::

    uv run python scripts/bal8b_melee_boss.py --jobs 8 --out docs/phases/BAL-8b/melee.md

在 bandit_lair（Boss 戰，無召喚）上，對每個 build 跑 N 場，用 ``on_step`` 取樣：

- 第一次與 Boss 相鄰（曼哈頓 1）的輪數（沒摸到 ＝ 不計入平均，另列「沒摸到的場數」）；
- 英雄存活且 Boss 存活的輪中，有相鄰的輪數比例；
- 英雄回合開始時沒有與 Boss 相鄰，且本回合移動力走不到任何 Boss 相鄰格的回合，依原因分類：
  「護衛擋住」（把非 Boss 敵人移除後就走得到）、「太遠／地形」（移除後仍走不到）；
- 英雄打到 Boss 的傷害占 Boss 受到的總傷害的比例。
"""

from __future__ import annotations

import argparse
import dataclasses
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from bal9_sweep import with_boss_approach  # type: ignore[import-not-found]
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import DamageDealt, TurnStarted
from trpg.engine.rules.geometry import manhattan, neighbors4
from trpg.engine.rules.movement import path_map
from trpg.engine.runner import run_battle
from trpg.engine.state import BattleState
from trpg.shared.types import UnitId
from trpg.sim.batch import BatchSpec
from trpg.sim.matrix import matrix_specs

MAP_ID = "bandit_lair"
LATE_ROUND = 3
"""第 3 輪起算「接近完成後」：前兩輪多半還在趕路。"""
WHITE_MELEE = ("build_blank_warrior", "build_blank_axe", "build_blank_spear", "build_blank_hammer")
SKILL_MELEE = ("build_tank", "build_charger", "build_push", "build_assassin")
RANGED = ("build_blank_crossbow", "build_blank_longgun", "build_ranged")

_CACHE: dict[str, object] = {}


@dataclass
class Sample:
    build: str
    seed: int
    win: bool = False
    rounds: int = 0
    first_adjacent: int | None = None
    live_rounds: set[int] = field(default_factory=set)
    adjacent_rounds: set[int] = field(default_factory=set)
    cats: dict[str, int] = field(default_factory=dict)
    late_cats: dict[str, int] = field(default_factory=dict)
    hero_boss_damage: int = 0
    boss_damage: int = 0


def _setup(build: str, boss_approach: int | None = None) -> BatchSpec:
    """``boss_approach``（BAL-9）：不為 None 時覆寫每個行為模式的 boss_approach（library 副本）。"""
    lib_key = f"lib:{boss_approach}"
    lib = _CACHE.get(lib_key)
    if lib is None:
        lib = load_library()
        if boss_approach is not None:
            lib = with_boss_approach(lib, boss_approach)
        _CACHE[lib_key] = lib
    assert isinstance(lib, ContentLibrary)
    key = f"spec:{build}:{boss_approach}"
    spec = _CACHE.get(key)
    if spec is None:
        spec = matrix_specs(lib, [build], [MAP_ID], [0])[0][2]
        _CACHE[key] = spec
    assert isinstance(spec, BatchSpec)
    return spec


def _without_escorts(state: BattleState, hero_id: UnitId, boss_id: UnitId) -> BattleState:
    units = {
        uid: u
        for uid, u in state.units.items()
        if u.team is state.units[hero_id].team or uid == boss_id or not u.alive
    }
    return dataclasses.replace(state, units=units)


def _turn_category(state: BattleState, hero_id: UnitId, boss_id: UnitId) -> str:
    """英雄回合開始時與 Boss 的關係：adjacent／reachable／escort／far。"""
    hero, boss = state.units[hero_id], state.units[boss_id]
    if manhattan(hero.xy, boss.xy) == 1:
        return "adjacent"
    ring = list(neighbors4(state, boss.xy))
    budget = hero.move_points
    pm = path_map(state, hero, budget)
    if any(pm.can_end_at(xy) for xy in ring):
        return "reachable"
    free = _without_escorts(state, hero_id, boss_id)
    pm2 = path_map(free, free.units[hero_id], budget)
    if any(pm2.can_end_at(xy) for xy in ring):
        return "escort"
    return "far"


def run_sample(task: tuple[str, int, int | None]) -> Sample:
    build, seed, boss_approach = task
    spec = _setup(build, boss_approach)
    sample = Sample(build, seed)
    ids: dict[str, UnitId] = {}

    def on_step(step: object, result: object) -> None:
        state: BattleState = result.state  # type: ignore[attr-defined]
        events = result.events  # type: ignore[attr-defined]
        if not ids:
            boss = next(u for u in state.units.values() if "boss" in u.tags)
            ally = [u for u in state.units.values() if u.team.value == "ally"]
            hero = next((u for u in ally if u.template_id == build), ally[0])
            ids["boss"], ids["hero"] = boss.id, hero.id
        hero, boss = state.units[ids["hero"]], state.units[ids["boss"]]
        r = state.round
        if hero.alive and boss.alive:
            sample.live_rounds.add(r)
            if manhattan(hero.xy, boss.xy) == 1:
                sample.adjacent_rounds.add(r)
                if sample.first_adjacent is None:
                    sample.first_adjacent = r
        for e in events:
            if (
                isinstance(e, TurnStarted)
                and e.unit_id == ids["hero"]
                and hero.alive
                and boss.alive
            ):
                if state.active_unit == ids["hero"]:
                    cat = _turn_category(state, ids["hero"], ids["boss"])
                    sample.cats[cat] = sample.cats.get(cat, 0) + 1
                    if state.round >= LATE_ROUND:
                        sample.late_cats[cat] = sample.late_cats.get(cat, 0) + 1
            elif isinstance(e, DamageDealt) and e.target_id == ids["boss"]:
                sample.boss_damage += e.amount
                if e.source_id == ids["hero"]:
                    sample.hero_boss_damage += e.amount

    run = run_battle(spec.setup, seed, spec.policy_factory(), on_step=on_step, max_actions=20000)
    final = run.state
    sample.rounds = final.round
    boss_alive = any("boss" in u.tags and u.alive for u in final.units.values())
    sample.win = not boss_alive
    return sample


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def summarize(label: str, samples: list[Sample]) -> str:
    n = len(samples)
    firsts = [s.first_adjacent for s in samples if s.first_adjacent is not None]
    live = sum(len(s.live_rounds) for s in samples)
    adj = sum(len(s.adjacent_rounds) for s in samples)
    tot_boss = sum(s.boss_damage for s in samples)
    hero_boss = sum(s.hero_boss_damage for s in samples)

    def pct(a: float, b: float) -> str:
        return f"{100.0 * a / b:.1f}%" if b else "—"

    def cat_cells(attr: str) -> str:
        counts = [getattr(s, attr) for s in samples]
        total = sum(sum(c.values()) for c in counts)
        return " | ".join(
            pct(sum(c.get(k, 0) for c in counts), total)
            for k in ("adjacent", "escort", "far", "reachable")
        )

    return (
        f"| {label} | {n} | {pct(sum(s.win for s in samples), n)} "
        f"| {_mean([s.rounds for s in samples]):.1f} "
        f"| {_mean([float(f) for f in firsts]):.1f}（{n - len(firsts)} 場沒摸到） "
        f"| {pct(adj, live)} | {cat_cells('cats')} | {cat_cells('late_cats')} "
        f"| {pct(hero_boss, tot_boss)} | {hero_boss / n:.1f} |"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--boss-approach", type=int, default=None, help="BAL-9：覆寫 boss_approach 權重")
    args = p.parse_args(argv)
    groups = {"白板近戰": WHITE_MELEE, "技能近戰": SKILL_MELEE, "遠程（對照）": RANGED}
    tasks = [
        (b, s, args.boss_approach) for bs in groups.values() for b in bs for s in range(args.seeds)
    ]
    if args.jobs > 1:
        with ProcessPoolExecutor(args.jobs) as ex:
            samples = list(ex.map(run_sample, tasks, chunksize=2))
    else:
        samples = [run_sample(t) for t in tasks]
    header = [
        "| 組別／build | 場數 | Boss 擊殺率 | 平均輪數 | 首次相鄰輪 | 相鄰輪比例 "
        "| 已相鄰 | 護衛擋住 | 太遠／地形 | 走得到 "
        "| 3 輪起已相鄰 | 3 輪起護衛擋住 | 3 輪起太遠／地形 | 3 輪起走得到 "
        "| 英雄傷害占比 | 每場英雄傷害 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines = ["# 近戰能否摸到 Boss（bandit_lair，無召喚）", "", f"每 build {args.seeds} 場。", ""]
    for name, builds in groups.items():
        rows = [s for s in samples if s.build in builds]
        lines += [f"## {name}", "", *header, summarize(f"**{name}合計**", rows)]
        lines += [summarize(b, [s for s in rows if s.build == b]) for b in builds]
        lines.append("")
    text = "\n".join(lines)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
