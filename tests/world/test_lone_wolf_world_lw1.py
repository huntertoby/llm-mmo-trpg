"""LW-1 獨狼（#156，06 6.37）走大世界真實路徑。

獨行成立；帶傭兵、帶影子不成立（影子本身也不成立）。
"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_encounter
from trpg.content.library import ContentLibrary
from trpg.engine import start_battle
from trpg.shared.types import Team
from trpg.world.battle import prepare_battle
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]


def _allies(library: ContentLibrary, char: CharacterState) -> dict[str, bool]:
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    ready = char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    prepared = prepare_battle(library, ready)
    state = start_battle(prepared.setup, prepared.seed)
    return {u.template_id: u.lone_wolf for u in state.units_sorted() if u.team is Team.ALLY}


def test_going_alone_is_lone_wolf(library: ContentLibrary, make_char: MakeChar) -> None:
    bob = make_char("bob").model_copy(update={"mercenaries": (), "shadows": (), "companions": ()})
    assert _allies(library, bob) == {bob.hero.id: True}


def test_mercenaries_count_as_allies(library: ContentLibrary, make_char: MakeChar) -> None:
    bob = make_char("bob").model_copy(
        update={"mercenaries": ("merc_tiebi",), "shadows": (), "companions": ()}
    )
    allies = _allies(library, bob)
    assert len(allies) == 2 and not any(allies.values())


def test_a_borrowed_shadow_is_never_lone_and_counts_as_an_ally(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    snap = shadow_snapshot(make_char("alice"), NOON)
    bob = make_char("bob").model_copy(
        update={"mercenaries": (), "shadows": (snap,), "companions": ()}
    )
    allies = _allies(library, bob)
    assert allies == {bob.hero.id: False, "shadow_alice": False}
