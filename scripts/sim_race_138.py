"""#138 種族勝率比較（只量不調）：人類 ／ 舊狐族（現行規則）／ 新獸耳族（近似）。

用法::

    uv run python scripts/sim_race_138.py --seeds 20 --jobs 8 --out scratchpad/race/report.md

**這支腳本只在模擬時改規則**：新獸耳族的「獸躍」「輕身」引擎沒有實作，這裡在本行程（與 spawn 的
工作行程）內以 monkeypatch 近似，不改 ``content/`` 與 ``src/``：

- 規則包：複製一份 ``Ruleset``，把種族 ``fox`` 的定義換成「獸耳族」——種族技 ``race_beast_leap``
  （形狀 ``ground_tile`` 射程 3，效果類型 ``leap``）、被動 ``beast_light_body``（規則
  ``fall_immunity``）。舊狐族與人類用原本的規則包。
- 獸躍（``leap``）：每場 1 次、1 AP；落點在曼哈頓 3 格內、看得到（``center_problem``：不是牆壁、
  視線不被牆擋＝「不能跳過牆」的近似）、可站立、沒有單位、不是致命地形、最多比現在高 2 層（往下
  不限）；以 ``MoveUnitEffect(mode="teleported")`` 移過去：不觸發藉機攻擊、不墜落，落點的陷阱與表面
  照常結算。
- 獸躍的 AI（近似「開場用一次、往上跳到最近的高處」）：回合開始 AP ≥ 2、場上有敵人、有比腳下高的
  合法落點時就用（每場 1 次，所以實際上是第一次有機會的回合）；選法＝高度差大的優先，再挑近的，
  同分取列舉順序 ``(y, x)``。不會為了平移或往下而用。
- 輕身：``unit_fell`` 的墜落傷害觸發對被動規則為 ``fall_immunity`` 的單位不產生傷害（被推下或自己
  往下都算）；致命地形不受影響。AI 的路徑估值不知道「不會摔傷」（照舊會避開往下 2 層的路）。
- 攀爬跳躍 +1／交涉 +1：只用在世界層的情境判定，戰鬥模擬裡沒有作用，不模擬。
- 舊狐族的「靈覺」照現行規則（看得見 2 格內的陷阱與隱蔽單位）；獸耳族沒有。

地圖：8 張戰鬥地圖（``content/maps``）＋ 2 張雲嶺實地地圖用 ``cut_battlefield`` 切出的 12×12
戰場（雨中梯田、渡口石階；敵方照開闊平原的預設陣容）。我方＝build 英雄（主角，換種族）＋ 標準隊友。
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef
from trpg.content.races import RaceDef, RaceEffect, RaceSkill
from trpg.engine import triggers
from trpg.engine.actions import UseRaceSkill
from trpg.engine.ai import race as race_ai
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import EffectBase, MoveUnitEffect
from trpg.engine.events import EventBase, RaceSkillUsed, UnitFell, UnitMoved
from trpg.engine.race import skills as race_skills
from trpg.engine.results import ResolveResult
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.landing import landing_problem
from trpg.engine.rules.movement import is_deadly
from trpg.engine.rules.statuses import is_rooted
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, assign_races, build_setup
from trpg.engine.skills import shapes
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team, UnitId
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, UtilityPolicyFactory
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks
from trpg.world.battlefield import UnitCounts, cut_battlefield

LEAP_RANGE: Final = 3
LEAP_MAX_RISE: Final = 2
MIN_AP_TO_LEAP: Final = 2
"""跳完還要能行動（同 ``engine/ai/race.py`` 的 ``_MIN_AP_AFTER``）。"""
FALL_IMMUNITY: Final = "fall_immunity"

VARIANTS: Final = ("human", "fox_old", "beast")
VARIANT_ZH: Final = {"human": "人類", "fox_old": "舊狐族", "beast": "獸耳族（近似）"}
VARIANT_RACE: Final = {"human": "human", "fox_old": "fox", "beast": "fox"}

FLAT_MAPS: Final = ("open_plain", "ruined_fort", "oil_depot")
OTHER_MAPS: Final = ("narrow_halls", "swamp", "dark_forest", "cliff_outpost", "bridge_chasm")
CUT_ENEMIES_FROM: Final = "open_plain"
CUTS: Final = {
    # 地圖 ID: (實地地圖, 接觸點, 走來的前一格, 敵方帶頭的)
    "cut_rain_terraces": ("rain_terraces", (12, 10), (12, 11), (12, 6)),
    "cut_ferry_steps": ("ferry_steps", (8, 8), (7, 8), (9, 6)),
}
MAPS: Final = (*FLAT_MAPS, *OTHER_MAPS, *CUTS)
MAP_ZH: Final = {
    "open_plain": "開闊平原",
    "ruined_fort": "廢墟要塞",
    "oil_depot": "油庫",
    "narrow_halls": "狹窄走廊",
    "swamp": "沼澤",
    "dark_forest": "幽暗森林",
    "cliff_outpost": "懸崖前哨",
    "bridge_chasm": "吊橋深淵",
    "cut_rain_terraces": "雨中梯田（雲嶺切圖）",
    "cut_ferry_steps": "渡口石階（雲嶺切圖）",
}
DEFAULT_BUILDS: Final = ("build_ranged", "build_charger")


# ---------------------------------------------------------------------------
# 模擬專用的規則近似（monkeypatch；只在這支腳本的行程內生效）
# ---------------------------------------------------------------------------


def _leap_problem(
    state: BattleState,
    unit: UnitState,
    _skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.target_pos is not None
    xy = (action.target_pos.x, action.target_pos.y)
    if is_rooted(state.ruleset, unit) or unit.speed == 0:
        return "不能移動"
    if xy == unit.xy:
        return "落點是原地"
    problem = shapes.center_problem(state, unit.xy, xy, effect.range or 0)
    if problem is not None:
        return problem
    if landing_problem(state, xy, mover=unit.id) is not None or is_deadly(state, xy):
        return "落點不能站"
    if state.tile(*xy).height - state.tile(*unit.xy).height > LEAP_MAX_RISE:
        return "太高"
    return None


def _do_leap(ctx: Ctx, unit: UnitState, _e: RaceEffect, action: UseRaceSkill) -> None:
    assert action.target_pos is not None
    dest = (action.target_pos.x, action.target_pos.y)
    move: EffectBase = MoveUnitEffect(
        source_id=unit.id, unit_id=unit.id, dest=dest, mode="teleported"
    )
    execute(ctx, [move])


def _leap_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    if unit.ap < MIN_AP_TO_LEAP or not any(
        u.team is not unit.team and not u.is_summon for u in state.living_units()
    ):
        return 0
    assert action.target_pos is not None
    xy = (action.target_pos.x, action.target_pos.y)
    rise = state.tile(*xy).height - state.tile(*unit.xy).height
    if rise < 1:
        return 0
    return rise * 10 + (LEAP_RANGE + 1 - manhattan(unit.xy, xy))


_ORIGINAL_FALL = triggers._fall_damage


def _light_body_fall(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, UnitFell)
    unit = ctx.state.units.get(event.unit_id)
    if (
        unit is not None
        and unit.race is not None
        and ctx.state.ruleset.race_def(unit.race).passive.rule == FALL_IMMUNITY
    ):
        return []
    return _ORIGINAL_FALL(ctx, event, depth)


def install_patches() -> None:
    race_skills.RACE_EFFECT_PROBLEMS["leap"] = _leap_problem
    race_skills.RACE_EFFECT_EXECUTORS["leap"] = _do_leap
    race_ai.RACE_EFFECT_SCORERS["leap"] = _leap_score
    fns = triggers._TRIGGERS["unit_fell"]
    triggers._TRIGGERS["unit_fell"] = [_light_body_fall if f is _ORIGINAL_FALL else f for f in fns]


install_patches()  # spawn 的工作行程匯入本模組時也會套用


def beast_race(fox: RaceDef) -> RaceDef:
    shape = fox.skill.shape.model_copy(update={"range": LEAP_RANGE})
    effect = fox.skill.effects[0].model_copy(
        update={
            "type": "leap",
            "range": LEAP_RANGE,
            "summon": None,
            "lifetime": None,
            "ai_trigger_range": None,
        }
    )
    skill = fox.skill.model_copy(
        update={"id": "race_beast_leap", "name_zh": "獸躍", "shape": shape, "effects": (effect,)}
    )
    passive = fox.passive.model_copy(
        update={"id": "beast_light_body", "name_zh": "輕身", "rule": FALL_IMMUNITY, "radius": None}
    )
    return fox.model_copy(update={"name_zh": "獸耳族", "skill": skill, "passive": passive})


# ---------------------------------------------------------------------------
# 內容庫與設定
# ---------------------------------------------------------------------------

_CACHE: dict[str, object] = {}


def _cut_maps(lib: ContentLibrary) -> dict[str, MapDef]:
    template = lib.map(CUT_ENEMIES_FROM)
    found: dict[str, MapDef] = {}
    for map_id, (field_id, contact, came_from, enemy_at) in CUTS.items():
        cut = cut_battlefield(
            lib,
            lib.field_maps[field_id],
            ally_at=contact,
            enemy_at=enemy_at,
            counts=UnitCounts(allies=3, enemies=4),
            first=None,
            template=template,
            came_from=came_from,
        )
        if isinstance(cut, str):
            raise SystemExit(f"{field_id} 切不出戰場：{cut}")
        battle, info = cut
        _CACHE[f"cutinfo/{map_id}"] = info
        found[map_id] = battle.model_copy(update={"id": map_id})
    return found


def _lib(variant: str) -> ContentLibrary:
    key = "lib/beast" if variant == "beast" else "lib/base"
    if key not in _CACHE:
        base = library_with_builds(load_library())
        base = dataclasses.replace(base, maps={**base.maps, **_cut_maps(base)})
        if variant == "beast":
            table = base.ruleset.races
            assert table is not None
            races = tuple(beast_race(r) if r.id == "fox" else r for r in table.races)
            new_table = table.model_copy(update={"races": races})
            ruleset = base.ruleset.model_copy(update={"races": new_table})
            ruleset.model_post_init(None)
            base = dataclasses.replace(base, ruleset=ruleset)
        _CACHE[key] = base
    lib = _CACHE[key]
    assert isinstance(lib, ContentLibrary)
    return lib


def _enemies(lib: ContentLibrary, map_id: str) -> tuple[str, ...]:
    source = CUT_ENEMIES_FROM if map_id in CUTS else map_id
    enc = lib.map(source).encounter
    assert enc is not None
    return tuple(enc.enemies)


def _setup(variant: str, build: str, map_id: str) -> BattleSetup:
    key = f"setup/{variant}/{build}/{map_id}"
    if key not in _CACHE:
        lib = _lib(variant)
        setup = build_setup(
            lib,
            map_id,
            (build, *lib.builds.companions),
            _enemies(lib, map_id),
            max_rounds=DEFAULT_MAX_ROUNDS,
        )
        _CACHE[key] = assign_races(setup, Team.ALLY, [VARIANT_RACE[variant]])
    cached = _CACHE[key]
    assert isinstance(cached, BattleSetup)
    return cached


# ---------------------------------------------------------------------------
# 執行
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Sample:
    variant: str
    build: str
    map_id: str
    ok: bool = True
    won: bool = False
    hero_downed: bool = False
    rounds: int = 0
    race_used: bool = False
    leap_rise: int = 0
    leap_on_raised: bool = False
    """獸躍的落點比地圖檔高（被技能抬高過的地形）。"""
    hero_falls: int = 0


type Task = tuple[str, str, str, int]


def work(_ctx: None, task: Task) -> Sample:
    variant, build, map_id, seed = task
    lib = _lib(variant)
    setup = _setup(variant, build, map_id)
    rows = _heights(setup.map)
    s = Sample(variant, build, map_id)
    hero_id: list[UnitId] = []

    def on_step(_step: object, result: ResolveResult) -> None:
        state = result.state
        if not hero_id:
            hero_id.append(
                next(u.id for u in state.units_sorted() if u.team is Team.ALLY and u.race)
            )
        hid = hero_id[0]
        just_used = False
        for e in result.events:
            if isinstance(e, RaceSkillUsed) and e.unit_id == hid:
                s.race_used = just_used = True
            elif (
                just_used
                and isinstance(e, UnitMoved)
                and e.unit_id == hid
                and e.mode == "teleported"
            ):
                just_used = False
                # 用當下的格子高度（技能的地形隆起、高台圖騰會改高度；地圖檔的高度另記）
                s.leap_rise = (
                    state.tile(e.to_pos.x, e.to_pos.y).height
                    - state.tile(e.from_pos.x, e.from_pos.y).height
                )
                s.leap_on_raised = (
                    rows[e.to_pos.y][e.to_pos.x] < state.tile(e.to_pos.x, e.to_pos.y).height
                )
            elif isinstance(e, UnitFell) and e.unit_id == hid:
                s.hero_falls += 1
        hero = state.units[hid]
        if hero.hp <= 0 or not hero.alive:
            s.hero_downed = True

    try:
        run = run_battle(
            setup, 1000 + seed, UtilityPolicyFactory(lib.ai_profiles)(), on_step=on_step
        )
    except TrpgError:
        s.ok = False
        return s
    s.won = run.state.winner is Team.ALLY
    s.rounds = run.state.round
    return s


def _heights(m: MapDef) -> list[list[int]]:
    return [[int(c) for c in line.strip()] for line in m.heights.strip().splitlines()]


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _stats(sel: list[Sample]) -> tuple[float, float, float, int]:
    ok = [x for x in sel if x.ok]
    if not ok:
        return (0.0, 0.0, 0.0, 0)
    return (
        100 * statistics.mean(x.won for x in ok),
        100 * statistics.mean(x.hero_downed for x in ok),
        statistics.mean(x.rounds for x in ok),
        len(ok),
    )


def _cell(sel: list[Sample]) -> str:
    win, down, rounds, n = _stats(sel)
    return f"{win:.0f}% / {down:.0f}% / {rounds:.1f}" if n else "—"


def _table(samples: list[Sample], maps: tuple[str, ...], builds: tuple[str, ...]) -> list[str]:
    names = " | ".join(VARIANT_ZH[v] for v in VARIANTS)
    head = f"| 地圖 | {names} | 種族技使用率（誘餌 / 獸躍） |"
    lines = [head, "|---|" + "---|" * (len(VARIANTS) + 1)]

    def row(name: str, sel: list[Sample]) -> str:
        cells = [_cell([x for x in sel if x.variant == v]) for v in VARIANTS]
        used = []
        for v in ("fox_old", "beast"):
            got = [x for x in sel if x.variant == v and x.ok]
            used.append(f"{100 * statistics.mean(x.race_used for x in got):.0f}%" if got else "—")
        return f"| {name} | " + " | ".join(cells) + f" | {' / '.join(used)} |"

    for m in maps:
        lines.append(row(MAP_ZH[m], [x for x in samples if x.map_id == m and x.build in builds]))
    groups = (
        ("平地多（3 張）", FLAT_MAPS),
        ("雲嶺切圖（2 張）", tuple(CUTS)),
        ("全部（10 張）", maps),
    )
    for name, group in groups:
        sel = [x for x in samples if x.map_id in group and x.build in builds]
        lines.append(row(f"**{name}**", sel))
    return lines


def _delta_table(samples: list[Sample], maps: tuple[str, ...]) -> list[str]:
    lines = [
        "| 地圖 | 勝率：獸耳族 − 舊狐族 | 勝率：獸耳族 − 人類 | 倒下率：獸耳族 − 舊狐族 |",
        "|---|---|---|---|",
    ]
    for m in maps:
        sel = [x for x in samples if x.map_id == m]
        b, f, h = (
            _stats([x for x in sel if x.variant == v]) for v in ("beast", "fox_old", "human")
        )
        lines.append(
            f"| {MAP_ZH[m]} | {b[0] - f[0]:+.0f} | {b[0] - h[0]:+.0f} | {b[1] - f[1]:+.0f} |"
        )
    return lines


def _map_profile(lib: ContentLibrary, maps: tuple[str, ...]) -> list[str]:
    lines = [
        "| 地圖 ID | 名稱 | 高度種類 | 相鄰高低差 ≥1 的格 | 3 格內可往上 2 層的格 |",
        "|---|---|---|---|---|",
    ]
    for m in maps:
        rows = _heights(lib.map(m))
        h, w = len(rows), len(rows[0])
        cells = [(x, y) for y in range(h) for x in range(w)]
        step = sum(
            1
            for x, y in cells
            if any(
                0 <= x + dx < w and 0 <= y + dy < h and rows[y + dy][x + dx] != rows[y][x]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
        )
        rise2 = sum(
            1
            for x, y in cells
            if any(
                rows[b][a] - rows[y][x] >= LEAP_MAX_RISE
                for a, b in cells
                if 0 < abs(a - x) + abs(b - y) <= LEAP_RANGE
            )
        )
        kinds = len({v for row in rows for v in row})
        lines.append(
            f"| `{m}` | {MAP_ZH[m]} | {kinds} | {100 * step // len(cells)}% | "
            f"{100 * rise2 // len(cells)}% |"
        )
    return lines


def format_report(samples: list[Sample], builds: tuple[str, ...], seeds: int) -> str:
    lib = _lib("human")
    bad = [x for x in samples if not x.ok]
    out = [
        "# #138 種族勝率（腳本輸出）",
        "",
        f"build：{'、'.join(builds)}；每格 = 每個 build × {seeds} 場（種子 1000 起）。"
        f" 例外：{len(bad)} 場。",
        "格式：勝率 / 主角倒下率 / 平均輪數。",
        "",
        "## 地圖高低差",
        "",
        *_map_profile(lib, MAPS),
        "",
    ]
    for name, sel in (("全部 build", builds), *((b, (b,)) for b in builds)):
        out += [f"## {name}", "", *_table(samples, MAPS, sel), ""]
    out += ["## 差距（全部 build）", "", *_delta_table(samples, MAPS), ""]
    beast = [x for x in samples if x.variant == "beast" and x.race_used]
    rises: dict[int, int] = {}
    for x in beast:
        rises[x.leap_rise] = rises.get(x.leap_rise, 0) + 1
    falls = {v: sum(x.hero_falls for x in samples if x.variant == v) for v in VARIANTS}
    out += [
        "## 其他",
        "",
        f"- 獸躍的高度差分布（用了的場次）：{dict(sorted(rises.items()))}",
        f"- 獸躍落在被技能抬高的地形上：{sum(x.leap_on_raised for x in beast)} 場"
        f"（共 {len(beast)} 場用了獸躍）",
        f"- 主角墜落次數（往下 2 層以上）：{falls}（獸耳族的不受傷）",
    ]
    for map_id in CUTS:
        info = _CACHE.get(f"cutinfo/{map_id}")
        out.append(f"- `{map_id}` 切法：{info}")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--builds", default=",".join(DEFAULT_BUILDS))
    parser.add_argument("--maps", default=",".join(MAPS))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    builds = tuple(args.builds.split(","))
    maps = tuple(args.maps.split(","))
    tasks: list[Task] = [
        (v, b, m, s) for m in maps for b in builds for v in VARIANTS for s in range(args.seeds)
    ]
    samples = run_tasks(work, None, tasks, jobs=args.jobs)
    text = format_report(samples, builds, args.seeds)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
