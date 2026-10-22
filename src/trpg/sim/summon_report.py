"""召喚物現況模擬（Phase 3-33a，``docs/design/06-技能.md`` 6.29.7；``trpg sim summons``）。

只讀統計、不改規則：每個開發者起始包（``content/dev_starters.yaml``）× 地圖 × 種子打一場，
我方 ＝ 該起始包的主角（:func:`trpg.roguelite.start.new_dev_run`，Lv1）＋標準隊友，
敵方 ＝ 地圖的預設陣容；效用 AI。召喚物統計從現有事件推導
（:attr:`trpg.sim.metrics.BattleMetrics.summons`）。

確定性：結果只取決於（起始包、地圖、種子）；與 ``--jobs`` 無關。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.engine.setup import UnitSpawn, build_setup
from trpg.roguelite.start import new_dev_run
from trpg.shared.rng import Rng
from trpg.shared.types import Team
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    BatchSpec,
    UtilityPolicyFactory,
    run_outcomes,
)
from trpg.sim.metrics import BattleMetrics

__all__ = [
    "BOSS_MAP",
    "DEFAULT_PACKS",
    "SUMMON_MAPS",
    "BattleSample",
    "PackSummary",
    "format_summons",
    "run_summon_sim",
    "summarize",
]

DEFAULT_PACKS: tuple[str, ...] = (
    "dev_spirit",
    "dev_summoner",
    "dev_summoner_bone",
    "dev_bulwark",
    "dev_blaze",
    "dev_hawkeye",
)
"""喚靈、保證帶召喚技的喚靈對照（元素之靈、骷髏戰士；3-33b）、普攻為主（鐵壁：單手劍）、
技能為主（烈焰：火焰法杖）、遠程（鷹眼）。"""
BOSS_MAP = "boss"
"""特殊地圖 ID：一輪的 Boss 戰（``roguelite.yaml`` 的 ``boss``：專屬地圖與加強版頭目）。"""
SUMMON_MAPS: tuple[str, ...] = ("open_plain", "dark_forest", "ruined_fort", "swamp", "narrow_halls")
"""預設的 5 張正式地圖。"""


@dataclass(frozen=True, slots=True)
class BattleSample:
    """一場戰鬥：起始包、地圖、樣本種子與指標（失敗時 ``metrics`` 為 ``None``）。"""

    pack: str
    map_id: str
    seed: int
    hero_id: str
    metrics: BattleMetrics | None


def _spec(
    library: ContentLibrary, pack: str, map_id: str, seed: int, max_rounds: int
) -> tuple[BatchSpec, str]:
    run = new_dev_run(library, pack, seed)
    real_map = map_id
    enemies: tuple[str, ...]
    if map_id == BOSS_MAP:
        real_map, enemies = library.roguelite.boss.map, library.roguelite.boss.enemies
    else:
        encounter = library.map(map_id).encounter
        if encounter is None:
            raise ValueError(f"{map_id} 沒有預設陣容（encounter）")
        enemies = encounter.enemies
    base = build_setup(
        library, real_map, library.roguelite.companions, enemies, max_rounds=max_rounds
    )
    hero = UnitSpawn(
        template=run.hero.model_copy(update={"level": run.level}),
        weapon=library.weapons[run.hero.weapon],
        equipment=library.loadout_of(run.hero),
        team=Team.ALLY,
    )
    setup = base.model_copy(
        update={
            "units": (hero, *base.units),
            "ruleset": library.ruleset.with_skills(run.generated_skills),
        }
    )
    battle_seed = Rng(seed).fork(f"plan/summon_sim/{pack}/{map_id}").next_u32()
    spec = BatchSpec(
        name=f"{pack}/{map_id}/{seed}",
        setup=setup,
        seeds=(battle_seed,),
        policy_factory=UtilityPolicyFactory(library.ai_profiles),
    )
    return spec, run.hero.id


def run_summon_sim(
    library: ContentLibrary,
    *,
    packs: Sequence[str] = DEFAULT_PACKS,
    maps: Sequence[str] = SUMMON_MAPS,
    seeds: int = 4,
    seed_start: int = 0,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    jobs: int = 1,
) -> list[BattleSample]:
    """每個起始包 × 地圖 × ``seeds`` 個種子各打一場；結果依（起始包、地圖、種子）排序。"""
    keys = [
        (pack, map_id, seed)
        for pack in packs
        for map_id in maps
        for seed in range(seed_start, seed_start + seeds)
    ]
    built = [_spec(library, *key, max_rounds) for key in keys]
    outcomes = run_outcomes([spec for spec, _ in built], jobs=jobs)
    return [
        BattleSample(pack, map_id, seed, hero_id, out[0].metrics)
        for (pack, map_id, seed), (_, hero_id), out in zip(keys, built, outcomes, strict=True)
    ]


@dataclass(frozen=True, slots=True)
class PackSummary:
    """一個起始包的彙總（只計完成的戰鬥）。"""

    pack: str
    battles: int
    failed: int
    wins: int
    rounds_mean: float
    hero_dpr: float
    """主角的平均 DPR（造成的傷害 ÷ 存活輪數，每場平均）。"""
    ally_damage: float
    """我方每場總傷害（含召喚物）。"""
    summon_damage: float
    """我方召喚物每場造成的傷害。"""
    summon_share: float
    """召喚物傷害占我方總傷害的比例（合計比，不是每場比例的平均）。"""
    summons_per_battle: float
    summons_total: int
    battles_with_summon: int
    """我方至少召喚過一次的戰鬥數。"""
    life_rounds_mean: float | None
    """每隻召喚物的平均存活輪數（出現後經過的 ``round_started``；沒有召喚物時 ``None``）。"""
    turns_mean: float | None
    """每隻召喚物平均行動的回合數。"""
    first_summon_round_mean: float | None
    """有召喚的戰鬥中，第一隻召喚物出現的平均輪數。"""
    ends: dict[str, int]
    """召喚物的結束原因計數。"""


def _mean(values: Sequence[int | Fraction]) -> float | None:
    return float(sum(values, Fraction(0)) / len(values)) if values else None


def summarize(samples: Sequence[BattleSample]) -> list[PackSummary]:
    """依起始包（保持出現順序）彙總。"""
    order: list[str] = []
    for s in samples:
        if s.pack not in order:
            order.append(s.pack)
    return [_summarize_pack(p, [s for s in samples if s.pack == p]) for p in order]


def _summarize_pack(pack: str, samples: Sequence[BattleSample]) -> PackSummary:
    done = [(s, s.metrics) for s in samples if s.metrics is not None]
    dprs: list[Fraction] = []
    life: list[int] = []
    turns: list[int] = []
    first: list[int] = []
    ends: Counter[str] = Counter()
    ally_total = summon_total = summons = wins = 0
    for sample, m in done:
        unit_by_id = {u.unit_id: u for u in m.units}
        hero = next(u for u in m.units if u.team is Team.ALLY and u.template_id == sample.hero_id)
        dprs.append(hero.dpr)
        ally_total += m.team_damage(Team.ALLY)
        summon_total += m.summon_damage(Team.ALLY)
        wins += m.result == "ally"
        mine = [r for r in m.summons if r.team is Team.ALLY]
        summons += len(mine)
        for r in mine:
            life.append(unit_by_id[r.unit_id].alive_rounds)
            turns.append(unit_by_id[r.unit_id].turns)
            ends[r.end] += 1
        if mine:
            first.append(min(r.spawn_round for r in mine))
    n = len(done)
    return PackSummary(
        pack=pack,
        battles=n,
        failed=len(samples) - n,
        wins=wins,
        rounds_mean=sum(m.rounds for _, m in done) / n if n else 0.0,
        hero_dpr=_mean(dprs) or 0.0,
        ally_damage=ally_total / n if n else 0.0,
        summon_damage=summon_total / n if n else 0.0,
        summon_share=summon_total / ally_total if ally_total else 0.0,
        summons_per_battle=summons / n if n else 0.0,
        summons_total=summons,
        battles_with_summon=len(first),
        life_rounds_mean=_mean(life),
        turns_mean=_mean(turns),
        first_summon_round_mean=_mean(first),
        ends=dict(sorted(ends.items())),
    )


def _fmt(value: float | None, spec: str = ".1f") -> str:
    return "—" if value is None else format(value, spec)


def format_summons(summaries: Sequence[PackSummary], labels: dict[str, str]) -> str:
    """Markdown 摘要表。"""
    lines = [
        "| 起始包 | 場數 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 "
        "| 召喚次數/場 | 有召喚場數 | 平均存活輪數 | 平均行動回合 | 首召輪 |",
        "|" + "---|" * 13,
    ]
    for s in summaries:
        win = "—" if s.battles == 0 else f"{s.wins * 100 // s.battles}%"
        lines.append(
            f"| {labels.get(s.pack, s.pack)}（{s.pack}） | {s.battles} | {win} "
            f"| {s.rounds_mean:.1f} | {s.hero_dpr:.1f} | {s.ally_damage:.0f} "
            f"| {s.summon_damage:.0f} | {s.summon_share * 100:.1f}% | {s.summons_per_battle:.2f} "
            f"| {s.battles_with_summon} | {_fmt(s.life_rounds_mean)} | {_fmt(s.turns_mean)} "
            f"| {_fmt(s.first_summon_round_mean)} |"
        )
    lines.append("")
    for s in summaries:
        if s.ends:
            ends = "、".join(f"{k} {v}" for k, v in s.ends.items())
            lines.append(f"召喚物結束原因（{s.pack}，共 {s.summons_total} 隻）：{ends}")
    failed = sum(s.failed for s in summaries)
    lines.append(f"未完成（例外或動作上限）：{failed} 場")
    return "\n".join(lines)
