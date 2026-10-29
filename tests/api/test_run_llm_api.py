"""網頁版 LLM 開關（Phase 4-L6b）：``POST /api/runs`` 的 ``llm``、連不到模型時的提示、統計。

全部用 ``MockLLMClient`` 或假的連線失敗（``httpx.MockTransport``）；不連任何真實位址。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.roguelite.helpers import full_library
from trpg.api.app import create_app
from trpg.api.llm_source import LLM_OFF_NOTICE, LocalLlmProvider, MockLlmProvider
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.llm.candidate_source import mock_proposer
from trpg.roguelite.state import CampfireNode
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.proposal_topic import LlmAttempt, LlmProposer

START: dict[str, Any] = {"weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


class _Provider(MockLlmProvider):
    """計算提議器被呼叫幾次。"""

    def __init__(self, *, reachable: bool = True) -> None:
        super().__init__(reachable=reachable)
        self.calls = 0

    def proposer(self, library: ContentLibrary) -> LlmProposer:
        inner = mock_proposer(library, naming=True)

        def counted(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
            self.calls += 1
            return inner(request, ctx, seed)

        return counted


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    # LLM 來源只在完整技能三選一（whiteboard: false）使用；預設的白板三選一不請 LLM（3W-4）
    return full_library()


def _client(library: ContentLibrary, tmp_path: Path, provider: Any) -> TestClient:
    return TestClient(create_app(library, save_dir=tmp_path / "saves", llm=provider))


@pytest.fixture
def provider() -> _Provider:
    return _Provider()


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path, provider: _Provider) -> Iterator[TestClient]:
    with _client(library, tmp_path, provider) as c:
        yield c


def _create(client: TestClient, **over: Any) -> dict[str, Any]:
    reply = client.post("/api/runs", json={**START, **over})
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _to_campfire(client: TestClient, run_id: str) -> None:
    """把一輪直接放到第 3 場後、還沒出過完整技能三選一的營火（不打戰鬥）：離開營火時會產生完整技能
    三選一（3W-5；取代舊的營火重骰），走候選產生器。"""
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    session = runs.get(run_id)
    node = CampfireNode(after_battle=3)
    session.run = session.run.model_copy(
        update={"node": node, "battles_done": 3, "campfires_done": (3,)}
    )


LEAVE = {"kind": "leave"}


def test_switch_off_by_default_does_not_probe_or_report(
    client: TestClient, provider: _Provider
) -> None:
    run = _create(client)
    assert run["llm"] is False and run["llm_notice"] is None and run["llm_stats"] is None
    assert provider.probes == 0 and provider.calls == 0
    _to_campfire(client, run["run_id"])
    reply = client.post(f"/api/runs/{run['run_id']}/choice", json=LEAVE)
    assert reply.status_code == 200 and provider.calls == 0
    offer = reply.json()["node"]["offer"]
    assert all(t["source"] != "llm" for t in offer["tags"])
    assert reply.json()["llm_stats"] is None


def test_switch_on_with_model_sets_the_run_flag_without_notice(
    client: TestClient, provider: _Provider
) -> None:
    run = _create(client, llm=True)
    assert run["llm"] is True and run["llm_notice"] is None and provider.probes == 1
    again = client.get(f"/api/runs/{run['run_id']}").json()
    assert again["llm"] is True and again["llm_notice"] is None
    assert again["llm_stats"]["total"] == 0 and again["llm_stats"]["alert"] is False


def test_switch_on_generates_candidates_through_the_provider(
    client: TestClient, provider: _Provider
) -> None:
    run = _create(client, llm=True)
    _to_campfire(client, run["run_id"])
    reply = client.post(f"/api/runs/{run['run_id']}/choice", json=LEAVE)
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert len(body["node"]["offer"]["candidates"]) == 3
    stats = body["llm_stats"]
    assert provider.calls >= 1 and stats["total"] == provider.calls
    assert stats["succeeded"] + stats["failed"] == stats["total"]
    assert stats["fallback_permille"] == stats["failed"] * 1000 // stats["total"]
    assert stats["alert"] is (stats["fallback_permille"] > stats["alert_permille"])
    assert stats["named"] == stats["name_generated"] + stats["name_fallback"]


def test_unreachable_model_does_not_fail_and_notifies_once(
    library: ContentLibrary, tmp_path: Path
) -> None:
    provider = _Provider(reachable=False)
    with _client(library, tmp_path, provider) as client:
        run = _create(client, llm=True)
        assert run["llm"] is False and run["llm_notice"] == LLM_OFF_NOTICE
        assert run["battle_id"] is None and run["node"]["kind"] == "battle"
        again = client.get(f"/api/runs/{run['run_id']}").json()
        assert again["llm"] is False and again["llm_notice"] is None
        _to_campfire(client, run["run_id"])
        client.post(f"/api/runs/{run['run_id']}/choice", json=LEAVE)
        assert provider.calls == 0  # 當作關閉：不呼叫提議器


def test_no_provider_configured_also_degrades(library: ContentLibrary, tmp_path: Path) -> None:
    app = create_app(library, save_dir=tmp_path / "saves")
    app.state.runs.llm = None
    with TestClient(app) as client:
        run = _create(client, llm=True)
    assert run["llm"] is False and run["llm_notice"] == LLM_OFF_NOTICE


def test_local_provider_with_failing_connection_degrades(
    library: ContentLibrary, tmp_path: Path
) -> None:
    """真的 ``LocalLlmProvider`` 配假的連線失敗（不連 8001）：開局照常，提示一次。"""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = LocalLlmProvider(transport=httpx.MockTransport(refuse))
    with _client(library, tmp_path, provider) as client:
        run = _create(client, llm=True)
    assert run["llm"] is False and run["llm_notice"] == LLM_OFF_NOTICE


def test_saved_llm_run_reloads_with_the_flag_and_a_proposer(
    client: TestClient, provider: _Provider
) -> None:
    run = _create(client, llm=True)
    run_id = run["run_id"]
    assert client.post(f"/api/runs/{run_id}/save").status_code == 200
    loaded = client.post("/api/runs/load", json={"run_id": run_id}).json()
    assert loaded["llm"] is True and loaded["llm_notice"] is None
    _to_campfire(client, run_id)
    client.post(f"/api/runs/{run_id}/choice", json=LEAVE)
    assert provider.calls >= 1


def _provider(
    tmp_path: Path, handler: Any, *, base_url: str = "http://127.0.0.1:9/v1"
) -> LocalLlmProvider:
    config = tmp_path / "llm.toml"
    config.write_text(f'base_url = "{base_url}"\n', encoding="utf-8")
    return LocalLlmProvider(config_path=config, transport=httpx.MockTransport(handler))


def test_probe_ok_when_the_models_endpoint_answers(tmp_path: Path) -> None:
    seen: list[str] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": []})

    assert _provider(tmp_path, ok).probe() is None
    assert seen == ["http://127.0.0.1:9/v1/models"]


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(503),
        lambda request: (_ for _ in ()).throw(httpx.ConnectTimeout("slow", request=request)),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("no", request=request)),
    ],
)
def test_probe_reports_unreachable_for_errors_and_timeouts(tmp_path: Path, handler: Any) -> None:
    assert _provider(tmp_path, handler).probe() == LLM_OFF_NOTICE


def test_probe_with_a_broken_config_degrades(tmp_path: Path) -> None:
    bad = tmp_path / "llm.toml"
    bad.write_text("timeout_s = -1\n", encoding="utf-8")
    assert LocalLlmProvider(config_path=bad).probe() == LLM_OFF_NOTICE
