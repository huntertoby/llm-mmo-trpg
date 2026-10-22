"""pytest 全域設定：標 slow 的測試放寬逾時（預設逾時見 pyproject 的 ``timeout``）。"""

from __future__ import annotations

import pytest

SLOW_TIMEOUT_SECONDS = 1800


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("slow") and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(SLOW_TIMEOUT_SECONDS))
