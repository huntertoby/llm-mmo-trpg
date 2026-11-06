"""5F-4b：影子循環賽的平衡候選（玩法 PM 2026-11-03 代決；只量不改 content）。

每個候選是一組循環賽規則（``LeagueRules`` 的 ``hp_permille``、``opening_statuses``、
``first_opening_statuses``），用同一批預設 build（``content/builds``，1 級新角色報名，
對戰時照規則拉到等級上限）打 ``--pairs`` 對組合 × 地圖輪替 × 交換先後手，輸出摘要表：

- 平均輪數（目標 ≥ 6）、先手勝率、後手勝率（各 40～60%）、和局率；
- 達標＝平均輪數 ≥ 6 且先手、後手勝率都在 40～60%（勝率＝勝場 ÷ 全部場次）。

用法::

    uv run python scripts/archive/league_balance.py --pairs 30 --jobs 8
    uv run python scripts/archive/league_balance.py --only hp2x_truce --pairs 40

候選照玩法 PM 的順序：先「開場 HP ×2＋第 1 輪不能造成傷害」，不達標再「拉開站位」，最後才
「先手少 1 AP」。第一組已達標，後兩種沒有實作（``LeagueRules`` 已有 ``first_opening_statuses``，
先手少 1 AP 只要加一個 ``ap_penalty: 1`` 的狀態；拉開站位要另加欄位）。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import cache
from typing import NamedTuple

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_season import LeagueRules
from trpg.world.league import (
    LeagueMatchSpec,
    league_rules,
    league_spawns,
    match_seed,
    match_setup,
    match_winner,
    play_match,
)
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import LeagueEntry
from trpg.world.step import new_character

NOW = 1_793_592_000
SEASON_SEED = 20261103
MIN_ROUNDS = 6
WIN_LOW, WIN_HIGH = 40, 60
EXCLUDED = ("build_form_tester", "build_form_tester_2", "build_blank_")


class Candidate(NamedTuple):
    id: str
    label: str
    hp_permille: int
    opening: tuple[str, ...]
    first: tuple[str, ...]


CANDIDATES = (
    Candidate("base", "目前（5F-4）", 1000, (), ()),
    Candidate("truce", "第 1 輪休戰", 1000, ("league_truce",), ()),
    Candidate("hp2x", "HP ×2", 2000, (), ()),
    Candidate("hp2x_truce", "HP ×2＋第 1 輪休戰", 2000, ("league_truce",), ()),
    Candidate("hp3x_truce", "HP ×3＋第 1 輪休戰", 3000, ("league_truce",), ()),
)


class Result(NamedTuple):
    candidate: str
    rounds: int
    first_win: bool
    second_win: bool
    error: str | None


@cache
def _library() -> ContentLibrary:
    return load_library()


def _builds(library: ContentLibrary) -> list[str]:
    return [
        b.id
        for b in library.builds.builds
        if not any(b.id == x or (x.endswith("_") and b.id.startswith(x)) for x in EXCLUDED)
    ]


def _entry(library: ContentLibrary, build: str, account: str) -> LeagueEntry:
    hero = next(b.hero for b in library.builds.builds if b.id == build)
    char = new_character(library, account, hero, region="cloud_ridge")
    return LeagueEntry(
        account=account,
        character_id=account,
        name=build,
        snapshot=shadow_snapshot(char, NOW),
        entered_at=NOW,
    )


def _pairs(builds: Sequence[str], count: int) -> list[tuple[str, str]]:
    """確定性的組合（依序 i、i+k 輪替），不重複。"""
    out: list[tuple[str, str]] = []
    n = len(builds)
    step = 1
    while len(out) < count and step < n:
        for i in range(n):
            pair = (builds[i], builds[(i + step) % n])
            key = tuple(sorted(pair))
            if pair[0] != pair[1] and all(tuple(sorted(p)) != key for p in out):
                out.append(pair)
            if len(out) >= count:
                break
        step += 1
    return out


def _rules(base: LeagueRules, c: Candidate) -> LeagueRules:
    return base.model_copy(
        update={
            "hp_permille": c.hp_permille,
            "opening_statuses": c.opening,
            "first_opening_statuses": c.first,
        }
    )


def _job(args: tuple[Candidate, str, str, str, int]) -> list[Result]:
    c, build_a, build_b, map_id, index = args
    library = _library()
    base = league_rules(library)
    assert base is not None
    rules = _rules(base, c)
    entries = [_entry(library, build_a, "acc_a"), _entry(library, build_b, "acc_b")]
    spawns = league_spawns(library, entries)
    seed = match_seed(SEASON_SEED, build_a, build_b, map_id, index)
    out: list[Result] = []
    for ally in ("acc_a", "acc_b"):
        spec = LeagueMatchSpec(
            id="m0001", a="acc_a", b="acc_b", map=map_id, seed_index=index, seed=seed, ally=ally
        )
        try:
            run = play_match(library, match_setup(library, rules, spawns, spec), seed)
        except Exception as exc:  # 量測腳本：單場出錯記下來、繼續
            out.append(Result(c.id, 0, False, False, f"{type(exc).__name__}: {exc}"))
            continue
        winner = match_winner(run.state, spec)
        out.append(Result(c.id, run.state.round, winner == spec.ally, winner == spec.enemy, None))
    return out


def _row(c: Candidate, results: Sequence[Result]) -> tuple[str, bool]:
    ok = [r for r in results if r.error is None]
    n = len(ok)
    if n == 0:
        return f"| {c.label} | 0 | - | - | - | - | 否 |", False
    rounds = sum(r.rounds for r in ok) / n
    first = sum(r.first_win for r in ok) * 100 / n
    second = sum(r.second_win for r in ok) * 100 / n
    draw = 100 - first - second
    passed = rounds >= MIN_ROUNDS and all(WIN_LOW <= w <= WIN_HIGH for w in (first, second))
    errors = len(results) - n
    err = f"（{errors} 場出錯）" if errors else ""
    line = (
        f"| {c.label} | {n}{err} | {rounds:.1f} | {first:.0f}% | {second:.0f}% | {draw:.0f}% "
        f"| {'是' if passed else '否'} |"
    )
    return line, passed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=int, default=30, help="每個候選幾對組合（每對 2 場）")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--only", default="", help="只跑這些候選（逗號分隔）")
    args = parser.parse_args(argv)
    library = _library()
    base = league_rules(library)
    if base is None:
        print("這一季沒有循環賽", file=sys.stderr)
        return 1
    only = {s for s in args.only.split(",") if s}
    cands = [c for c in CANDIDATES if not only or c.id in only]
    pairs = _pairs(_builds(library), args.pairs)
    jobs = [
        (c, a, b, base.maps[i % len(base.maps)], 0) for c in cands for i, (a, b) in enumerate(pairs)
    ]
    results: dict[str, list[Result]] = {c.id: [] for c in cands}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for chunk in pool.map(_job, jobs, chunksize=2):
            for r in chunk:
                results[r.candidate].append(r)
    print(f"組合 {len(pairs)} 對 × 交換先後手；地圖輪替 {', '.join(base.maps)}")
    print("| 候選 | 場數 | 平均輪數 | 先手勝 | 後手勝 | 和局 | 達標 |")
    print("|---|---|---|---|---|---|---|")
    for c in cands:
        line, _ = _row(c, results[c.id])
        print(line)
    for c in cands:
        for r in results[c.id]:
            if r.error:
                print(f"[{c.id}] {r.error}", file=sys.stderr)
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
