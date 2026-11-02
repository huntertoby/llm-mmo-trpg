"""5A-SIM：練等手感與經驗曲線（代決初值；只量不改 content）。

兩個子命令：

- ``encounter``：同等級主角（5A-6 成長：每級屬性 +2 加在最高屬性、07 7.6 技能階級）＋原型 2 名
  標準隊友，打雲嶺每個有遭遇表的地點（敵人照地點 ``level_min`` 成長）；另量「主角低 2 級」（去高
  2 級的地點）。輸出勝率與結束時主角剩餘 HP%。``--variants`` 可以試敵人成長倍率（只在本腳本的
  記憶體內換掉 ``trpg.world.battle.grow_enemy``，不改 content）。
- ``curve``：照經驗來源比例與「認真玩每天約 3 小時」的行為假設，推出 1→10 級的經驗門檻（解析
  計算，不跑戰鬥）。

用法::

    uv run python scripts/world_leveling_sim.py encounter --seeds 6 --jobs 6 \\
        --variants "2:50,2:100,3:100" --out .scratch_5asim
    uv run python scripts/world_leveling_sim.py curve

變體格式 ``屬性點每級:HP 每級‰``（基準＝``2:50``，和主角相同：每級 +2 屬性、HP +5%）。
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Literal, NamedTuple

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.results import battle_result
from trpg.engine.runner import advance
from trpg.engine.setup import BattleSetup
from trpg.roguelite.offers import at_run_tier
from trpg.roguelite.progress import hero_unit_id
from trpg.roguelite.start import new_run
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Attribute, Team
from trpg.world import battle as world_battle
from trpg.world.actions import AllocateAction
from trpg.world.common import rules_of
from trpg.world.encounters import elite_kinds
from trpg.world.growth import apply_growth, gain_xp
from trpg.world.state import CharacterState, EncounterResult, WorldState
from trpg.world.step import new_character

REGION = "cloud_ridge"
NOON = 1_793_592_000
SIM_THRESHOLDS = tuple(100 * n for n in range(1, 10))
"""模擬用的門檻（每 100 經驗 1 級），只為了用 ``gain_xp`` 把主角升到指定等級。"""
BASE_VARIANT = (2, 50)

_LIB: ContentLibrary | None = None


# ---------------------------------------------------------------------------
# 內容庫與敵人成長變體
# ---------------------------------------------------------------------------


def sim_library() -> ContentLibrary:
    """每個行程載入一次；門檻換成 ``SIM_THRESHOLDS``（可以升到 10 級）。"""
    global _LIB  # noqa: PLW0603
    if _LIB is None:
        library = load_library()
        roguelite = library.roguelite.model_copy(update={"level_thresholds": SIM_THRESHOLDS})
        _LIB = dataclasses.replace(library, roguelite=roguelite)
    return _LIB


def grow_variant(attr_per_level: int, hp_permille: int) -> Any:
    """``grow_enemy`` 的變體：每級屬性 ``attr_per_level``、HP 每級 ``hp_permille``‰。"""

    def grow(
        library: ContentLibrary, template: UnitTemplate, level: int
    ) -> tuple[UnitTemplate, tuple[SkillDef, ...]]:
        if level <= 1:
            return template, ()
        growth = rules_of(library).enemy_growth
        attributes = dict(template.attributes)
        best = max(attributes.get(a, 0) for a in Attribute)
        top = next(a for a in Attribute if attributes.get(a, 0) == best)
        attributes[top] = best + attr_per_level * (level - 1)
        tier = growth.tier_for(level)
        rename: dict[str, str] = {}
        extra: dict[str, SkillDef] = {}
        for skill_id in template.skills:
            skill = library.skills[skill_id]
            if skill.tier >= tier:
                continue
            done = at_run_tier(library, skill, tier)
            rename[skill_id] = done.id
            extra[done.id] = done
        update: dict[str, object] = {
            "attributes": attributes,
            "max_hp": template.max_hp + template.max_hp * hp_permille * (level - 1) // 1000,
            "skills": tuple(rename.get(s, s) for s in template.skills),
            "level": level,
        }
        if template.reactions is not None:
            update["reactions"] = tuple(
                r.model_copy(update={"reaction": rename[r.reaction]}) if r.reaction in rename else r
                for r in template.reactions
            )
        return template.model_copy(update=update), tuple(extra[k] for k in sorted(extra))

    return grow


# ---------------------------------------------------------------------------
# 主角與遭遇
# ---------------------------------------------------------------------------


def make_hero(library: ContentLibrary, build_id: str, level: int) -> CharacterState:
    """``build_id`` 的主角（開局預設配點）升到 ``level``；每級的屬性點全加在目前最高的屬性。"""
    hero = new_run(library, build_id, seed=0).hero
    world = WorldState.model_validate(
        {"season_id": "sim", "season_seed": 20261103, "season_start": NOON}
    )
    char = new_character(library, f"sim_{build_id}", hero, region=REGION)
    if level > 1:
        char, _ = gain_xp(library, world, char, SIM_THRESHOLDS[level - 2])
    if char.attribute_points > 0:
        attrs = char.hero.attributes
        best = max(attrs[a] for a in Attribute)
        top = next(a for a in Attribute if attrs[a] == best)
        action = AllocateAction(attributes={top: char.attribute_points})
        char, _ = apply_growth(library, world, char, action, NOON)
    return char


def make_encounter(
    library: ContentLibrary, location: str, level: int, seed: int
) -> EncounterResult:
    """地點 ``location`` 的遭遇：地圖從地點的 ``battle_maps`` 抽、日夜交替、天氣照區域權重。"""
    loc = library.world_maps[REGION].location_by_id()[location]
    rng = Rng(fnv1a64(f"5asim:{location}:{seed}".encode()))
    battle_map = rng.choice(loc.battle_maps) if loc.battle_maps else None
    phase: Literal["day", "night"] = "day" if seed % 2 == 0 else "night"
    weights = rules_of(library).weather_for(REGION).for_phase(phase)
    roll = rng.randint(0, sum(w for _, w in weights) - 1)
    weather = weights[-1][0]
    for name, w in weights:
        if roll < w:
            weather = name
            break
        roll -= w
    return EncounterResult(
        region=REGION,
        location=location,
        level=level,
        battle_map=battle_map,
        battle_seed=rng.next_u32(),
        weather=weather,
        day_phase=phase,
        at=NOON,
        from_location=None,
    )


def encounter_locations(library: ContentLibrary) -> list[tuple[str, int, str]]:
    """雲嶺有遭遇表的地點：（ID、level_min、種類），依等級與 ID 排序。"""
    table = library.world_encounters[REGION]
    locations = library.world_maps[REGION].location_by_id()
    rows = []
    for entry in table.locations:
        loc = locations[entry.location]
        rows.append((loc.id, loc.level_min or 1, loc.kind))
    return sorted(rows, key=lambda r: (r[1], r[0]))


# ---------------------------------------------------------------------------
# 戰鬥
# ---------------------------------------------------------------------------


class Job(NamedTuple):
    variant: tuple[int, int]
    build: str
    location: str
    loc_level: int
    hero_level: int
    seeds: tuple[int, ...]
    grow_companions: bool = False


class Row(NamedTuple):
    attr: int
    hp_permille: int
    build: str
    location: str
    loc_level: int
    hero_level: int
    seed: int
    won: int
    hero_hp: int
    team_hp: int
    rounds: int
    elite: int
    enemies: int


def run_job(job: Job) -> list[Row]:
    library = sim_library()
    world_battle.grow_enemy = grow_variant(*job.variant)  # 只在本行程的記憶體內
    char = make_hero(library, job.build, job.hero_level)
    policy = CommandedAI(UtilityAI(library.ai_profiles), {})
    rows: list[Row] = []
    for seed in job.seeds:
        encounter = make_encounter(library, job.location, job.loc_level, seed)
        start = char.model_copy(update={"pending_encounter": encounter})
        prepared = world_battle.prepare_battle(library, start)
        setup = prepared.setup
        if job.grow_companions:
            setup = with_grown_companions(library, setup, job.hero_level)
        opening = begin_battle(setup, prepared.seed)
        state, _, _ = advance(opening.state, opening.pending, policy)
        result = battle_result(state)
        hero = result.ally(hero_unit_id(state))
        assert hero is not None
        team_hp = sum(a.hp for a in result.allies)
        team_max = sum(a.max_hp for a in result.allies)
        elite = int(bool(elite_kinds(library, prepared.lineup)))
        rows.append(
            Row(
                attr=job.variant[0],
                hp_permille=job.variant[1],
                build=job.build,
                location=job.location,
                loc_level=job.loc_level,
                hero_level=job.hero_level,
                seed=seed,
                won=int(result.winner is Team.ALLY),
                hero_hp=hero.hp * 1000 // max(1, hero.max_hp),
                team_hp=team_hp * 1000 // max(1, team_max),
                rounds=result.round,
                elite=elite,
                enemies=len(prepared.lineup.members),
            )
        )
    return rows


def with_grown_companions(library: ContentLibrary, setup: BattleSetup, level: int) -> BattleSetup:
    """標準隊友照主角等級成長（同敵人基準：每級 +2 屬性加最高項、HP +5%、07 7.6 階級）。"""
    if level <= 1:
        return setup
    grow = grow_variant(*BASE_VARIANT)
    units = list(setup.units)
    extra: dict[str, SkillDef] = {}
    for index, unit in enumerate(units):
        if index == 0 or unit.team is not Team.ALLY:
            continue
        grown, skills = grow(library, unit.template, level)
        extra.update((k.id, k) for k in skills)
        units[index] = unit.model_copy(update={"template": grown})
    ruleset = setup.ruleset.with_skills(extra[k] for k in sorted(extra))
    return setup.model_copy(update={"units": tuple(units), "ruleset": ruleset})


def make_jobs(
    library: ContentLibrary,
    variants: Sequence[tuple[int, int]],
    builds: Sequence[str],
    seeds: int,
    gaps: Sequence[int],
    *,
    grow_companions: bool,
) -> list[Job]:
    jobs = []
    for variant in variants:
        for loc, level, _ in encounter_locations(library):
            for gap in gaps:
                hero_level = level - gap
                if hero_level < 1:
                    continue
                for build in builds:
                    jobs.append(
                        Job(
                            variant,
                            build,
                            loc,
                            level,
                            hero_level,
                            tuple(range(seeds)),
                            grow_companions,
                        )
                    )
    return jobs


# ---------------------------------------------------------------------------
# 彙整
# ---------------------------------------------------------------------------


def _pct(num: int, den: int) -> str:
    return f"{100 * num / den:.0f}%" if den else "—"


def _mean(values: Sequence[int]) -> str:
    return f"{sum(values) / len(values) / 10:.0f}%" if values else "—"


def summarize(rows: Iterable[Row], kinds: dict[str, str]) -> str:
    """每個變體：地點 × 等級差的勝率、勝場主角剩餘 HP%、全場隊伍剩餘 HP%；再依等級彙總。"""
    by_key: dict[tuple[tuple[int, int], int, str, int], list[Row]] = defaultdict(list)
    for r in rows:
        key = ((r.attr, r.hp_permille), r.loc_level - r.hero_level, r.location, r.loc_level)
        by_key[key].append(r)
    out: list[str] = []
    for variant in sorted({k[0] for k in by_key}):
        out.append(f"\n## 變體 屬性 +{variant[0]}／級、HP +{variant[1]}‰／級\n")
        out.append(
            "| 等級差 | 地點 | 種類 | 地點等級 | n | 勝率 | 勝場主角 HP | 勝場隊伍 HP | 精英場 |"
        )
        out.append("|---|---|---|---|---|---|---|---|---|")
        for key in sorted(k for k in by_key if k[0] == variant):
            group = by_key[key]
            wins = [r for r in group if r.won]
            out.append(
                f"| {key[1]} | {key[2]} | {kinds[key[2]]} | {key[3]} | {len(group)} | "
                f"{_pct(len(wins), len(group))} | {_mean([r.hero_hp for r in wins])} | "
                f"{_mean([r.team_hp for r in wins])} | "
                f"{_pct(sum(r.elite for r in group), len(group))} |"
            )
        out.append(
            "\n| 等級差 | 地點等級 | n | 勝率 | 勝場主角 HP | 不含精英巢穴／秘境／Boss 的勝率 |"
        )
        out.append("|---|---|---|---|---|---|")
        levels: dict[tuple[int, int], list[Row]] = defaultdict(list)
        for key, group in by_key.items():
            if key[0] == variant:
                levels[(key[1], key[3])] += group
        for (gap, level), group in sorted(levels.items()):
            wins = [r for r in group if r.won]
            plain = [r for r in group if kinds[r.location] not in ("elite_lair", "secret", "boss")]
            out.append(
                f"| {gap} | {level} | {len(group)} | {_pct(len(wins), len(group))} | "
                f"{_mean([r.hero_hp for r in wins])} | "
                f"{_pct(sum(r.won for r in plain), len(plain))} |"
            )
    return "\n".join(out)


def parse_variants(text: str) -> list[tuple[int, int]]:
    result = []
    for part in text.split(","):
        attr, hp = part.split(":")
        result.append((int(attr), int(hp)))
    return result


def cmd_encounter(args: argparse.Namespace) -> int:
    library = sim_library()
    builds = args.builds.split(",") if args.builds else [b.id for b in library.builds.sim_builds()]
    variants = parse_variants(args.variants)
    gaps = [int(g) for g in args.gaps.split(",")]
    jobs = make_jobs(
        library, variants, builds, args.seeds, gaps, grow_companions=args.grow_companions
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rows: list[Row] = []
    with ProcessPoolExecutor(max_workers=min(args.jobs, 6)) as pool:
        for chunk in pool.map(run_job, jobs, chunksize=1):
            rows += chunk
    elapsed = time.perf_counter() - started
    with (out / f"{args.name}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(Row._fields)
        writer.writerows(rows)
    kinds = {loc: kind for loc, _, kind in encounter_locations(library)}
    text = summarize(rows, kinds)
    header = f"# {args.name}：{len(rows)} 場、{len(builds)} 個 build、{elapsed:.0f} 秒"
    (out / f"{args.name}.md").write_text(
        header + "\n" + text + "\n", encoding="utf-8", newline="\n"
    )
    print(header)
    print(text)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    library = sim_library()
    kinds = {loc: kind for loc, _, kind in encounter_locations(library)}
    rows: list[Row] = []
    for path in args.csv:
        with Path(path).open(encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                values = {k: v if k in ("build", "location") else int(v) for k, v in rec.items()}
                rows.append(Row(**values))  # type: ignore[arg-type]
    print(summarize(rows, kinds))
    return 0


# ---------------------------------------------------------------------------
# 經驗曲線（解析）
# ---------------------------------------------------------------------------

SOURCE_SHARES: dict[str, float] = {
    "battle": 1.0,
    "elite": 3.0,
    "chain_step": 3.0,
    "main_step": 5.0,
    "situation_success": 0.5,
    "situation_partial": 0.25,
    "hidden_location": 2.0,
    "bounty": 4.0,
}
"""經驗來源比例（07 7.8；一般戰鬥＝1 份）。"""

SITUATION_SUCCESS = 0.50
SITUATION_PARTIAL = 0.25
"""情境判定的結果分布假設（d20＋修正對基準難度，主屬性在允許清單內：約一半成功、1/4 部分）。"""

DAY_KEYS = ("battle", "elite", "chain_step", "main_step", "situation", "hidden", "bounty")
_DAY_ROWS: tuple[tuple[float, ...], ...] = (
    # 欄位照 DAY_KEYS：一般戰鬥、精英、任務鏈步、主線步、情境判定、發現隱藏地點、懸賞。
    # 第 1 天（雲嶺 1～3 級）：新手任務鏈 3 步、主線第 1 章第 1 步；戰鬥較慢（教學）。
    (12, 0.5, 3, 1, 6, 0, 0),
    # 第 2 天（雲嶺 3～4 級）：主線第 1 章 2 步（約第 2 天給劇情技能）、區域任務鏈 2 步、丹爐洞。
    (14, 1, 2, 2, 8, 1, 0),
    # 第 3 天（雲嶺 4～6 級）：區域任務鏈 3 步、主線第 1 章 2 步（含雲頂觀）、懸賞 2 個、鶴歸崖。
    (14, 1.5, 3, 2, 8, 1, 2),
    # 第 4～6 天（灰燼荒原 5～8 級）：區域任務鏈 5 步、主線第 2 章 5 步分 3 天、懸賞每天 1 個。
    (15, 1.5, 2, 1, 8, 0.5, 1),
    (15, 1.5, 2, 2, 8, 0.5, 1),
    (15, 1.5, 1, 2, 8, 0.5, 1),
    # 第 7～8 天：主線第 3 章（封印鑰匙）每天 1 步，其餘是練等與懸賞。
    (16, 2, 0, 1, 8, 0.5, 1),
    (16, 2, 0, 1, 8, 0, 1),
)
DAY_PLAN: tuple[dict[str, float], ...] = tuple(
    dict(zip(DAY_KEYS, row, strict=True)) for row in _DAY_ROWS
)
"""每天（約 3 小時）的行為假設，數字是當天的次數（說明見報告第 2 節）。"""

DAY_CONTENT_LEVEL: tuple[float, ...] = (1.5, 3.0, 4.5, 5.5, 6.5, 7.5, 8.5, 9.0)
"""每天主要打的內容等級（地點建議等級；雲嶺 1～6、灰燼荒原 5～10），只給「每份經驗隨內容等級
加成」的方案 B 用。"""

ANCHOR_5 = 3.0
"""5 級的目標時間（第 3 天結束）。"""
ANCHOR_10 = 7.75
"""10 級的目標時間（第 7～8 天的中點）。8 級落在第幾天由曲線形狀決定（目標約第 6 天）。"""
RAMP_WEIGHTS = (1, 3, 5, 6)
"""2～5 級每級需要的經驗比例（前期快、逐級變多）。6～10 級每級需要相同。"""


def day_shares(plan: dict[str, float]) -> float:
    situation = plan["situation"] * (
        SITUATION_SUCCESS * SOURCE_SHARES["situation_success"]
        + SITUATION_PARTIAL * SOURCE_SHARES["situation_partial"]
    )
    return (
        plan["battle"] * SOURCE_SHARES["battle"]
        + plan["elite"] * SOURCE_SHARES["elite"]
        + plan["chain_step"] * SOURCE_SHARES["chain_step"]
        + plan["main_step"] * SOURCE_SHARES["main_step"]
        + plan["hidden"] * SOURCE_SHARES["hidden_location"]
        + plan["bounty"] * SOURCE_SHARES["bounty"]
        + situation
    )


def share_value(base: int, scale_permille: int, content_level: float) -> float:
    """1 份的經驗：``base`` ×（1 ＋ ``scale_permille``‰ ×（內容等級 − 1））。"""
    return base * (1 + scale_permille * (content_level - 1) / 1000)


def cumulative_at(day: float, per_day: Sequence[float]) -> float:
    """第 ``day`` 天（可帶小數，當天內均勻）結束時的累計值。"""
    whole = int(day)
    total = sum(per_day[:whole])
    if whole < len(per_day):
        total += per_day[whole] * (day - whole)
    return total


def day_reached(value: float, per_day: Sequence[float]) -> float:
    """累計值到 ``value`` 的時間（第幾天，帶小數）。"""
    running = 0.0
    for day, amount in enumerate(per_day):
        if running + amount >= value:
            return day + (value - running) / amount
        running += amount
    return float(len(per_day))


def solve_thresholds(per_day: Sequence[float], round_to: int) -> list[int]:
    """2～10 級的累計門檻：2～5 級照 ``RAMP_WEIGHTS`` 分攤到第 3 天結束的累計，6～10 級每級相同、
    10 級落在 ``ANCHOR_10``。"""
    t5 = cumulative_at(ANCHOR_5, per_day)
    t10 = cumulative_at(ANCHOR_10, per_day)
    ramp = [t5 * w / sum(RAMP_WEIGHTS) for w in RAMP_WEIGHTS]
    flat = (t10 - t5) / 5
    needs = ramp + [flat] * 5
    thresholds = []
    running = 0.0
    for need in needs:
        running += need
        thresholds.append(int(round(running / round_to) * round_to))
    return thresholds


def print_curve(
    name: str, per_day: Sequence[float], unit_per_day: Sequence[float], rnd: int
) -> None:
    thresholds = solve_thresholds(per_day, rnd)
    print(f"\n## {name}\n")
    print("| 等級 | 累計門檻 | 本級需要 | 約幾場一般戰鬥（當時） | 到達（第幾天） |")
    print("|---|---|---|---|---|")
    previous = 0
    for level, threshold in enumerate(thresholds, start=2):
        need = threshold - previous
        day = day_reached(threshold, per_day)
        battle = unit_per_day[min(int(day), len(unit_per_day) - 1)]
        print(f"| {level} | {threshold} | {need} | {need / battle:.0f} | {day:.2f} |")
        previous = threshold


def cmd_curve(args: argparse.Namespace) -> int:
    shares = [day_shares(p) for p in DAY_PLAN]
    print("# 經驗曲線\n")
    print(
        "| 天 | 一般戰鬥 | 精英 | 任務鏈步 | 主線步 | 情境判定 | 隱藏地點 | 懸賞 "
        "| 當天份數 | 累計份數 | 戰鬥占比 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    running = 0.0
    for day, (plan, amount) in enumerate(zip(DAY_PLAN, shares, strict=True), start=1):
        running += amount
        cells = " | ".join(f"{plan[k]:g}" for k in DAY_KEYS)
        print(f"| {day} | {cells} | {amount:.1f} | {running:.1f} | {plan['battle'] / amount:.0%} |")
    for scale in (0, args.level_scale_permille):
        units = [
            share_value(args.xp_per_share, scale, lvl) for lvl in DAY_CONTENT_LEVEL[: len(shares)]
        ]
        per_day = [s * u for s, u in zip(shares, units, strict=True)]
        label = "方案 A：1 份固定"
        if scale:
            label = f"方案 B：1 份 ×（1＋{scale}‰ ×（內容等級−1））"
        print_curve(f"{label}（基準 1 份＝{args.xp_per_share}）", per_day, units, args.round_to)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    enc = sub.add_parser("encounter")
    enc.add_argument("--seeds", type=int, default=6)
    enc.add_argument("--jobs", type=int, default=6)
    enc.add_argument("--builds", default="")
    enc.add_argument("--variants", default="2:50")
    enc.add_argument("--gaps", default="0,2", help="主角比地點低幾級（逗號分隔）")
    enc.add_argument("--name", default="encounter")
    enc.add_argument(
        "--grow-companions", action="store_true", help="標準隊友照主角等級成長（基準規則）"
    )
    enc.add_argument("--out", default=".scratch_5asim")
    rep = sub.add_parser("report")
    rep.add_argument("csv", nargs="+")
    cur = sub.add_parser("curve")
    cur.add_argument("--xp-per-share", type=int, default=100)
    cur.add_argument("--round-to", type=int, default=50)
    cur.add_argument("--level-scale-permille", type=int, default=100)
    args = parser.parse_args(argv)
    if args.cmd == "encounter":
        return cmd_encounter(args)
    if args.cmd == "report":
        return cmd_report(args)
    return cmd_curve(args)


if __name__ == "__main__":
    sys.exit(main())
