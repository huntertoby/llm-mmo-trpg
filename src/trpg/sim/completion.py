"""完成度檢查（Phase 2C-4 3.4）：全部非測試地圖 × 全部指揮官設定 × 多個種子，確認每場戰鬥都打得完。

這不是平衡工具：勝率與輪數只記錄。驗收標準是三種異常（``exception``、``max_actions``、
``draw``）全部為 0。結果依（設定、地圖、種子）排序後才彙總，所以輸出與 ``--jobs`` 無關。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, BatchReport, map_spec, run_batches
from trpg.sim.commanders import COMMANDER_IDS

__all__ = [
    "COMPLETION_ANOMALY_KINDS",
    "CompletionAnomaly",
    "CompletionCell",
    "CompletionConfig",
    "CompletionReport",
    "completion_configs",
    "format_completion",
    "run_completion",
]

COMPLETION_ANOMALY_KINDS = ("exception", "max_actions", "draw")


@dataclass(frozen=True)
class CompletionConfig:
    """一種指揮官設定：我方與敵方的腳本指揮官（``None`` ＝ 沒有）。"""

    ally: str | None = None
    enemy: str | None = None

    @property
    def label(self) -> str:
        if self.ally is None and self.enemy is None:
            return "無指揮官"
        side, commander = ("我方", self.ally) if self.ally is not None else ("敵方", self.enemy)
        return f"{side} {commander}"


def completion_configs() -> tuple[CompletionConfig, ...]:
    """9 種設定：無指揮官、我方各指揮官（敵方無）、敵方各指揮官（我方無）。"""
    return (
        CompletionConfig(),
        *(CompletionConfig(ally=c) for c in COMMANDER_IDS),
        *(CompletionConfig(enemy=c) for c in COMMANDER_IDS),
    )


@dataclass(frozen=True)
class CompletionCell:
    config: CompletionConfig
    map_id: str
    battles: int
    ally_win_rate: float
    rounds_mean: float
    anomalies: int


@dataclass(frozen=True)
class CompletionAnomaly:
    config: CompletionConfig
    map_id: str
    seed: int
    kind: str
    detail: str


@dataclass(frozen=True)
class CompletionReport:
    configs: tuple[CompletionConfig, ...]
    maps: tuple[str, ...]
    seeds: tuple[int, ...]
    cells: tuple[CompletionCell, ...]
    """依（設定順序、地圖順序）排列。"""
    anomalies: tuple[CompletionAnomaly, ...]

    def cell(self, config: CompletionConfig, map_id: str) -> CompletionCell:
        return next(c for c in self.cells if c.config == config and c.map_id == map_id)

    @property
    def clean(self) -> bool:
        return not self.anomalies


def _anomalies_of(
    config: CompletionConfig, map_id: str, report: BatchReport
) -> list[CompletionAnomaly]:
    found: list[CompletionAnomaly] = []
    for kind in COMPLETION_ANOMALY_KINDS:
        anomaly = report.anomaly(kind)
        if anomaly is None:
            continue
        for seed in anomaly.seeds:
            found.append(
                CompletionAnomaly(config, map_id, seed, kind, anomaly.details.get(seed, ""))
            )
    return found


def run_completion(
    library: ContentLibrary,
    map_ids: Sequence[str],
    seeds: Sequence[int],
    *,
    jobs: int = 1,
    configs: Sequence[CompletionConfig] | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> CompletionReport:
    config_list = tuple(completion_configs() if configs is None else configs)
    maps = tuple(map_ids)
    keys = [(config, map_id) for config in config_list for map_id in maps]
    specs = [
        map_spec(
            library,
            map_id,
            seeds,
            max_rounds=max_rounds,
            ally_commander=config.ally,
            enemy_commander=config.enemy,
        )
        for config, map_id in keys
    ]
    reports = run_batches(specs, jobs=jobs)
    cells: list[CompletionCell] = []
    anomalies: list[CompletionAnomaly] = []
    for (config, map_id), report in zip(keys, reports, strict=True):
        found = _anomalies_of(config, map_id, report)
        anomalies.extend(found)
        cells.append(
            CompletionCell(
                config,
                map_id,
                report.battles,
                report.ally_win_rate,
                report.rounds_mean,
                len(found),
            )
        )
    return CompletionReport(config_list, maps, tuple(seeds), tuple(cells), tuple(anomalies))


def format_completion(report: CompletionReport) -> str:
    """摘要表（設定 × 地圖，每格「我方勝率／平均輪數／異常數」）與異常清單。"""
    seeds = report.seeds
    battles = len(report.configs) * len(report.maps) * len(seeds)
    lines = [
        f"完成度檢查：{len(report.configs)} 種設定 × {len(report.maps)} 張地圖 × "
        f"{len(seeds)} 個種子（{seeds[0]}–{seeds[-1]}）＝ {battles} 場，"
        f"max_rounds={DEFAULT_MAX_ROUNDS}",
        "每格：我方勝率／平均輪數／異常數（exception、max_actions、draw）",
        "",
        "| 設定 | " + " | ".join(report.maps) + " |",
        "|---|" + "---|" * len(report.maps),
    ]
    for config in report.configs:
        row = []
        for map_id in report.maps:
            cell = report.cell(config, map_id)
            row.append(f"{cell.ally_win_rate:.0%}／{cell.rounds_mean:.1f}／{cell.anomalies}")
        lines.append(f"| {config.label} | " + " | ".join(row) + " |")
    lines.append("")
    counts = {k: sum(1 for a in report.anomalies if a.kind == k) for k in COMPLETION_ANOMALY_KINDS}
    lines.append(
        "異常合計："
        + "、".join(f"{kind} {counts[kind]}" for kind in COMPLETION_ANOMALY_KINDS)
        + (" —— 通過" if report.clean else " —— 未通過")
    )
    if report.anomalies:
        lines.append("")
        lines.append("異常清單（設定, 地圖, 種子）：")
        for a in report.anomalies:
            detail = f"：{a.detail}" if a.detail else ""
            lines.append(f"- {a.kind} ({a.config.label}, {a.map_id}, {a.seed}){detail}")
    return "\n".join(lines)
