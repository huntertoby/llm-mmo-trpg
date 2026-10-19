"""``tests/api`` 共用的 fixture：內容庫與 FastAPI ``TestClient``（不需網路）。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.sessions import SessionStore
from trpg.content.library import ContentLibrary, load_library


@pytest.fixture(scope="session")
def library() -> ContentLibrary:
    return load_library()


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
