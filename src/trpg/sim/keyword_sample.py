"""關鍵字組合抽樣（Phase 3-24b2，``docs/design/06-技能.md`` 6.27.6）：``trpg sim keywords``。

每個樣本以種子抽一把武器與 2 個關鍵字（與 ``trpg run auto`` 沒有指定開局時相同：
:func:`trpg.roguelite.start.default_start`），照新開局的規則從兩個池子各給 1 招起始技能，組成
一名測試角色（:func:`trpg.roguelite.start.new_keyword_run` 的主角，Lv1、屬性配在武器的縮放屬性），
再抽一張地圖（``plan/sample_map``），我方 ＝ 測試角色 ＋ roguelite 的標準隊友，敵方 ＝ 地圖的
預設陣容（``encounter``）。

``content/sim/builds.yaml`` 照舊是回歸範本（``trpg sim matrix``），不進開局。

確定性：樣本只取決於樣本種子；戰鬥由 :func:`trpg.sim.batch.run_batches` 執行（與 ``--jobs`` 無關）。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.engine.setup import UnitSpawn, build_setup
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.shared.rng import Rng
from trpg.shared.types import Team
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    BatchReport,
    BatchSpec,
    UtilityPolicyFactory,
    run_batches,
)

__all__ = ["KeywordSample", "SampleResult", "format_samples", "keyword_samples", "run_samples"]


@dataclass(frozen=True, slots=True)
class KeywordSample:
    """一個樣本：樣本種子、武器、關鍵字、起始技能、地圖與戰鬥設定。"""

    seed: int
    weapon: str
    keywords: tuple[str, ...]
    skills: tuple[str, ...]
    """起始技能的中文名。"""
    map_id: str
    spec: BatchSpec


@dataclass(frozen=True, slots=True)
class SampleResult:
    sample: KeywordSample
    report: BatchReport


def _sample(
    library: ContentLibrary, seed: int, maps: Sequence[str], battles: int, max_rounds: int
) -> KeywordSample:
    weapon, keywords = default_start(library, seed)
    run = new_keyword_run(library, weapon, keywords, seed)
    map_id = Rng(seed).fork("plan/sample_map").choice(sorted(maps))
    encounter = library.map(map_id).encounter
    if encounter is None:
        raise ValueError(f"{map_id} 沒有預設陣容（encounter）")
    base = build_setup(
        library,
        map_id,
        library.roguelite.companions,
        encounter.enemies,
        max_rounds=max_rounds,
    )
    hero = UnitSpawn(
        template=run.hero,
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
    battle_seeds = tuple(
        Rng(seed).fork(f"plan/sample_battle/{i}").next_u32() for i in range(battles)
    )
    spec = BatchSpec(
        name=f"{seed}",
        setup=setup,
        seeds=battle_seeds,
        policy_factory=UtilityPolicyFactory(library.ai_profiles),
    )
    generated = {g.id: g.name_zh for g in run.generated_skills}
    names = tuple(
        library.skills[i].name_zh if i in library.skills else generated[i] for i in run.hero.skills
    )
    return KeywordSample(seed, weapon, keywords, names, map_id, spec)


def keyword_samples(
    library: ContentLibrary,
    *,
    samples: int,
    seed_start: int,
    maps: Sequence[str],
    battles: int = 1,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> list[KeywordSample]:
    """樣本種子 ``seed_start``～``seed_start + samples − 1`` 的樣本（每個樣本 ``battles`` 場）。"""
    if not maps:
        raise ValueError("至少要有一張地圖")
    return [
        _sample(library, seed, maps, battles, max_rounds)
        for seed in range(seed_start, seed_start + samples)
    ]


def run_samples(samples: Sequence[KeywordSample], *, jobs: int = 1) -> list[SampleResult]:
    reports = run_batches([s.spec for s in samples], jobs=jobs)
    return [SampleResult(s, r) for s, r in zip(samples, reports, strict=True)]


def _rate(wins: int, battles: int) -> str:
    return "—" if battles == 0 else f"{wins * 100 // battles}%"


def format_samples(library: ContentLibrary, results: Sequence[SampleResult]) -> str:
    """報表：每個樣本一行，加上依關鍵字、依武器大類的勝率摘要。"""
    defs = library.keywords.by_id()
    lines = [
        "| 樣本 | 武器 | 關鍵字 | 起始技能 | 地圖 | 我方勝 | 完成 | 平均輪數 |",
        "|" + "---|" * 8,
    ]
    by_keyword: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_class: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    errors = 0
    for result in results:
        s, r = result.sample, result.report
        names = "＋".join(defs[k].name_zh for k in s.keywords)
        skills = "、".join(s.skills)
        lines.append(
            f"| {s.seed} | {library.weapons[s.weapon].name_zh} | {names} | {skills} | {s.map_id} "
            f"| {r.ally_wins}/{r.battles} | {r.completed}/{r.battles} | {r.rounds_mean:.1f} |"
        )
        errors += r.battles - r.completed
        for key, table in ((k, by_keyword) for k in s.keywords):
            table[key][0] += r.ally_wins
            table[key][1] += r.battles
        weapon_class = library.weapons[s.weapon].weapon_class
        by_class[weapon_class][0] += r.ally_wins
        by_class[weapon_class][1] += r.battles
    total_wins = sum(r.report.ally_wins for r in results)
    total = sum(r.report.battles for r in results)
    lines.append("")
    lines.append(f"合計：{len(results)} 個樣本、{total} 場，我方勝率 {_rate(total_wins, total)}")
    lines.append(f"未完成（例外或動作上限）：{errors} 場")
    lines.append(
        "依關鍵字："
        + "、".join(
            f"{defs[k].name_zh} {_rate(*by_keyword[k])}（{by_keyword[k][1]} 場）"
            for k in library.keywords.ids()
            if k in by_keyword
        )
    )
    lines.append(
        "依武器大類："
        + "、".join(f"{c} {_rate(*by_class[c])}（{by_class[c][1]} 場）" for c in sorted(by_class))
    )
    return "\n".join(lines)
