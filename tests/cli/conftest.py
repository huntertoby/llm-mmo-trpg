"""CLI 測試共用的內容庫快取（PERF-4）：每個指令各載一次內容庫太慢，行程內共用一份。

只有「用預設內容」時走快取；帶 ``content_dir`` 或設了 ``TRPG_CONTENT_DIR`` 的一律走原函式
（這些測試就是要讀自己的內容或測錯誤訊息）。不改正式 CLI。
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import pytest

from trpg.api.primitive_coverage import load_checked_library
from trpg.cli import main as cli_main
from trpg.content.library import ContentLibrary
from trpg.content.loader import CONTENT_DIR_ENV

_original = load_checked_library


@cache
def _shared_library() -> ContentLibrary:
    return _original()


def cached_load_checked_library(content_dir: Path | None = None) -> ContentLibrary:
    if content_dir is None and CONTENT_DIR_ENV not in os.environ:
        return _shared_library()
    return _original(content_dir)


@pytest.fixture(autouse=True)
def _share_cli_library(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "load_checked_library", cached_load_checked_library)
