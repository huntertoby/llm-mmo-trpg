"""數值工坊的模擬工作（NW-1a A7，規格 5.4；NW-2a 加地圖戰）：改前／改後同種子配對。

- 情境：頭目戰（:meth:`SimJobs.start`，NW-1）、地圖戰（:meth:`SimJobs.start_map`，NW-2a 5.6：
  勝率、輪數、倒下率、受測招的單招施放率）與 1 階比值（:meth:`SimJobs.start_ratio`，NW-2c 5.7：
  一個工作單位是一組「武器 × 招」，改前結果與快取由 :mod:`trpg.api.tuning.ratios` 管）。
- 背景執行緒＋程序池（spawn，``min(4, 核心數 − 2)``）；**一次只跑一個**（再開回 409）；可取消
  （取消還沒開始的場次；已在跑的那幾場跑完就丟掉）。
- 程序池在工作之間保留（Windows spawn 每個行程要重新匯入 ``trpg``，第一次較慢）；每個工作行程依
  內容資料夾快取內容庫（:func:`trpg.sim.boss_probe.library_for`）。
- 改前結果以「``content/`` 的樹雜湊＋情境參數」為鍵存 ``<save_dir>/tuning/sims/``；同鍵直接用。
- 規模上限 :data:`MAX_BATTLES`（單次改後的場數）。
- 結果不含耗時（同參數同內容跑兩次逐字相同）；耗時另放 ``elapsed_s``。每場秒數依情境分開記
  （頭目戰與地圖戰不共用，NW-1b 待決 5）。
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import secrets
import threading
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import CancelledError, Executor, Future, ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from trpg.api.tuning.schemas import (
    SMALL_SAMPLE,
    TuningMapSide,
    TuningMapSimResult,
    TuningRatioSimResult,
    TuningSimBuildResult,
    TuningSimFlips,
    TuningSimJob,
    TuningSimPhase,
    TuningSimResult,
    TuningSimSide,
    TuningSimSkill,
    TuningSkillRate,
)
from trpg.content.library import ContentLibrary
from trpg.sim.boss_probe import (
    BOSSES,
    BossBattle,
    ProbeJob,
    base_skill,
    boss_jobs,
    phase_skills,
    probe_task,
)
from trpg.sim.skill_probe import MapBattle, SkillProbeJob
from trpg.sim.skill_probe import probe_task as map_probe_task
from trpg.sim.skill_ratio import RatioJob, ratio_task

__all__ = [
    "DEFAULT_MAP_SECONDS_PER_BATTLE",
    "DEFAULT_RATIO_RATE",
    "DEFAULT_SECONDS_PER_BATTLE",
    "MAX_BATTLES",
    "SimBusyError",
    "SimJobs",
    "SimRequestError",
    "default_workers",
    "summarize",
    "summarize_map",
]

MAX_BATTLES: Final = 160
DEFAULT_SECONDS_PER_BATTLE: Final = 1.6
"""沒實測過時的每場秒數（BAL-20：頭目戰每場約 1.2～1.9 核心秒）。"""
DEFAULT_MAP_SECONDS_PER_BATTLE: Final = 0.8
"""地圖戰沒實測過時的每場秒數（NW-2a 實測 14 張圖單場 0.5～1.2 秒）。"""
DEFAULT_RATIO_RATE: Final = 450.0
"""比值情境沒實測過時的每秒場數（BAL-21e：27 萬場程序池 4 約 10 分鐘；NW-2 T11）。"""
_TIMING_FILE: Final = "timing.json"
_BOSS_TIMING: Final = "seconds_per_battle"
_MAP_TIMING: Final = "map_seconds_per_battle"
_RATIO_TIMING: Final = "ratio_battles_per_second"

type Task = Callable[[str | None, ProbeJob], BossBattle]
type MapTask = Callable[[str | None, SkillProbeJob], MapBattle]
type RatioTask = Callable[[str | None, RatioJob], dict[str, Any]]
type ExecutorFactory = Callable[[int], Executor]


class SimBusyError(RuntimeError):
    """已有模擬在跑（409）。"""


class SimRequestError(ValueError):
    """情境參數不對（422）。"""


def default_workers() -> int:
    return max(1, min(4, (os.cpu_count() or 1) - 2))


def _spawn_pool(workers: int) -> Executor:
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))


# ---------------------------------------------------------------------------
# 頭目戰的彙總（NW-1a）
# ---------------------------------------------------------------------------


def _side(library: ContentLibrary, which: str, battles: Sequence[BossBattle]) -> TuningSimSide:
    tally: Counter[str] = Counter()
    for battle in battles:
        tally.update(battle.tally)
    n = len(battles)
    unit = library.unit(BOSSES[which][0])
    phases: list[TuningSimPhase] = []
    for index, skills in phase_skills(library, which):
        turns = tally[f"turn|{index}"]
        reached = n if index == 1 else tally[f"reach|{index}"]
        phases.append(
            TuningSimPhase(
                phase=index,
                name_zh=unit.phases[index - 1].name_zh,
                reached=reached,
                turns=turns,
                skills=[
                    TuningSimSkill(
                        skill=base_skill(s),
                        casts=tally[f"cast|{index}|{base_skill(s)}"],
                        turns=turns,
                        small=turns < SMALL_SAMPLE,
                    )
                    for s in skills
                ],
            )
        )
    builds: dict[str, list[BossBattle]] = {}
    for battle in battles:
        builds.setdefault(battle.build, []).append(battle)
    return TuningSimSide(
        n=n,
        wins=sum(b.won for b in battles),
        rounds=sum(b.rounds for b in battles),
        allies=sum(b.allies for b in battles),
        downed=sum(b.downed for b in battles),
        small=n < SMALL_SAMPLE,
        phases=phases,
        builds=[
            TuningSimBuildResult(build=k, n=len(v), wins=sum(b.won for b in v))
            for k, v in builds.items()
        ],
    )


def summarize(
    library: ContentLibrary,
    which: str,
    before: Sequence[BossBattle],
    after: Sequence[BossBattle],
    *,
    before_cached: bool,
) -> TuningSimResult:
    """改前／改後兩邊的彙總與同種子配對的勝負翻轉。"""
    old = {(b.build, b.seed): b.won for b in before}
    flips = Counter(
        ("won_to_lost" if old[(b.build, b.seed)] else "lost_to_won")
        for b in after
        if (b.build, b.seed) in old and old[(b.build, b.seed)] != b.won
    )
    return TuningSimResult(
        boss=which,
        battles=len(after),
        before=_side(library, which, before),
        after=_side(library, which, after),
        flips=TuningSimFlips(won_to_lost=flips["won_to_lost"], lost_to_won=flips["lost_to_won"]),
        before_cached=before_cached,
    )


# ---------------------------------------------------------------------------
# 地圖戰的彙總（NW-2a）
# ---------------------------------------------------------------------------


def _map_side(battles: Sequence[MapBattle], probe: Sequence[str]) -> TuningMapSide:
    tally: Counter[str] = Counter()
    for battle in battles:
        tally.update(battle.tally)
    n = len(battles)
    rates: list[TuningSkillRate] = []
    for skill in probe:
        for team in ("ally", "enemy"):
            turns = tally[f"turns|{team}|{skill}"]
            casts = tally[f"cast|{team}|{skill}"]
            if turns or casts:
                rates.append(
                    TuningSkillRate(
                        skill=skill,
                        team=team,
                        casts=casts,
                        turns=turns,
                        battles=n,
                        small=turns < SMALL_SAMPLE,
                    )
                )
    maps: dict[str, list[MapBattle]] = {}
    for battle in battles:
        maps.setdefault(battle.map_id, []).append(battle)
    return TuningMapSide(
        n=n,
        wins=sum(b.won for b in battles),
        rounds=sum(b.rounds for b in battles),
        allies=sum(b.allies for b in battles),
        downed=sum(b.downed for b in battles),
        small=n < SMALL_SAMPLE,
        skills=rates,
        maps=[
            TuningSimBuildResult(build=k, n=len(v), wins=sum(b.won for b in v))
            for k, v in maps.items()
        ],
    )


def summarize_map(
    maps: Sequence[str],
    probe: Sequence[str],
    before: Sequence[MapBattle],
    after: Sequence[MapBattle],
    *,
    before_cached: bool,
) -> TuningMapSimResult:
    """地圖戰改前／改後的彙總（勝率、輪數、倒下率、受測招施放率）與同種子配對的勝負翻轉。"""
    old = {(b.map_id, b.seed): b.won for b in before}
    flips = Counter(
        ("won_to_lost" if old[(b.map_id, b.seed)] else "lost_to_won")
        for b in after
        if (b.map_id, b.seed) in old and old[(b.map_id, b.seed)] != b.won
    )
    return TuningMapSimResult(
        maps=list(maps),
        battles=len(after),
        before=_map_side(before, probe),
        after=_map_side(after, probe),
        flips=TuningSimFlips(won_to_lost=flips["won_to_lost"], lost_to_won=flips["lost_to_won"]),
        before_cached=before_cached,
    )


# ---------------------------------------------------------------------------
# 工作
# ---------------------------------------------------------------------------


@dataclass
class _Job:
    job_id: str
    which: str
    total: int
    estimate_s: float
    started: float
    done: int = 0
    state: Literal["running", "done", "failed", "cancelled"] = "running"
    error_zh: str | None = None
    result: TuningSimResult | None = None
    map_result: TuningMapSimResult | None = None
    ratio_result: TuningRatioSimResult | None = None
    elapsed_s: float = 0.0
    cancelled: threading.Event = field(default_factory=threading.Event)
    futures: list[Future[Any]] = field(default_factory=list)

    def view(self) -> TuningSimJob:
        running = self.state == "running"
        return TuningSimJob(
            job_id=self.job_id,
            state=self.state,
            done=self.done,
            total=self.total,
            estimate_s=round(self.estimate_s, 1),
            elapsed_s=round(time.perf_counter() - self.started if running else self.elapsed_s, 1),
            error_zh=self.error_zh,
            result=self.result,
            map_result=self.map_result,
            ratio_result=self.ratio_result,
        )


@dataclass(frozen=True)
class _Plan:
    job: _Job
    task: Callable[[str | None, Any], Any]
    jobs: Sequence[Any]
    cached: list[Any] | None
    before_key: str
    before_root: str
    after_root: str
    finish: Callable[[_Job, list[Any], list[Any], bool], None]
    """把改前／改後的結果彙總進 ``_Job``。"""
    timing: str
    persist: bool = True
    """改前結果存進 ``sims/before-*.json``（比值另由 ``finish`` 存進 ``ratios/``，這裡為假）。"""
    same: bool = False
    """改前改後是同一份內容：只跑一次，改後＝改前。"""
    battles: int | None = None
    """比值：一次（改前或改後）的場數（組數 × 種子），記每秒場數用。"""


class SimJobs:
    """一次一個的模擬工作（伺服器內共用一份）。"""

    def __init__(
        self,
        cache_dir: Path,
        *,
        workers: int | None = None,
        task: Task = probe_task,
        map_task: MapTask = map_probe_task,
        ratio_task: RatioTask = ratio_task,
        executor_factory: ExecutorFactory = _spawn_pool,
    ) -> None:
        self.cache_dir = cache_dir
        self.workers = workers or default_workers()
        self._task = task
        self._map_task = map_task
        self._ratio_task = ratio_task
        self._factory = executor_factory
        self._pool: Executor | None = None
        self._lock = threading.Lock()
        self._jobs: dict[str, _Job] = {}
        self._current: _Job | None = None
        self._thread: threading.Thread | None = None

    # -- 估時 ---------------------------------------------------------------

    def _timing(self, key: str, default: float) -> float:
        try:
            data = json.loads((self.cache_dir / _TIMING_FILE).read_text(encoding="utf-8"))
            return float(data[key])
        except (OSError, ValueError, KeyError, TypeError):
            return default

    @property
    def seconds_per_battle(self) -> float:
        return self._timing(_BOSS_TIMING, DEFAULT_SECONDS_PER_BATTLE)

    @property
    def map_seconds_per_battle(self) -> float:
        return self._timing(_MAP_TIMING, DEFAULT_MAP_SECONDS_PER_BATTLE)

    @property
    def ratio_battles_per_second(self) -> float:
        return self._timing(_RATIO_TIMING, DEFAULT_RATIO_RATE)

    def _record_timing(self, key: str, battles: int, seconds: float) -> None:
        if battles <= 0:
            return
        per = max(seconds * self.workers / battles, 0.01)
        self._write_timing(key, round(per, 3))

    def _write_timing(self, key: str, value: float) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / _TIMING_FILE
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data = data if isinstance(data, dict) else {}
        data[key] = value
        path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

    def estimate(self, battles: int, per: float | None = None) -> float:
        return battles * (self.seconds_per_battle if per is None else per) / self.workers

    # -- 快取 ---------------------------------------------------------------

    def _before_path(self, key: str) -> Path:
        return self.cache_dir / f"before-{key[:24]}.json"

    def _load_before(self, key: str, kind: type[Any]) -> list[Any] | None:
        path = self._before_path(key)
        if not path.is_file():
            return None
        rows = json.loads(path.read_text(encoding="utf-8"))
        return [kind(**row) for row in rows]

    def _save_before(self, key: str, battles: Sequence[Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        rows = [asdict(b) for b in battles]
        text = json.dumps(rows, ensure_ascii=False, sort_keys=True)
        self._before_path(key).write_text(text, encoding="utf-8")

    @staticmethod
    def before_key(tree: str, which: str, builds: Sequence[str], seeds: int) -> str:
        raw = json.dumps([tree, which, list(builds), seeds])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def map_before_key(tree: str, jobs: Sequence[SkillProbeJob]) -> str:
        """地圖戰改前快取的鍵：樹雜湊＋整份工作清單（地圖、種子、陣容、裝到 build、受測招）。"""
        raw = json.dumps(["map", tree, [asdict(j) for j in jobs]], sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # -- 工作 ---------------------------------------------------------------

    @property
    def running(self) -> str | None:
        current = self._current
        return current.job_id if current is not None and current.state == "running" else None

    def _launch(
        self,
        which: str,
        count: int,
        cached: list[Any] | None,
        per: float,
        *,
        same: bool = False,
        estimate_s: float | None = None,
    ) -> _Job:
        runs = 1 if cached is not None or same else 2
        total = count * runs
        with self._lock:
            if self.running is not None:
                raise SimBusyError("已有模擬在跑，等它跑完或先取消")
            job = _Job(
                job_id=secrets.token_hex(6),
                which=which,
                total=total,
                estimate_s=self.estimate(total, per) if estimate_s is None else estimate_s * runs,
                started=time.perf_counter(),
            )
            self._jobs = {k: v for k, v in self._jobs.items() if v.state != "running"}
            self._jobs[job.job_id] = job
            self._current = job
        return job

    def _spawn(self, plan: _Plan) -> TuningSimJob:
        self._thread = threading.Thread(target=self._run, args=(plan,), daemon=True)
        self._thread.start()
        return plan.job.view()

    def start(
        self,
        library: ContentLibrary,
        *,
        which: str,
        builds: Sequence[str],
        seeds: int,
        before_root: Path,
        after_root: Path,
        before_key: str,
    ) -> TuningSimJob:
        """頭目戰（NW-1）。"""
        if which not in BOSSES:
            raise SimRequestError(f"沒有這個頭目情境：{which}")
        known = {b.id for b in library.builds.builds}
        unknown = [b for b in builds if b not in known]
        if unknown or not builds:
            raise SimRequestError("build 不對：" + ("、".join(unknown) or "至少要選一個"))
        jobs = boss_jobs(library, which, seeds, builds)
        if len(jobs) > MAX_BATTLES:
            raise SimRequestError(
                f"一次最多 {MAX_BATTLES} 場（這次 {len(jobs)} 場），請減少種子或 build"
            )
        cached = self._load_before(before_key, BossBattle)
        job = self._launch(which, len(jobs), cached, self.seconds_per_battle)

        def finish(job: _Job, before: list[Any], after: list[Any], was_cached: bool) -> None:
            job.result = summarize(library, which, before, after, before_cached=was_cached)

        plan = _Plan(
            job,
            self._task,
            jobs,
            cached,
            before_key,
            str(before_root),
            str(after_root),
            finish,
            _BOSS_TIMING,
        )
        return self._spawn(plan)

    def start_map(
        self,
        *,
        jobs: Sequence[SkillProbeJob],
        probe: Sequence[str],
        before_root: Path,
        after_root: Path,
        before_key: str,
    ) -> TuningSimJob:
        """地圖戰（NW-2a 5.6）：``jobs`` 由呼叫端組好（地圖、種子、陣容、受測招）。"""
        if not jobs:
            raise SimRequestError("至少要選一張地圖")
        if len(jobs) > MAX_BATTLES:
            raise SimRequestError(
                f"一次最多 {MAX_BATTLES} 場（這次 {len(jobs)} 場），請減少種子或地圖"
            )
        cached = self._load_before(before_key, MapBattle)
        job = self._launch("map", len(jobs), cached, self.map_seconds_per_battle)
        maps = list(dict.fromkeys(j.map_id for j in jobs))

        def finish(job: _Job, before: list[Any], after: list[Any], was_cached: bool) -> None:
            job.map_result = summarize_map(maps, probe, before, after, before_cached=was_cached)

        plan = _Plan(
            job,
            self._map_task,
            jobs,
            cached,
            before_key,
            str(before_root),
            str(after_root),
            finish,
            _MAP_TIMING,
        )
        return self._spawn(plan)

    def start_ratio(
        self,
        *,
        jobs: Sequence[RatioJob],
        battles: int,
        cached: list[Any] | None,
        same: bool,
        before_root: Path,
        after_root: Path,
        finish: Callable[[list[Any], list[Any], bool], TuningRatioSimResult],
    ) -> TuningSimJob:
        """1 階比值（NW-2c 5.7）：``jobs`` 一組一個工作單位；``battles``＝組數 × 種子（估時與記
        每秒場數用）；``cached``＝改前的列（:class:`~trpg.api.tuning.ratios.RatioStore`）；
        ``same``＝草稿沒改內容（只跑一次）。``finish(改前, 改後, 是否快取)`` 回結果並自行存檔。"""
        if not jobs:
            raise SimRequestError("沒有量得到比值的招（只量 1 階主動武器技、非敵人專用）")
        estimate = battles / self.ratio_battles_per_second
        job = self._launch("ratio", len(jobs), cached, 0.0, same=same, estimate_s=estimate)

        def done(job: _Job, before: list[Any], after: list[Any], was_cached: bool) -> None:
            job.ratio_result = finish(before, after, was_cached)

        plan = _Plan(
            job,
            self._ratio_task,
            jobs,
            cached,
            "",
            str(before_root),
            str(after_root),
            done,
            _RATIO_TIMING,
            persist=False,
            same=same,
            battles=battles,
        )
        return self._spawn(plan)

    def _pool_for(self) -> Executor:
        if self._pool is None:
            self._pool = self._factory(self.workers)
        return self._pool

    def _batch(
        self,
        job: _Job,
        task: Callable[[str | None, Any], Any],
        root: str,
        jobs: Sequence[Any],
    ) -> list[Any] | None:
        pool = self._pool_for()
        futures = [pool.submit(task, root, j) for j in jobs]
        job.futures = futures
        out: list[Any] = []
        for future in futures:
            if job.cancelled.is_set():
                for pending in futures:
                    pending.cancel()
                return None
            try:
                out.append(future.result())
            except CancelledError:
                return None
            job.done += 1
        return out

    def _run(self, plan: _Plan) -> None:
        job, jobs, cached = plan.job, plan.jobs, plan.cached
        try:
            before = cached
            if before is None:
                before = self._batch(job, plan.task, plan.before_root, jobs)
                if before is not None and plan.persist:
                    self._save_before(plan.before_key, before)
            if before is None or plan.same:
                after = before
            else:
                after = self._batch(job, plan.task, plan.after_root, jobs)
            if before is None or after is None:
                job.state = "cancelled"
                return
            plan.finish(job, before, after, cached is not None)
            job.elapsed_s = time.perf_counter() - job.started
            self._record(plan, job)
            job.state = "done"
        except Exception as exc:  # 背景工作：任何錯誤都轉成工作的失敗狀態
            job.error_zh = f"模擬失敗：{exc}"
            job.state = "failed"
        finally:
            if job.state != "done":
                job.elapsed_s = time.perf_counter() - job.started

    def _record(self, plan: _Plan, job: _Job) -> None:
        if plan.battles is None:
            self._record_timing(plan.timing, job.total, job.elapsed_s)
            return
        runs = job.total // max(1, len(plan.jobs))
        if runs > 0 and job.elapsed_s > 0:
            rate = plan.battles * runs / job.elapsed_s
            self._write_timing(plan.timing, round(max(rate, 1.0), 1))

    def get(self, job_id: str) -> TuningSimJob | None:
        job = self._jobs.get(job_id)
        return None if job is None else job.view()

    def cancel(self, job_id: str) -> TuningSimJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.cancelled.set()
        for future in job.futures:
            future.cancel()
        return job.view()

    def wait(self, timeout: float | None = None) -> None:
        """等目前的背景執行緒結束（測試與關機用）。"""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def shutdown(self) -> None:
        current = self._current
        if current is not None:
            current.cancelled.set()
        pool, self._pool = self._pool, None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
