"""數值工坊的 1 階比值（NW-2c，``docs/phases/PhaseNW-2計畫.md`` 5.7、T11、T12、D4）。

- **量測**：:mod:`trpg.sim.skill_ratio`（BAL-21e 的核心）；工作照模擬工作一次一個
  （:meth:`trpg.api.tuning.sim_jobs.SimJobs.start_ratio`），規模上限「組數 × 種子」
  :data:`MAX_WORK`（組＝武器 × 招 × 情境）。
- **結果存放**（T12）：``<save_dir>/tuning/ratios/``。每次工作把改前（基底內容）與改後（草稿內容，
  和改前不同時）各存一份 ``run-<序號>-<鍵>.json``，鍵＝內容樹雜湊＋招＋種子；同鍵的改前直接用
  （快取）。最多留 :data:`KEEP_RUNS` 份。格式內含 ``t1_skill_ratio.py run`` JSON 的
  ``seeds``／``dot_rounds``／``skills``／``rows``（同一套彙總函式）。
- **基準匯入**：``t1_skill_ratio.py run`` 的 JSON 存成 ``baseline.json``，記下匯入當時的內容樹雜湊
  （腳本的 JSON 沒有雜湊）；之後內容變了，畫面標「內容已變，僅供參考」。
- **技能表單的比值**：目前內容量過的（最新一次）優先，否則用基準；「上次」＝最近一份**不同內容**
  的量測（或基準）。參考線只當參考（D4），不擋寫回。

確定性：彙總只依 JSON 內容；序號只用來排新舊（不讀時間）。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from trpg.api.tuning.schemas import (
    TuningRatioBaseline,
    TuningRatioLine,
    TuningRatioPlan,
    TuningRatioRow,
    TuningRatioSimResult,
    TuningRatioSkip,
    TuningRatioSummary,
    TuningSkillRatio,
)
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.sim.skill_ratio import (
    DOT_ROUNDS,
    RatioJob,
    is_measurable,
    low_tag,
    meta_of,
    odd_conditions,
    ratio_jobs,
    reference_checks,
    scenario_count,
    skill_summary,
    summary_cells,
)

__all__ = [
    "DEFAULT_RATE",
    "DEFAULT_SEEDS",
    "KEEP_RUNS",
    "MAX_WORK",
    "BaselineError",
    "RatioPlanned",
    "RatioStore",
    "plan_ratio",
    "plan_view",
    "ratio_result",
    "run_data",
    "summary_of",
]

DEFAULT_SEEDS: Final = 50
"""每組預設種子數（T11；BAL-21e 是 250）。"""
MAX_WORK: Final = 40_000
"""單次上限：組數 × 種子（T11）。"""
DEFAULT_RATE: Final = 450.0
"""沒實測過時的每秒場數（BAL-21e：27 萬場程序池 4 約 10 分鐘）。"""
KEEP_RUNS: Final = 40
_RUN: Final = re.compile(r"^run-(\d{6})-[0-9a-f]{16}\.json$")
_BASELINE: Final = "baseline.json"
_NOT_MEASURABLE_ZH: Final = "比值只量 1 階主動武器技（非敵人專用）；這招不適用"
_NO_DATA_ZH: Final = (
    "還沒有比值：在「小模擬」選「比值」跑這招，或匯入 t1_skill_ratio.py run 的 JSON 當基準"
)


class BaselineError(ValueError):
    """匯入的 JSON 不是 ``t1_skill_ratio.py run`` 的格式（422）。"""


# ---------------------------------------------------------------------------
# 規模
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RatioPlanned:
    """一個比值工作的規模與要量的招（:func:`plan_ratio`）。"""

    skills: list[SkillDef]
    skipped: list[TuningRatioSkip]
    jobs: list[RatioJob]
    groups: int
    seeds: int

    @property
    def work(self) -> int:
        return self.groups * self.seeds


def plan_ratio(library: ContentLibrary, skill_ids: Sequence[str], seeds: int) -> RatioPlanned:
    """要量的招（依輸入順序去重；不存在的招丟 :class:`KeyError`）、跳過的招與組數。"""
    skills: list[SkillDef] = []
    skipped: list[TuningRatioSkip] = []
    for skill_id in dict.fromkeys(skill_ids):
        skill = library.skills.get(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        if is_measurable(skill):
            skills.append(skill)
        else:
            skipped.append(
                TuningRatioSkip(
                    skill_id=skill_id, name_zh=skill.name_zh, reason_zh=_NOT_MEASURABLE_ZH
                )
            )
    jobs = ratio_jobs(library, skills, seeds)
    by_id = {s.id: s for s in skills}
    groups = sum(scenario_count(by_id[j.skill]) for j in jobs)
    return RatioPlanned(skills, skipped, jobs, groups, seeds)


def plan_view(planned: RatioPlanned, rate: float) -> TuningRatioPlan:
    problem: str | None = None
    if not planned.skills:
        problem = "沒有量得到比值的招（只量 1 階主動武器技、非敵人專用）"
    elif planned.work > MAX_WORK:
        problem = (
            f"一次最多 {MAX_WORK:,} 組×種子（這次 {planned.groups} 組 × {planned.seeds} 種子"
            f"＝{planned.work:,}），請減少招或種子"
        )
    return TuningRatioPlan(
        skills=[s.id for s in planned.skills],
        skipped=planned.skipped,
        jobs=len(planned.jobs),
        groups=planned.groups,
        seeds=planned.seeds,
        work=planned.work,
        max_work=MAX_WORK,
        seconds=round(planned.work / rate, 1),
        problem_zh=problem,
    )


# ---------------------------------------------------------------------------
# 彙總
# ---------------------------------------------------------------------------


def summary_of(
    meta: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    seeds: int,
    source: str,
    source_zh: str,
    stale: bool = False,
) -> TuningRatioSummary | None:
    """一招的摘要格與參考線（沒有任何武器的列時 ``None``）。"""
    if not rows:
        return None
    cells = summary_cells(meta, rows)
    lines = [
        TuningRatioLine(
            key=line.key,
            label_zh=line.label_zh,
            threshold=line.threshold,
            value=value,
            ok=None if value is None else value >= line.threshold,
            tentative=line.tentative,
        )
        for line, value in reference_checks(meta, skill_summary(meta, rows))
    ]
    return TuningRatioSummary(
        **cells,
        category_zh=low_tag(meta),
        lines=lines,
        seeds=seeds,
        source="workshop" if source == "workshop" else "baseline",
        source_zh=source_zh,
        stale=stale,
    )


def _rows_by_skill(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in data["rows"]:
        out.setdefault(str(row["skill"]), []).append(row)
    return out


def run_data(
    library: ContentLibrary, skills: Iterable[str], seeds: int, rows: list[Any]
) -> dict[str, Any]:
    """``t1_skill_ratio.py run`` 的 JSON 格式（``skills`` 是摘要用的 meta）。"""
    ids = list(dict.fromkeys(skills))
    return {
        "seeds": seeds,
        "dot_rounds": DOT_ROUNDS,
        "skills": {i: meta_of(library, library.skills[i]) for i in ids if i in library.skills},
        "rows": sorted(rows, key=lambda r: (str(r["skill"]), str(r["weapon"]))),
    }


def ratio_result(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    skipped: Sequence[TuningRatioSkip],
    groups: int,
    before_cached: bool,
    same_content: bool,
) -> TuningRatioSimResult:
    """改前／改後並排（逐招）。"""
    b_rows, a_rows = _rows_by_skill(before), _rows_by_skill(after)
    out: list[TuningRatioRow] = []
    for skill_id, meta in after["skills"].items():
        b_meta = before["skills"].get(skill_id, meta)
        out.append(
            TuningRatioRow(
                skill_id=skill_id,
                name_zh=str(meta["name_zh"]),
                before=summary_of(
                    b_meta,
                    b_rows.get(skill_id, []),
                    seeds=before["seeds"],
                    source="workshop",
                    source_zh="改前",
                ),
                after=summary_of(
                    meta,
                    a_rows.get(skill_id, []),
                    seeds=after["seeds"],
                    source="workshop",
                    source_zh="改後",
                ),
            )
        )
    return TuningRatioSimResult(
        skills=out,
        skipped=list(skipped),
        seeds=after["seeds"],
        groups=groups,
        before_cached=before_cached,
        same_content=same_content,
        odd=odd_conditions(after),
    )


# ---------------------------------------------------------------------------
# 存放
# ---------------------------------------------------------------------------


def run_key(tree: str, skills: Sequence[str], seeds: int) -> str:
    raw = json.dumps(["ratio", tree, sorted(set(skills)), seeds])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_script_json(data: Any) -> dict[str, Any]:
    """``t1_skill_ratio.py run`` 的 JSON（寬鬆檢查會用到的鍵）。"""
    if not isinstance(data, dict):
        raise BaselineError("不是 t1_skill_ratio.py run 的 JSON（要是一個物件）")
    for key, kind in (("seeds", int), ("dot_rounds", int), ("skills", dict), ("rows", list)):
        if not isinstance(data.get(key), kind):
            raise BaselineError(f"不是 t1_skill_ratio.py run 的 JSON：缺 {key}")
    for row in data["rows"]:
        if not (
            isinstance(row, dict)
            and isinstance(row.get("skill"), str)
            and isinstance(row.get("weapon"), str)
            and isinstance(row.get("scenarios"), dict)
            and row["skill"] in data["skills"]
        ):
            raise BaselineError("不是 t1_skill_ratio.py run 的 JSON：rows 的格式不對")
    needed = ("name_zh", "class", "ap", "shape", "conds", "bound", "variants", "lingers")
    for skill_id, meta in data["skills"].items():
        if not isinstance(meta, dict) or any(k not in meta for k in needed):
            raise BaselineError(f"不是 t1_skill_ratio.py run 的 JSON：skills.{skill_id} 少欄位")
    return data


class RatioStore:
    """``<save_dir>/tuning/ratios/`` 的比值結果與匯入的基準。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    # -- 量測 ---------------------------------------------------------------

    def _runs(self) -> list[tuple[int, Path]]:
        if not self.root.is_dir():
            return []
        found = []
        for path in self.root.iterdir():
            match = _RUN.match(path.name)
            if match:
                found.append((int(match.group(1)), path))
        return sorted(found)

    def _read(self, path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def find(self, tree: str, skills: Sequence[str], seeds: int) -> dict[str, Any] | None:
        """同鍵（內容、招、種子）最新的一份量測的 JSON 資料（改前快取）。"""
        key = run_key(tree, skills, seeds)
        for _order, path in reversed(self._runs()):
            if path.name.endswith(f"-{key[:16]}.json"):
                run = self._read(path)
                if run is not None and run.get("key") == key:
                    return dict(run["data"])
        return None

    def save(self, tree: str, skills: Sequence[str], seeds: int, data: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        runs = self._runs()
        order = (runs[-1][0] + 1) if runs else 1
        key = run_key(tree, skills, seeds)
        path = self.root / f"run-{order:06d}-{key[:16]}.json"
        body = {
            "key": key,
            "tree": tree,
            "skills": sorted(set(skills)),
            "seeds": seeds,
            "data": data,
        }
        path.write_text(json.dumps(body, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        for _old, stale in runs[: max(0, len(runs) + 1 - KEEP_RUNS)]:
            stale.unlink(missing_ok=True)
        return path

    # -- 基準 ---------------------------------------------------------------

    def import_baseline(self, data: Any, tree: str) -> TuningRatioBaseline:
        checked = _check_script_json(data)
        self.root.mkdir(parents=True, exist_ok=True)
        body = {"tree": tree, "data": checked}
        (self.root / _BASELINE).write_text(
            json.dumps(body, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        return self.baseline_info(tree) or _baseline_view(checked, same=True)

    def _baseline(self) -> dict[str, Any] | None:
        body = self._read(self.root / _BASELINE)
        if body is None or not isinstance(body.get("data"), dict):
            return None
        return body

    def baseline_info(self, tree: str) -> TuningRatioBaseline | None:
        body = self._baseline()
        if body is None:
            return None
        return _baseline_view(body["data"], same=body.get("tree") == tree)

    # -- 技能表單 -----------------------------------------------------------

    def _entries(self, skill_id: str) -> list[tuple[str | None, dict[str, Any], str]]:
        """含這招的量測（新到舊），最後接基準：(內容樹雜湊, JSON 資料, 來源)。"""
        out: list[tuple[str | None, dict[str, Any], str]] = []
        for _order, path in reversed(self._runs()):
            run = self._read(path)
            if run is not None and skill_id in run.get("skills", ()):
                out.append((run.get("tree"), run["data"], "workshop"))
        base = self._baseline()
        if base is not None and skill_id in base["data"].get("skills", {}):
            out.append((base.get("tree"), base["data"], "baseline"))
        return out

    def skill_view(self, skill: SkillDef, tree: str) -> TuningSkillRatio:
        """技能表單的比值區（目前值＋上次不同內容的量測）。"""
        if not is_measurable(skill):
            return TuningSkillRatio(
                skill_id=skill.id, applicable=False, reason_zh=_NOT_MEASURABLE_ZH
            )
        entries = self._entries(skill.id)
        current = next((e for e in entries if e[0] == tree and e[2] == "workshop"), None)
        if current is None:
            current = next((e for e in entries if e[2] == "baseline"), None)
        if current is None:
            return TuningSkillRatio(skill_id=skill.id, applicable=True, reason_zh=_NO_DATA_ZH)
        rest = entries[entries.index(current) + 1 :] if current[2] == "workshop" else entries
        previous = next((e for e in rest if e is not current and e[0] != current[0]), None)
        return TuningSkillRatio(
            skill_id=skill.id,
            applicable=True,
            current=_entry_summary(skill.id, current, tree),
            previous=None if previous is None else _entry_summary(skill.id, previous, tree),
        )

    def current_summary(self, skill: SkillDef, tree: str) -> TuningRatioSummary | None:
        """分組預覽用：這招目前的摘要（沒有時 ``None``）。"""
        return self.skill_view(skill, tree).current


def _entry_summary(
    skill_id: str, entry: tuple[str | None, dict[str, Any], str], tree: str
) -> TuningRatioSummary | None:
    run_tree, data, source = entry
    stale = run_tree != tree
    seeds = int(data["seeds"])
    if source == "workshop":
        label = f"工坊量測（{seeds} 種子）" + ("：當時的內容和現在不同" if stale else "")
    else:
        label = f"匯入的基準（{seeds} 種子）" + ("：內容已變，僅供參考" if stale else "")
    return summary_of(
        data["skills"][skill_id],
        _rows_by_skill(data).get(skill_id, []),
        seeds=seeds,
        source=source,
        source_zh=label,
        stale=stale,
    )


def _baseline_view(data: dict[str, Any], *, same: bool) -> TuningRatioBaseline:
    note = (
        "匯入時記下目前的內容；之後內容改了（寫回），表單會標「內容已變，僅供參考」。"
        "腳本的 JSON 沒有內容雜湊：請匯入用目前內容跑出來的結果。"
    )
    return TuningRatioBaseline(
        skills=len(data["skills"]),
        rows=len(data["rows"]),
        seeds=int(data["seeds"]),
        same_content=same,
        note_zh=note if same else "內容已變（匯入後有寫回），僅供參考。" + note,
    )
