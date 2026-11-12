"""NW-2c：工坊內的 1 階比值（T-C2）、基準匯入（T12）、分組預覽的結構違規（NW-2b 待決 5）。

比值工作用真的量測核心（``trpg.sim.skill_ratio.ratio_task``）但在執行緒池裡跑、每組 2 種子（冒煙
規模）；讀專案內建 ``content/`` 的服務一律 ``git = None``（不可能寫回）。"""

from __future__ import annotations

import json
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.tuning.ratios import MAX_WORK, BaselineError, RatioStore, run_data
from trpg.api.tuning.schemas import (
    TuningChangeIn,
    TuningGroupIn,
    TuningGroupOp,
    TuningSimRequest,
)
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.sim_jobs import SimJobs, SimRequestError
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.sim.skill_ratio import RatioJob, measure

FIRE = "skill_fire_arrow"
FIRE_FILE = "skills/skill_fire_arrow.yaml"
SEEDS = 2


def _threads(workers: int) -> Executor:
    return ThreadPoolExecutor(max_workers=workers)


@pytest.fixture
def service(tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    sims = SimJobs(tmp_path / "saves" / "tuning" / "sims", workers=2, executor_factory=_threads)
    svc = TuningService(bundled_content_dir(), tmp_path / "saves", content_library, sims=sims)
    svc.git = None
    return svc


def _fire_up(service: TuningService, new: int = 900) -> None:
    service.put_draft(
        "current",
        [TuningChangeIn(file=FIRE_FILE, path="effects[0].multiplier_permille", old=800, new=new)],
    )


def _run(service: TuningService, skills: list[str], seeds: int = SEEDS) -> object:
    started = service.start_sim(TuningSimRequest(scenario="ratio", skills=skills, seeds=seeds))
    service.sims.wait(120)
    job = service.sims.get(started.job_id)
    assert job is not None and job.state == "done", job
    return job


def test_ratio_job_before_after_cache_and_determinism(service: TuningService) -> None:
    _fire_up(service)
    plan = service.ratio_plan([FIRE], SEEDS)
    assert plan.problem_zh is None and plan.jobs == 6 and plan.groups == 6
    first = _run(service, [FIRE])
    assert first.total == 12  # type: ignore[attr-defined]  # 改前改後各 6 組
    result = first.ratio_result  # type: ignore[attr-defined]
    assert result is not None and not result.before_cached and not result.same_content
    [row] = result.skills
    assert row.skill_id == FIRE and row.before is not None and row.after is not None
    before = float(row.before.plain.split("～")[-1])
    after = float(row.after.plain.split("～")[-1])
    assert after > before  # 武器倍率 800 → 900，比值變高
    assert [line.key for line in row.after.lines] == ["arrow"]  # 1 AP 箭類（建議線）
    assert row.after.lines[0].tentative
    second = _run(service, [FIRE])
    assert second.total == 6  # type: ignore[attr-defined]  # 改前命中快取
    again = second.ratio_result  # type: ignore[attr-defined]
    assert again is not None and again.before_cached
    assert again.skills == result.skills  # 同參數兩次相同


def test_without_a_draft_the_ratio_runs_once(service: TuningService) -> None:
    job = _run(service, [FIRE, "skill_fire_bolt"])
    assert job.total == 6  # type: ignore[attr-defined]  # 沒有草稿：改前＝改後，只跑一次
    result = job.ratio_result  # type: ignore[attr-defined]
    assert result is not None and result.same_content
    assert [s.skill_id for s in result.skipped] == ["skill_fire_bolt"]  # 法術不量
    [row] = result.skills
    assert row.before is not None and row.after is not None
    assert row.before.model_copy(update={"source_zh": ""}) == row.after.model_copy(
        update={"source_zh": ""}
    )
    view = service.skill_ratio(FIRE)
    assert view.applicable and view.current is not None
    assert view.current.source == "workshop" and not view.current.stale
    assert view.current.plain == row.after.plain


def test_plan_limits_and_unknown_skills(
    service: TuningService, content_library: ContentLibrary
) -> None:
    measurable = [
        s.id
        for s in sorted(content_library.skills.values(), key=lambda s: s.id)
        if s.tier == 1 and s.kind == "active" and s.category == "weapon" and not s.enemy_only
    ][:100]
    big = service.ratio_plan(measurable, 250)
    assert big.work == big.groups * 250 > MAX_WORK
    assert big.problem_zh is not None and "40,000" in big.problem_zh
    with pytest.raises(SimRequestError, match="40,000"):
        service.start_sim(TuningSimRequest(scenario="ratio", skills=measurable, seeds=250))
    with pytest.raises(SimRequestError, match="沒有這招"):
        service.ratio_plan(["skill_nope"], 5)
    none = service.ratio_plan(["skill_fire_bolt"], 5)
    assert none.problem_zh is not None and none.jobs == 0
    small = service.ratio_plan([FIRE], 50)
    assert small.seconds == pytest.approx(small.work / 450, abs=0.1)


def test_baseline_import_and_staleness(
    service: TuningService, content_library: ContentLibrary, tmp_path: Path
) -> None:
    rows = [measure(content_library, RatioJob("bow", FIRE, SEEDS))]
    data = run_data(content_library, [FIRE], SEEDS, rows)
    info = service.import_ratio_baseline(json.loads(json.dumps(data)))
    assert info.skills == 1 and info.rows == 1 and info.same_content
    view = service.skill_ratio(FIRE)
    assert view.current is not None and view.current.source == "baseline"
    assert not view.current.stale and view.previous is None
    store = RatioStore(tmp_path / "other")
    store.import_baseline(data, "some-older-tree")
    stale = store.skill_view(content_library.skills[FIRE], "current-tree")
    assert stale.current is not None and stale.current.stale
    assert "內容已變，僅供參考" in stale.current.source_zh
    with pytest.raises(BaselineError):
        service.import_ratio_baseline({"seeds": 1})
    assert not service.skill_ratio("skill_fire_bolt").applicable


def test_previous_is_the_last_measurement_of_other_content(
    content_library: ContentLibrary, tmp_path: Path
) -> None:
    store = RatioStore(tmp_path / "ratios")
    old = run_data(content_library, [FIRE], 1, [measure(content_library, RatioJob("bow", FIRE, 1))])
    new = run_data(content_library, [FIRE], 2, [measure(content_library, RatioJob("bow", FIRE, 2))])
    store.save("tree-a", [FIRE], 1, old)
    store.save("tree-b", [FIRE], 2, new)
    view = store.skill_view(content_library.skills[FIRE], "tree-b")
    assert view.current is not None and view.current.seeds == 2
    assert view.previous is not None and view.previous.seeds == 1 and view.previous.stale
    assert store.find("tree-a", [FIRE], 1) == old
    assert store.find("tree-a", [FIRE], 2) is None


def test_group_preview_lists_structure_violations_and_ratio(service: TuningService) -> None:
    preview = service.group_preview(
        TuningGroupIn(
            skills=["skill_rng_hamstring_shot", FIRE],
            target="damage_base",
            op=TuningGroupOp(kind="ladder", value=1),
        )
    )
    rows = {r.skill_id: r for r in preview.rows}
    hamstring = rows["skill_rng_hamstring_shot"]
    assert [v.rule for v in hamstring.violations] == ["skeleton.secondary_share"]
    assert "骨架" in hamstring.violations[0].message_zh
    assert rows[FIRE].violations == []
    assert all(not v.rule.startswith("budget.") for r in preview.rows for v in r.violations)
    assert rows[FIRE].ratio is None  # 還沒有量過


def test_ratio_routes(service: TuningService) -> None:
    app = create_app(tuning=True)
    app.state.tuning = service
    with TestClient(app) as client:
        plan = client.post("/api/tuning/skills/ratio-plan", json={"skills": [FIRE], "seeds": 5})
        assert plan.status_code == 200 and plan.json()["groups"] == 6
        view = client.get(f"/api/tuning/skills/{FIRE}/ratio")
        assert view.status_code == 200 and view.json()["applicable"] is True
        assert client.get("/api/tuning/skills/skill_nope/ratio").status_code == 404
        assert client.get("/api/tuning/skills/ratio-baseline").json() is None
        bad = client.post("/api/tuning/skills/ratio-baseline", json={"rows": []})
        assert bad.status_code == 422
        options = client.get("/api/tuning/sims/options").json()
        assert options["ratio_default_seeds"] == 50 and options["ratio_max_work"] == 40000
