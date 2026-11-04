"""``tests/api`` 共用的 fixture：內容庫與 FastAPI ``TestClient``（不需網路）。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import with_test_fields
from trpg.api.app import create_app
from trpg.api.sessions import SessionStore
from trpg.api.world import START_REGION, spawn_region
from trpg.content.library import ContentLibrary, load_library


@pytest.fixture(scope="session", autouse=True)
def _old_spawn() -> Iterator[None]:
    """6F-2（#125）起新角色出生在主城；6F-2 以前寫的世界 API 測試都假設建角後站在雲嶺小鎮，照舊
    讓它們在 :data:`~trpg.api.world.START_REGION` 出生（比照 ``library`` 拿掉實地地圖的做法；
    session 範圍，模組範圍的 fixture 建的角色也算）。測開局本身的測試標
    ``@pytest.mark.capital_spawn``（:func:`_capital_spawn` 換回正式的 ``spawn_region``）。

    注意（6F-2b）：這是 **測試捷徑**；正式開局照 #125 在主城出生，不要把這裡的雲嶺出生當成規則。"""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("trpg.api.world.spawn_region", lambda _library: START_REGION)
        yield


@pytest.fixture(autouse=True)
def _capital_spawn(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("capital_spawn") is not None:
        monkeypatch.setattr("trpg.api.world.spawn_region", spawn_region)


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
