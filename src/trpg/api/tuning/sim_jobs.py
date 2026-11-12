"""數值工坊的模擬工作（NW-1a A7，規格 5.4）：頭目戰改前／改後同種子配對。

- 背景執行緒＋程序池（spawn，``min(4, 核心數 − 2)``）；**一次只跑一個**（再開回 409）；可取消
  （取消還沒開始的場次；已在跑的那幾場跑完就丟掉）。
- 程序池在工作之間保留（Windows spawn 每個行程要重新匯入 ``trpg``，第一次較慢）；每個工作行程依
  內容資料夾快取內容庫（:func:`trpg.sim.boss_probe.library_for`）。
- 改前結果以「``content/`` 的樹雜湊＋情境參數」為鍵存 ``<save_dir>/tuning/sims/``；同鍵直接用。
- 規模上限 :data:`MAX_BATTLES`（單次改後的場數）。
- 結果不含耗時（同參數同內容跑兩次逐字相同）；耗時另放 ``elapsed_s``。
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
from typing import Final, Literal

from trpg.api.tuning.schemas import (
    SMALL_SAMPLE,
    TuningSimBuildResult,
    TuningSimFlips,
    TuningSimJob,
    TuningSimPhase,
    TuningSimResult,
    TuningSimSide,
    TuningSimSkill,
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

__all__ = [
    "DEFAULT_SECONDS_PER_BATTLE",
    "MAX_BATTLES",
    "SimBusyError",
    "SimJobs",
    "SimRequestError",
    "default_workers",
    "summarize",
]

MAX_BATTLES: Final = 160
DEFAULT_SECONDS_PER_BATTLE: Final = 1.6
"""沒實測過時的每場秒數（BAL-20：頭目戰每場約 1.2～1.9 核心秒）。"""
_TIMING_FILE: Final = "timing.json"

type Task = Callable[[str | None, ProbeJob], BossBattle]
type ExecutorFactory = Callable[[int], Executor]


class SimBusyError(RuntimeError):
    """已有模擬在跑（409）。"""


class SimRequestError(ValueError):
    """情境參數不對（422）。"""


def default_workers() -> int:
    return max(1, min(4, (os.cpu_count() or 1) - 2))


def _spawn_pool(workers: int) -> Executor:
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))


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
    elapsed_s: float = 0.0
    cancelled: threading.Event = field(default_factory=threading.Event)
    futures: list[Future[BossBattle]] = field(default_factory=list)

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
        )


@dataclass(frozen=True)
class _Plan:
    library: ContentLibrary
    job: _Job
    jobs: Sequence[ProbeJob]
    cached: list[BossBattle] | None
    before_key: str
    before_root: str
    after_root: str


class SimJobs:
    """一次一個的模擬工作（伺服器內共用一份）。"""

    def __init__(
        self,
        cache_dir: Path,
        *,
        workers: int | None = None,
        task: Task = probe_task,
        executor_factory: ExecutorFactory = _spawn_pool,
    ) -> None:
        self.cache_dir = cache_dir
        self.workers = workers or default_workers()
        self._task = task
        self._factory = executor_factory
        self._pool: Executor | None = None
        self._lock = threading.Lock()
        self._jobs: dict[str, _Job] = {}
        self._current: _Job | None = None
        self._thread: threading.Thread | None = None

    # -- 估時 ---------------------------------------------------------------

    @property
    def seconds_per_battle(self) -> float:
        try:
            data = json.loads((self.cache_dir / _TIMING_FILE).read_text(encoding="utf-8"))
            return float(data["seconds_per_battle"])
        except (OSError, ValueError, KeyError, TypeError):
            return DEFAULT_SECONDS_PER_BATTLE

    def _record_timing(self, battles: int, seconds: float) -> None:
        if battles <= 0:
            return
        per = max(seconds * self.workers / battles, 0.01)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"seconds_per_battle": round(per, 3)})
        (self.cache_dir / _TIMING_FILE).write_text(text, encoding="utf-8")

    def estimate(self, battles: int) -> float:
        return battles * self.seconds_per_battle / self.workers

    # -- 快取 ---------------------------------------------------------------

    def _before_path(self, key: str) -> Path:
        return self.cache_dir / f"before-{key[:24]}.json"

    def _load_before(self, key: str) -> list[BossBattle] | None:
        path = self._before_path(key)
        if not path.is_file():
            return None
        rows = json.loads(path.read_text(encoding="utf-8"))
        return [BossBattle(**row) for row in rows]

    def _save_before(self, key: str, battles: Sequence[BossBattle]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        rows = [asdict(b) for b in battles]
        text = json.dumps(rows, ensure_ascii=False, sort_keys=True)
        self._before_path(key).write_text(text, encoding="utf-8")

    @staticmethod
    def before_key(tree: str, which: str, builds: Sequence[str], seeds: int) -> str:
        raw = json.dumps([tree, which, list(builds), seeds])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # -- 工作 ---------------------------------------------------------------

    @property
    def running(self) -> str | None:
        current = self._current
        return current.job_id if current is not None and current.state == "running" else None

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
        cached = self._load_before(before_key)
        total = len(jobs) * (1 if cached is not None else 2)
        with self._lock:
            if self.running is not None:
                raise SimBusyError("已有模擬在跑，等它跑完或先取消")
            job = _Job(
                job_id=secrets.token_hex(6),
                which=which,
                total=total,
                estimate_s=self.estimate(total),
                started=time.perf_counter(),
            )
            self._jobs = {k: v for k, v in self._jobs.items() if v.state != "running"}
            self._jobs[job.job_id] = job
            self._current = job
        plan = _Plan(library, job, jobs, cached, before_key, str(before_root), str(after_root))
        self._thread = threading.Thread(target=self._run, args=(plan,), daemon=True)
        self._thread.start()
        return job.view()

    def _pool_for(self) -> Executor:
        if self._pool is None:
            self._pool = self._factory(self.workers)
        return self._pool

    def _batch(self, job: _Job, root: str, jobs: Sequence[ProbeJob]) -> list[BossBattle] | None:
        pool = self._pool_for()
        futures = [pool.submit(self._task, root, j) for j in jobs]
        job.futures = futures
        out: list[BossBattle] = []
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
        library, job, jobs, cached = plan.library, plan.job, plan.jobs, plan.cached
        before_key, before_root, after_root = plan.before_key, plan.before_root, plan.after_root
        try:
            before = cached if cached is not None else self._batch(job, before_root, jobs)
            if before is not None and cached is None:
                self._save_before(before_key, before)
            after = None if before is None else self._batch(job, after_root, jobs)
            if before is None or after is None:
                job.state = "cancelled"
                return
            job.result = summarize(
                library, job.which, before, after, before_cached=cached is not None
            )
            job.elapsed_s = time.perf_counter() - job.started
            self._record_timing(job.total, job.elapsed_s)
            job.state = "done"
        except Exception as exc:  # 背景工作：任何錯誤都轉成工作的失敗狀態
            job.error_zh = f"模擬失敗：{exc}"
            job.state = "failed"
        finally:
            if job.state != "done":
                job.elapsed_s = time.perf_counter() - job.started

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
