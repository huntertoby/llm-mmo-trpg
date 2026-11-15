"""挑選模式三選一「每格候選數」的統計（Phase PK-3；不請 LLM、不跑戰鬥）。

固定樣本：12 個 build × 種子 0、1 × 升級白板三選一／完整技能三選一＝48 份、144 格，照目前的程式
（``trpg.skillgen.pick_offer.pick_slots``）算每格送給 LLM 的候選數，輸出 JSON：

- 每格候選數分布（1、2、3、4、5 張各幾格）；
- 請 LLM 挑的格子比例（候選至少 ``pool.min_for_llm`` 張的格子）；
- 分數第一名的偏離張數（每份三選一，沒有 LLM 時玩家看到的那一份）。

PK-2 的對照用同一支腳本跑 ``git archive main`` 的程式（``PYTHONPATH=<副本>/src``）。

用法::

    uv run python scripts/pick_slot_stats.py --out docs/phases/PK-3資料/slot_stats.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from trpg.content.library import load_library
from trpg.roguelite import new_run
from trpg.roguelite.offers import _rules, candidate_request, pick_player
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import follows_attr
from trpg.skillgen.pick_offer import pick_slots

BUILDS: tuple[str, ...] = (
    "build_push",
    "build_fire",
    "build_ranged",
    "build_healer",
    "build_storm",
    "build_summoner",
    "build_tank",
    "build_runeweaver",
    "build_assassin",
    "build_trapper",
    "build_seer",
    "build_warlock",
)
SEEDS: tuple[int, ...] = (0, 1)
REASONS: tuple[str, ...] = ("level_up", "complete")


def collect() -> dict[str, Any]:
    lib = load_library()
    rules = _rules(lib.roguelite.candidates, 0)
    rows: list[dict[str, Any]] = []
    for build in BUILDS:
        for seed in SEEDS:
            run = new_run(lib, build, seed)
            request = candidate_request(lib, run)
            top = top_attribute(run.hero.attributes)
            for reason in REASONS:
                start = time.perf_counter()
                slots = pick_slots(
                    lib,
                    request,
                    rules,
                    player=pick_player(lib, run),
                    whiteboard=reason == "level_up",
                )
                seconds = round(time.perf_counter() - start, 2)
                firsts = [s.slate.ranked[0].skill for s in slots]
                rows.append(
                    {
                        "build": build,
                        "seed": seed,
                        "reason": reason,
                        "sizes": [len(s.slate.ranked) for s in slots],
                        "kinds": [s.original.kind for s in slots],
                        "off_route_top": sum(
                            not follows_attr(s, top, request.weapon_attrs) for s in firsts
                        ),
                        "seconds": seconds,
                    }
                )
                print(build, seed, reason, rows[-1]["sizes"], seconds, flush=True)
    return {"min_for_llm": lib.skill_pick.pool.min_for_llm, "rows": rows}


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["rows"]
    sizes = [n for r in rows for n in r["sizes"]]
    need = data["min_for_llm"]
    by_reason: dict[str, Any] = {}
    for reason in REASONS:
        part = [n for r in rows if r["reason"] == reason for n in r["sizes"]]
        by_reason[reason] = {
            "slots": len(part),
            "distribution": dict(sorted(Counter(part).items())),
            "ask_llm": sum(n >= need for n in part),
        }
    off = [r["off_route_top"] for r in rows]
    return {
        "offers": len(rows),
        "slots": len(sizes),
        "distribution": dict(sorted(Counter(sizes).items())),
        "ask_llm": sum(n >= need for n in sizes),
        "mean_candidates": round(statistics.fmean(sizes), 2),
        "by_reason": by_reason,
        "off_route_top_mean": round(statistics.fmean(off), 2),
        "off_route_top_max": max(off),
        "seconds_mean": {
            reason: round(statistics.fmean(r["seconds"] for r in rows if r["reason"] == reason), 2)
            for reason in REASONS
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    data = collect()
    data["summary"] = summarize(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(data["summary"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
