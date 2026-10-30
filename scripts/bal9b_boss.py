"""BAL-9b：Boss 戰頭目 HP 倍率對照與輸場追蹤（只量不調；頭目 HP 只在模擬覆寫）。

用法::

    uv run python scripts/bal9b_boss.py --mults 1000,800,700,650,500 --seeds 60 --jobs 8 \
        --out docs/phases/BAL-9b/boss_hp.md

每個倍率、每個起始包（有召喚 3 包＋無召喚 3 包）、每個種子一場 Boss 戰（與
``run_boss_config`` 同一套跑法與同一批種子），用 ``on_step`` 追蹤每場：
結果、輪數、頭目死亡輪、頭目殘血、第 3 輪援軍到場時頭目 HP、我方死亡時間、
敵方傷害落點（英雄／隊友／召喚物）依頭目血量分段、頭目回合與最近我方的距離。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from bal9_sweep import with_boss_hp  # type: ignore[import-not-found]
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import DamageDealt, TurnStarted, UnitDowned
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import run_battle
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId
from trpg.sim.attrition import PLAIN_PACKS, SUMMON_PACKS
from trpg.sim.parallel import run_tasks
from trpg.sim.summon_report import BOSS_MAP, _spec

REINFORCE_ROUND = 3
BASE_PERMILLE = 1000


@dataclass
class Rec:
    pack: str
    seed: int
    mult: int
    summon: bool
    win: bool = False
    rounds: int = 0
    end_reason: str = ""
    boss_dead_round: int | None = None
    boss_frac_end: float = 1.0
    boss_frac_r3: float | None = None  # 第 3 輪開始時頭目血量比（None＝沒打到第 3 輪）
    reinforced: bool = False  # 援軍到場時（第 3 輪起）戰鬥仍在進行
    allies_down: list[int] = field(default_factory=list)  # 我方（非召喚）倒下的輪數
    hero_down_round: int | None = None
    enemies_alive_end: int = 0
    allies_alive_end: int = 0
    # 敵方傷害落點：(phase, kind) → 傷害；phase: hi（頭目血 > 50%）／lo（<= 50%）
    dmg: dict[str, int] = field(default_factory=dict)
    # 頭目回合與最近存活我方（非召喚）的曼哈頓距離總和／次數，依 phase
    dist: dict[str, list[int]] = field(default_factory=dict)
    # 我方（含召喚物）打出的傷害依目標範本；敵方打出的傷害依來源範本
    out_by_target: dict[str, int] = field(default_factory=dict)
    in_by_source: dict[str, int] = field(default_factory=dict)
    # 各敵方範本被擊倒的輪數（範本 → 輪數列表）
    enemy_down: dict[str, list[int]] = field(default_factory=dict)


def _kind(state: BattleState, uid: UnitId, hero: UnitId) -> str:
    u = state.units[uid]
    if uid == hero:
        return "hero"
    return "summon" if u.is_summon else "comp"


def _on_downed(rec: Rec, state: BattleState, e: UnitDowned, hero: UnitId) -> None:
    u = state.units[e.unit_id]
    if u.team is Team.ENEMY:
        rec.enemy_down.setdefault(u.template_id, []).append(state.round)
    if u.team is Team.ALLY and not u.is_summon:
        rec.allies_down.append(state.round)
        if e.unit_id == hero and rec.hero_down_round is None:
            rec.hero_down_round = state.round


def _on_damage(rec: Rec, state: BattleState, e: DamageDealt, hero: UnitId, ph: str) -> None:
    assert e.source_id is not None
    src = state.units.get(e.source_id)
    tgt = state.units.get(e.target_id)
    if not src or not tgt:
        return
    if src.team is Team.ALLY and tgt.team is Team.ENEMY:
        rec.out_by_target[tgt.template_id] = rec.out_by_target.get(tgt.template_id, 0) + e.amount
    elif src.team is Team.ENEMY and tgt.team is Team.ALLY:
        rec.in_by_source[src.template_id] = rec.in_by_source.get(src.template_id, 0) + e.amount
        k = f"{ph}:{_kind(state, e.target_id, hero)}"
        rec.dmg[k] = rec.dmg.get(k, 0) + e.amount


def run_one(libs: dict[int, ContentLibrary], task: tuple[str, int, int]) -> Rec:
    pack, seed, mult = task
    lib = libs[mult]
    spec, hero_id_s = _spec(lib, pack, BOSS_MAP, seed, 30)
    rec = Rec(pack, seed, mult, pack in SUMMON_PACKS)
    ids: dict[str, UnitId] = {}

    def phase(state: BattleState) -> str:
        boss = state.units[ids["boss"]]
        return "hi" if boss.hp * 2 > boss.max_hp else "lo"

    def on_step(step: object, result: object) -> None:
        state: BattleState = result.state  # type: ignore[attr-defined]
        events = result.events  # type: ignore[attr-defined]
        if not ids:
            boss = next(u for u in state.units.values() if "boss" in u.tags)
            ids["boss"] = boss.id
            ids["hero"] = next(
                u.id for u in state.units.values() if u.team is Team.ALLY and not u.is_summon
            )
        boss = state.units[ids["boss"]]
        if rec.boss_frac_r3 is None and state.round >= REINFORCE_ROUND:
            rec.boss_frac_r3 = boss.hp / boss.max_hp
            rec.reinforced = True
        if not boss.alive and rec.boss_dead_round is None:
            rec.boss_dead_round = state.round
        ph = phase(state)
        for e in events:
            if isinstance(e, UnitDowned):
                _on_downed(rec, state, e, ids["hero"])
            elif isinstance(e, DamageDealt) and e.source_id is not None:
                _on_damage(rec, state, e, ids["hero"], ph)
            elif isinstance(e, TurnStarted) and e.unit_id == ids["boss"] and boss.alive:
                near = [
                    manhattan(boss.xy, u.xy)
                    for u in state.units.values()
                    if u.alive and u.team is Team.ALLY and not u.is_summon
                ]
                if near:
                    rec.dist.setdefault(ph, []).append(min(near))

    run = run_battle(
        spec.setup, spec.seeds[0], spec.policy_factory(), on_step=on_step, max_actions=20000
    )
    final = run.state
    boss = final.units[ids["boss"]]
    rec.rounds = final.round
    rec.win = bool(final.winner is Team.ALLY) if hasattr(final, "winner") else False
    rec.boss_frac_end = max(0, boss.hp) / boss.max_hp
    rec.enemies_alive_end = sum(1 for u in final.units.values() if u.alive and u.team is Team.ENEMY)
    rec.allies_alive_end = sum(
        1 for u in final.units.values() if u.alive and u.team is Team.ALLY and not u.is_summon
    )
    del hero_id_s
    return rec


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return 100 * (c - m) / d, 100 * (c + m) / d


def summarize(recs: Sequence[Rec]) -> str:
    n = len(recs)
    w = sum(r.win for r in recs)
    lo, hi = wilson(w, n)
    rounds = statistics.mean(r.rounds for r in recs)
    return f"{100 * w / n:.1f}%（{w}/{n}，95%CI {lo:.0f}–{hi:.0f}）／{rounds:.1f}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mults", default="1000,800,700,650,500")
    p.add_argument("--seeds", type=int, default=60)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--plain-only", action="store_true", help="只跑無召喚三包")
    p.add_argument("--dump", type=Path, default=None, help="逐場記錄（JSON）")
    args = p.parse_args(argv)
    mults = [int(x) for x in args.mults.split(",")]
    base = load_library()
    libs = {m: (base if m == BASE_PERMILLE else with_boss_hp(base, m)) for m in mults}
    tasks = [
        (pack, s, m)
        for m in mults
        for pack in (PLAIN_PACKS if args.plain_only else (*SUMMON_PACKS, *PLAIN_PACKS))
        for s in range(args.seeds)
    ]
    recs = run_tasks(run_one, libs, tasks, jobs=args.jobs)
    if args.dump:
        args.dump.parent.mkdir(parents=True, exist_ok=True)
        args.dump.write_text(
            json.dumps([dataclasses.asdict(r) for r in recs], ensure_ascii=False), encoding="utf-8"
        )
    lines = ["| 頭目 HP | 有召喚 勝率／輪數 | 無召喚 勝率／輪數 |", "|---|---|---|"]
    for m in mults:
        sel = [r for r in recs if r.mult == m]
        s = [r for r in sel if r.summon]
        pl = [r for r in sel if not r.summon]
        sm = summarize(s) if s else "—"
        lines.append(f"| {m}‰ | {sm} | {summarize(pl)} |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
