"""遭遇預覽列出三方混戰的第三方（Phase 5B-M3；``docs/phases/Phase5計畫.md`` 20.6 第 5 項）。"""

from __future__ import annotations

from tests.world.helpers import hero, make_encounter
from trpg.api.world_presenter import _encounter_view
from trpg.content.library import ContentLibrary
from trpg.world.encounters import roll_lineup
from trpg.world.step import new_character


def test_encounter_view_lists_third_after_enemies(library: ContentLibrary) -> None:
    encounter = make_encounter("crystal_rift", seed=2, level=5)
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"location": "crystal_rift", "pending_encounter": encounter})
    view = _encounter_view(library, char, in_battle=False)
    assert view is not None
    lineup = roll_lineup(library, encounter)
    assert len(view.enemies) == len(lineup.members) + 2
    assert [e.third for e in view.enemies[-2:]] == [True, True]
    assert not any(e.third for e in view.enemies[:-2])
    assert [e.name_zh for e in view.enemies[-2:]] == [
        library.unit("sect_swordsman").name_zh,
        library.unit("sect_acolyte").name_zh,
    ]
    assert not any(e.elite for e in view.enemies[-2:])
