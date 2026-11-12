"""NW-1a T-A7 與端點：三道門（``dev_mode``、``TRPG_TUNING=1``、轉發標頭 403）與各端點的來回。

寫回一律換成暫存 repo 的服務；讀專案 content/ 的服務把 ``git`` 設成 ``None``（不可能寫回）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from trpg.api.tuning.routes import TUNNEL_ZH
from trpg.api.tuning.service import TUNING_ENV, TuningService
from trpg.api.tuning.sim_jobs import SimJobs
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.sim.boss_probe import BossBattle, ProbeJob

DEV = AccountSettings(dev_mode=True)
HEART = "units/ashen_heart.yaml"


def _tuning(client: TestClient) -> TuningService:
    service = client.app.state.tuning  # type: ignore[attr-defined]
    assert isinstance(service, TuningService)
    return service


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    made = make_client(library, accounts=DEV, tuning=True)
    _tuning(made).git = None  # 讀的是專案的 content/：絕不寫回
    return made


def test_dev_mode_off_means_no_routes(library: ContentLibrary, make_client: ClientFactory) -> None:
    locked = make_client(library, accounts=AccountSettings(dev_mode=False), tuning=True)
    assert locked.get("/api/tuning/status").status_code == 404
    assert not hasattr(locked.app.state, "tuning")  # type: ignore[attr-defined]
    assert not any(p.startswith("/api/tuning") for p in locked.app.openapi()["paths"])  # type: ignore[attr-defined]


def test_switch_off_means_no_routes(
    library: ContentLibrary, make_client: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(TUNING_ENV, raising=False)
    off = make_client(library, accounts=DEV)
    assert off.get("/api/tuning/status").status_code == 404
    assert off.get("/api/tuning/objects").status_code == 404
    monkeypatch.setenv(TUNING_ENV, "0")
    assert make_client(library, accounts=DEV).get("/api/tuning/status").status_code == 404
    monkeypatch.setenv(TUNING_ENV, "1")
    on = make_client(library, accounts=DEV)
    _tuning(on).git = None
    assert on.get("/api/tuning/status").status_code == 200


@pytest.mark.parametrize(
    "header",
    [
        {"CF-Connecting-IP": "203.0.113.5"},
        {"X-Forwarded-For": "203.0.113.5"},
        {"Forwarded": "for=203.0.113.5"},
        {"x-forwarded-for": ""},
    ],
)
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "/api/tuning/status"),
        ("GET", "/api/tuning/objects"),
        ("PUT", "/api/tuning/drafts/current"),
        ("POST", "/api/tuning/drafts/current/apply"),
        ("POST", "/api/tuning/sims"),
    ],
)
def test_forwarded_requests_are_refused(
    client: TestClient, header: dict[str, str], method: str, url: str
) -> None:
    reply = client.request(method, url, headers=header, json={"changes": []})
    assert reply.status_code == 403
    assert reply.json() == {"detail": TUNNEL_ZH}


def test_objects_and_fields(client: TestClient) -> None:
    rows = client.get("/api/tuning/objects", params={"kind": "unit"}).json()
    heart = next(r for r in rows if r["id"] == "ashen_heart")
    assert heart == {
        "kind": "unit",
        "id": "ashen_heart",
        "name_zh": "灰燼之心",
        "category": "boss",
        "file": HEART,
    }
    assert not any(r["id"].startswith("sim_") for r in rows)
    detail = client.get("/api/tuning/objects/unit/ashen_heart").json()
    fields = {f["path"]: f for f in detail["fields"]}
    assert fields["max_hp"]["value"] == 160 and fields["max_hp"]["label_zh"] == "最大 HP"
    assert fields["speed"]["value"] == 0
    assert fields["max_mana"]["value"] is None and "依武器大類" in fields["max_mana"]["default_zh"]
    assert fields["phases[1].trigger.permille"]["value"] == 600
    assert fields["phases[1].trigger.permille"]["label_zh"].startswith("第 2 階段「呼吸」")
    assert "phases[0].trigger.permille" not in fields
    assert any("遭遇護甲調整" in n for n in detail["notes_zh"])
    assert client.get("/api/tuning/objects/unit/sim_duelist").status_code == 404
    assert client.get("/api/tuning/objects/skill/x").status_code == 404


def test_draft_round_trip_check_and_diff(client: TestClient) -> None:
    body = {"changes": [{"file": HEART, "path": "max_hp", "old": 160, "new": "150"}]}
    put = client.put("/api/tuning/drafts/current", json=body)
    assert put.status_code == 200, put.text
    assert put.json()["changes"] == [
        {
            "file": HEART,
            "path": "max_hp",
            "old": 160,
            "new": 150,
            "object_id": "ashen_heart",
            "label_zh": "最大 HP",
        }
    ]
    assert client.get("/api/tuning/drafts/current").json() == put.json()
    assert client.get("/api/tuning/status").json()["drafts"] == ["current"]
    diff = client.get("/api/tuning/drafts/current/diff").json()
    assert diff["rows"][0]["object_name_zh"] == "灰燼之心"
    assert "-max_hp: 160\n+max_hp: 150\n" in diff["text"]
    checked = client.post("/api/tuning/drafts/current/check").json()
    assert checked["ok"] is True, checked
    bad = {"changes": [{"file": HEART, "path": "attributes.str", "old": 12, "new": "abc"}]}
    result = client.post("/api/tuning/drafts/current/check", json=bad).json()
    assert result["ok"] is False
    assert result["field_errors"] == [
        {"file": HEART, "path": "attributes.str", "message_zh": "要填整數（例：120）"}
    ]
    refused = client.put("/api/tuning/drafts/current", json=bad)
    assert refused.status_code == 422 and "要填整數" in refused.json()["detail"]
    assert client.put("/api/tuning/drafts/BAD!", json=body).status_code == 422
    assert client.delete("/api/tuning/drafts/current").status_code == 204
    assert client.delete("/api/tuning/drafts/current").status_code == 204
    assert client.get("/api/tuning/drafts/current").json()["changes"] == []


def test_apply_without_git_is_refused(client: TestClient) -> None:
    body = {"changes": [{"file": HEART, "path": "max_hp", "old": 160, "new": 150}]}
    client.put("/api/tuning/drafts/current", json=body)
    status = client.get("/api/tuning/status").json()
    assert status["can_write"] is False and "只能模擬" in status["reason_zh"]
    reply = client.post("/api/tuning/drafts/current/apply")
    assert reply.status_code == 409 and "只能模擬" in reply.json()["detail"]
    assert client.get("/api/tuning/history").json() == []


def test_apply_and_revert_through_the_api(
    client: TestClient, repo_service: TuningService, repo: Path
) -> None:
    client.app.state.tuning = repo_service  # type: ignore[attr-defined]
    original = (repo / "content" / HEART).read_bytes()
    body = {"changes": [{"file": HEART, "path": "max_hp", "old": 160, "new": 150}]}
    client.put("/api/tuning/drafts/current", json=body)
    applied = client.post("/api/tuning/drafts/current/apply")
    assert applied.status_code == 200, applied.text
    commit = applied.json()["commit"]
    assert "重開伺服器" in applied.json()["restart_note_zh"]
    status = client.get("/api/tuning/status").json()
    assert status["restart_needed"] is True and status["can_write"] is True
    assert client.get("/api/tuning/history").json()[0]["commit"] == commit
    reverted = client.post(f"/api/tuning/drafts/current/revert/{commit}").json()
    assert [(c["path"], c["old"], c["new"]) for c in reverted["changes"]] == [("max_hp", 150, 160)]
    assert client.post("/api/tuning/drafts/current/apply").status_code == 200
    assert (repo / "content" / HEART).read_bytes() == original
    assert client.post("/api/tuning/drafts/current/revert/zzz").status_code == 422


def _instant(root: str | None, job: ProbeJob) -> BossBattle:
    return BossBattle(job.boss or "", job.build, job.seed, True, 9, 3, 0, {"turn|1": 4})


def test_sim_endpoints(client: TestClient, tmp_path: Path) -> None:
    service = _tuning(client)
    service.sims = SimJobs(
        tmp_path / "sims",
        workers=2,
        task=_instant,
        executor_factory=lambda n: ThreadPoolExecutor(max_workers=n),
    )
    options = client.get("/api/tuning/sims/options").json()
    assert [b["key"] for b in options["bosses"]] == ["mist", "ashen", "rift"]
    assert len(options["builds"]) == 8 and options["default_seeds"] == 3
    assert options["max_battles"] == 160 and options["workers"] == 2
    started = client.post("/api/tuning/sims", json={"boss": "ashen", "seeds": 1})
    assert started.status_code == 200, started.text
    job_id = started.json()["job_id"]
    service.sims.wait(30)
    done = client.get(f"/api/tuning/sims/{job_id}").json()
    assert done["state"] == "done" and done["result"]["battles"] == 8
    assert client.get("/api/tuning/sims/nope").status_code == 404
    assert client.delete("/api/tuning/sims/nope").status_code == 404
    too_big = client.post("/api/tuning/sims", json={"boss": "ashen", "seeds": 40})
    assert too_big.status_code == 422 and "一次最多" in too_big.json()["detail"]
    assert client.post("/api/tuning/sims", json={"boss": "x"}).status_code == 422
    bad = {"changes": [{"file": HEART, "path": "max_hp", "old": 160, "new": 0}]}
    client.put("/api/tuning/drafts/current", json=bad)
    refused = client.post("/api/tuning/sims", json={"boss": "ashen", "seeds": 1})
    assert refused.status_code == 422 and "草稿有錯" in refused.json()["detail"]


def test_openapi_lists_tuning_routes_when_on(client: TestClient) -> None:
    paths = client.app.openapi()["paths"]  # type: ignore[attr-defined]
    for path in (
        "/api/tuning/status",
        "/api/tuning/objects",
        "/api/tuning/objects/{kind}/{object_id}",
        "/api/tuning/drafts/{name}",
        "/api/tuning/drafts/{name}/check",
        "/api/tuning/drafts/{name}/diff",
        "/api/tuning/drafts/{name}/revert/{commit}",
        "/api/tuning/drafts/{name}/apply",
        "/api/tuning/history",
        "/api/tuning/sims",
        "/api/tuning/sims/options",
        "/api/tuning/sims/{job_id}",
    ):
        assert path in paths, path
