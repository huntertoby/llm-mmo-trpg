"""本機模型的健康檢查（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.4）。"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.account_config import AccountSettings
from trpg.api.app import create_app
from trpg.api.llm_health import LlmHealth
from trpg.api.llm_source import MockLlmProvider
from trpg.api.server_config import ServerSettings
from trpg.api.world_flow import WorldLlm
from trpg.content.library import ContentLibrary


def test_unavailable_model_turns_story_off_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    provider = MockLlmProvider(generate=True)
    health = LlmHealth(provider, interval_s=0, clock=lambda: 100)
    llm = WorldLlm(provider, health)
    assert llm.client() is not None  # 還沒檢查：照開關
    provider.reachable = False
    with caplog.at_level(logging.INFO, logger="trpg.llm_health"):
        assert health.check() is False
    assert "不可用" in caplog.text
    assert llm.client() is None  # 全部走模板
    view = llm.view()
    assert view.enabled is True and view.model_available is False
    assert view.notice_zh is not None and "模板" in view.notice_zh
    provider.reachable = True
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="trpg.llm_health"):
        health.check()
    assert "恢復" in caplog.text
    assert llm.client() is not None and llm.view().model_available is True
    assert health.checked_at == 100


def test_only_pings_while_switch_on() -> None:
    provider = MockLlmProvider(generate=False)
    health = LlmHealth(provider, interval_s=0)
    llm = WorldLlm(provider, health)
    health.active = lambda: llm.enabled
    health.start()
    assert provider.probes == 0 and health.available is None
    llm.set(True)  # 打開時的探測也更新健康狀態
    assert provider.probes == 1 and health.available is True
    health.tick()
    assert provider.probes == 2


def test_app_pings_at_startup(library: ContentLibrary, tmp_path: Path) -> None:
    provider = MockLlmProvider(generate=True, reachable=False)
    app = create_app(
        library,
        save_dir=tmp_path,
        llm=provider,
        accounts=AccountSettings(dev_mode=True),
        server=ServerSettings(llm_health_interval_s=0),
    )
    with TestClient(app) as client:
        assert provider.probes == 1
        view = client.get("/api/world/llm").json()
    assert view["model_available"] is False and view["enabled"] is True
    assert "模板" in view["notice_zh"]
