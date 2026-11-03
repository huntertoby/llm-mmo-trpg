"""``tests/world`` 共用的 fixture。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import hero, with_rules
from trpg.content.library import ContentLibrary, load_library
from trpg.world.state import CharacterState
from trpg.world.step import new_character


@pytest.fixture(scope="session")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="session")
def calm(library: ContentLibrary) -> ContentLibrary:
    """不會遇敵的內容庫。"""
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


@pytest.fixture(scope="session")
def ambush(library: ContentLibrary) -> ContentLibrary:
    """每一步都遇敵（城鎮與傳送點除外）的內容庫。"""
    return with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})


@pytest.fixture
def make_char(library: ContentLibrary) -> Callable[..., CharacterState]:
    def factory(
        character_id: str = "alice", *, wis: int | None = None, **updates: Any
    ) -> CharacterState:
        char = new_character(library, character_id, hero(library, wis=wis), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    return factory
