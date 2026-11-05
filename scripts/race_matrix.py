"""種族勝率矩陣（Phase 6R-1 B，#138；玩法 PM「種族讓任務過易盤點」第 5 節 B）。只量不調。

走大世界的真實路徑（:func:`trpg.world.battle.prepare_battle`）：每個 **遭遇組合**＝一張實地地圖上的
一隊駐守敵人（雲嶺、灰燼荒原，含新手固定戰、精英巢穴、兩區 Boss 地圖），主角從地圖入口照走路規則
（BFS）走到那一隊 3 格內就地開打（就地切 12×12，同 6C-2）；主角＝build 底稿照敵我同一套成長拉到地點
的建議等級，只換種族；隊友＝預設系統傭兵（沒有種族）。雙方都由效用 AI 操作，輪數上限照世界規則。

- 種族：``races.yaml`` 的 10 族（獸耳族＝``fox``，用正式規則）。
- build：``--builds``（預設 ``build_ranged``、``build_charger``，同 #138 模擬）。
- 場次：每個（種族, 遭遇組合, build）``--seeds`` 場；種子固定（``1000 + i``），結果確定。
- 篩選：先每組 20 場（10 種子 × 2 build）；``--combos`` 只跑指定的（區域:地點:隊伍:種族），用來補到
  60 場。

輸出（Markdown，只有摘要）：區域 × 種族的勝率與主角倒下率、10 族平均、超過平均 +10 個百分點的格；
遭遇組合 × 種族超過該組合平均 +10 的組合（篩選候選）。用法::

    uv run python scripts/race_matrix.py --seeds 10 --jobs 8 --out scratchpad/race/b20.md
    uv run python scripts/race_matrix.py --seeds 30 \
        --combos cloud_ridge:north_slope:north_slope_pack:fox
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.movement import step_cost
from trpg.engine.runner import run_battle
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.leap_check import field_as_battle_map, probe_state
from trpg.sim.parallel import run_tasks
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.common import max_hp
from trpg.world.errors import WorldActionError
from trpg.world.party import default_party
from trpg.world.state import CharacterState, EncounterResult, FieldContact, FieldPos
from trpg.world.step import new_character

REGIONS: Final = ("cloud_ridge", "ashen_waste")
REGION_ZH: Final = {"cloud_ridge": "雲嶺", "ashen_waste": "灰燼荒原"}
DEFAULT_BUILDS: Final = ("build_ranged", "build_charger")
NOON: Final = 1_793_592_000
CONTACT_RANGE: Final = 3
FLAG_POINTS: Final = 10
"""超過 10 族平均幾個百分點就標出（盤點第 3 節原則 4）。"""

type Combo = tuple[str, str, int, str]
"""(區域, 地點, 駐守的索引, 隊伍 ID)。"""
type Task = tuple[Combo, str, str, int]
"""(遭遇組合, 種族, build, 種子)。"""


@dataclass(frozen=True, slots=True)
class Sample:
    combo: Combo
    race: str
    build: str
    ok: bool
    won: bool = False
    hero_down: bool = False
    rounds: int = 0


# ---------------------------------------------------------------------------
# 遭遇組合
# ---------------------------------------------------------------------------


def combos(library: ContentLibrary) -> list[Combo]:
    """兩區每張實地地圖上的每一隊駐守（依區域、地點、索引）。"""
    found: list[Combo] = []
    for region in REGIONS:
        places = library.world_maps[region].location_by_id()
        for field in sorted(
            (f for f in library.field_maps.values() if f.region == region), key=lambda f: f.id
        ):
            place = places.get(field.location)
            if place is None or place.level_min is None:
                continue
            found += [(region, field.location, i, s.group) for i, s in enumerate(field.spawns)]
    return found


def _approach(library: ContentLibrary, combo: Combo) -> tuple[XY, XY] | None:
    """從入口照走路規則（BFS，四方向）走到那一隊 ``CONTACT_RANGE`` 格內的第一格與它的前一格。"""
    region, location, index, _group = combo
    field = next(
        f for f in library.field_maps.values() if f.region == region and f.location == location
    )
    target = field.spawns[index].at
    state = probe_state(library, field_as_battle_map(library, field))
    start: XY = (field.entry[0], field.entry[1])
    parent: dict[XY, XY | None] = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if manhattan(cur, (target[0], target[1])) <= CONTACT_RANGE and cur != start:
            prev = parent[cur]
            return cur, prev if prev is not None else cur
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in parent or not state.in_bounds(*nxt) or step_cost(state, cur, nxt) is None:
                continue
            parent[nxt] = cur
            queue.append(nxt)
    return None


_CACHE: dict[object, object] = {}


def _library() -> ContentLibrary:
    if "lib" not in _CACHE:
        _CACHE["lib"] = load_library()
    lib = _CACHE["lib"]
    assert isinstance(lib, ContentLibrary)
    return lib


def _hero_base(library: ContentLibrary, build: str, level: int) -> tuple[object, object]:
    key = ("hero", build, level)
    if key not in _CACHE:
        base = next(b.hero for b in library.builds.builds if b.id == build)
        grown, skills = grow_enemy(library, base, level)
        _CACHE[key] = (grown.model_copy(update={"max_hp": base.max_hp, "level": 1}), skills)
    return _CACHE[key]  # type: ignore[return-value]


def make_char(library: ContentLibrary, task: Task) -> CharacterState | None:
    combo, race, build, seed = task
    region, location, index, group = combo
    place = library.world_maps[region].location_by_id()[location]
    assert place.level_min is not None
    level = place.level_min
    key = ("approach", combo)
    if key not in _CACHE:
        _CACHE[key] = _approach(library, combo)
    way = _CACHE[key]
    if way is None:
        return None
    (cx, cy), came_from = way  # type: ignore[misc]
    hero, skills = _hero_base(library, build, level)
    hero = hero.model_copy(update={"race": race})  # type: ignore[attr-defined]
    char = new_character(library, "sim", hero, region=region)  # type: ignore[arg-type]
    field = next(
        f for f in library.field_maps.values() if f.region == region and f.location == location
    )
    spawn = field.spawns[index]
    contact = FieldContact(
        map=field.id,
        spawn=index,
        group=group,
        lineup_seed=seed,
        x=cx,
        y=cy,
        first=None,
        retreat_to=FieldPos(map=field.id, x=field.entry[0], y=field.entry[1]),
        came_from=came_from,
        enemy_at=(spawn.at[0], spawn.at[1]),
    )
    table = library.world_encounters[region].location_by_id().get(location)
    encounter = EncounterResult(
        region=region,
        location=location,
        level=level,
        battle_map=place.battle_maps[seed % len(place.battle_maps)] if place.battle_maps else None,
        battle_seed=seed,
        weather="clear",
        day_phase="day",
        at=NOON,
        objective=None if table is None else table.objective,
        contact=contact,
    )
    char = char.model_copy(
        update={
            "level": level,
            "location": location,
            "mercenaries": default_party(library),
            "generated_skills": skills,
            "pending_encounter": encounter,
        }
    )
    return char.model_copy(update={"hp": max_hp(library, char)})


def work(_ctx: None, task: Task) -> Sample:
    combo, race, build, _seed = task
    library = _library()
    try:
        char = make_char(library, task)
        if char is None:
            return Sample(combo, race, build, ok=False)
        prepared = prepare_battle(library, char)
        run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    except (TrpgError, WorldActionError, KeyError, ValueError, IndexError):
        return Sample(combo, race, build, ok=False)
    hero = run.state.units_sorted()[0]
    return Sample(
        combo,
        race,
        build,
        ok=True,
        won=run.state.winner is Team.ALLY,
        hero_down=not hero.alive and not hero.escaped,
        rounds=run.state.round,
    )


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _rate(sel: list[Sample]) -> float | None:
    ok = [s for s in sel if s.ok]
    return None if not ok else 100 * statistics.mean(s.won for s in ok)


def _down(sel: list[Sample]) -> float | None:
    ok = [s for s in sel if s.ok]
    return None if not ok else 100 * statistics.mean(s.hero_down for s in ok)


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.0f}%"


def region_table(samples: list[Sample], races: list[str], names: dict[str, str]) -> list[str]:
    head = "| 區域 | " + " | ".join(names.get(r, r) for r in races) + " | 10 族平均 |"
    lines = [head, "|---|" + "---:|" * (len(races) + 1)]
    flagged: list[str] = []
    groups: list[tuple[str, list[Sample]]] = [
        (REGION_ZH[reg], [s for s in samples if s.combo[0] == reg]) for reg in REGIONS
    ]
    groups.append(("全部", samples))
    for label, sel in groups:
        rates = {r: _rate([s for s in sel if s.race == r]) for r in races}
        known = [v for v in rates.values() if v is not None]
        mean = statistics.mean(known) if known else None
        cells = []
        for r in races:
            v = rates[r]
            mark = ""
            if v is not None and mean is not None and v > mean + FLAG_POINTS:
                mark = " ⚠"
                flagged.append(f"{label} {names.get(r, r)} {v:.0f}%（平均 {mean:.0f}%）")
            cells.append(f"{_pct(v)}{mark}")
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {_pct(mean)} |")
    downs = "| 主角倒下率（全部） | " + " | ".join(
        _pct(_down([s for s in samples if s.race == r])) for r in races
    )
    lines.append(downs + " | — |")
    lines.append("")
    lines.append("超過 10 族平均 +10 個百分點：" + ("、".join(flagged) if flagged else "沒有"))
    return lines


def combo_flags(samples: list[Sample], races: list[str], names: dict[str, str]) -> list[str]:
    lines = [
        "| 遭遇組合 | 種族 | 勝率 | 組合平均 | 場數 |",
        "|---|---|---:|---:|---:|",
    ]
    hits = 0
    for combo in sorted({s.combo for s in samples}):
        sel = [s for s in samples if s.combo == combo]
        rates = {r: _rate([s for s in sel if s.race == r]) for r in races}
        known = [v for v in rates.values() if v is not None]
        if not known:
            continue
        mean = statistics.mean(known)
        for r in races:
            v = rates[r]
            if v is not None and v > mean + FLAG_POINTS:
                n = sum(1 for s in sel if s.race == r and s.ok)
                region, location, index, group = combo
                lines.append(
                    f"| `{region}:{location}:{group}`（#{index}） | {names.get(r, r)} | {v:.0f}% | "
                    f"{mean:.0f}% | {n} |"
                )
                hits += 1
    if hits == 0:
        lines.append("| — | — | — | — | — |")
    return lines


def format_report(samples: list[Sample], races: list[str], builds: tuple[str, ...]) -> str:
    library = _library()
    names = {} if library.races is None else {r.id: r.name_zh for r in library.races.races}
    bad = [s for s in samples if not s.ok]
    combos_n = len({s.combo for s in samples})
    per = len(samples) // max(1, combos_n * len(races))
    out = [
        "# 種族勝率矩陣（6R-1 B，腳本輸出）",
        "",
        f"遭遇組合 {combos_n} 個；build：{'、'.join(builds)}；每個（種族, 組合）{per} 場；"
        f"共 {len(samples)} 場，例外 {len(bad)} 場。",
        "",
        "## 區域 × 種族（勝率）",
        "",
        *region_table(samples, races, names),
        "",
        "## 遭遇組合 × 種族：超過組合平均 +10 個百分點（篩選候選）",
        "",
        *combo_flags(samples, races, names),
        "",
    ]
    out += ["## 每個（遭遇組合, 種族）", "", "| 遭遇組合 | 種族 | 勝率 | 主角倒下率 | 場數 |"]
    out.append("|---|---|---:|---:|---:|")
    for combo, race in sorted({(s.combo, s.race) for s in samples}):
        sel = [s for s in samples if s.combo == combo and s.race == race]
        n = sum(1 for s in sel if s.ok)
        out.append(
            f"| `{combo[0]}:{combo[1]}:{combo[3]}` | {names.get(race, race)} | "
            f"{_pct(_rate(sel))} | {_pct(_down(sel))} | {n} |"
        )
    out.append("")
    if bad:
        skipped = sorted({f"{c[0]}:{c[1]}:{c[3]}" for c in (s.combo for s in bad)})
        out += ["例外（切不出戰場或開戰失敗）的組合：" + "、".join(skipped), ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--builds", default=",".join(DEFAULT_BUILDS))
    parser.add_argument("--races", default="")
    parser.add_argument("--combos", default="", help="區域:地點:隊伍:種族，逗號分隔")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    library = _library()
    assert library.races is not None
    races = [r for r in args.races.split(",") if r] or [r.id for r in library.races.races]
    builds = tuple(args.builds.split(","))
    all_combos = combos(library)
    tasks: list[Task] = []
    if args.combos:
        for spec in args.combos.split(","):
            region, location, group, race = spec.split(":")
            for combo in all_combos:
                if combo[0] == region and combo[1] == location and combo[3] == group:
                    tasks += [(combo, race, b, 1000 + i) for b in builds for i in range(args.seeds)]
    else:
        tasks = [
            (combo, race, b, 1000 + i)
            for combo in all_combos
            for race in races
            for b in builds
            for i in range(args.seeds)
        ]
    samples = run_tasks(work, None, tasks, jobs=args.jobs)
    text = format_report(samples, races, builds)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
