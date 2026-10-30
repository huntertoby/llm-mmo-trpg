"""BAL-8b 套用後的複測（武器勝率／DPR、代價技使用率）；沿用 ``bal8_measure`` 的函式。

用法::

    uv run python scripts/bal8b_measure.py weapons --jobs 8 --out docs/phases/BAL-8b/weapons.md
    uv run python scripts/bal8b_measure.py cost --jobs 8 --out docs/phases/BAL-8b/cost.md

``weapons``：單手劍（基準）、雙匕首、火槍、弩的白板 build，10 圖 × 10 種子 ＝ 每武器 100 場。
``cost``：現行（BAL-8b 後）AI 數值下，透支技與自暈技的使用率與勝率，10 圖 × 20 種子。
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from bal8_measure import (  # type: ignore[import-not-found]
    SWORD,
    _cost_row,
    mark_dpr,
    mark_win,
    seeds_of,
    stats,
    weapon_of,
)
from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.matrix import run_matrix

TARGETS = ("dual_dagger", "longgun", "crossbow")


def cmd_weapons(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    wmap = weapon_of(library)
    builds = [SWORD, *(b for b, w in sorted(wmap.items()) if w in TARGETS and "blank" in b)]
    report = run_matrix(library, builds, maps, seeds_of(args.seeds), jobs=args.jobs)
    st = stats(report)
    base = st[SWORD].dpr
    lines = [
        f"# BAL-8b 武器複測（{len(maps)} 圖 × {args.seeds} 種子；每武器 {st[SWORD].n} 場）",
        "",
        "| 武器 | 勝率 | 標記 | 輪數 | DPR | DPR／單手劍 | 標記 |",
        "|---|---|---|---|---|---|---|",
    ]
    for b in builds:
        s = st[b]
        ratio = 100.0 * s.dpr / base
        lines.append(
            f"| {wmap[b]} | {s.win:.1f}% | {mark_win(s.win)} | {s.rounds:.1f} "
            f"| {s.dpr:.2f} | {ratio:.1f}% | {mark_dpr(ratio)} |"
        )
    lines.append("")
    return "\n".join(lines)


def cmd_cost(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    seeds = seeds_of(args.seeds)
    builds = {b.id: b for b in library.builds.builds}
    warrior, mage = builds[SWORD].hero, builds["build_blank_mage"].hero
    heroes = {
        "cost_base_w": warrior.model_copy(update={"id": "cost_base_w"}),
        "cost_overdraft": warrior.model_copy(
            update={"id": "cost_overdraft", "skills": ["skill_overdraft_strike"]}
        ),
        "cost_base_m": mage.model_copy(update={"id": "cost_base_m"}),
        "cost_stun": mage.model_copy(
            update={"id": "cost_stun", "skills": ["skill_frost_armor_seal"]}
        ),
    }
    extra = tuple(
        builds[SWORD].model_copy(update={"id": hid, "hero": hero, "blank": False})
        for hid, hero in heroes.items()
    )
    lib = dataclasses.replace(
        library,
        builds=library.builds.model_copy(update={"builds": (*library.builds.builds, *extra)}),
    )
    od, st = "skill_overdraft_strike", "skill_frost_armor_seal"
    cases = [
        ("cost_base_w", od, "對照：白板戰士（沒帶技能）"),
        ("cost_overdraft", od, "透支（overdrawn 價值 3）"),
        ("cost_base_m", st, "對照：白板法師（沒帶技能）"),
        ("cost_stun", st, "自暈（自己承受 stun 價值 5）"),
    ]
    rows = [
        _cost_row(label, lib, hero, skill, maps=maps, seeds=seeds, jobs=args.jobs)
        for hero, skill, label in cases
    ]
    lines = [
        f"# BAL-8b 代價技複測（{len(maps)} 圖 × {args.seeds} 種子）",
        "",
        "| 情況 | 場數 | 有使用的場 | 使用率 | 平均次數 | 整體勝率 | 使用的場勝率 | 沒用的場勝率 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        per = r.uses / r.used_battles if r.used_battles else 0.0
        lines.append(
            f"| {r.label} | {r.battles} | {r.used_battles} "
            f"| {100.0 * r.used_battles / r.battles:.1f}% "
            f"| {per:.2f} | {r.win_all:.1f}% | {r.win_used:.1f}% | {r.win_unused:.1f}% |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", choices=("weapons", "cost"))
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    library = load_library()
    text = {"weapons": cmd_weapons, "cost": cmd_cost}[args.section](library, args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
