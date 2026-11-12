"""NW-1a T-A9：模擬工作（一次一個、取消、改前快取、規模上限、翻轉計數）。

用假的每場函式與執行緒池（不開程序、不真的打）；真的頭目戰另見 ``test_sim_real.py``（slow）。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path

import pytest

from trpg.api.tuning.schemas import TuningSimJob
from trpg.api.tuning.sim_jobs import MAX_BATTLES, SimBusyError, SimJobs, SimRequestError, summarize
from trpg.content.library import ContentLibrary
from trpg.sim.boss_probe import BUILDS, BossBattle, ProbeJob


def _fake(after_wins: Callable[[ProbeJob], bool]) -> Callable[[str | None, ProbeJob], BossBattle]:
    def task(root: str | None, job: ProbeJob) -> BossBattle:
        assert root is not None
        after = root.endswith("after")
        won = after_wins(job) if after else job.seed % 2 == 0
        tally = {"turn|1": 10, "cast|1|skill_cluster_bolt": 3, "turn|2": 4, "reach|2": 1}
        return BossBattle(
            boss=job.boss or "",
            build=job.build,
            seed=job.seed,
            won=won,
            rounds=12 if after else 10,
            allies=3,
            downed=1 if won else 3,
            tally=tally,
        )

    return task


def _threads(workers: int) -> Executor:
    return ThreadPoolExecutor(max_workers=workers)


def _jobs(tmp_path: Path, task: Callable[[str | None, ProbeJob], BossBattle]) -> SimJobs:
    return SimJobs(tmp_path / "sims", workers=2, task=task, executor_factory=_threads)


def _start(
    sims: SimJobs, library: ContentLibrary, tmp_path: Path, seeds: int = 2, key: str = "k"
) -> TuningSimJob:
    return sims.start(
        library,
        which="mist",
        builds=list(BUILDS[:2]),
        seeds=seeds,
        before_root=tmp_path / "before",
        after_root=tmp_path / "after",
        before_key=key,
    )


def test_job_runs_before_and_after_and_counts_flips(
    tmp_path: Path, content_library: ContentLibrary
) -> None:
    sims = _jobs(tmp_path, _fake(lambda job: True))  # 改後全贏
    started = _start(sims, content_library, tmp_path)
    assert started.total == 8 and started.state == "running"
    sims.wait(30)
    job = sims.get(started.job_id)
    assert job is not None and job.state == "done" and job.done == 8
    result = job.result
    assert result is not None and result.battles == 4 and not result.before_cached
    assert result.before.wins == 2 and result.after.wins == 4  # 改前偶數種子贏
    assert result.flips.lost_to_won == 2 and result.flips.won_to_lost == 0
    assert result.after.rounds == 48 and result.after.allies == 12 and result.after.downed == 4
    assert result.after.small  # 4 場 < 30
    phase1 = result.after.phases[0]
    assert phase1.turns == 40 and phase1.skills[0].skill == "skill_cluster_bolt"
    assert phase1.skills[0].casts == 12 and phase1.skills[0].small is False
    assert sims.seconds_per_battle > 0


def test_before_results_are_cached(tmp_path: Path, content_library: ContentLibrary) -> None:
    calls: list[str] = []

    def counting(root: str | None, job: ProbeJob) -> BossBattle:
        calls.append(str(root))
        return _fake(lambda j: False)(root, job)

    sims = _jobs(tmp_path, counting)
    _start(sims, content_library, tmp_path)
    sims.wait(30)
    assert len(calls) == 8
    second = _start(sims, content_library, tmp_path)
    assert second.total == 4  # 改前命中快取，只跑改後
    sims.wait(30)
    done = sims.get(second.job_id)
    assert done is not None and done.result is not None and done.result.before_cached
    assert len(calls) == 12 and all(c.endswith("after") for c in calls[8:])
    third = _start(sims, content_library, tmp_path, key="other-content")  # 內容變了：重跑改前
    assert third.total == 8
    sims.wait(30)


def test_only_one_job_at_a_time_and_cancel(tmp_path: Path, content_library: ContentLibrary) -> None:
    gate = threading.Event()

    def blocked(root: str | None, job: ProbeJob) -> BossBattle:
        gate.wait(30)
        return _fake(lambda j: True)(root, job)

    sims = _jobs(tmp_path, blocked)
    first = _start(sims, content_library, tmp_path)
    assert sims.running == first.job_id
    with pytest.raises(SimBusyError, match="已有模擬在跑"):
        _start(sims, content_library, tmp_path)
    cancelled = sims.cancel(first.job_id)
    assert cancelled is not None
    gate.set()
    sims.wait(30)
    job = sims.get(first.job_id)
    assert job is not None and job.state == "cancelled" and job.result is None
    assert sims.running is None
    _start(sims, content_library, tmp_path)  # 取消後可以再開
    sims.wait(30)
    sims.shutdown()


def test_scale_limit_and_bad_requests(tmp_path: Path, content_library: ContentLibrary) -> None:
    sims = _jobs(tmp_path, _fake(lambda j: True))
    seeds = MAX_BATTLES // 2 + 1
    with pytest.raises(SimRequestError, match=f"一次最多 {MAX_BATTLES} 場"):
        _start(sims, content_library, tmp_path, seeds=seeds)
    for kwargs, why in (({"which": "nope"}, "頭目情境"), ({"builds": ["build_x"]}, "build 不對")):
        args = {
            "which": "mist",
            "builds": list(BUILDS[:1]),
            "seeds": 1,
            "before_root": tmp_path,
            "after_root": tmp_path,
            "before_key": "k",
            **kwargs,
        }
        with pytest.raises(SimRequestError, match=why):
            sims.start(content_library, **args)  # type: ignore[arg-type]
    assert sims.running is None


def test_failure_becomes_a_failed_job(tmp_path: Path, content_library: ContentLibrary) -> None:
    def broken(root: str | None, job: ProbeJob) -> BossBattle:
        raise RuntimeError("內容庫載入失敗")

    sims = _jobs(tmp_path, broken)
    started = _start(sims, content_library, tmp_path)
    sims.wait(30)
    job = sims.get(started.job_id)
    assert job is not None and job.state == "failed" and "內容庫載入失敗" in (job.error_zh or "")


def test_summarize_is_deterministic(content_library: ContentLibrary) -> None:
    battles = [
        BossBattle("mist", "build_fire", s, s % 2 == 0, 10, 3, 1, {"turn|1": 5}) for s in range(3)
    ]
    one = summarize(content_library, "mist", battles, battles, before_cached=False)
    two = summarize(content_library, "mist", battles, battles, before_cached=False)
    assert one.model_dump_json() == two.model_dump_json()
    assert one.flips.won_to_lost == one.flips.lost_to_won == 0
    assert all(p.name_zh for p in one.after.phases)
