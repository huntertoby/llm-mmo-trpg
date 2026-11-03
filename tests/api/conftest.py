"""``tests/api`` 共用的 fixture：內容庫與 FastAPI ``TestClient``（不需網路）。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import with_test_fields
from trpg.api.app import create_app
from trpg.api.sessions import SessionStore
from trpg.content.library import ContentLibrary, load_library


@pytest.fixture(scope="session")
def library() -> ContentLibrary:
    """沒有實地地圖的內容庫（Phase 6B-2：有實地地圖的地點不能 ``travel``；5A～5F 的世界 API 測試
    照舊點地點移動）。實地地圖的測試用 ``field_library``。"""
    return replace(load_library(), field_maps={})


@pytest.fixture(scope="session")
def field_library() -> ContentLibrary:
    """完整的內容庫（含實地地圖；6B-2 起）。霧渡鎮、渡口石階與室內圖換成測試專用的凍結複本
    （6C-R2，:func:`tests.world.helpers.with_test_fields`）。"""
    return with_test_fields(load_library())


@pytest.fixture
def client(library: ContentLibrary) -> Iterator[TestClient]:
    with TestClient(create_app(library)) as c:
        yield c


def store_of(client: TestClient) -> SessionStore:
    store = client.app.state.store  # type: ignore[attr-defined]
    assert isinstance(store, SessionStore)
    return store


def with_prompt_reactions(library: ContentLibrary) -> ContentLibrary:
    """測試用：每個 build 英雄的反應規則改為 ``prompt``（目前的內容沒有 ``prompt`` 反應，網頁上
    不會出現詢問；測試反應詢問的 API 流程時用這份內容庫）。"""
    rules = tuple(
        r.model_copy(update={"mode": "prompt"}) for r in library.ruleset.reactions.default_rules
    )
    builds = tuple(
        b.model_copy(update={"hero": b.hero.model_copy(update={"reactions": rules})})
        for b in library.builds.builds
    )
    return replace(library, builds=library.builds.model_copy(update={"builds": builds}))


@pytest.fixture(scope="session")
def prompt_library(library: ContentLibrary) -> ContentLibrary:
    return with_prompt_reactions(library)


@pytest.fixture
def prompt_client(prompt_library: ContentLibrary) -> Iterator[TestClient]:
    with TestClient(create_app(prompt_library)) as c:
        yield c
