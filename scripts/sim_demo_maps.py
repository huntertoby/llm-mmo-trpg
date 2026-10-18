"""示範地圖的批次模擬：效用 AI 對戰 N 個種子的我方勝率與輪數（Phase 1C 決定 #4）。

用法::

    uv run python scripts/sim_demo_maps.py [--seeds 20] [--maps bridge_chasm,oil_depot]

每張地圖使用地圖檔的預設陣容（``encounter``）、``max_rounds=30``、種子 ``0 … N−1``。
目標（docs/phases/Phase1C計畫.md 2.5 #4）：我方勝率 35%–65%、平均輪數 4–6。

最後另外印出技能使用統計（Phase 2A-2 6.4 第 5 條）：每個技能在全部場次中被使用的次數、命中的
次數與命中率（每個目標各擲一次）、平均傷害（該技能直接造成的傷害 ÷ 使用次數；連鎖爆炸、表面等
間接傷害不計）。只列出，不調整。
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

from trpg.content.library import load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import AttackRolled, DamageDealt, EventBase, Healed, SkillUsed
from trpg.engine.runner import run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Team

DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp", "ruined_fort")
MAX_ROUNDS = 30


@dataclass
class SkillStats:
    """一個技能的累計統計。"""

    uses: int = 0
    rolls: int = 0
    hits: int = 0
    damage: int = 0
    healed: int = 0
    teams: Counter[str] = field(default_factory=Counter)


def collect_skill_stats(
    events: list[EventBase], teams: dict[str, Team], stats: dict[str, SkillStats]
) -> None:
    """把一場戰鬥的事件累計進 ``stats``。

    ``skill_used`` 之後、下一個動作（沒有 ``skill_id`` 的命中擲骰、或下一個 ``skill_used``）之前的
    「cause=attack」傷害與治療歸給該技能。
    """
    current: str | None = None
    caster: str | None = None
    for event in events:
        if isinstance(event, SkillUsed):
            current, caster = event.skill_id, event.unit_id
            entry = stats.setdefault(current, SkillStats())
            entry.uses += 1
            entry.teams["我方" if teams[event.unit_id] is Team.ALLY else "敵方"] += 1
        elif isinstance(event, AttackRolled):
            current, caster = event.skill_id, event.attacker_id
            if current is not None:
                entry = stats.setdefault(current, SkillStats())
                entry.rolls += 1
                entry.hits += 1 if event.hit else 0
        elif (
            isinstance(event, DamageDealt)
            and current is not None
            and event.cause == "attack"
            and event.source_id == caster
        ):
            stats.setdefault(current, SkillStats()).damage += event.amount
        elif isinstance(event, Healed) and current is not None and event.source_id == caster:
            stats.setdefault(current, SkillStats()).healed += event.amount


def print_skill_stats(stats: dict[str, SkillStats], names: dict[str, str]) -> None:
    print()
    print("技能使用統計（全部地圖、全部種子）")
    print("| 技能 | 陣營 | 使用次數 | 命中率 | 平均傷害／次 | 平均治療／次 |")
    print("|---|---|---|---|---|---|")
    for skill_id in sorted(stats, key=lambda k: (-stats[k].uses, k)):
        e = stats[skill_id]
        side = "、".join(f"{t} {n}" for t, n in sorted(e.teams.items()))
        rate = f"{e.hits}/{e.rolls}（{e.hits / e.rolls:.0%}）" if e.rolls else "—"
        avg = f"{e.damage / e.uses:.1f}" if e.uses else "—"
        heal = f"{e.healed / e.uses:.1f}" if e.healed else "—"
        label = f"{names.get(skill_id, skill_id)}（{skill_id}）"
        print(f"| {label} | {side} | {e.uses} | {rate} | {avg} | {heal} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="示範地圖的批次模擬")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--maps", default=",".join(DEMO_MAPS))
    args = parser.parse_args(argv)
    library = load_library()
    ai = UtilityAI(library.ai_profiles)
    print(f"效用 AI，種子 0–{args.seeds - 1}，max_rounds={MAX_ROUNDS}")
    stats: dict[str, SkillStats] = {}
    print("| 地圖 | 我方勝 | 敵方勝 | 平手 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場時間 |")
    print("|---|---|---|---|---|---|---|---|")
    for map_id in args.maps.split(","):
        encounter = library.map(map_id).encounter
        if encounter is None:
            raise SystemExit(f"{map_id} 沒有預設陣容（encounter）")
        setup = build_setup(
            library, map_id, encounter.allies, encounter.enemies, max_rounds=MAX_ROUNDS
        )
        wins = {Team.ALLY: 0, Team.ENEMY: 0, None: 0}
        rounds: list[int] = []
        start = time.perf_counter()
        for seed in range(args.seeds):
            run = run_battle(setup, seed, ai)
            state = run.state
            collect_skill_stats(
                list(run.events), {u.id: u.team for u in state.units.values()}, stats
            )
            wins[state.winner] += 1
            rounds.append(state.round)
        elapsed = (time.perf_counter() - start) / args.seeds
        rate = wins[Team.ALLY] / args.seeds
        print(
            f"| {map_id} | {wins[Team.ALLY]} | {wins[Team.ENEMY]} | {wins[None]} | "
            f"{rate:.0%} | {statistics.mean(rounds):.2f} | {min(rounds)}–{max(rounds)} | "
            f"{elapsed * 1000:.0f} ms |",
            flush=True,
        )
    print_skill_stats(stats, {s.id: s.name_zh for s in library.skills.values()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
