"""遭遇畫面帶出就地開打的戰場範圍與退回模板的原因（Phase 6C-2）。"""

from __future__ import annotations

import pytest

from tests.world.helpers import NOON, PARTY, make_world
from tests.world.test_field_enemies import (
    GUARD,
    _char,
    _library,
    _play,
    _seed_facing,
    _steps_map,
    _visit,
    _walk,
)
from trpg.api.world_presenter import world_view
from trpg.content.library import ContentLibrary, load_library
from trpg.world.state import CharacterState


@pytest.fixture(scope="module")
def guard_lib() -> ContentLibrary:
    return _library(load_library(), _steps_map([GUARD]))


def _touched(library: ContentLibrary) -> CharacterState:
    start = _char(library, (1, 6), field_visit=_visit(_seed_facing(GUARD, "e")), mercenaries=PARTY)
    _world, live, _ = _play(library, start, [_walk((2, 6), (3, 6), (4, 6), (5, 6))], make_world())
    return live


def test_encounter_view_frames_the_cut(guard_lib: ContentLibrary) -> None:
    live = _touched(guard_lib)
    view = world_view(guard_lib, make_world(), live, NOON + 1)
    assert view.encounter is not None
    rect = view.encounter.battlefield
    assert rect is not None
    assert (rect.field_map, rect.x, rect.y, rect.width, rect.height) == (
        "ferry_steps",
        0,
        0,
        12,
        12,
    )
    assert view.encounter.battlefield_fallback_zh is None


def test_encounter_view_explains_fallback(guard_lib: ContentLibrary) -> None:
    live = _touched(guard_lib)
    encounter = live.pending_encounter
    assert encounter is not None and encounter.contact is not None
    contact = encounter.contact.model_copy(update={"enemy_at": None})
    old = live.model_copy(
        update={"pending_encounter": encounter.model_copy(update={"contact": contact})}
    )
    view = world_view(guard_lib, make_world(), old, NOON + 1)
    assert view.encounter is not None
    assert view.encounter.battlefield is None
    assert view.encounter.battlefield_fallback_zh == "舊存檔的遭遇沒有敵人位置"
