"""``trpg serve`` 提供建置好的前端（Phase 3-3 5.4）：``/`` 為 index.html，``/api/*`` 不受影響。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.cli.serve import cmd_serve, find_client_dist
from trpg.content.library import ContentLibrary

INDEX = "<!doctype html><html><body><div id='root'></div></body></html>"


@pytest.fixture
def fake_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return dist


def test_root_serves_index_and_api_still_works(library: ContentLibrary, fake_dist: Path) -> None:
    with TestClient(create_app(library, static_dir=fake_dist)) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.headers["content-type"].startswith("text/html")
        assert "id='root'" in root.text
        assert client.get("/assets/app.js").status_code == 200
        maps = client.get("/api/maps")
        assert maps.status_code == 200
        assert len(maps.json()) == 10
        assert client.get("/api/battles/nope").status_code == 404


def test_without_static_dir_root_is_404(library: ContentLibrary) -> None:
    with TestClient(create_app(library)) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/maps").status_code == 200


def test_find_client_dist_needs_an_index(tmp_path: Path, fake_dist: Path) -> None:
    assert find_client_dist(fake_dist) == fake_dist
    assert find_client_dist(tmp_path / "missing") is None
    (tmp_path / "empty").mkdir()
    assert find_client_dist(tmp_path / "empty") is None


def _fake_run(seen: dict[str, Any]) -> Any:
    def run(app: object, **kwargs: Any) -> None:
        seen["app"] = app

    return run


def test_serve_mounts_the_client_when_built(
    monkeypatch: pytest.MonkeyPatch, fake_dist: Path
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(uvicorn, "run", _fake_run(seen))
    out = io.StringIO()
    assert cmd_serve("127.0.0.1", 8000, out, client_dist=fake_dist) == 0
    app = seen["app"]
    assert isinstance(app, FastAPI)
    assert "網頁：http://127.0.0.1:8000/" in out.getvalue()
    with TestClient(app) as client:
        assert "id='root'" in client.get("/").text


def test_serve_without_a_build_prints_a_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(uvicorn, "run", _fake_run(seen))
    out = io.StringIO()
    assert cmd_serve("127.0.0.1", 8000, out, client_dist=tmp_path / "none") == 0
    assert "corepack pnpm -C client build" in out.getvalue()
    with TestClient(seen["app"]) as client:
        assert client.get("/").status_code == 404
