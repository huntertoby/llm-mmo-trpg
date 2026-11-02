"""機遇給的三選一沿用待選三選一的顯示（Phase 5B-4c；Phase5計畫 21.4、21.9）。"""

from __future__ import annotations

from tests.world.helpers import hero, make_world
from trpg.api.world_story_view import pending_offer_view
from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import make_offer
from trpg.world.growth import as_run, world_library
from trpg.world.state import PendingOffer
from trpg.world.step import new_character


def test_opportunity_offer_named_after_skeleton(library: ContentLibrary) -> None:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    offer = make_offer(world_library(library), as_run(char, seed=1), "level_up")
    pending = PendingOffer(
        quest="storm_altar", step="opportunity", offer=offer, source="opportunity"
    )
    char = char.model_copy(update={"pending_offers": (pending,)})
    view = pending_offer_view(library, make_world(), char)
    assert view is not None
    assert view.quest_name_zh == "雷雨中的古松祭壇"
    assert view.step_zh == "機遇"
    assert len(view.offer.candidates) == 3
