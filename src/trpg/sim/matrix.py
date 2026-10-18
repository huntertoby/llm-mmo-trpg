"""build × 地圖矩陣（Phase 2C-3 5.4；``docs/design/06-技能.md`` 6.8）。

每個（build, 地圖）跑一批戰鬥：我方 ＝ build 英雄 ＋ 標準隊友（``content/sim/builds.yaml``），
敵方 ＝ 地圖 ``encounter.enemies``。每格記錄我方勝率、build 英雄的 DPR 與存活率、平均輪數。

- **排名**：每張地圖內依「勝率，平手比 build 英雄 DPR」排序（仍相同時依 build 在檔案中的順序）；
  **前段 ＝ 前 ``max(1, n ÷ 3)`` 名**（6 個 build 時為前 2 名）。
- **地圖類型**：同一類型有多張地圖時，勝率、DPR、存活率、輪數取各地圖的平均，再以同樣的規則排名。
- **兩條標準**：(1) 沒有任何 build 在所有地圖類型都排名前段；
  (2) 每個 build 至少在一種地圖類型排名前段。
  這裡只檢查並列出，不通過不算失敗（平衡由 2C-4 處理）。

純函式 :func:`assemble_matrix` 由各格的原始數字計算排名與標準（測試用手工的小矩陣）；
:func:`run_matrix` 負責跑模擬。報表不含時間，相同的輸入必得逐字相同的輸出，且與 ``jobs`` 無關。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction

from pydantic import BaseModel, ConfigDict, TypeAdapter

from trpg.content.library import ContentLibrary
from trpg.content.maps import ARCHETYPES
from trpg.engine.setup import build_setup
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    BatchReport,
    BatchSpec,
    UtilityPolicyFactory,
    run_batches,
)

__all__ = [
    "ArchetypeCell",
    "MapInfo",
    "MatrixCell",
    "MatrixReport",
    "RawCell",
    "Standards",
    "assemble_matrix",
    "format_matrix",
    "library_with_builds",
    "matrix_specs",
    "run_matrix",
    "top_count",
]


MIN_ARCHETYPES_FOR_STANDARD_1 = 2


def top_count(builds: int) -> int:
    """「前段」的名次數：``max(1, builds ÷ 3)``（6 個 build 時為 2）。"""
    return max(1, builds // 3)


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MapInfo(_Model):
    map_id: str
    archetype: str


@dataclass(frozen=True)
class RawCell:
    """一格（build, 地圖）的原始數字（尚未排名）。"""

    build_id: str
    map_id: str
    archetype: str
    battles: int
    completed: int
    ally_wins: int
    draws: int
    hero_dpr: float
    hero_survival: float
    rounds_mean: float
    errors: int = 0
    """`exception`／`max_actions` 的場次（不進任何彙總）。"""
    hero_healing: float = 0.0
    hero_shield: float = 0.0
    hero_taken: float = 0.0
    teammate_survival: float = 0.0
    """保護指標（Phase 2D-2）：build 英雄每場平均的治療量、護盾吸收量（它施放的護盾）、承受傷害，
    以及戰鬥結束時隊友的存活率。只列數字，不進排名與 6.8 標準。"""


class MatrixCell(_Model):
    """一格（build, 地圖）：數字與該地圖內的名次。"""

    build_id: str
    map_id: str
    archetype: str
    battles: int
    completed: int
    ally_wins: int
    draws: int
    win_rate: float
    hero_dpr: float
    hero_survival: float
    rounds_mean: float
    errors: int
    rank: int
    top: bool
    hero_healing: float = 0.0
    hero_shield: float = 0.0
    hero_taken: float = 0.0
    teammate_survival: float = 0.0


class ArchetypeCell(_Model):
    """一格（build, 地圖類型）：各地圖的平均與該類型內的名次。"""

    build_id: str
    archetype: str
    maps: tuple[str, ...]
    win_rate: float
    hero_dpr: float
    hero_survival: float
    rounds_mean: float
    rank: int
    top: bool
    hero_healing: float = 0.0
    hero_shield: float = 0.0
    hero_taken: float = 0.0
    teammate_survival: float = 0.0


class Standards(_Model):
    """6.8 的兩條標準。"""

    top_count: int
    archetypes: int
    always_top: tuple[str, ...]
    """在 **所有** 地圖類型都排名前段的 build（標準 1 要求為空）。"""
    never_top: tuple[str, ...]
    """在 **任何** 地圖類型都沒有排名前段的 build（標準 2 要求為空）。"""

    @property
    def no_build_always_top(self) -> bool:
        return not self.always_top

    @property
    def every_build_top_somewhere(self) -> bool:
        return not self.never_top


class MatrixReport(_Model):
    seeds: tuple[int, ...]
    builds: tuple[str, ...]
    maps: tuple[MapInfo, ...]
    cells: tuple[MatrixCell, ...]
    archetype_cells: tuple[ArchetypeCell, ...]
    standards: Standards

    def cell(self, build_id: str, map_id: str) -> MatrixCell:
        return next(c for c in self.cells if c.build_id == build_id and c.map_id == map_id)

    def archetype_cell(self, build_id: str, archetype: str) -> ArchetypeCell:
        return next(
            c for c in self.archetype_cells if c.build_id == build_id and c.archetype == archetype
        )

    @property
    def archetypes(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(m.archetype for m in self.maps))


MATRIX_ADAPTER: TypeAdapter[MatrixReport] = TypeAdapter(MatrixReport)


# ---------------------------------------------------------------------------
# 排名與標準（純函式）
# ---------------------------------------------------------------------------


def _win_rate(cell: RawCell) -> Fraction:
    return Fraction(cell.ally_wins, cell.completed) if cell.completed else Fraction(0)


def _ranked[T](items: Sequence[T], key: Mapping[int, tuple[Fraction, float]]) -> list[int]:
    """依 ``key``（勝率、DPR；越大越前面）排序後的名次（1 起算）；同分依原順序。"""
    order = sorted(range(len(items)), key=lambda i: (-key[i][0], -key[i][1], i))
    ranks = [0] * len(items)
    for place, index in enumerate(order, start=1):
        ranks[index] = place
    return ranks


def assemble_matrix(
    builds: Sequence[str],
    maps: Sequence[MapInfo],
    raw: Sequence[RawCell],
    seeds: Sequence[int],
) -> MatrixReport:
    """由各格的原始數字計算地圖內與類型內的排名，以及兩條標準。"""
    n = len(builds)
    top = top_count(n)
    index = {b: i for i, b in enumerate(builds)}
    cells: list[MatrixCell] = []
    for info in maps:
        row = sorted((c for c in raw if c.map_id == info.map_id), key=lambda c: index[c.build_id])
        keys = {i: (_win_rate(c), c.hero_dpr) for i, c in enumerate(row)}
        ranks = _ranked(row, keys)
        cells += [
            MatrixCell(
                build_id=c.build_id,
                map_id=c.map_id,
                archetype=c.archetype,
                battles=c.battles,
                completed=c.completed,
                ally_wins=c.ally_wins,
                draws=c.draws,
                win_rate=float(_win_rate(c)),
                hero_dpr=c.hero_dpr,
                hero_survival=c.hero_survival,
                rounds_mean=c.rounds_mean,
                errors=c.errors,
                rank=rank,
                top=rank <= top,
                hero_healing=c.hero_healing,
                hero_shield=c.hero_shield,
                hero_taken=c.hero_taken,
                teammate_survival=c.teammate_survival,
            )
            for c, rank in zip(row, ranks, strict=True)
        ]
    archetypes = tuple(dict.fromkeys(m.archetype for m in maps))
    archetype_cells: list[ArchetypeCell] = []
    for archetype in archetypes:
        rows: list[
            tuple[str, tuple[str, ...], Fraction, float, float, float, tuple[float, ...]]
        ] = []
        for build in builds:
            mine = [c for c in raw if c.build_id == build and c.archetype == archetype]
            k = len(mine)
            rows.append(
                (
                    build,
                    tuple(c.map_id for c in mine),
                    sum((_win_rate(c) for c in mine), Fraction(0)) / k,
                    sum(c.hero_dpr for c in mine) / k,
                    sum(c.hero_survival for c in mine) / k,
                    sum(c.rounds_mean for c in mine) / k,
                    (
                        sum(c.hero_healing for c in mine) / k,
                        sum(c.hero_shield for c in mine) / k,
                        sum(c.hero_taken for c in mine) / k,
                        sum(c.teammate_survival for c in mine) / k,
                    ),
                )
            )
        keys = {i: (r[2], r[3]) for i, r in enumerate(rows)}
        ranks = _ranked(rows, keys)
        archetype_cells += [
            ArchetypeCell(
                build_id=b,
                archetype=archetype,
                maps=ms,
                win_rate=float(w),
                hero_dpr=d,
                hero_survival=s,
                rounds_mean=r,
                rank=rank,
                top=rank <= top,
                hero_healing=prot[0],
                hero_shield=prot[1],
                hero_taken=prot[2],
                teammate_survival=prot[3],
            )
            for (b, ms, w, d, s, r, prot), rank in zip(rows, ranks, strict=True)
        ]
    always = tuple(
        b for b in builds if archetypes and all(c.top for c in archetype_cells if c.build_id == b)
    )
    never = tuple(b for b in builds if not any(c.top for c in archetype_cells if c.build_id == b))
    return MatrixReport(
        seeds=tuple(seeds),
        builds=tuple(builds),
        maps=tuple(maps),
        cells=tuple(cells),
        archetype_cells=tuple(archetype_cells),
        standards=Standards(
            top_count=top,
            archetypes=len(archetypes),
            always_top=always,
            never_top=never,
        ),
    )


# ---------------------------------------------------------------------------
# 模擬
# ---------------------------------------------------------------------------


def library_with_builds(library: ContentLibrary) -> ContentLibrary:
    """把 build 英雄範本加入 ``units`` 的內容庫副本（build 的 ID 就是範本 ID）。"""
    heroes = {b.id: b.hero for b in library.builds.builds}
    return replace(library, units={**library.units, **heroes})


def matrix_specs(
    library: ContentLibrary,
    builds: Sequence[str],
    maps: Sequence[str],
    seeds: Sequence[int],
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> list[tuple[str, str, BatchSpec]]:
    """每個（build, 地圖）一個 :class:`BatchSpec`：我方 ＝ build 英雄 ＋ 標準隊友。"""
    known = library.builds.by_id()
    unknown = sorted(b for b in builds if b not in known)
    if unknown:
        raise ValueError(f"未知的 build：{', '.join(unknown)}（可用：{', '.join(sorted(known))}）")
    lib = library_with_builds(library)
    specs: list[tuple[str, str, BatchSpec]] = []
    for map_id in maps:
        encounter = library.map(map_id).encounter
        if encounter is None:
            raise ValueError(f"{map_id} 沒有預設陣容（encounter）")
        for build in builds:
            setup = build_setup(
                lib,
                map_id,
                (build, *library.builds.companions),
                encounter.enemies,
                max_rounds=max_rounds,
            )
            specs.append(
                (
                    build,
                    map_id,
                    BatchSpec(
                        name=f"{build} × {map_id}",
                        setup=setup,
                        seeds=tuple(seeds),
                        policy_factory=UtilityPolicyFactory(library.ai_profiles),
                    ),
                )
            )
    return specs


def _raw_cell(build: str, map_id: str, archetype: str, report: BatchReport) -> RawCell:
    hero = next((t for t in report.templates if t.template_id == build), None)
    return RawCell(
        build_id=build,
        map_id=map_id,
        archetype=archetype,
        battles=report.battles,
        completed=report.completed,
        ally_wins=report.ally_wins,
        draws=report.draws,
        hero_dpr=0.0 if hero is None else hero.dpr,
        hero_survival=0.0 if hero is None else hero.survival,
        rounds_mean=report.rounds_mean,
        errors=report.battles - report.completed,
        hero_healing=0.0 if hero is None else hero.healing,
        hero_shield=0.0 if hero is None else hero.shield_provided,
        hero_taken=0.0 if hero is None else hero.damage_taken,
        teammate_survival=(
            0.0 if hero is None or hero.teammate_survival is None else hero.teammate_survival
        ),
    )


def run_matrix(
    library: ContentLibrary,
    builds: Sequence[str],
    maps: Sequence[str],
    seeds: Sequence[int],
    *,
    jobs: int = 1,
) -> MatrixReport:
    """跑完整個矩陣（所有（build, 地圖）攤平後交給 :func:`run_batches`）。"""
    specs = matrix_specs(library, builds, maps, seeds)
    reports = run_batches([spec for _, _, spec in specs], jobs=jobs)
    raw = [
        _raw_cell(build, map_id, library.map(map_id).archetype, report)
        for (build, map_id, _), report in zip(specs, reports, strict=True)
    ]
    infos = [MapInfo(map_id=m, archetype=library.map(m).archetype) for m in maps]
    return assemble_matrix(builds, infos, raw, seeds)


# ---------------------------------------------------------------------------
# 文字報表
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _archetype_order(report: MatrixReport) -> list[str]:
    known = [a for a in ARCHETYPES if a in report.archetypes]
    return known + [a for a in report.archetypes if a not in known]


def format_matrix(report: MatrixReport) -> str:
    """矩陣的文字格式（繁體中文）：每張地圖一節，加上類型層級的勝率、DPR、排名矩陣與標準檢查。"""
    out: list[str] = []
    seeds = report.seeds
    out.append(
        f"build × 地圖矩陣：種子 {seeds[0]}–{seeds[-1]}（{len(seeds)} 場／格），"
        f"我方 ＝ build 英雄 ＋ 標準隊友，敵方 ＝ 地圖的預設遭遇；"
        f"前段 ＝ 每張地圖（類型）前 {report.standards.top_count} 名"
    )
    for info in report.maps:
        out.append("")
        out.append(f"## {info.map_id}（{info.archetype}）")
        rows = sorted((c for c in report.cells if c.map_id == info.map_id), key=lambda c: c.rank)
        out += _table(
            ["名次", "build", "勝率", "英雄 DPR", "英雄存活率", "平均輪數", "平手", "異常場次"],
            [
                [
                    f"{c.rank}{'*' if c.top else ''}",
                    c.build_id,
                    _pct(c.win_rate),
                    f"{c.hero_dpr:.2f}",
                    _pct(c.hero_survival),
                    f"{c.rounds_mean:.2f}",
                    str(c.draws),
                    str(c.errors),
                ]
                for c in rows
            ],
        )
    archetypes = _archetype_order(report)
    heading = ["build", *archetypes]
    out.append("")
    out.append("## 勝率矩陣（地圖類型內有多張地圖時取平均）")
    out += _table(
        heading,
        [
            [b, *(_pct(report.archetype_cell(b, a).win_rate) for a in archetypes)]
            for b in report.builds
        ],
    )
    out.append("")
    out.append("## build 英雄 DPR 矩陣")
    out += _table(
        heading,
        [
            [b, *(f"{report.archetype_cell(b, a).hero_dpr:.2f}" for a in archetypes)]
            for b in report.builds
        ],
    )
    out.append("")
    out.append(
        "## 保護矩陣（build 英雄每場平均；只列數字，不進排名與 6.8 標準）"
        "：治療量／護盾吸收量（它施放的護盾）／承受傷害／隊友存活率"
    )
    out += _table(
        ["build", *archetypes],
        [
            [
                b,
                *(
                    "／".join(
                        (
                            f"{c.hero_healing:.1f}",
                            f"{c.hero_shield:.1f}",
                            f"{c.hero_taken:.1f}",
                            _pct(c.teammate_survival),
                        )
                    )
                    for c in (report.archetype_cell(b, a) for a in archetypes)
                ),
            ]
            for b in report.builds
        ],
    )
    out.append("")
    out.append(f"## 排名矩陣（* ＝ 前段，前 {report.standards.top_count} 名）")
    out += _table(
        [*heading, "前段次數"],
        [
            [
                b,
                *(
                    f"{c.rank}{'*' if c.top else ''}"
                    for c in (report.archetype_cell(b, a) for a in archetypes)
                ),
                str(sum(1 for a in archetypes if report.archetype_cell(b, a).top)),
            ]
            for b in report.builds
        ],
    )
    s = report.standards
    out.append("")
    out.append("## 6.8 標準檢查")
    note = (
        ""
        if s.archetypes >= MIN_ARCHETYPES_FOR_STANDARD_1
        else "（地圖類型少於 2 種，標準 1 僅供參考）"
    )
    out.append(
        "1. 沒有任何 build 在所有地圖類型都排名前段："
        + ("通過" if s.no_build_always_top else "不通過：" + "、".join(s.always_top))
        + note
    )
    out.append(
        "2. 每個 build 至少在一種地圖類型排名前段："
        + ("通過" if s.every_build_top_somewhere else "不通過：" + "、".join(s.never_top))
    )
    failed = [c for c in report.cells if c.errors]
    if failed:
        out.append("")
        out.append("異常場次（exception／max_actions，不進彙總）：")
        out += [f"- {c.build_id} × {c.map_id}：{c.errors} 場" for c in failed]
    return "\n".join(out)
