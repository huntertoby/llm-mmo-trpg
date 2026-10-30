"""武器與 Boss 公平性量測（BAL-8）：只在記憶體內覆寫，不改 content 預設。

用法::

    uv run python scripts/bal8_measure.py weapons --jobs 8 --out docs/phases/BAL-8/weapons.md
    uv run python scripts/bal8_measure.py b18 --jobs 8 --out docs/phases/BAL-8/b18.md
    uv run python scripts/bal8_measure.py longgun --jobs 8 --out docs/phases/BAL-8/longgun.md
    uv run python scripts/bal8_measure.py boss --jobs 8 --out docs/phases/BAL-8/boss.md
    uv run python scripts/bal8_measure.py cost --jobs 8 --out docs/phases/BAL-8/cost.md

DPR ＝ build 英雄每存活回合打出的**總傷害**（含所有目標，``trpg.sim.metrics``）；
比例 ＝ 對白板戰士（單手劍）的 DPR，目標 75–125%。勝率目標 35–65%。
"""

from __future__ import annotations

import argparse
import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.battle import Dice
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.setup import build_setup
from trpg.sim.attack_flow_report import BUILDS as FLOW_BUILDS
from trpg.sim.baseline import _run_packs
from trpg.sim.batch import BatchSpec, UtilityPolicyFactory, run_outcomes
from trpg.sim.matrix import MatrixReport, library_with_builds, run_matrix

SWORD = "build_blank_warrior"
WIN_LO, WIN_HI = 35.0, 65.0
DPR_LO, DPR_HI = 75.0, 125.0


@dataclass(frozen=True)
class Stat:
    win: float
    dpr: float
    rounds: float
    n: int


def stats(report: MatrixReport) -> dict[str, Stat]:
    out: dict[str, Stat] = {}
    for build in report.builds:
        cells = [c for c in report.cells if c.build_id == build]
        done = sum(c.completed for c in cells)
        wins = sum(c.ally_wins for c in cells)
        out[build] = Stat(
            win=100.0 * wins / done if done else 0.0,
            dpr=sum(c.hero_dpr for c in cells) / len(cells) if cells else 0.0,
            rounds=sum(c.rounds_mean for c in cells) / len(cells) if cells else 0.0,
            n=done,
        )
    return out


def mark_win(v: float) -> str:
    return "✓" if WIN_LO <= v <= WIN_HI else "⚠"


def mark_dpr(v: float) -> str:
    return "✓" if DPR_LO <= v <= DPR_HI else "⚠"


def with_weapon(library: ContentLibrary, weapon_id: str, **update: object) -> ContentLibrary:
    weapons = dict(library.weapons)
    weapons[weapon_id] = weapons[weapon_id].model_copy(update=update)
    return dataclasses.replace(library, weapons=weapons)


def with_weights(library: ContentLibrary, **update: int) -> ContentLibrary:
    table = library.ai_profiles
    profiles = tuple(
        p.model_copy(update={"weights": p.weights.model_copy(update=update)})
        for p in table.profiles
    )
    return dataclasses.replace(library, ai_profiles=table.model_copy(update={"profiles": profiles}))


def seeds_of(n: int) -> list[int]:
    return list(range(n))


def weapon_of(library: ContentLibrary) -> dict[str, str]:
    return {b.id: b.hero.weapon for b in library.builds.builds}


# ---------------------------------------------------------------------------
# 1. 武器表
# ---------------------------------------------------------------------------


def cmd_weapons(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    builds = sorted(b.id for b in library.builds.builds if b.blank)
    report = run_matrix(library, builds, maps, seeds_of(args.seeds), jobs=args.jobs)
    st = stats(report)
    base = st[SWORD].dpr
    wmap = weapon_of(library)
    lines = [
        f"# 武器表（{len(maps)} 圖 × {args.seeds} 種子；每武器 {st[SWORD].n} 場）",
        "",
        "| 武器 | build | 勝率 | 勝率標記 | 輪數 | DPR（總傷害） | DPR／單手劍 | 標記 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for build in sorted(builds, key=lambda b: wmap[b]):
        s = st[build]
        ratio = 100.0 * s.dpr / base
        lines.append(
            f"| {wmap[build]} | {build} | {s.win:.1f}% | {mark_win(s.win)} | {s.rounds:.1f} "
            f"| {s.dpr:.2f} | {ratio:.1f}% | {mark_dpr(ratio)} |"
        )
    lines += ["", f"地圖：{', '.join(maps)}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. B18 雙匕首
# ---------------------------------------------------------------------------

DAGGER = "build_blank_dual_dagger"


def cmd_b18(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    variants: list[tuple[str, dict[str, object]]] = [
        ("現行（1d4×2，背刺每下）", {}),
        ("背刺只加成第一下", {"backstab_first_only": True}),
        ("1d3×2（降一階）", {"dice": Dice(count=1, sides=3)}),
        (
            "背刺只第一下＋1d3×2",
            {"backstab_first_only": True, "dice": Dice(count=1, sides=3)},
        ),
    ]
    lines = [
        f"# B18 雙匕首（{len(maps)} 圖 × {args.seeds} 種子）",
        "",
        "| 變體 | 勝率 | 標記 | DPR | DPR／單手劍 | 標記 | 單手劍勝率／DPR |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, update in variants:
        lib = with_weapon(library, "dual_dagger", **update)
        report = run_matrix(lib, [SWORD, DAGGER], maps, seeds_of(args.seeds), jobs=args.jobs)
        st = stats(report)
        ratio = 100.0 * st[DAGGER].dpr / st[SWORD].dpr
        lines.append(
            f"| {label} | {st[DAGGER].win:.1f}% | {mark_win(st[DAGGER].win)} "
            f"| {st[DAGGER].dpr:.2f} | {ratio:.1f}% | {mark_dpr(ratio)} "
            f"| {st[SWORD].win:.1f}%／{st[SWORD].dpr:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. 火槍保持距離
# ---------------------------------------------------------------------------

LONGGUN = "build_blank_longgun"


def cmd_longgun(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    lines = [
        f"# 火槍「遠距站位」AI 權重（`far_range`；{len(maps)} 圖 × {args.seeds} 種子）",
        "",
        "| far_range | 勝率 | 標記 | 輪數 | DPR | DPR／單手劍 | 標記 | 單手劍勝率／DPR |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for value in args.values:
        lib = with_weights(library, far_range=value)
        report = run_matrix(lib, [SWORD, LONGGUN], maps, seeds_of(args.seeds), jobs=args.jobs)
        st = stats(report)
        ratio = 100.0 * st[LONGGUN].dpr / st[SWORD].dpr
        lines.append(
            f"| {value} | {st[LONGGUN].win:.1f}% | {mark_win(st[LONGGUN].win)} "
            f"| {st[LONGGUN].rounds:.1f} | {st[LONGGUN].dpr:.2f} "
            f"| {ratio:.1f}% | {mark_dpr(ratio)} "
            f"| {st[SWORD].win:.1f}%／{st[SWORD].dpr:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. B7 Boss 公平性
# ---------------------------------------------------------------------------

BOSS_MAP_ID = "bandit_lair"
PLAIN = ("dev_bulwark", "dev_blaze", "dev_hawkeye")
SUMMON = ("dev_spirit", "dev_summoner", "dev_summoner_bone")


def _boss_table(
    title: str, builds: Sequence[str], st: dict[str, Stat], label: Callable[[str], str]
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| build | 武器／流派 | 勝率 | 輪數 | 場數 |",
        "|---|---|---|---|---|",
    ]
    for b in sorted(builds, key=lambda x: -st[x].win):
        lines.append(f"| {b} | {label(b)} | {st[b].win:.1f}% | {st[b].rounds:.1f} | {st[b].n} |")
    lines.append("")
    return lines


def cmd_boss(library: ContentLibrary, args: argparse.Namespace) -> str:
    wmap = weapon_of(library)
    blank = sorted(b.id for b in library.builds.builds if b.blank)
    skilled = sorted(b.id for b in library.builds.sim_builds())
    flow = list(FLOW_BUILDS)
    builds = [*blank, *skilled, *flow]
    report = run_matrix(library, builds, [BOSS_MAP_ID], seeds_of(args.seeds), jobs=args.jobs)
    st = stats(report)
    lines = [f"# B7 Boss 公平性（{BOSS_MAP_ID}，無召喚；每 build {args.seeds} 場）", ""]
    lines += _boss_table(
        "普攻流 vs 技能流", flow, st, lambda b: "普攻流" if "attack" in b else "技能流"
    )
    lines += _boss_table("白板 build（各武器，只有普攻）", blank, st, lambda b: wmap[b])
    lines += _boss_table("技能 build（sim_builds）", skilled, st, lambda b: wmap[b])
    pack_seeds = seeds_of(args.pack_seeds)
    plan = [(p, "boss", s) for p in (*PLAIN, *SUMMON) for s in pack_seeds]
    results = _run_packs(library, plan, args.jobs)
    lines += [
        f"## 一輪 Boss 戰（專屬地圖 boss；起始包 Lv1，每包 {args.pack_seeds} 場）",
        "",
        "| 起始包 | 類型 | 勝率 | 輪數 | 場數 |",
        "|---|---|---|---|---|",
    ]
    kinds = {
        "dev_bulwark": "單手劍普攻為主",
        "dev_blaze": "火焰法杖技能為主",
        "dev_hawkeye": "遠程（弓）",
        "dev_spirit": "召喚",
        "dev_summoner": "召喚",
        "dev_summoner_bone": "召喚",
    }
    for pack in (*PLAIN, *SUMMON):
        ms = [r.sample.metrics for r in results if r.sample.pack == pack]
        done = [m for m in ms if m is not None]
        wins = sum(1 for m in done if m.result == "ally")
        rounds = sum(m.rounds for m in done) / len(done) if done else 0.0
        win = 100.0 * wins / len(done) if done else 0.0
        lines.append(f"| {pack} | {kinds[pack]} | {win:.1f}% | {rounds:.1f} | {len(done)} |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. B20 代價技 AI
# ---------------------------------------------------------------------------


def _with_self_cost(library: ContentLibrary, **update: int) -> ContentLibrary:
    table = library.ai_profiles
    cost = table.self_cost.model_copy(update=update)
    profiles = tuple(
        p.model_copy(update={"self_cost": p.self_cost.model_copy(update=update)})
        for p in table.profiles
    )
    return dataclasses.replace(
        library, ai_profiles=table.model_copy(update={"profiles": profiles, "self_cost": cost})
    )


def _with_status_value(library: ContentLibrary, status: str, value: int) -> ContentLibrary:
    table = library.ai_profiles
    profiles = tuple(
        p.model_copy(update={"status_values": {**p.status_values, status: value}})
        for p in table.profiles
    )
    return dataclasses.replace(
        library,
        ai_profiles=table.model_copy(
            update={"profiles": profiles, "status_values": {**table.status_values, status: value}}
        ),
    )


@dataclass(frozen=True)
class CostRow:
    label: str
    battles: int
    used_battles: int
    uses: int
    win_all: float
    win_used: float
    win_unused: float


def _cost_specs(
    library: ContentLibrary, hero_id: str, maps: Sequence[str], seeds: Sequence[int]
) -> list[BatchSpec]:
    lib = library_with_builds(library)
    out = []
    for map_id in maps:
        encounter = library.map(map_id).encounter
        assert encounter is not None
        setup = build_setup(
            lib, map_id, (hero_id, *library.builds.companions), encounter.enemies, max_rounds=30
        )
        out.append(
            BatchSpec(
                name=f"{hero_id} × {map_id}",
                setup=setup,
                seeds=tuple(seeds),
                policy_factory=UtilityPolicyFactory(library.ai_profiles),
            )
        )
    return out


def _cost_row(
    label: str,
    library: ContentLibrary,
    hero_id: str,
    skill_id: str,
    *,
    maps: Sequence[str],
    seeds: Sequence[int],
    jobs: int,
) -> CostRow:
    groups = run_outcomes(_cost_specs(library, hero_id, maps, seeds), jobs=jobs)
    done = [o.metrics for g in groups for o in g if o.metrics is not None]
    used = [m for m in done if m.skills.get(skill_id) and m.skills[skill_id].uses > 0]
    unused = [m for m in done if m not in used]

    def win(ms: list) -> float:  # type: ignore[type-arg]
        return 100.0 * sum(1 for m in ms if m.result == "ally") / len(ms) if ms else float("nan")

    uses = sum(m.skills[skill_id].uses for m in used)
    return CostRow(label, len(done), len(used), uses, win(done), win(used), win(unused))


def cmd_cost(library: ContentLibrary, args: argparse.Namespace) -> str:
    maps = default_sim_maps(library)
    seeds = seeds_of(args.seeds)
    builds = {b.id: b for b in library.builds.builds}
    warrior = builds[SWORD].hero
    mage = builds["build_blank_mage"].hero
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
    lib = dataclasses.replace(
        library,
        builds=library.builds.model_copy(
            update={
                "builds": (
                    *library.builds.builds,
                    *(
                        builds[SWORD].model_copy(update={"id": hid, "hero": hero, "blank": False})
                        for hid, hero in heroes.items()
                    ),
                )
            }
        ),
    )
    od, st = "skill_overdraft_strike", "skill_frost_armor_seal"
    no_od = {"overdraft_min_targets": 1}
    no_st = {"stun_hp_below_permille": 1000, "stun_enemy_radius": 99}
    cases = [
        ("cost_base_w", od, "對照：白板戰士（沒帶技能）", lib),
        ("cost_overdraft", od, "透支：現行（波及 ≥ 2 或能擊殺；overdrawn 價值 8）", lib),
        ("cost_overdraft", od, "透支：無條件（min_targets=1）", _with_self_cost(lib, **no_od)),
        (
            "cost_overdraft",
            od,
            "透支：現行條件、overdrawn 價值 4",
            _with_status_value(lib, "overdrawn", 4),
        ),
        (
            "cost_overdraft",
            od,
            "透支：現行條件、overdrawn 價值 2",
            _with_status_value(lib, "overdrawn", 2),
        ),
        (
            "cost_overdraft",
            od,
            "透支：無條件、overdrawn 價值 2",
            _with_status_value(_with_self_cost(lib, **no_od), "overdrawn", 2),
        ),
        ("cost_base_m", st, "對照：白板法師（沒帶技能）", lib),
        ("cost_stun", st, "自暈：現行（HP < 50%、6 格內有敵人；stun 價值 12）", lib),
        ("cost_stun", st, "自暈：無條件", _with_self_cost(lib, **no_st)),
        ("cost_stun", st, "自暈：現行條件、stun 價值 6", _with_status_value(lib, "stun", 6)),
        ("cost_stun", st, "自暈：現行條件、stun 價值 3", _with_status_value(lib, "stun", 3)),
        (
            "cost_stun",
            st,
            "自暈：無條件、stun 價值 3",
            _with_status_value(_with_self_cost(lib, **no_st), "stun", 3),
        ),
    ]
    rows = [
        _cost_row(label, lb, hero, skill, maps=maps, seeds=seeds, jobs=args.jobs)
        for hero, skill, label, lb in cases
    ]
    lines = [
        f"# B20 代價技 AI（{len(maps)} 圖 × {args.seeds} 種子）",
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


def cmd_dice(library: ContentLibrary, args: argparse.Namespace) -> str:
    """武器傷害骰掃描（建議值用；``--weapon`` 對應的白板 build 與單手劍比較）。"""
    maps = default_sim_maps(library)
    build = next(b for b, w in weapon_of(library).items() if w == args.weapon and "blank" in b)
    lines = [
        f"# {args.weapon} 傷害骰掃描（{len(maps)} 圖 × {args.seeds} 種子）",
        "",
        "| 骰 | 勝率 | 標記 | DPR | DPR／單手劍 | 標記 | 單手劍勝率／DPR |",
        "|---|---|---|---|---|---|---|",
    ]
    for text in args.dice:
        count, sides = (int(x) for x in text.split("d"))
        lib = with_weapon(library, args.weapon, dice=Dice(count=count, sides=sides))
        st = stats(run_matrix(lib, [SWORD, build], maps, seeds_of(args.seeds), jobs=args.jobs))
        ratio = 100.0 * st[build].dpr / st[SWORD].dpr
        lines.append(
            f"| {text} | {st[build].win:.1f}% | {mark_win(st[build].win)} | {st[build].dpr:.2f} "
            f"| {ratio:.1f}% | {mark_dpr(ratio)} | {st[SWORD].win:.1f}%／{st[SWORD].dpr:.2f} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", choices=("weapons", "b18", "longgun", "boss", "cost", "dice"))
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--pack-seeds", type=int, default=30)
    parser.add_argument("--values", type=int, nargs="*", default=[0, 12, 24, 40])
    parser.add_argument("--weapon", default="longgun")
    parser.add_argument("--dice", nargs="*", default=["1d12", "1d10", "1d8"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    library = load_library()
    handlers = {
        "weapons": cmd_weapons,
        "b18": cmd_b18,
        "longgun": cmd_longgun,
        "boss": cmd_boss,
        "cost": cmd_cost,
        "dice": cmd_dice,
    }
    text = handlers[args.section](library, args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
