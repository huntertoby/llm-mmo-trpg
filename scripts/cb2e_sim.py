"""CB-2e（#149）頭目每回合施放率與「會隱蔽的敵人」前後對照的模擬報表。**只產報表，不調數值。**

走大世界的真實路徑（``prepare_battle``，同 ``scripts/cb2a_sim.py``）：主角是 build 底稿拉到地點建議
等級、帶系統傭兵，雙方都由效用 AI 操作。

- ``bosses``：三個頭目各階段各招的每回合施放率（施放次數 ÷ 頭目在該階段的行動回合數）、勝率、輪數、
  分 build 勝場。階段只認頭目本體的 ``BossPhaseChanged``（``cb2a_sim.py`` 把源晶柱的 ``surge``
  也算進碎晶之主第 1 階段，這裡修掉）；頭目回合中途轉階段、且該回合還沒放招時，回合歸到新階段。
- ``conceal``：含會自己隱蔽的單位的戰鬥，逐場輸出結果，供 ``compare`` 同種子前後配對。
- ``compare``：兩份 ``conceal`` 結果的各組勝率對照。

建角、``_BossWatch`` 歸屬規則與 ``bosses`` 的彙總在 :mod:`trpg.sim.boss_probe`（NW-1a 搬去，數值工坊
共用；輸出逐字不變）。

用法::

    uv run python scripts/cb2e_sim.py bosses --out bosses.json
    uv run python scripts/cb2e_sim.py bosses --only rift --seeds 30 --out lord30.json
    uv run python scripts/cb2e_sim.py report bosses.json
    uv run python scripts/cb2e_sim.py conceal --content before/content --out before.json
    uv run python scripts/cb2e_sim.py compare before.json after.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Step
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import TurnStarted
from trpg.engine.events.combat import ReactionTriggered
from trpg.engine.events.skills import SkillUsed
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.sim.boss_probe import BOSS_NAMES, BOSSES, BUILDS, phase_skills, run_boss_probe
from trpg.sim.boss_probe import ProbeJob as Job
from trpg.sim.boss_probe import base_skill as _base_skill
from trpg.sim.boss_probe import character as _character
from trpg.world.battle import prepare_battle

JOBS = 8
LOW_PERMILLE = 100
OK_PERMILLE = 200
WIN_FLOOR_PERCENT = 40
CONCEAL_SKILLS = frozenset(
    {"skill_blink", "skill_mist_shift", "skill_vanish", "skill_flight", "skill_rx_slip_away"}
)
GENERAL_KINDS = ("camp", "ruin", "village")
REGIONS = ("cloud_ridge", "ashen_waste")
CAMP_MIST_VEILED = (
    ("ferry_steps", 9),
    ("ferry_steps", 46),
    ("bamboo_path", 9),
    ("bamboo_path", 46),
    ("rain_terraces", 9),
    ("rain_terraces", 46),
    ("cliff_gang_fort", 94),
    ("cloud_sea_bridge", 8),
    ("cloud_sea_bridge", 9),
    ("winter_lake", 8),
    ("winter_lake", 46),
)
"""雲嶺營地抽到「霧隱的」精英的（地點, 種子）；調查時掃種子 0～149 找到的（共用筆記
「調查-AI隱蔽分數與碎晶之主兩招」）。陣容抽法變了就要重掃；報表的「隱蔽招回合數」為 0 代表失效。"""
TRAITOR_SEEDS = 8
SURGE_SEEDS = 4
BLINK_SEEDS = 2
GROUP_NAMES = {
    "bounty_mist_swordsman": "懸賞霧中劍客",
    "camp_mist_veiled": "營地霧隱精英",
    "wraith_crystal_rift": "裂痕霧魅",
    "molten_wraith_horned_altar": "角魔祭壇熔晶魅",
    "traitor_steward": "叛徒戰（青霧執事，霧隱）",
    "night_wraith_surge": "夜間霧魅增援（有加到霧魅的場次）",
    "ally_blink_builds": "帶 skill_blink 的我方 build",
}


_LIBRARY: ContentLibrary | None = None


def _init(root: str | None) -> None:
    global _LIBRARY  # noqa: PLW0603
    _LIBRARY = load_library(None if root is None else Path(root))


def _lib() -> ContentLibrary:
    assert _LIBRARY is not None
    return _LIBRARY


# ---------------------------------------------------------------------------
# bosses：各階段各招的每回合施放率
# ---------------------------------------------------------------------------


def _mark(casts: int, turns: int) -> str:
    if not turns:
        return "—"
    permille = casts * 1000 // turns
    text = f"{casts * 100 / turns:.0f}%"
    if permille < LOW_PERMILLE:
        return f"**{text}（< 10%）**"
    if permille < OK_PERMILLE:
        return f"{text}（10～20%）"
    return text


def _row(cells: list[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _boss_report(library: ContentLibrary, which: str, tally: Counter[str]) -> list[str]:
    n = tally["n"]
    lines = [
        f"### {BOSS_NAMES[which]}（{n} 場；勝率 {tally['win'] * 100 / n:.0f}%、"
        f"平均 {tally['rounds'] / n:.1f} 輪）",
        "",
        _row(["階段（進入場數／平均進入輪；頭目行動回合數）", "招", "次數", "每回合施放率"]),
        _row(["---"] * 4),
    ]
    for phase, skills in phase_skills(library, which):
        turns = tally[f"turn|{phase}"]
        reach = n if phase == 1 else tally[f"reach|{phase}"]
        entered = f"{tally[f'reach_round|{phase}'] / reach:.1f}" if phase > 1 and reach else "—"
        head = f"第 {phase} 階段（{reach}／{entered}；{turns}）"
        for skill in skills:
            casts = tally[f"cast|{phase}|{_base_skill(skill)}"]
            lines.append(_row([head, f"`{_base_skill(skill)}`", casts, _mark(casts, turns)]))
            head = ""
    lines += ["", _row(["build", "勝場", "勝率", "平均輪數"]), _row(["---"] * 4)]
    for build in BUILDS:
        played, wins = tally[f"n|{build}"], tally[f"win|{build}"]
        low = "（< 40%）" if wins * 100 < WIN_FLOOR_PERCENT * played else ""
        rounds = tally[f"rounds|{build}"] / played
        cell = f"{wins * 100 / played:.0f}%{low}"
        lines.append(
            _row([build.removeprefix("build_"), f"{wins}/{played}", cell, f"{rounds:.1f}"])
        )
    lines.append("")
    return lines


def _bosses(root: str | None, out: Path, only: str | None, seeds: int) -> None:
    _init(root)
    library = _lib()
    which = [only] if only is not None else list(BOSSES)
    print(f"頭目戰 {len(which) * len(BUILDS) * seeds} 場", file=sys.stderr)
    data = run_boss_probe(library, root, which, seeds, jobs=JOBS)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    lines: list[str] = []
    for w in which:
        lines += _boss_report(library, w, Counter(data[w]))
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# conceal：會自己隱蔽的單位的戰鬥，逐場結果
# ---------------------------------------------------------------------------


def _place_jobs(
    library: ContentLibrary,
    group: str,
    region: str,
    location: str,
    seeds: list[int],
    *,
    builds: tuple[str, ...] = BUILDS,
    **extra: Any,
) -> list[Job]:
    place = library.world_maps[region].location_by_id()[location]
    maps: tuple[str | None, ...] = place.battle_maps or (None,)
    level = extra.pop("level", None) or place.level_min
    assert level is not None
    return [
        Job(group, region, location, maps[seed % len(maps)], level, build, seed, **extra)
        for seed in seeds
        for build in builds
    ]


def _blink_builds(library: ContentLibrary) -> tuple[str, ...]:
    return tuple(
        b.id
        for b in library.builds.builds
        if any(_base_skill(s) == "skill_blink" for s in b.hero.skills)
    )


def _conceal_jobs(library: ContentLibrary) -> list[Job]:
    season = library.world_season
    assert season is not None
    bounty = next(b for b in season.bounties if b.id == "mist_swordsman")
    ten = list(range(10))
    jobs = _place_jobs(
        library,
        "bounty_mist_swordsman",
        bounty.region,
        bounty.location,
        ten,
        bounty=bounty.id,
        level=bounty.level,
    )
    jobs += _place_jobs(library, "wraith_crystal_rift", "cloud_ridge", "crystal_rift", ten)
    jobs += _place_jobs(library, "molten_wraith_horned_altar", "ashen_waste", "horned_altar", ten)
    for location, seed in CAMP_MIST_VEILED:
        jobs += _place_jobs(library, "camp_mist_veiled", "cloud_ridge", location, [seed])
    jobs += _place_jobs(
        library,
        "traitor_steward",
        "cloud_ridge",
        "mist_temple_gate",
        list(range(TRAITOR_SEEDS)),
        story_flags=("temple_traitor_strikes",),
    )
    blink = _blink_builds(library)
    for region in REGIONS:
        for place in library.world_maps[region].locations:
            if place.kind == "camp" and region == "cloud_ridge":
                jobs += _place_jobs(
                    library,
                    "night_wraith_surge",
                    region,
                    place.id,
                    list(range(SURGE_SEEDS)),
                    night=True,
                    world_flags=("wraiths_surge",),
                )
            if place.kind in GENERAL_KINDS and place.level_min:
                jobs += _place_jobs(
                    library,
                    "ally_blink_builds",
                    region,
                    place.id,
                    list(range(BLINK_SEEDS)),
                    builds=blink,
                )
    return jobs


def _run_conceal(job: Job) -> tuple[str, list[int]]:
    library = _lib()
    prepared = prepare_battle(library, _character(library, job))
    count: Counter[str] = Counter()
    team = Team.ALLY if job.group == "ally_blink_builds" else Team.ENEMY

    def on_step(_step: Step | None, result: ResolveResult) -> None:
        units = result.state.units
        for event in result.events:
            if not isinstance(event, SkillUsed | ReactionTriggered | TurnStarted):
                continue
            unit = units.get(event.unit_id)
            if unit is None or unit.team is not team:
                continue
            if isinstance(event, SkillUsed):
                count["cast"] += _base_skill(event.skill_id) in CONCEAL_SKILLS
            elif isinstance(event, ReactionTriggered):
                count["rx"] += _base_skill(event.reaction) in CONCEAL_SKILLS
            elif any(_base_skill(s) in CONCEAL_SKILLS for s in unit.skills):
                count["turn"] += 1

    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles), on_step=on_step)
    wraith = any(u.template_id.startswith("mist_wraith") for u in run.state.units.values())
    keep = int(job.group != "night_wraith_surge" or wraith)
    key = f"{job.group}|{job.location}|{job.build}|{job.seed}"
    won = int(run.state.winner is Team.ALLY)
    return key, [won, run.state.round, count["cast"], count["turn"], count["rx"], keep]


def _render(path: Path) -> None:
    _init(None)
    data: dict[str, dict[str, int]] = json.loads(path.read_text(encoding="utf-8"))
    lines: list[str] = []
    for which, tally in data.items():
        lines += _boss_report(_lib(), which, Counter(tally))
    print("\n".join(lines))


def _conceal(root: str | None, out: Path) -> None:
    _init(root)
    jobs = _conceal_jobs(_lib())
    print(f"隱蔽相關戰鬥 {len(jobs)} 場", file=sys.stderr)
    results: dict[str, list[int]] = {}
    with ProcessPoolExecutor(max_workers=JOBS, initializer=_init, initargs=(root,)) as pool:
        for key, value in pool.map(_run_conceal, jobs, chunksize=4):
            results[key] = value
    out.write_text(json.dumps(results, indent=0, sort_keys=True), encoding="utf-8")
    print(f"寫出 {out}（{len(results)} 場）", file=sys.stderr)


def _group_totals(results: dict[str, list[int]], keys: set[str]) -> dict[str, Counter[str]]:
    totals: dict[str, Counter[str]] = {}
    for key in sorted(keys):
        won, rounds, cast, turn, _rx, _keep = results[key]
        total = totals.setdefault(key.split("|")[0], Counter())
        total.update({"n": 1, "win": won, "rounds": rounds, "cast": cast, "turn": turn})
    return totals


def _compare(before_path: Path, after_path: Path) -> None:
    before: dict[str, list[int]] = json.loads(before_path.read_text(encoding="utf-8"))
    after: dict[str, list[int]] = json.loads(after_path.read_text(encoding="utf-8"))
    keys = {k for k in before if k in after and before[k][5] and after[k][5]}
    old, new = _group_totals(before, keys), _group_totals(after, keys)
    flipped: Counter[str] = Counter()
    for key in keys:
        flipped[key.split("|")[0]] += before[key][0] != after[key][0]
    header = ["組", "場數", "前：勝率／輪數", "後：勝率／輪數", "變動", "隱蔽招 前→後（次／回合）"]
    lines = [_row(list(header)), _row(["---"] * len(header))]
    for group, name in GROUP_NAMES.items():
        if group not in old:
            continue
        a, b = old[group], new[group]
        n = a["n"]
        delta = (b["win"] - a["win"]) * 100 / n
        lines.append(
            _row(
                [
                    name,
                    n,
                    f"{a['win'] * 100 / n:.1f}%（{a['win']}）／{a['rounds'] / n:.1f}",
                    f"{b['win'] * 100 / n:.1f}%（{b['win']}）／{b['rounds'] / n:.1f}",
                    f"{delta:+.1f}（勝負翻轉 {flipped[group]} 場）",
                    f"{a['cast']}/{a['turn']} → {b['cast']}/{b['turn']}",
                ]
            )
        )
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bosses = sub.add_parser("bosses")
    bosses.add_argument("--content", default=None, help="content 目錄；省略用專案內建")
    bosses.add_argument("--out", type=Path, required=True)
    bosses.add_argument("--only", choices=sorted(BOSSES), default=None)
    bosses.add_argument("--seeds", type=int, default=10, help="每個 build 的種子數")
    conceal = sub.add_parser("conceal")
    conceal.add_argument("--content", default=None)
    conceal.add_argument("--out", type=Path, required=True)
    render = sub.add_parser("report", help="把 bosses 的 JSON 重新印成表（招式組照目前的內容）")
    render.add_argument("json", type=Path)
    compare = sub.add_parser("compare")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    args = parser.parse_args()
    if args.command == "bosses":
        _bosses(args.content, args.out, args.only, args.seeds)
    elif args.command == "report":
        _render(args.json)
    elif args.command == "conceal":
        _conceal(args.content, args.out)
    else:
        _compare(args.before, args.after)


if __name__ == "__main__":
    main()
