"""雲頂觀 Boss 階段的小模擬（Phase 5F-2；``docs/phases/Phase5計畫.md`` 34.8）。

在 Boss 地圖 ``cloud_summit`` 上，同一組陣容各跑若干種子，比較霧鎖真人 **沒有階段**（同範本拿掉
``phases``，整場停在第 1 階段）與 **有階段** 的勝率、平均輪數、真人剩餘 HP 與各階段到達率。

- 隊伍：地圖預設的原型三人（``hero_fighter``、``hero_archer``、``hero_mage``），1 級與 6 級
  （6 級＝雲頂觀建議等級；敵我都照大世界 ``grow_enemy``／``grow_allies`` 成長，召喚的霧行者同級）。
- 雙方都由效用 AI 操作；``max_rounds`` 30（超過算敗）。

用法::

    uv run python scripts/archive/boss_phase_sim.py [--seeds 40]
    uv run python scripts/archive/boss_phase_sim.py --sweep 100:30,110:40,120:40   # 5F-2b：候選 HP

``--sweep``（Phase 5F-2b）：只跑「有階段」，每組「真人 HP:石靈 HP」（範本的 1 級 ``max_hp``，體質
與等級成長照常）各跑 1 級與 6 級，不改 content。

只輸出摘要表；數值建議寫進報告由 PM 決定（CLAUDE.md 第 11 條）。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import BossPhaseChanged
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup, with_phase_assets
from trpg.engine.state import SpawnTemplate
from trpg.shared.types import Team
from trpg.world.battle import grow_allies, grow_enemy

MAP_ID = "cloud_summit"
BOSS = "sect_mist_lock_master"
STONE = "sect_summit_array_stone"
MAX_ROUNDS = 30
LEVELS = (1, 6)
LAST_PHASE_CHANGES = 2
"""到第 3 階段＝轉換 2 次。"""


@dataclass(frozen=True)
class Outcome:
    won: bool
    rounds: int
    boss_hp_permille: int
    phases: int


def _grow(library: ContentLibrary, setup: BattleSetup, level: int) -> BattleSetup:
    if level <= 1:
        return setup
    extra: dict[str, SkillDef] = {}
    allies = [u for u in setup.units if u.team is Team.ALLY]
    grown_allies, skills = grow_allies(library, allies, level)
    extra.update((s.id, s) for s in skills)
    enemies: list[UnitSpawn] = []
    for unit in setup.units:
        if unit.team is Team.ALLY:
            continue
        template, skills = grow_enemy(library, unit.template, level)
        extra.update((s.id, s) for s in skills)
        enemies.append(unit.model_copy(update={"template": template}))
    spawns: dict[str, SpawnTemplate] = {}
    for template_id, spawn in setup.spawn_templates.items():
        template, skills = grow_enemy(library, spawn.template, level)
        extra.update((s.id, s) for s in skills)
        spawns[template_id] = spawn.model_copy(update={"template": template})
    return setup.model_copy(
        update={
            "units": (*grown_allies, *enemies),
            "spawn_templates": spawns,
            "ruleset": library.ruleset.with_skills(extra[k] for k in sorted(extra)),
        }
    )


def _with_hp(setup: BattleSetup, hp: tuple[int, int] | None) -> BattleSetup:
    """候選 HP（5F-2b ``--sweep``）：真人與石靈範本的 ``max_hp`` 換成 ``hp``。"""
    if hp is None:
        return setup
    wanted = {BOSS: hp[0], STONE: hp[1]}
    units = tuple(
        u.model_copy(
            update={"template": u.template.model_copy(update={"max_hp": wanted[u.template.id]})}
        )
        if u.template.id in wanted
        else u
        for u in setup.units
    )
    return setup.model_copy(update={"units": units})


def make_setup(
    library: ContentLibrary, *, phases: bool, level: int, hp: tuple[int, int] | None = None
) -> BattleSetup:
    map_def = library.map(MAP_ID)
    assert map_def.encounter is not None
    setup = build_setup(
        library,
        MAP_ID,
        map_def.encounter.allies,
        map_def.encounter.enemies,
        max_rounds=MAX_ROUNDS,
    )
    if not phases:
        units = tuple(
            u.model_copy(update={"template": u.template.model_copy(update={"phases": ()})})
            if u.template.id == BOSS
            else u
            for u in setup.units
        )
        setup = setup.model_copy(
            update={"units": units, "spawn_templates": {}, "phase_weathers": {}}
        )
    setup = with_phase_assets(library, _with_hp(setup, hp))
    return _grow(library, setup, level)


def _run(args: tuple[bool, int, int, tuple[int, int] | None]) -> Outcome:
    phases, level, seed, hp = args
    library = load_library()
    setup = make_setup(library, phases=phases, level=level, hp=hp)
    run = run_battle(setup, seed, UtilityAI(library.ai_profiles))
    boss = next(u for u in run.state.units.values() if u.template_id == BOSS)
    return Outcome(
        won=run.state.winner is Team.ALLY,
        rounds=run.state.round,
        boss_hp_permille=boss.hp * 1000 // boss.max_hp,
        phases=sum(1 for e in run.events if isinstance(e, BossPhaseChanged)),
    )


def summarize(label: str, outcomes: Sequence[Outcome]) -> str:
    n = len(outcomes)
    wins = sum(o.won for o in outcomes)
    rounds = sum(o.rounds for o in outcomes) / n
    left = [o.boss_hp_permille for o in outcomes if not o.won]
    left_avg = f"{sum(left) / len(left) / 10:.0f}%" if left else "—"
    p2 = sum(o.phases >= 1 for o in outcomes) * 100 // n
    p3 = sum(o.phases >= LAST_PHASE_CHANGES for o in outcomes) * 100 // n
    return f"| {label} | {n} | {wins * 100 // n}% | {rounds:.1f} | {left_avg} | {p2}% | {p3}% |"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--sweep", default="", help="候選「真人HP:石靈HP」，逗號分隔")
    args = parser.parse_args(argv)
    print("| 條件 | 場數 | 勝率 | 平均輪數 | 敗場真人剩餘 HP | 到第 2 階段 | 到第 3 階段 |")
    print("|---|---|---|---|---|---|---|")
    if args.sweep:
        return _sweep(args.sweep, args.seeds, args.workers)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for level in LEVELS:
            for phases in (False, True):
                jobs = [(phases, level, seed, None) for seed in range(1, args.seeds + 1)]
                outcomes = list(pool.map(_run, jobs))
                label = f"{level} 級・{'有階段' if phases else '沒有階段'}"
                print(summarize(label, outcomes), flush=True)
    return 0


def _sweep(spec: str, seeds: int, workers: int) -> int:
    candidates = [tuple(int(v) for v in item.split(":")) for item in spec.split(",") if item]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for boss_hp, stone_hp in candidates:
            for level in LEVELS:
                hp = (boss_hp, stone_hp)
                jobs = [(True, level, seed, hp) for seed in range(1, seeds + 1)]
                outcomes = list(pool.map(_run, jobs))
                label = f"真人 {boss_hp}／石靈 {stone_hp}・{level} 級"
                print(summarize(label, outcomes), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
