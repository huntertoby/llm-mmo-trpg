"""NW-2a：地圖戰的模擬工作（假的每場函式＋執行緒池）。

真的地圖戰見 ``tests/sim/test_skill_probe.py``。"""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path

import pytest

from trpg.api.tuning.schemas import TuningSimInject, TuningSimRequest
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.sim_jobs import SimJobs, SimRequestError
from trpg.sim.skill_probe import MapBattle, SkillProbeJob, map_jobs


def _task(root: str | None, job: SkillProbeJob) -> MapBattle:
    assert root is not None
    after = root.endswith("after") or "draft" in root
    won = after or job.seed % 2 == 0
    tally = {f"cast|ally|{s}": 2 for s in job.probe} | {f"turns|ally|{s}": 5 for s in job.probe}
    return MapBattle(job.map_id, job.seed, won, 7, 4, 1, tally)


def _threads(workers: int) -> Executor:
    return ThreadPoolExecutor(max_workers=workers)


def test_map_job_summarizes_rates_flips_and_caches(tmp_path: Path) -> None:
    sims = SimJobs(tmp_path / "sims", workers=2, map_task=_task, executor_factory=_threads)
    jobs = map_jobs(["open_plain"], 4, None, (), ["skill_fire_arrow"])
    key = SimJobs.map_before_key("tree", jobs)
    started = sims.start_map(
        jobs=jobs,
        probe=["skill_fire_arrow"],
        before_root=tmp_path / "before",
        after_root=tmp_path / "after",
        before_key=key,
    )
    assert started.total == 8
    sims.wait(30)
    job = sims.get(started.job_id)
    assert job is not None and job.state == "done" and job.result is None
    result = job.map_result
    assert result is not None and result.battles == 4 and result.maps == ["open_plain"]
    assert result.before.wins == 2 and result.after.wins == 4
    assert result.flips.lost_to_won == 2 and result.flips.won_to_lost == 0
    rate = result.after.skills[0]
    assert (rate.skill, rate.team, rate.casts, rate.turns, rate.battles) == (
        "skill_fire_arrow",
        "ally",
        8,
        20,
        4,
    )
    assert rate.small and sims.map_seconds_per_battle > 0
    again = sims.start_map(
        jobs=jobs,
        probe=["skill_fire_arrow"],
        before_root=tmp_path / "before",
        after_root=tmp_path / "after",
        before_key=key,
    )
    assert again.total == 4  # 改前命中快取
    sims.wait(30)
    second = sims.get(again.job_id)
    assert second is not None and second.map_result is not None
    assert second.map_result.before_cached
    assert second.map_result.after == result.after


def test_map_request_validation(read_service: TuningService) -> None:
    with pytest.raises(SimRequestError, match="地圖"):
        read_service.start_sim(TuningSimRequest(scenario="map", maps=["test_small"]))
    with pytest.raises(SimRequestError, match="地圖"):
        read_service.start_sim(TuningSimRequest(scenario="map"))
    with pytest.raises(SimRequestError, match="build"):
        read_service.start_sim(
            TuningSimRequest(scenario="map", maps=["open_plain"], allies=["build_nope"])
        )
    with pytest.raises(SimRequestError, match="沒有這招"):
        read_service.start_sim(
            TuningSimRequest(
                scenario="map",
                maps=["open_plain"],
                inject=[TuningSimInject(build="build_fire", skill="skill_nope")],
            )
        )
    with pytest.raises(SimRequestError, match="頭目"):
        read_service.start_sim(TuningSimRequest(scenario="boss"))
    options = read_service.sim_options()
    ids = [m.id for m in options.maps]
    assert len(ids) == 14 and "training_range" not in ids
    assert not any(m.startswith("test_") for m in ids)
