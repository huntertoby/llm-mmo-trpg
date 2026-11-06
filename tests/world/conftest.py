"""``tests/world`` 共用的 fixture。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import hero, without_fields
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState
from trpg.world.step import new_character


@pytest.fixture(scope="session")
def library(content_library: ContentLibrary) -> ContentLibrary:
    """5A～5F 的測試用：沒有實地地圖（照舊點地點移動；見 :func:`without_fields`）。
    ``field_library``、``calm``、``ambush`` 在根目錄的 ``tests/conftest.py``。"""
    return without_fields(content_library)


@pytest.fixture
def make_char(library: ContentLibrary) -> Callable[..., CharacterState]:
    def factory(
        character_id: str = "alice", *, wis: int | None = None, **updates: Any
    ) -> CharacterState:
        char = new_character(library, character_id, hero(library, wis=wis), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    return factory
