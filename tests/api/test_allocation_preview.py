"""升級配點與營火重配的資源預覽（Phase 3H-5）：後端算，和一輪面板同一組函式。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_runs_api import _create, _ok, runs_client, save_dir  # noqa: F401
from trpg.content.library import ContentLibrary


def test_allocation_preview_matches_the_run_formulas(
    runs_client: TestClient,  # noqa: F811
    library: ContentLibrary,
) -> None:
    run = _create(runs_client)
    core = library.ruleset.core
    hero = run["hero"]
    url = f"/api/runs/{run['run_id']}/allocation-preview"
    none = _ok(runs_client.post(url, json={"attributes": {}}))
    assert none["summary_zh"] == "" and none["hp"] == hero["max_hp"]
    out = _ok(runs_client.post(url, json={"attributes": {"con": 2, "str": 1}}))
    assert out["hp"] == hero["max_hp"] + 2 * core.hp_per_con_point
    assert "最大 HP ＋" in out["summary_zh"]


def test_negative_points_count_as_zero_and_unknown_run_is_404(
    runs_client: TestClient,  # noqa: F811
) -> None:
    run = _create(runs_client)
    url = f"/api/runs/{run['run_id']}/allocation-preview"
    out = _ok(runs_client.post(url, json={"attributes": {"con": -3}}))
    assert out["summary_zh"] == ""
    assert (
        runs_client.post("/api/runs/nope/allocation-preview", json={"attributes": {}}).status_code
        == 404
    )
