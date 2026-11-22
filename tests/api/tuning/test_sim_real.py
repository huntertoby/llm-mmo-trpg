"""NW-1a T-A9（真的打）：spawn 程序池跑頭目戰，改前／改後各 1 場；同參數兩次結果逐字相同。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.schemas import TuningSimRequest, TuningSimResult
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.sim_jobs import SimJobs
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir

pytestmark = pytest.mark.slow
UNIT_FILE = "units/ashen_heart.yaml"


def _run(tmp: Path, library: ContentLibrary) -> TuningSimResult:
    service = TuningService(bundled_content_dir(), tmp, library, sims=SimJobs(tmp / "s", workers=2))
    service.git = None
    # 現值從內容讀（×10 之後是 1360，寫死 160 會讓草稿驗證不過）；改後照舊是一半。
    unit = yaml.safe_load((bundled_content_dir() / UNIT_FILE).read_text(encoding="utf-8"))
    max_hp = int(unit["max_hp"])
    change = Change(file=UNIT_FILE, path="max_hp", old=max_hp, new=max_hp // 2)
    service.drafts.put(Draft(name="current", changes=(change,)))
    request = TuningSimRequest(boss="ashen", builds=["build_tank"], seeds=1)
    try:
        job = service.start_sim(request)
        service.sims.wait(600)
        view = service.sims.get(job.job_id)
    finally:
        service.shutdown()
    assert view is not None and view.state == "done", view
    assert view.result is not None
    return view.result


def test_real_pool_is_deterministic(tmp_path: Path, content_library: ContentLibrary) -> None:
    one = _run(tmp_path / "a", content_library)
    two = _run(tmp_path / "b", content_library)
    assert one == two
    assert one.battles == 1 and one.before.n == one.after.n == 1
    assert one.before.phases[0].turns > 0
