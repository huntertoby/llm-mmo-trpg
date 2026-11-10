"""PERF-4 R1：CLI 測試的內容庫快取只在「預設內容」時生效。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.cli import conftest as cli_conftest
from trpg.cli import main as cli_main
from trpg.content.library import ContentLibrary
from trpg.content.loader import CONTENT_DIR_ENV


def _installed() -> Callable[..., ContentLibrary]:
    """CLI 實際會呼叫的函式（``vars``：``trpg.cli.main`` 沒有對外匯出這個名字）。"""
    loader: Callable[..., ContentLibrary] = vars(cli_main)["load_checked_library"]
    return loader


@pytest.fixture
def original_calls(monkeypatch: pytest.MonkeyPatch) -> list[Path | None]:
    """把原函式換成記錄呼叫的替身（先載好共用內容庫，替身才不會被快取呼叫到）。"""
    monkeypatch.delenv(CONTENT_DIR_ENV, raising=False)
    shared = _installed()()
    calls: list[Path | None] = []

    def spy(content_dir: Path | None = None) -> ContentLibrary:
        calls.append(content_dir)
        return shared

    monkeypatch.setattr(cli_conftest, "_original", spy)
    return calls


def test_default_content_uses_the_shared_library(original_calls: list[Path | None]) -> None:
    first = _installed()()
    assert _installed()() is first
    assert original_calls == []


def test_explicit_content_dir_calls_the_original(
    original_calls: list[Path | None], tmp_path: Path
) -> None:
    _installed()(tmp_path)
    assert original_calls == [tmp_path]


@pytest.mark.parametrize("value", ["some/content", ""], ids=["set", "empty"])
def test_content_dir_env_calls_the_original(
    original_calls: list[Path | None], monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(CONTENT_DIR_ENV, value)
    _installed()()
    assert original_calls == [None]
