"""賽季 Boss「碎晶之主」的小模擬（Phase 5F-3；``docs/phases/Phase5計畫.md`` 37.9、19.7 #87）。

走大世界的真實路徑：角色在城鎮挑戰（``season_boss`` 的遭遇）、``prepare_battle`` 開戰——我方＝主角＋
2 名系統傭兵（輸出與控制主角帶預設的鐵壁、回春；守護主角帶赤焰、回春；輔助主角帶赤焰、穿雲；照主角
等級成長、穿系統裝備）、敵方＝本體＋三根源晶柱（10 級），地圖裂界門。主角是數種 build 的底稿照
大世界敵我同一套成長規則拉到 10 級（屬性、HP、技能階級；``grow_enemy``）。
雙方都由效用 AI 操作；``max_rounds`` 照世界規則（30，超過算敗）。

用法::

    uv run python scripts/season_boss_sim.py [--seeds 5] [--builds build_striker,build_fire]
    uv run python scripts/season_boss_sim.py --sweep 380:60,450:60   # 候選「本體HP:柱子HP」

只輸出摘要表（勝率、平均輪數、敗場本體剩餘 HP、到第 2／3 階段的比例）；數值建議寫進報告由 PM 決定
（CLAUDE.md 第 11 條）。
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
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
from trpg.world.clock import day_phase
from trpg.world.party import default_party
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character

BOSS = "rift_shard_lord"
LEVEL = 10
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
"""輸出、守護、輔助、控制各 2 種（#87）。"""
PARTIES = {
    "build_tank": ("merc_chiyan", "merc_huichun"),
    "build_guardian": ("merc_chiyan", "merc_huichun"),
    "build_healer": ("merc_chiyan", "merc_chuanyun"),
    "build_support": ("merc_chiyan", "merc_chuanyun"),
}
"""主角是守護或輔助時改帶輸出傭兵（其他主角帶預設的鐵壁＋回春）：玩家會挑補足自己的傭兵。"""


@dataclass(frozen=True)
class Outcome:
    build: str
    won: bool
    rounds: int
    boss_hp_permille: int
    phases: int


PILLARS = ("rift_pillar_mist", "rift_pillar_thunder", "rift_pillar_fire")

type Candidate = tuple[int, int] | None
"""候選（本體 HP, 柱子 HP）（1 級基準）；``None``＝現值。"""


def _library(candidate: Candidate) -> ContentLibrary:
    library = load_library()
    if candidate is None:
        return library
    boss_hp, pillar_hp = candidate
    units = dict(library.units)
    units[BOSS] = units[BOSS].model_copy(update={"max_hp": boss_hp})
    for pillar in PILLARS:
        units[pillar] = units[pillar].model_copy(update={"max_hp": pillar_hp})
    return dataclasses.replace(library, units=units)


def make_char(library: ContentLibrary, build_id: str, seed: int) -> CharacterState:
    """10 級的主角（照敵我同一套成長）＋預設傭兵，身上有賽季 Boss 的遭遇。"""
    base = next(b.hero for b in library.builds.builds if b.id == build_id)
    grown, skills = grow_enemy(library, base, LEVEL)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1})  # 等級 HP 由開戰時加
    char = new_character(library, "sim", hero, region="cloud_ridge")
    boss = library.world_season.season_boss if library.world_season is not None else None
    assert boss is not None
    encounter = EncounterResult(
        region="cloud_ridge",
        location=char.location,
        level=boss.level,
        battle_map=boss.battle_map,
        battle_seed=seed,
        weather="clear",
        day_phase=day_phase(NOON),
        at=NOON,
        season_boss=boss.id,
    )
    return char.model_copy(
        update={
            "level": LEVEL,
            "mercenaries": PARTIES.get(build_id, default_party(library)),
            "generated_skills": skills,
            "pending_encounter": encounter,
        }
    )


def _run(args: tuple[str, int, Candidate]) -> Outcome:
    build_id, seed, candidate = args
    library = _library(candidate)
    prepared = prepare_battle(library, make_char(library, build_id, seed))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    boss = next(u for u in run.state.units.values() if u.template_id == BOSS)
    boss_unit = boss.id
    changes = [e for e in run.events if isinstance(e, BossPhaseChanged) and e.unit_id == boss_unit]
    return Outcome(
        build=build_id,
        won=run.state.winner is Team.ALLY,
        rounds=run.state.round,
        boss_hp_permille=boss.hp * 1000 // max(1, boss.max_hp),
        phases=len(changes),
    )


def summarize(label: str, outcomes: Sequence[Outcome]) -> str:
    n = len(outcomes)
    wins = sum(o.won for o in outcomes)
    rounds = sum(o.rounds for o in outcomes) / n
    won_rounds = [o.rounds for o in outcomes if o.won]
    won_avg = f"{sum(won_rounds) / len(won_rounds):.1f}" if won_rounds else "—"
    left = [o.boss_hp_permille for o in outcomes if not o.won]
    left_avg = f"{sum(left) / len(left) / 10:.0f}%" if left else "—"
    p2 = sum(o.phases >= 1 for o in outcomes) * 100 // n
    p3 = sum(o.phases >= 2 for o in outcomes) * 100 // n  # noqa: PLR2004 - 第 3 階段＝轉換 2 次
    return (
        f"| {label} | {n} | {wins * 100 // n}% | {rounds:.1f} | {won_avg} | {left_avg} "
        f"| {p2}% | {p3}% |"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--builds", default=",".join(BUILDS))
    parser.add_argument(
        "--sweep", default="", help="候選「本體HP:柱子HP」（1 級基準），逗號分隔；不改 content"
    )
    args = parser.parse_args(argv)
    builds = [b for b in args.builds.split(",") if b]
    candidates: list[Candidate] = [
        (int(a), int(b)) for a, b in (v.split(":") for v in args.sweep.split(",") if v)
    ] or [None]
    print("| 條件 | 場數 | 勝率 | 平均輪數 | 勝場輪數 | 敗場本體剩餘 HP | 柱子全倒 | 到核心過載 |")
    print("|---|---|---|---|---|---|---|---|")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for candidate in candidates:
            jobs = [(b, seed, candidate) for b in builds for seed in range(1, args.seeds + 1)]
            outcomes = list(pool.map(_run, jobs))
            prefix = "現值" if candidate is None else f"本體 {candidate[0]}／柱 {candidate[1]}"
            for build in builds:
                rows = [o for o in outcomes if o.build == build]
                print(summarize(f"{prefix}・{build}", rows), flush=True)
            print(summarize(f"{prefix}・全部", outcomes), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
