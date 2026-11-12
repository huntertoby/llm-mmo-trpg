"""OB-6b（#150）：入門配備打新手第 1、2 步，正式配備打第 3 步路上（含雨中梯田巡邏）的小模擬。

走大世界的真實路徑（純函式 :func:`~trpg.world.step.world_step`，不開伺服器、不寫檔）：

1. ``new_character`` 建角（未完成開局，站在霧渡鎮；跳過主城那段，
   同 ``scripts/archive/f4_newbie_sim.py``）→ ``opening_class``（大類）→ 接新手任務。
2. 用入門配備打第 1、2 步：BFS 一次走一格，盡量避開固定戰以外的視野，碰到就打
   （入門期其他敵人看不到，OB-4）；效用 AI 代打主角與隊友。輸了這個人就停（另列，不算第 3 步分母）。
3. 走回霧渡鎮 ``opening_confirm``（Q7 的 4 種正式配備）→ 兩組延後的三選一一律選第 1 張。
4. 第 3 步：從霧渡鎮一路走到雨中梯田固定戰 ``terrace_clash``，**路上碰到的每一場都打**
   （巡邏＋固定戰）；輸了就停。這一步對每個候選內容各跑一次，第 1、2 步只跑一次（候選之間配對）。

種子全部由（格, 第 i 人）決定：``SEED_BASE + 格 × 1000 + i``，當世界種子、開局種子；角色 ID 也由它們
決定。時間固定在 ``NOW``（白天，被清空的隊伍不會重生）。

用法（結果 JSON 放暫存區，不進 repo）::

    uv run python scripts/ob6_newbie_sim.py run --per-cell 2 --out <暫存>/smoke.json
    uv run python scripts/ob6_newbie_sim.py run --candidates current --out <暫存>/current.json
    uv run python scripts/ob6_newbie_sim.py run --candidates current,hp-10,hp-20 --out <暫存>/c.json
    uv run python scripts/ob6_newbie_sim.py report <暫存>/c.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
import time
from collections import Counter, deque
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_quests import WinBattle
from trpg.engine.actions import Step
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.events import UnitDowned
from trpg.engine.events.skills import SkillUsed
from trpg.engine.results import ResolveResult
from trpg.engine.runner import advance
from trpg.roguelite.progress import hero_unit_id
from trpg.shared.types import Team
from trpg.world.actions import (
    AcceptQuestAction,
    FightAction,
    OfferPickAction,
    OpeningClassAction,
    OpeningConfirmAction,
    RetreatAction,
    WorldAction,
)
from trpg.world.battle import prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.field import field_grid, field_map, placed
from trpg.world.field_actions import WalkAction
from trpg.world.field_enemies import field_enemies
from trpg.world.opening import new_opening, pending_hero, range_content
from trpg.world.opening_limits import fight_problem
from trpg.world.season import FIRST_SEASON_ID
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import new_character, world_step

NOW = 1_793_592_000
"""2026-11-02 12:00 台北（同 ``tests/world/helpers.py`` 的 ``NOON``）；整個模擬時間不動。"""
REGION = "cloud_ridge"
QUEST = "starter_ferry"
TOWN = "mist_ferry"
TERRACE = "rain_terraces"
FIXED = "terrace_clash"
PATROL = "terrace_patrol"
SEED_BASE = 60_000
MAX_JOBS = 6
MAX_MOVES = 600
MAX_TOP_UP_ROUNDS = 5
LIMIT_PERCENT = 40
TIER_SUFFIX = re.compile(r"_t\d+$")
FORWARD = {"mist_ferry": "ferry_steps", "ferry_steps": "bamboo_path", "bamboo_path": TERRACE}
BACK = {"bamboo_path": "ferry_steps", "ferry_steps": TOWN}
CELLS: dict[str, tuple[str, str, tuple[str, str]]] = {
    # 格 → （入門大類, 正式選的武器, 關鍵字）：CB-2d 的 4 種開局（對照 42%），Q7
    "火焰法杖 點燃＋帶電": ("focus", "fire_staff", ("ignite", "charged")),
    "匕首 冰凍＋隱蔽": ("melee", "dagger", ("frozen", "concealed")),
    "巨劍 倒地＋撞擊": ("melee", "greatsword", ("prone", "collision")),
    "弓 標記＋高處": ("ranged", "bow", ("marked", "high_ground")),
}
CLASS_NAMES = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}
BASE_UNIT = "sect_acolyte"
TERRACE_UNIT = "sect_acolyte_terrace"
CANDIDATES: dict[str, int | None] = {
    # 候選 → 巡邏兩名 ``sect_acolyte_terrace`` 的 max_hp（``None``＝目前內容，不換）。
    # Q8：不減人、不換結構，只調 HP；``sect_acolyte`` 的 22 × 0.9／0.8／0.7
    # （捨去，同 CB-2d 的 bandit_rookie_terrace）
    "current": None,
    "hp-10": 19,
    "hp-20": 17,
    "hp-30": 15,
}

type XY = tuple[int, int]
type Record = dict[str, Any]


# ---------------------------------------------------------------------------
# 內容
# ---------------------------------------------------------------------------

_LIBS: dict[str, ContentLibrary] = {}


def candidate_library(library: ContentLibrary, hp: int | None) -> ContentLibrary:
    """記憶體裡把 ``terrace_patrol`` 的兩名換成 HP ``hp`` 的 ``sect_acolyte_terrace``（其餘照
    ``sect_acolyte``）；``hp`` 為 ``None`` 時原樣回傳。"""
    if hp is None:
        return library
    unit = library.units[BASE_UNIT].model_copy(update={"id": TERRACE_UNIT, "max_hp": hp})
    table = library.world_encounters[REGION]
    groups = tuple(
        g.model_copy(update={"units": tuple(TERRACE_UNIT for _ in g.units)})
        if g.id == PATROL
        else g
        for g in table.groups
    )
    encounters = {**library.world_encounters, REGION: table.model_copy(update={"groups": groups})}
    return dataclasses.replace(
        library, units={**library.units, TERRACE_UNIT: unit}, world_encounters=encounters
    )


def _init(candidates: tuple[str, ...]) -> None:
    base = load_library()
    _LIBS.clear()
    _LIBS["base"] = base
    for name in candidates:
        _LIBS[name] = candidate_library(base, CANDIDATES[name])


def _fixed_groups(library: ContentLibrary) -> list[tuple[str, str]]:
    """新手任務各步的固定戰（地點, 陣容），讀任務資料。"""
    quest = next(q for q in library.world_quests.quests[REGION].quests if q.id == QUEST)
    found: list[tuple[str, str]] = []
    for step in quest.steps:
        for cond in step.when:
            if isinstance(cond, WinBattle) and cond.location and cond.group:
                found.append((cond.location, cond.group))
    return found


# ---------------------------------------------------------------------------
# 走路與打
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Walker:
    library: ContentLibrary
    world: WorldState
    char: CharacterState

    def act(self, action: WorldAction) -> None:
        result = world_step(self.library, self.world, self.char, action, NOW)
        self.world, self.char = result.world, result.char

    def here(self) -> CharacterState:
        return placed(self.library, self.char)


def _bfs(library: ContentLibrary, char: CharacterState, goals: set[XY], avoid: set[XY]) -> list[XY]:
    assert char.field is not None
    found = field_map(library, char.field.map)
    assert found is not None
    grid = field_grid(library, char, found)
    climb = library.ruleset.core.max_climb_height
    width, height = found.size
    start = (char.field.x, char.field.y)
    prev: dict[XY, XY] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell in goals:
            path = [cell]
            while path[-1] != start:
                path.append(prev[path[-1]])
            return path[::-1][1:]
        x, y = cell
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt in seen or (nxt in avoid and nxt not in goals):
                continue
            if not (0 <= nxt[0] < width and 0 <= nxt[1] < height):
                continue
            if not grid.can_step(cell, nxt, climb):
                continue
            seen.add(nxt)
            prev[nxt] = cell
            queue.append(nxt)
    return []


def _fight(walker: Walker) -> Record:
    """效用 AI 代打目前的遭遇，送 ``fight``；回傳這場的摘要（陣容、勝負、主角倒下、輪數、
    主角用招）。"""
    library, char = walker.library, walker.char
    encounter = char.pending_encounter
    assert encounter is not None
    group = "" if encounter.contact is None else encounter.contact.group
    prepared = prepare_battle(library, char)
    opening = begin_battle(prepared.setup, prepared.seed)
    hero = hero_unit_id(opening.state)
    uses: Counter[str] = Counter()
    downed = False
    steps: list[Step] = []

    def on_step(step: Step | None, result: ResolveResult) -> None:
        nonlocal downed
        assert step is not None
        steps.append(step)
        for event in result.events:
            if isinstance(event, SkillUsed) and event.unit_id == hero:
                uses[TIER_SUFFIX.sub("", event.skill_id)] += 1
            elif isinstance(event, UnitDowned) and event.unit_id == hero:
                downed = True

    policy = CommandedAI(UtilityAI(library.ai_profiles), {})
    state, _pending, _steps = advance(opening.state, opening.pending, policy, on_step=on_step)
    walker.act(FightAction(steps=tuple(steps)))
    down = downed or state.units[hero].hp <= 0
    won = state.winner is Team.ALLY
    return {"group": group, "won": won, "down": down, "rounds": state.round, "uses": dict(uses)}


def _walk_to(
    walker: Walker, route: dict[str, str], goal_map: str, group: str | None
) -> list[Record]:
    """一次走一格：沿 ``route`` 到 ``goal_map``；``group`` 給了就再走進那一隊的視野。路上碰到的遭遇
    都打（入門期不能打的撤退），輸了就停。回傳打過的每一場（最後一場是 ``group`` 或輸掉的那場）。"""
    fights: list[Record] = []
    library = walker.library
    for _ in range(MAX_MOVES):
        char = walker.here()
        assert char.field is not None
        here = char.field.map
        enemies = field_enemies(library, walker.world, char, NOW)
        avoid = {c for e in enemies for c in e.sight if e.spawn.group != group}
        if here == goal_map:
            if group is None:
                return fights
            goals = {c for e in enemies if e.spawn.group == group for c in e.sight}
            if not goals:
                return fights
        else:
            found = field_map(library, here)
            assert found is not None
            goals = {c for e in found.exits if e.to == route[here] for c in e.at}
        path = _bfs(library, char, goals, avoid) or _bfs(library, char, goals, set())
        if not path:
            return fights
        walker.act(WalkAction(path=(path[0],)))
        if walker.char.pending_encounter is None:
            continue
        if fight_problem(library, walker.char) is not None:
            walker.act(RetreatAction())
            continue
        record = _fight(walker)
        fights.append(record)
        if record["group"] == group or not record["won"]:
            return fights
    return fights


def _pick_offers(walker: Walker) -> int:
    """延後的三選一一律選第 1 張（放不下就跳過）；回傳跳過的組數。"""
    skipped = 0
    for _ in range(4):
        if not walker.char.pending_offers:
            break
        try:
            walker.act(OfferPickAction(pick=0))
        except WorldActionError:
            walker.act(OfferPickAction(pick=None))
            skipped += 1
    return skipped


# ---------------------------------------------------------------------------
# 一個人
# ---------------------------------------------------------------------------


def person_seed(cell: int, index: int) -> int:
    return SEED_BASE + cell * 1000 + index


def _new_walker(library: ContentLibrary, cell: int, index: int, cls: str) -> Walker:
    seed = person_seed(cell, index)
    world = WorldState(season_id=FIRST_SEASON_ID, season_seed=seed, season_start=NOW)
    char = new_character(library, f"ob6c{cell}n{index:04d}", pending_hero(library), region=REGION)
    walker = Walker(library, world, char.model_copy(update={"opening": new_opening(seed)}))
    walker.act(OpeningClassAction(weapon_class=cls))  # type: ignore[arg-type]
    walker.act(AcceptQuestAction(quest=QUEST))
    return walker


def _step3(walker: Walker) -> Record:
    fights = _walk_to(walker, FORWARD, TERRACE, FIXED)
    road = [f for f in fights if f["group"] != FIXED]
    fixed = next((f for f in fights if f["group"] == FIXED), None)
    return {
        "down_road": any(f["down"] for f in road),
        "down_patrol": any(f["down"] for f in road if f["group"] == PATROL),
        "down_fixed": fixed is not None and fixed["down"],
        "reached_fixed": fixed is not None,
        "won_fixed": fixed is not None and fixed["won"],
        "rounds_fixed": 0 if fixed is None else fixed["rounds"],
        "road": [[f["group"], int(f["won"]), int(f["down"])] for f in road],
        "level": walker.char.level,
    }


def run_person(job: tuple[int, int, tuple[str, ...]]) -> Record:
    cell, index, candidates = job
    name = list(CELLS)[cell]
    cls, weapon, keywords = CELLS[name]
    library = _LIBS["base"]
    walker = _new_walker(library, cell, index, cls)
    record: Record = {"cell": name, "index": index, "cls": cls, "steps": [], "step3": {}}
    for location, group in _fixed_groups(library)[:2]:
        fights = _walk_to(walker, FORWARD, location, group)
        last = fights[-1] if fights else None
        done = last is not None and last["group"] == group and last["won"]
        record["steps"].append({"location": location, "fights": fights, "done": done})
        if not done:
            return record
    _walk_to(walker, BACK, TOWN, None)
    walker.act(OpeningConfirmAction(weapon=weapon, keywords=keywords))
    record["offers_skipped"] = _pick_offers(walker)
    record["level_at_choice"] = walker.char.level
    for name_c in candidates:
        branch = Walker(_LIBS[name_c], walker.world, walker.char)
        record["step3"][name_c] = _step3(branch)
    return record


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _pct(n: int, d: int) -> str:
    return f"{n}/{d}（{n * 100 / max(1, d):.0f}%）"


def _row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _starter_table(library: ContentLibrary, people: list[Record]) -> list[str]:
    demos = range_content(library).demos
    head = ["大類", "人數", "步", "勝率", "主角倒下", "平均輪數", "入門招每場使用次數"]
    lines = [_row(head), _row(["---"] * len(head))]
    for cls in ("melee", "ranged", "focus"):
        mine = [p for p in people if p["cls"] == cls]
        for number, (place, group) in enumerate(_fixed_groups(library)[:2]):
            fights = [
                f
                for p in mine
                if len(p["steps"]) > number
                for f in p["steps"][number]["fights"]
                if f["group"] == group
            ]
            n = len(fights)
            wins = sum(f["won"] for f in fights)
            down = sum(f["down"] for f in fights)
            rounds = sum(f["rounds"] for f in fights) / max(1, n)
            uses = "、".join(
                f"`{s}` {sum(f['uses'].get(s, 0) for f in fights) / max(1, n):.2f}"
                for s in demos[cls]
            )
            label = f"{CLASS_NAMES[cls]}（{len(mine)}）" if number == 0 else ""
            lines.append(
                _row(
                    [
                        label,
                        n,
                        f"{number + 1} {place}",
                        _pct(wins, n),
                        _pct(down, n),
                        f"{rounds:.1f}",
                        uses,
                    ]
                )
            )
    return lines


def _step3_table(people: list[Record], candidate: str) -> list[str]:
    head = [
        "格（正式配備）",
        "人數",
        "走不到第 3 步",
        "第 3 步路上主角倒下",
        "倒在路上（其中巡邏）",
        "倒在固定戰",
        "固定戰勝率",
        "固定戰平均輪數",
        "≤ 40%？",
    ]
    lines = [_row(head), _row(["---"] * len(head))]
    for name in CELLS:
        mine = [p for p in people if p["cell"] == name]
        reached = [p["step3"][candidate] for p in mine if candidate in p["step3"]]
        n = len(reached)
        down = sum(r["down_road"] or r["down_fixed"] for r in reached)
        road = sum(r["down_road"] for r in reached)
        patrol = sum(r["down_patrol"] for r in reached)
        fixed = sum(r["down_fixed"] for r in reached)
        wins = sum(r["won_fixed"] for r in reached)
        fought = [r for r in reached if r["reached_fixed"]]
        rounds = sum(r["rounds_fixed"] for r in fought) / max(1, len(fought))
        ok = "是" if down * 100 <= LIMIT_PERCENT * max(1, n) else "**否**"
        lines.append(
            _row(
                [
                    name,
                    len(mine),
                    len(mine) - n,
                    _pct(down, n),
                    f"{road}（{patrol}）",
                    fixed,
                    _pct(wins, n),
                    f"{rounds:.1f}",
                    ok,
                ]
            )
        )
    return lines


def _compare_table(people: list[Record], candidates: list[str]) -> list[str]:
    base = "current"
    head = ["格", "人數", *(f"{c} 倒下" for c in candidates)]
    head += [f"{c} 淨變動／翻轉" for c in candidates if c != base]
    lines = [_row(head), _row(["---"] * len(head))]
    for name in CELLS:
        mine = [p for p in people if p["cell"] == name and p["step3"]]
        cells: list[object] = [name, len(mine)]
        downs = {}
        for c in candidates:
            downs[c] = [r["step3"][c]["down_road"] or r["step3"][c]["down_fixed"] for r in mine]
            cells.append(_pct(sum(downs[c]), len(mine)))
        for c in candidates:
            if c == base:
                continue
            delta = sum(downs[c]) - sum(downs[base])
            flips = sum(a != b for a, b in zip(downs[base], downs[c], strict=True))
            cells.append(f"{delta:+d}／{flips}")
        lines.append(_row(cells))
    return lines


def render(data: Record) -> str:
    library = load_library()
    meta = data["meta"]
    people: list[Record] = data["people"]
    tried: dict[str, int] = meta.get("tried") or dict.fromkeys(CELLS, meta["per_cell"])
    span = "、".join(f"{name.split()[0]} 0～{n - 1}" for name, n in tried.items())
    seeds = f"{SEED_BASE}+格×1000+i（i：{span}）"
    lines = [
        f"每格 {meta['per_cell']} 人走到第 3 步（走不到的另列、依序補人），"
        f"{len(CELLS)} 格共 {len(people)} 人；種子 {seeds}；"
        f"--jobs {meta['jobs']}；耗時 {meta['seconds']:.0f} 秒",
        "",
        "### ① 第 1、2 步（入門配備，依大類）",
        "",
        *_starter_table(library, people),
        "",
    ]
    candidates: list[str] = meta["candidates"]
    for c in candidates:
        hp = CANDIDATES[c]
        label = "目前內容" if hp is None else f"巡邏兩名 {TERRACE_UNIT} max_hp {hp}"
        lines += [f"### ② 第 3 步路上（{c}：{label}）", "", *_step3_table(people, c), ""]
    if "current" in candidates and len(candidates) > 1:
        lines += ["### 候選對照（同一批人配對）", "", *_compare_table(people, candidates), ""]
    return "\n".join(lines)


def _run(
    per_cell: int, jobs: int, candidates: tuple[str, ...], only: str | None, out: Path
) -> None:
    """每格先跑 ``per_cell`` 人；走不到第 3 步的人另列，再依序補第 ``per_cell``、``per_cell + 1``…
    個人，直到每格都有 ``per_cell`` 人走到第 3 步（分母 ≥ ``per_cell``，驗收條件）。"""
    cells = [i for i, name in enumerate(CELLS) if only is None or only in name]
    names = list(CELLS)
    tried = dict.fromkeys(cells, 0)
    short = dict.fromkeys(cells, per_cell)
    people: list[Record] = []
    print(f"候選 {','.join(candidates)}、--jobs {jobs}", file=sys.stderr)
    start = time.monotonic()
    os.environ["PYTHONHASHSEED"] = "0"
    with ProcessPoolExecutor(max_workers=jobs, initializer=_init, initargs=(candidates,)) as pool:
        for _round in range(MAX_TOP_UP_ROUNDS):
            work = [(c, tried[c] + k, candidates) for c in cells for k in range(short[c])]
            if not work:
                break
            print(f"這一輪 {len(work)} 人", file=sys.stderr)
            for c in cells:
                tried[c] += short[c]
            people += pool.map(run_person, work, chunksize=1)
            for c in cells:
                reached = sum(1 for p in people if p["cell"] == names[c] and p["step3"])
                short[c] = max(0, per_cell - reached)
    seconds = time.monotonic() - start
    people.sort(key=lambda p: (names.index(p["cell"]), p["index"]))
    meta = {
        "per_cell": per_cell,
        "tried": {names[c]: n for c, n in tried.items()},
        "jobs": jobs,
        "candidates": list(candidates),
        "seconds": seconds,
    }
    data = {"meta": meta, "people": people}
    out.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8")
    print(render(data))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--per-cell", type=int, default=80)
    run.add_argument("--jobs", type=int, default=4)
    run.add_argument("--candidates", default="current", help="逗號分隔：" + ",".join(CANDIDATES))
    run.add_argument("--only", default=None, help="只跑名稱含這段字的格")
    run.add_argument("--out", type=Path, required=True)
    report = sub.add_parser("report", help="把 run 的 JSON 重新印成表（不重跑）")
    report.add_argument("json", type=Path)
    args = parser.parse_args()
    if args.command == "report":
        print(render(json.loads(args.json.read_text(encoding="utf-8"))))
        return
    candidates = tuple(args.candidates.split(","))
    unknown = [c for c in candidates if c not in CANDIDATES]
    if unknown:
        parser.error(f"未知的候選：{unknown}")
    _run(args.per_cell, min(MAX_JOBS, max(1, args.jobs)), candidates, args.only, args.out)


if __name__ == "__main__":
    main()
