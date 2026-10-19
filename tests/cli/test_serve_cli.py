"""``trpg serve``（Phase 3-2 4.1）：以 uvicorn 啟動，預設只綁 127.0.0.1（不實際開埠）。"""

from __future__ import annotations

from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI

from trpg.cli.main import main


def _capture(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake_run(app: object, **kwargs: Any) -> None:
        seen["app"] = app
        seen.update(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_run)
    return seen


def test_serve_defaults_to_localhost_8000(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture(monkeypatch)
    assert main(["serve"]) == 0
    assert isinstance(seen["app"], FastAPI)
    assert (seen["host"], seen["port"]) == ("127.0.0.1", 8000)


def test_serve_accepts_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture(monkeypatch)
    assert main(["serve", "--host", "127.0.0.2", "--port", "8123"]) == 0
    assert (seen["host"], seen["port"]) == ("127.0.0.2", 8123)


def test_serve_rejects_a_bad_port(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture(monkeypatch)
    assert main(["serve", "--port", "0"]) == 2
