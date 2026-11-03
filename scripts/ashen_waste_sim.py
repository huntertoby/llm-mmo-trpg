"""灰燼荒原的小模擬（Phase 5F-5a；``docs/phases/Phase5計畫.md`` 39.5）。

走大世界的真實路徑（``prepare_battle``）：我方＝主角＋2 名系統傭兵（輸出與控制主角帶預設的鐵壁、
回春；守護與輔助主角帶赤焰、回春／穿雲），主角是數種 build 的底稿照大世界敵我同一套成長規則拉到
地點的建議等級；雙方都由效用 AI 操作；``max_rounds`` 照世界規則（30，超過算敗）。

- ``general``：荒原一般遭遇。依序輪流挑營地與村落（每個地點照遭遇表抽陣容、照地點的戰鬥地圖；
  村落是守點戰），主角等級＝地點建議等級。
- ``boss``：熔心坑灰燼之心（9 級、Boss 地圖 ``molten_heart_pit``），護甲不調整（沒有旗標與線頭）。

用法::

    uv run python scripts/ashen_waste_sim.py [--runs 40] [--only general|boss]
    uv run python scripts/ashen_waste_sim.py --only boss --boss-hp 200,240   # 候選 HP（1 級）

只輸出摘要表（勝率、平均輪數、敗場；Boss 另列到第 2／3 階段的比例、敗場剩餘 HP）；數值建議寫進報告由
PM 決定（CLAUDE.md 第 11 條）。
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import BossPhaseChanged
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.common import max_hp
from trpg.world.party import default_party
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character

REGION = "ashen_waste"
BOSS = "ashen_heart"
BOSS_LOCATION = "molten_heart_pit"
NOON = 1_793_592_000
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
"""輸出、守護、輔助、控制各 2 種（同 5F-3 的 season_boss_sim）。"""
PARTIES = {
    "build_tank": ("merc_chiyan", "merc_huichun"),
    "build_guardian": ("merc_chiyan", "merc_huichun"),
    "build_healer": ("merc_chiyan", "merc_chuanyun"),
}
GENERAL_LOCATIONS = (
    "scorched_outskirts",
    "deadwood_forest",
    "red_sand_village",
    "ash_mire",
    "gang_convoy_road",
    "ash_well_village",
    "tar_pits",
    "lava_cave",
    "iron_forge_village",
    "ruined_fortress",
)
"""一般遭遇輪流挑的地點（營地、村落與遺跡；不含精英巢穴、隱藏地點與 Boss）。"""


@dataclass(frozen=True)
class Outcome:
    label: str
    build: str
    won: bool
    rounds: int
    boss_hp_permille: int = 0
    phases: int = 0


def make_char(library: ContentLibrary, build_id: str, location: str, seed: int) -> CharacterState:
    """地點建議等級的主角（照敵我同一套成長）＋預設傭兵，身上有那個地點的遭遇。"""
    place = library.world_maps[REGION].location_by_id()[location]
    assert place.level_min is not None
    level = place.level_min
    base = next(b.hero for b in library.builds.builds if b.id == build_id)
    grown, skills = grow_enemy(library, base, level)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1})  # 等級 HP 由開戰時加
    char = new_character(library, "sim", hero, region=REGION)
    table = library.world_encounters[REGION]
    objective = table.location_by_id()[location].objective
    encounter = EncounterResult(
        region=REGION,
        location=location,
        level=level,
        battle_map=place.battle_maps[seed % len(place.battle_maps)] if place.battle_maps else None,
        battle_seed=seed,
        weather="clear",
        day_phase="day",
        at=NOON,
        objective=objective,
    )
    char = char.model_copy(
        update={
            "level": level,
            "location": location,
            "mercenaries": PARTIES.get(build_id, default_party(library)),
            "generated_skills": skills,
            "pending_encounter": encounter,
        }
    )

    return char.model_copy(update={"hp": max_hp(library, char)})


def _library(boss_hp: int | None) -> ContentLibrary:
    library = load_library()
    if boss_hp is None:
        return library
    units = dict(library.units)
    units[BOSS] = units[BOSS].model_copy(update={"max_hp": boss_hp})
    return dataclasses.replace(library, units=units)


def _run(args: tuple[str, str, str, int, int | None]) -> Outcome:
    label, build_id, location, seed, boss_hp = args
    library = _library(boss_hp)
    prepared = prepare_battle(library, make_char(library, build_id, location, seed))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    won = run.state.winner is Team.ALLY
    boss = next((u for u in run.state.units.values() if u.template_id == BOSS), None)
    if boss is None:
        return Outcome(label=label, build=build_id, won=won, rounds=run.state.round)
    changes = [e for e in run.events if isinstance(e, BossPhaseChanged) and e.unit_id == boss.id]
    return Outcome(
        label=label,
        build=build_id,
        won=won,
        rounds=run.state.round,
        boss_hp_permille=boss.hp * 1000 // max(1, boss.max_hp),
        phases=len(changes),
    )


def summarize(title: str, outcomes: Sequence[Outcome], *, boss: bool) -> str:
    n = len(outcomes)
    wins = sum(o.won for o in outcomes)
    rounds = sum(o.rounds for o in outcomes) / n
    lines = [
        f"## {title}（{n} 場）",
        f"勝率 {wins * 100 // n}%（{wins}/{n}）、平均 {rounds:.1f} 輪",
    ]
    if boss:
        left = [o.boss_hp_permille for o in outcomes if not o.won]
        left_avg = f"{sum(left) / len(left) / 10:.0f}%" if left else "—"
        p2 = sum(o.phases >= 1 for o in outcomes) * 100 // n
        p3 = sum(o.phases >= 2 for o in outcomes) * 100 // n  # noqa: PLR2004
        lines.append(f"到第 2 階段 {p2}%、到第 3 階段 {p3}%、敗場 Boss 剩餘 HP 平均 {left_avg}")
    by_build: Counter[str] = Counter()
    played: Counter[str] = Counter()
    for o in outcomes:
        played[o.build] += 1
        by_build[o.build] += o.won
    lines.append(
        "build 勝場："
        + "、".join(f"{b.removeprefix('build_')} {by_build[b]}/{played[b]}" for b in sorted(played))
    )
    if not boss:
        by_place: Counter[str] = Counter()
        place_n: Counter[str] = Counter()
        for o in outcomes:
            place_n[o.label] += 1
            by_place[o.label] += o.won
        lines.append(
            "地點勝場：" + "、".join(f"{p} {by_place[p]}/{place_n[p]}" for p in sorted(place_n))
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--runs", type=int, default=40)
    parser.add_argument("--only", choices=("general", "boss"), default=None)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--boss-hp", default="", help="候選的灰燼之心 HP（逗號分隔；空＝現值）")
    args = parser.parse_args(argv)
    jobs: dict[str, list[tuple[str, str, str, int, int | None]]] = {}
    if args.only in (None, "general"):
        jobs["荒原一般遭遇"] = [
            (loc, BUILDS[i % len(BUILDS)], loc, 1000 + i, None)
            for i in range(args.runs)
            for loc in (GENERAL_LOCATIONS[i % len(GENERAL_LOCATIONS)],)
        ]
    if args.only in (None, "boss"):
        candidates = [int(v) for v in args.boss_hp.split(",") if v] or [None]
        for hp in candidates:
            label = "現值" if hp is None else f"HP {hp}"
            jobs[f"灰燼之心（熔心坑，9 級；{label}）"] = [
                (BOSS_LOCATION, BUILDS[i % len(BUILDS)], BOSS_LOCATION, 2000 + i, hp)
                for i in range(args.runs)
            ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for title, batch in jobs.items():
            outcomes = list(pool.map(_run, batch))
            print(summarize(title, outcomes, boss=title.startswith("灰燼之心")))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
