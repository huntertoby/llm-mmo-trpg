"""情境覆蓋表（Phase 6Q-A；玩法 PM「種族讓任務過易」盤點第 5 節 A）。

只讀內容，不跑戰鬥、不呼叫 LLM、不改狀態。對每一區 × 每一族列出：

- 能吃到種族加值的情境模板（模板的 ``methods`` 含該族的 ``race_methods``，而且模板屬性和該方法的
  常見屬性有交集，否則提議不合法：:func:`~trpg.content.world_situations.proposal_problems`）；
- 這些模板的基準 DC 分布；
- 最好情況的成功率（照 :func:`trpg.world.situations.resolve_situation` 的結算，見
  :func:`best_case`）。

並標出兩種情況：某區某族能吃加值的模板少於 :data:`MIN_TEMPLATES` 個；基準 DC ≤
:data:`LOW_DC` 但事件骨架沒有前置門檻的模板。另列一份資訊（不警告）：``基準 DC − dc_shift_max``
≤ :data:`LOW_DC` 但沒有前置門檻的模板（LLM 給最低難度時才落到門檻以下）。

口徑（Phase 6Q-B，玩法 PM 決定）：

- 前置門檻＝骨架 ``unlock_only`` 或 ``follows``（要先有線頭）；``day_phase``、``weather``、``once``
  不算（:func:`skeleton_gated`）。
- 計算用的等級：骨架地點的建議等級最高者；城鎮等沒有建議等級的地點用該區的等級下限（地點圖的
  ``level_min``），不再照 1 級算。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef
from trpg.content.world_situations import SituationRules, SituationTemplateDef
from trpg.world.common import location_level, world_map_of
from trpg.world.situations import situation_rules

__all__ = [
    "DICE_PAIRS",
    "LOW_DC",
    "MIN_TEMPLATES",
    "BestCase",
    "CoverageInputs",
    "CoverageReport",
    "LowDcFlag",
    "RaceRegionRow",
    "best_case",
    "build_coverage",
    "format_report",
    "inputs_from_library",
    "skeleton_gated",
    "success_hits",
]

MIN_TEMPLATES: Final = 3
"""每區每族能吃加值的模板至少幾個（盤點原則 4）。"""
LOW_DC: Final = 10
"""基準 DC ≤ 這個值的模板必須有前置門檻（盤點原則 3）。"""
DICE_PAIRS: Final = 400
"""引擎一律擲兩顆 d20（``_roll``）：20 × 20 種組合等機率。"""


@dataclass(frozen=True)
class CoverageInputs:
    """計算覆蓋表需要的資料（:func:`inputs_from_library` 從內容庫取；測試可直接組假資料）。"""

    rules: SituationRules
    templates: Mapping[str, tuple[SituationTemplateDef, ...]]
    """區域 → 情境模板。"""
    gated_skeletons: Mapping[str, frozenset[str]]
    """區域 → 有前置門檻（``unlock_only`` 或 ``follows``，:func:`skeleton_gated`）的事件骨架 ID。"""
    template_levels: Mapping[tuple[str, str], int]
    """（區域, 模板 ID）→ 計算最佳屬性用的等級（骨架地點的建議等級最高者，沒有建議等級的地點用
    區域等級下限；不超過等級上限）。"""
    races: tuple[str, ...]
    """要列的種族（``race_methods`` 的種族＋種族表裡沒有方法的種族）。"""
    race_names: Mapping[str, str] = field(default_factory=dict)
    base_attribute: int = 10
    points_per_level: int = 2
    ability_mod_base: int = 10
    ability_mod_divisor: int = 2


@dataclass(frozen=True)
class BestCase:
    """一個模板在「最好情況」下的判定（某族用自己的方法）。"""

    template: str
    base_dc: int
    level: int
    attribute_value: int
    bonus: int
    """屬性修正＋用心清單上限＋種族加值。"""
    advantage: bool
    hits_base: int
    """難度 ±0 時，400 種骰子組合中成功的數目。"""
    hits_best: int
    """LLM 把難度調到 −``dc_shift_max`` 時，400 種骰子組合中成功的數目。"""


@dataclass(frozen=True)
class RaceRegionRow:
    region: str
    race: str
    method: str | None
    cases: tuple[BestCase, ...]

    @property
    def count(self) -> int:
        return len(self.cases)

    def dc_distribution(self) -> tuple[tuple[int, int], ...]:
        """（基準 DC, 模板數），依 DC 排序。"""
        return tuple(sorted(Counter(c.base_dc for c in self.cases).items()))


@dataclass(frozen=True)
class LowDcFlag:
    region: str
    template: str
    skeleton: str
    base_dc: int


@dataclass(frozen=True)
class CoverageReport:
    rows: tuple[RaceRegionRow, ...]
    low_dc: tuple[LowDcFlag, ...]
    """警告：基準 DC ≤ :data:`LOW_DC` 但沒有前置門檻。"""
    shifted_low_dc: tuple[LowDcFlag, ...]
    """資訊（不警告）：基準 DC > :data:`LOW_DC`，但 ``基準 DC − dc_shift_max`` ≤ :data:`LOW_DC`
    且沒有前置門檻。"""
    template_counts: Mapping[str, int]
    race_names: Mapping[str, str] = field(default_factory=dict)
    dc_shift_max: int = 2

    def few(self) -> tuple[RaceRegionRow, ...]:
        """能吃加值的模板少於 :data:`MIN_TEMPLATES` 個的區域 × 種族。"""
        return tuple(r for r in self.rows if r.count < MIN_TEMPLATES)


# ---------------------------------------------------------------------------
# 計算
# ---------------------------------------------------------------------------


def success_hits(need: int, *, advantage: bool) -> int:
    """擲兩顆 d20 時，「採用的骰值 ≥ ``need``」的組合數（共 :data:`DICE_PAIRS`）。

    同引擎 ``_roll``：沒有優勢採第一顆，優勢取高；沒有自然 1／20 的特例（``_outcome`` 只比總值）。
    """
    hits = 0
    for first in range(1, 21):
        for second in range(1, 21):
            roll = max(first, second) if advantage else first
            hits += roll >= need
    return hits


def best_case(
    inputs: CoverageInputs, region: str, template: SituationTemplateDef, race: str
) -> BestCase:
    """``race`` 用自己的方法做 ``template`` 的最好情況（同 ``resolve_situation`` 的結算）。

    - 總值＝採用的骰值＋屬性修正＋用心加值＋種族加值；總值 ≥ DC＝成功。
    - 屬性：開局 ``base_attribute``，到地點建議等級為止每級的屬性點全部加在這一項；修正＝
      ``(屬性 − ability_mod_base) // ability_mod_divisor``（``attribute_modifier``）。判定只看主角
      的基礎屬性（``char.hero.attributes``），裝備詞條不算。
    - 用心清單：``care_max``（補給交換＋任一線頭或弱點就湊得到）。
    - 種族：``race_bonus``（方法對上才有）。
    - 優勢：模板有 ``advantage_threads`` 就當作持有（判定沒有物品欄位，這是唯一的「道具」）。
    - DC：``base_dc``（±0）與 ``base_dc − dc_shift_max``（LLM 給的最低難度）各算一次。
    """
    check = inputs.rules.check
    level = inputs.template_levels.get((region, template.id), 1)
    value = inputs.base_attribute + inputs.points_per_level * (level - 1)
    modifier = (value - inputs.ability_mod_base) // inputs.ability_mod_divisor
    race_method = inputs.rules.race_methods.get(race)
    race_bonus = check.race_bonus if race_method in template.methods else 0
    bonus = modifier + check.care_max + race_bonus
    advantage = bool(template.advantage_threads)
    return BestCase(
        template=template.id,
        base_dc=template.base_dc,
        level=level,
        attribute_value=value,
        bonus=bonus,
        advantage=advantage,
        hits_base=success_hits(template.base_dc - bonus, advantage=advantage),
        hits_best=success_hits(template.base_dc - check.dc_shift_max - bonus, advantage=advantage),
    )


def skeleton_gated(skeleton: EventSkeletonDef) -> bool:
    """骨架有前置門檻：``unlock_only``（解鎖才出現）或 ``follows``（要先有線頭）。

    時段（``day_phase``）、天氣（``weather``）、``once`` 不算門檻（玩法 PM，Phase 6Q-B）。
    """
    return skeleton.unlock_only or bool(skeleton.follows)


def _eligible(rules: SituationRules, template: SituationTemplateDef, method: str) -> bool:
    """模板允許 ``method``，而且有一個模板屬性是這個方法的常見屬性（提議才合法）。"""
    found = rules.method_by_id().get(method)
    if found is None or method not in template.methods:
        return False
    return any(a in template.attributes for a in found.attributes)


def build_coverage(inputs: CoverageInputs) -> CoverageReport:
    rules = inputs.rules
    rows: list[RaceRegionRow] = []
    low: list[LowDcFlag] = []
    shifted: list[LowDcFlag] = []
    shift = rules.check.dc_shift_max
    for region in sorted(inputs.templates):
        templates = inputs.templates[region]
        for race in inputs.races:
            method = rules.race_methods.get(race)
            cases = tuple(
                best_case(inputs, region, t, race)
                for t in templates
                if method is not None and _eligible(rules, t, method)
            )
            rows.append(RaceRegionRow(region=region, race=race, method=method, cases=cases))
        gated = inputs.gated_skeletons.get(region, frozenset())
        open_templates = [t for t in templates if t.skeleton not in gated]
        low += [_flag(region, t) for t in open_templates if t.base_dc <= LOW_DC]
        shifted += [
            _flag(region, t) for t in open_templates if t.base_dc > LOW_DC >= t.base_dc - shift
        ]
    return CoverageReport(
        rows=tuple(rows),
        low_dc=tuple(low),
        shifted_low_dc=tuple(shifted),
        template_counts={r: len(inputs.templates[r]) for r in sorted(inputs.templates)},
        race_names=dict(inputs.race_names),
        dc_shift_max=shift,
    )


def _flag(region: str, template: SituationTemplateDef) -> LowDcFlag:
    return LowDcFlag(
        region=region, template=template.id, skeleton=template.skeleton, base_dc=template.base_dc
    )


def inputs_from_library(library: ContentLibrary) -> CoverageInputs:
    """從內容庫取覆蓋表的資料（規則、模板、骨架門檻、地點建議等級、種族）。"""
    rules = situation_rules(library)
    content = library.world_event_content
    cap = library.world_rules.hero_growth.level_cap if library.world_rules is not None else 99
    templates: dict[str, tuple[SituationTemplateDef, ...]] = {}
    gated: dict[str, frozenset[str]] = {}
    levels: dict[tuple[str, str], int] = {}
    for region, table in sorted(content.situations.templates.items()):
        templates[region] = table.templates
        events = content.events.get(region)
        skeletons = {} if events is None else events.skeleton_by_id()
        gated[region] = frozenset(s.id for s in skeletons.values() if skeleton_gated(s))
        region_min = world_map_of(library, region).level_min
        for template in table.templates:
            skeleton = skeletons.get(template.skeleton)
            locations = () if skeleton is None else skeleton.locations
            level = max(
                (location_level(library, region, loc, default=region_min) for loc in locations),
                default=region_min,
            )
            levels[(region, template.id)] = min(level, cap)
    names = {} if library.races is None else {r.id: r.name_zh for r in library.races.races}
    races = [*rules.race_methods, *(r for r in sorted(names) if r not in rules.race_methods)]
    core = library.ruleset.core
    return CoverageInputs(
        rules=rules,
        templates=templates,
        gated_skeletons=gated,
        template_levels=levels,
        races=tuple(races),
        race_names=names,
        base_attribute=library.roguelite.base_attribute,
        points_per_level=library.roguelite.attribute_points_per_level,
        ability_mod_base=core.ability_mod_base,
        ability_mod_divisor=core.ability_mod_divisor,
    )


# ---------------------------------------------------------------------------
# 輸出
# ---------------------------------------------------------------------------


def _pct(hits: int) -> str:
    return f"{hits * 100 // DICE_PAIRS}%"


def _range(values: list[int]) -> str:
    if not values:
        return "—"
    low, high = min(values), max(values)
    return _pct(low) if low == high else f"{_pct(low)}～{_pct(high)}"


def _race_label(report: CoverageReport, row: RaceRegionRow) -> str:
    name = report.race_names.get(row.race, row.race)
    return f"{name}（{row.race}）"


def _row_line(report: CoverageReport, row: RaceRegionRow) -> str:
    dcs = " ".join(f"{dc}×{n}" for dc, n in row.dc_distribution()) or "—"
    base = _range([c.hits_base for c in row.cases])
    best = _range([c.hits_best for c in row.cases])
    method = row.method or "（沒有方法）"
    return (
        f"| {row.region} | {_race_label(report, row)} | {method} | {row.count} | {dcs} "
        f"| {base} | {best} |"
    )


def format_report(report: CoverageReport, *, quiet: bool = False) -> str:
    """覆蓋表（Markdown 表格）。``quiet``：只印摘要與被標出的項目。"""
    few = report.few()
    counts = "、".join(f"{r} {n} 個" for r, n in report.template_counts.items())
    lines = [
        f"情境覆蓋表：{counts}模板；{len(report.rows)} 列（區域 × 種族）；"
        f"標出 {len(few)} 列模板少於 {MIN_TEMPLATES} 個、{len(report.low_dc)} 個 DC ≤ {LOW_DC} "
        f"沒有前置門檻；資訊 {len(report.shifted_low_dc)} 個 DC − {report.dc_shift_max} ≤ {LOW_DC}"
    ]
    if not quiet:
        lines += [
            "",
            "| 區域 | 種族 | 方法 | 模板數 | DC 分布 | 最好情況（±0） | 最好情況（−2） |",
            "|---|---|---|---:|---|---|---|",
            *(_row_line(report, r) for r in report.rows),
        ]
    if few:
        lines += ["", f"警告：能吃種族加值的模板少於 {MIN_TEMPLATES} 個："]
        lines += [
            f"  - {r.region} {_race_label(report, r)} {r.method or '（沒有方法）'}：{r.count} 個"
            for r in few
        ]
    if report.low_dc:
        lines += ["", f"警告：DC ≤ {LOW_DC} 但骨架沒有前置門檻（unlock_only／follows）："]
        lines += [
            f"  - {f.region} {f.template}（骨架 {f.skeleton}）：DC {f.base_dc}"
            for f in report.low_dc
        ]
    if report.shifted_low_dc and not quiet:
        shift = report.dc_shift_max
        lines += ["", f"資訊（不警告）：DC − {shift} ≤ {LOW_DC} 但骨架沒有前置門檻："]
        lines += [
            f"  - {f.region} {f.template}（骨架 {f.skeleton}）：DC {f.base_dc}→{f.base_dc - shift}"
            for f in report.shifted_low_dc
        ]
    return "\n".join(lines)
