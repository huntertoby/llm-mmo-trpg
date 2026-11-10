"""CB-2a 敵人招式數 #149 的模擬報表：比較 A（門檻 11、補招前）、B（門檻 8）、C（門檻 8＋補招）。

走大世界的真實路徑（``prepare_battle``，同 ``scripts/archive/`` 的 ``ashen_waste_sim.py``）：
主角是 8 種 build 的底稿拉到地點建議等級、帶系統傭兵，雙方都由效用 AI 操作。每組用一個 content
目錄跑一次，把統計寫成 JSON；``--report`` 把三組併成 Markdown 摘要表。**只產報表，不調數值。**

用法::

    uv run python scripts/cb2a_sim.py --content .scratch_cb2a/A/content --out a.json
    uv run python scripts/cb2a_sim.py --out c.json
    uv run python scripts/cb2a_sim.py --report A=a.json B=b.json C=c.json

新手戰另用 ``scripts/archive/f4_newbie_sim.py``（要走大地圖），以 ``TRPG_CONTENT_DIR`` 切換內容。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.engine import build_setup
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    BossPhaseChanged,
    EventBase,
    ManeuverRolled,
    RoundStarted,
    StatusSaveRolled,
    TurnStarted,
    UnitAimed,
    UnitDowned,
)
from trpg.engine.events.skills import SkillUsed
from trpg.engine.runner import BattleRun, run_battle
from trpg.shared.types import Team, UnitId
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.clock import day_phase
from trpg.world.party import default_party
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character

NOON = 1_793_592_000
JOBS = 8
GENERAL_SEEDS = 4
ELITE_SEEDS = 5
BOSS_SEEDS = 10
DEMO_SEEDS = 20
MAX_ROUNDS = 30
SHOVE_WINDOW = 8
RARE_CASTS_PER_UNIT = 0.1
BOSS_PHASE_TWO = 2
TIER_SUFFIX = re.compile(r"_t\d+$")
BUILDS = (
    "build_striker",
    "build_fire",
    "build_storm",
    "build_ranged",
    "build_tank",
    "build_guardian",
    "build_healer",
    "build_trapper",
)
PARTIES = {
    "build_tank": ("merc_chiyan", "merc_huichun"),
    "build_guardian": ("merc_chiyan", "merc_huichun"),
    "build_healer": ("merc_chiyan", "merc_chuanyun"),
}
GENERAL_KINDS = ("camp", "ruin", "village")
REGIONS = ("cloud_ridge", "ashen_waste")
BOSSES = (
    ("boss_mist_lock", "cloud_ridge", "cloud_summit", "cloud_summit", 6),
    ("boss_ashen_heart", "ashen_waste", "molten_heart_pit", "molten_heart_pit", 9),
)
SEASON_BOSS_LEVEL = 10
SEASON_BOSS = "rift_shard_lord"
AFFIX_IDS = (
    "regenerating",
    "mist_veiled",
    "heart_linked",
    "berserk",
    "blazing",
    "hard_shelled",
)
DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp", "ruined_fort", "open_plain")

type Job = tuple[str, str, str, str | None, int, str, int, str | None]
"""(類別, 區域, 地點, 戰鬥地圖, 等級, build, 種子, 懸賞 ID 或 ``"season"``)。"""
type DemoJob = tuple[str, int]
type Tally = dict[str, Any]

_LIBRARY: ContentLibrary | None = None


def _init(root: str | None) -> None:
    global _LIBRARY  # noqa: PLW0603
    _LIBRARY = load_library(None if root is None else Path(root))


def _lib() -> ContentLibrary:
    assert _LIBRARY is not None
    return _LIBRARY


def _hero(library: ContentLibrary, build_id: str, level: int) -> tuple[Any, Any]:
    base = next(b.hero for b in library.builds.builds if b.id == build_id)
    grown, skills = grow_enemy(library, base, level)
    return grown.model_copy(update={"max_hp": base.max_hp, "level": 1}), skills


def _encounter(job: Job) -> EncounterResult:
    _category, region, location, battle_map, level, _build, seed, extra = job
    return EncounterResult(
        region=region,
        location=location,
        level=level,
        battle_map=battle_map,
        battle_seed=seed,
        weather="clear",
        day_phase=day_phase(NOON),
        at=NOON,
        bounty=None if extra in (None, "season") else extra,
        season_boss=SEASON_BOSS if extra == "season" else None,
    )


def _character(library: ContentLibrary, job: Job) -> CharacterState:
    region, location, level, build = job[1], job[2], job[4], job[5]
    hero, skills = _hero(library, build, level)
    char = new_character(library, "sim", hero, region=region)
    update: dict[str, Any] = {
        "level": level,
        "mercenaries": PARTIES.get(build, default_party(library)),
        "generated_skills": skills,
        "pending_encounter": _encounter(job),
    }
    if job[7] != "season":
        update["location"] = location
    return char.model_copy(update=update)


def _base_skill(skill_id: str) -> str:
    return TIER_SUFFIX.sub("", skill_id)


def _control_key(team: Team, status: str, ok: bool) -> str:
    return f"{team.value}|{status}|{'ok' if ok else 'fail'}"


def _shove_killed(events: Sequence[EventBase], index: int, target: UnitId) -> bool:
    window = events[index + 1 : index + 1 + SHOVE_WINDOW]
    return any(isinstance(e, UnitDowned) and e.unit_id == target for e in window)


def _maneuver(tally: Tally, run: BattleRun, events: Sequence[EventBase], index: int) -> None:
    event = events[index]
    assert isinstance(event, ManeuverRolled)
    unit = run.state.units[event.attacker_id]
    tally["man"][f"{unit.team.value}|{event.maneuver}|{'ok' if event.success else 'fail'}"] += 1
    if event.maneuver == "shove":
        profile = unit.ai_profile or "default"
        tally["shove"][profile] += 1
        if event.success and _shove_killed(events, index, event.target_id):
            tally["shove_kill"][profile] += 1


def _count_event(tally: Tally, run: BattleRun, events: Sequence[EventBase], index: int) -> None:
    event = events[index]
    if isinstance(event, StatusSaveRolled):
        team = run.state.units[event.attacker_id].team
        tally["save"][_control_key(team, event.status_id, event.applied)] += 1
    elif isinstance(event, ManeuverRolled):
        _maneuver(tally, run, events, index)
    elif isinstance(event, SkillUsed):
        unit = run.state.units[event.unit_id]
        if unit.team is Team.ENEMY:
            tally["cast"][f"{unit.template_id}|{_base_skill(event.skill_id)}"] += 1
    elif isinstance(event, UnitAimed):
        tally["aim"][run.state.units[event.unit_id].team.value] += 1
    elif isinstance(event, TurnStarted):
        unit = run.state.units[event.unit_id]
        tally["turn"][unit.team.value] += 1
        tally["turn_profile"][unit.ai_profile or "default"] += 1


def _empty() -> Tally:
    keys = ("save", "man", "cast", "present", "aim", "turn", "turn_profile", "shove", "shove_kill")
    return {key: Counter[str]() for key in keys}


def _phase_one_rounds(events: Sequence[EventBase], final_round: int) -> tuple[bool, int]:
    current = 0
    for event in events:
        if isinstance(event, RoundStarted):
            current = event.round
        elif isinstance(event, BossPhaseChanged) and event.phase == BOSS_PHASE_TWO:
            return True, current
    return False, final_round


def _tally(category: str, run: BattleRun) -> Tally:
    tally = _empty()
    tally["category"] = category
    tally["won"] = run.state.winner is Team.ALLY
    tally["rounds"] = run.state.round
    for unit in run.state.units.values():
        if unit.team is Team.ENEMY:
            tally["present"][unit.template_id] += 1
    events = list(run.events)
    for index in range(len(events)):
        _count_event(tally, run, events, index)
    if category == "boss_rift_shard_lord":
        reached, rounds = _phase_one_rounds(events, run.state.round)
        tally["phase_one"] = (reached, rounds)
    return tally


def _run_world(job: Job) -> Tally:
    library = _lib()
    prepared = prepare_battle(library, _character(library, job))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    return _tally(job[0], run)


def _run_demo(job: DemoJob) -> Tally:
    library = _lib()
    map_id, seed = job
    encounter = library.map(map_id).encounter
    assert encounter is not None
    setup = build_setup(library, map_id, encounter.allies, encounter.enemies, max_rounds=MAX_ROUNDS)
    return _tally(f"demo_{map_id}", run_battle(setup, seed, UtilityAI(library.ai_profiles)))


def _general_jobs(library: ContentLibrary) -> list[Job]:
    jobs: list[Job] = []
    for region in REGIONS:
        places = library.world_maps[region].location_by_id()
        for entry in library.world_encounters[region].locations:
            place = places[entry.location]
            if entry.elite is not None or place.kind not in GENERAL_KINDS or not place.level_min:
                continue
            maps = place.battle_maps or (None,)
            jobs += [
                (
                    f"general_{region}",
                    region,
                    entry.location,
                    maps[seed % len(maps)],
                    place.level_min,
                    build,
                    seed,
                    None,
                )
                for build in BUILDS
                for seed in range(GENERAL_SEEDS)
            ]
    return jobs


def _elite_jobs(library: ContentLibrary) -> list[Job]:
    season = library.world_season
    assert season is not None
    jobs: list[Job] = []
    for bounty in season.bounties:
        place = library.world_maps[bounty.region].location_by_id()[bounty.location]
        maps = place.battle_maps or (None,)
        jobs += [
            (
                "elite_bounty",
                bounty.region,
                bounty.location,
                maps[seed % len(maps)],
                bounty.level,
                build,
                seed,
                bounty.id,
            )
            for build in BUILDS
            for seed in range(ELITE_SEEDS)
        ]
    return jobs


def _boss_jobs(library: ContentLibrary) -> list[Job]:
    jobs: list[Job] = [
        (label, region, location, battle_map, level, build, seed, None)
        for label, region, location, battle_map, level in BOSSES
        for build in BUILDS
        for seed in range(BOSS_SEEDS)
    ]
    season = library.world_season
    assert season is not None and season.season_boss is not None
    boss = season.season_boss
    jobs += [
        (
            "boss_rift_shard_lord",
            "cloud_ridge",
            "",
            boss.battle_map,
            SEASON_BOSS_LEVEL,
            build,
            seed,
            "season",
        )
        for build in BUILDS
        for seed in range(BOSS_SEEDS)
    ]
    return jobs


def _merge(into: dict[str, Any], tally: Tally) -> None:
    into["n"] += 1
    into["wins"] += int(tally["won"])
    into["rounds"] += tally["rounds"]
    for key in (
        "save",
        "man",
        "cast",
        "present",
        "aim",
        "turn",
        "turn_profile",
        "shove",
        "shove_kill",
    ):
        into[key].update(tally[key])
    if "phase_one" in tally:
        reached, rounds = tally["phase_one"]
        into["phase_one_reached"] = into.get("phase_one_reached", 0) + int(reached)
        into["phase_one_rounds"] = into.get("phase_one_rounds", 0) + rounds


def _bucket() -> dict[str, Any]:
    keys = ("save", "man", "cast", "present", "aim", "turn", "turn_profile", "shove", "shove_kill")
    return {"n": 0, "wins": 0, "rounds": 0} | {k: Counter[str]() for k in keys}


def _simulate(root: str | None, out: Path) -> None:
    _init(root)
    library = _lib()
    world_jobs = [*_general_jobs(library), *_elite_jobs(library), *_boss_jobs(library)]
    demo_jobs: list[DemoJob] = [(m, s) for m in DEMO_MAPS for s in range(DEMO_SEEDS)]
    print(f"世界戰鬥 {len(world_jobs)} 場、示範地圖 {len(demo_jobs)} 場", file=sys.stderr)
    buckets: dict[str, dict[str, Any]] = defaultdict(_bucket)
    with ProcessPoolExecutor(max_workers=JOBS, initializer=_init, initargs=(root,)) as pool:
        for tally in pool.map(_run_world, world_jobs, chunksize=4):
            _merge(buckets[tally["category"]], tally)
        for tally in pool.map(_run_demo, demo_jobs, chunksize=4):
            _merge(buckets[tally["category"]], tally)
    data = {
        cat: {k: dict(v) if isinstance(v, Counter) else v for k, v in b.items()}
        for cat, b in buckets.items()
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _pct(n: int, d: int) -> str:
    return f"{n * 100 / d:.0f}%" if d else "—"


def _row(cells: Iterable[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _sum_counter(data: Mapping[str, Mapping[str, Any]], key: str, *cats: str) -> Counter[str]:
    total: Counter[str] = Counter()
    for cat in cats:
        if cat in data:
            total.update(data[cat][key])
    return total


def _win_cell(bucket: Mapping[str, Any] | None) -> str:
    if bucket is None or not bucket["n"]:
        return "—"
    return f"{_pct(bucket['wins'], bucket['n'])}／{bucket['rounds'] / bucket['n']:.1f}"


def _win_table(groups: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> list[str]:
    cats = sorted({c for data in groups.values() for c in data})
    lines = ["## 勝率／平均輪數", "", _row(["類別", *groups, "場數（C）"])]
    lines.append(_row(["---"] * (len(groups) + 2)))
    for cat in cats:
        cells = [_win_cell(data.get(cat)) for data in groups.values()]
        last = next(reversed(list(groups.values()))).get(cat)
        lines.append(_row([cat, *cells, 0 if last is None else last["n"]]))
    lines += [
        "",
        _row(["碎晶之主第 1 階段（到第 2 階段比例／輪數）", *groups]),
        _row(["---"] * (len(groups) + 1)),
    ]
    cells = []
    for data in groups.values():
        lord = data.get("boss_rift_shard_lord")
        if lord is None or not lord["n"]:
            cells.append("—")
            continue
        reached = lord.get("phase_one_reached", 0)
        rounds = lord.get("phase_one_rounds", 0) / lord["n"]
        cells.append(f"{_pct(reached, lord['n'])}／{rounds:.1f}")
    lines.append(_row(["全部 build", *cells]))
    return lines


def _rate_counts(counter: Counter[str], prefix: str) -> tuple[int, int]:
    ok = sum(v for k, v in counter.items() if k.startswith(prefix) and k.endswith("|ok"))
    fail = sum(v for k, v in counter.items() if k.startswith(prefix) and k.endswith("|fail"))
    return ok + fail, ok


def _control_table(
    groups: Mapping[str, Mapping[str, Mapping[str, Any]]], cats: Sequence[str]
) -> list[str]:
    lines = ["## 控制與推擠成功率（發動次數／成功率）", ""]
    header = _row(["項目", *groups])
    lines += [header, _row(["---"] * (len(groups) + 1))]
    labels: list[tuple[str, str, str]] = [
        ("控制對抗：敵打我", "save", "enemy|"),
        ("控制對抗：我打敵", "save", "ally|"),
        ("推擊 shove：敵打我", "man", "enemy|shove|"),
        ("推擊 shove：我打敵", "man", "ally|shove|"),
        ("絆倒 trip：敵打我", "man", "enemy|trip|"),
        ("絆倒 trip：我打敵", "man", "ally|trip|"),
        ("擊倒 knock_prone：敵打我", "man", "enemy|knock_prone|"),
        ("擊倒 knock_prone：我打敵", "man", "ally|knock_prone|"),
        ("傳送 teleport：我打敵", "man", "ally|teleport|"),
    ]
    for label, key, prefix in labels:
        cells = []
        for data in groups.values():
            total, ok = _rate_counts(_sum_counter(data, key, *cats), prefix)
            cells.append(f"{total}／{_pct(ok, total)}")
        lines.append(_row([label, *cells]))
    return lines


def _unit_matches(template_id: str, unit: str) -> bool:
    """``unit`` 是範本 ID（帶或不帶詞綴字尾）或 ``*_詞綴``（任何帶那個詞綴的單位）。"""
    if unit.startswith("*_"):
        return template_id.endswith(unit[1:])
    return template_id == unit or any(template_id == f"{unit}_{a}" for a in AFFIX_IDS)


def _cast_table(
    data: Mapping[str, Mapping[str, Any]], cats: Sequence[str], added: Sequence[tuple[str, str]]
) -> list[str]:
    casts = _sum_counter(data, "cast", *cats)
    present = _sum_counter(data, "present", *cats)
    lines = [
        "## C 組：補上的招的施放次數",
        "",
        _row(["敵人", "招", "出場單位數", "施放次數", "每單位每場"]),
    ]
    lines.append(_row(["---"] * 5))
    rare: list[str] = []
    for unit, skill in added:
        units = sum(v for k, v in present.items() if _unit_matches(k, unit))
        cast = sum(
            v
            for k, v in casts.items()
            if _unit_matches(k.split("|")[0], unit) and k.endswith(f"|{skill}")
        )
        rate = cast / units if units else 0
        mark = "⚠" if units and rate < RARE_CASTS_PER_UNIT else ""
        lines.append(_row([unit, skill, units, cast, f"{rate:.2f}{mark}"]))
        if units and rate < RARE_CASTS_PER_UNIT:
            rare.append(f"{unit}/{skill}")
    lines += ["", f"幾乎不施放（每單位每場 < {RARE_CASTS_PER_UNIT}）：" + ("、".join(rare) or "無")]
    return lines


def _ai_table(
    groups: Mapping[str, Mapping[str, Mapping[str, Any]]], cats: Sequence[str]
) -> list[str]:
    lines = [
        "## AI 訊號（示範地圖合計）",
        "",
        _row(["項目", *groups]),
        _row(["---"] * (len(groups) + 1)),
    ]
    for team, label in (("ally", "我方"), ("enemy", "敵方")):
        cells = []
        for data in groups.values():
            aim = _sum_counter(data, "aim", *cats)[team]
            turns = _sum_counter(data, "turn", *cats)[team]
            cells.append(f"{aim}／{_pct(aim, turns)}（每回合）")
        lines.append(_row([f"瞄準：{label}", *cells]))
    profiles = sorted({p for data in groups.values() for p in _sum_counter(data, "shove", *cats)})
    for profile in profiles:
        cells = []
        for data in groups.values():
            shove = _sum_counter(data, "shove", *cats)[profile]
            kill = _sum_counter(data, "shove_kill", *cats)[profile]
            turns = _sum_counter(data, "turn_profile", *cats)[profile]
            cells.append(f"{shove}（{_pct(shove, turns)} 回合）／致死 {kill}")
        lines.append(_row([f"推擊：{profile}", *cells]))
    return lines


def _report(specs: Sequence[str], added_path: Path | None) -> None:
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for spec in specs:
        label, path = spec.split("=", 1)
        groups[label] = json.loads(Path(path).read_text(encoding="utf-8"))
    world = [c for c in next(iter(groups.values())) if not c.startswith("demo_")]
    demos = [c for c in next(iter(groups.values())) if c.startswith("demo_")]
    lines = [*_win_table(groups), "", *_control_table(groups, world), "", *_ai_table(groups, demos)]
    if added_path is not None:
        added = [tuple(x) for x in json.loads(added_path.read_text(encoding="utf-8"))]
        lines += ["", *_cast_table(groups[list(groups)[-1]], [*world, *demos], added)]
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content", default=None, help="content 目錄；省略用專案內建")
    parser.add_argument("--out", type=Path, default=None, help="統計 JSON 輸出路徑")
    parser.add_argument("--report", nargs="+", default=None, help="組名=JSON，依序併成報表")
    parser.add_argument("--added", type=Path, default=None, help="（敵人, 招）清單 JSON")
    args = parser.parse_args()
    if args.report is not None:
        _report(args.report, args.added)
        return
    if args.out is None:
        parser.error("--out 必填")
    _simulate(args.content, args.out)


if __name__ == "__main__":
    main()
