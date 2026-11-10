"""pytest 全域設定：標 slow 的測試放寬逾時（預設逾時見 pyproject 的 ``timeout``），以及共用的內容庫
固件（CODE-2）。

內容庫的固件都是 session 範圍：``ContentLibrary`` 是 frozen dataclass，測試要改規則時一律用
``dataclasses.replace``／``model_copy`` 做新的一份，不修改共用的物件。"""

from __future__ import annotations

import os

import pytest

from tests.world.helpers import with_rules, with_test_fields, without_fields
from trpg.content.library import ContentLibrary
from trpg.skillgen.random_composer import default_library

os.environ["TRPG_LEGACY_CREATE"] = "1"
"""OB-1（#150）：舊流程建角（``weapon``＋``keywords``）正式模式會拒絕；大量測試用它快速建角，這裡
統一打開（:data:`trpg.api.routes.world.LEGACY_CREATE_ENV`）。測試拒絕路徑時用
``monkeypatch.delenv``。"""

SLOW_TIMEOUT_SECONDS = 1800


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("slow") and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(SLOW_TIMEOUT_SECONDS))


@pytest.fixture(scope="session")
def content_library() -> ContentLibrary:
    """正式的 ``content/`` 內容庫（行程內只載入一次，與正式碼的 ``default_library()`` 是同一份）。

    子目錄的 conftest 會覆寫 ``library``（例如 ``tests/api``、``tests/world`` 拿掉實地地圖）；要正式
    內容又在那些目錄裡的測試用這個名字。"""
    return default_library()


@pytest.fixture(scope="session")
def library(content_library: ContentLibrary) -> ContentLibrary:
    """預設的內容庫：正式內容（``tests/api``、``tests/world`` 覆寫成沒有實地地圖的版本）。"""
    return content_library


@pytest.fixture(scope="session")
def field_library(content_library: ContentLibrary) -> ContentLibrary:
    """完整的內容庫（含實地地圖；6B-2 起）。霧渡鎮、渡口石階與室內圖換成測試專用的凍結複本
    （6C-R2，:func:`tests.world.helpers.with_test_fields`）；正式內容的結構性質在
    ``tests/content/``。"""
    return with_test_fields(content_library)


@pytest.fixture(scope="session")
def calm(content_library: ContentLibrary) -> ContentLibrary:
    """不會遇敵、沒有實地地圖的內容庫（5A～5F 的世界規則測試用）。"""
    return with_rules(
        without_fields(content_library), encounter={"base_permille": 0, "per_level_permille": 0}
    )


@pytest.fixture(scope="session")
def ambush(content_library: ContentLibrary) -> ContentLibrary:
    """每一步都遇敵（城鎮與傳送點除外）、沒有實地地圖的內容庫。"""
    return with_rules(
        without_fields(content_library), encounter={"base_permille": 1000, "max_permille": 1000}
    )
