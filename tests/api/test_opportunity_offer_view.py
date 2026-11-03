"""機遇給的三選一沿用待選三選一的顯示（Phase 5B-4c；Phase5計畫 21.4、21.9）。"""

from __future__ import annotations

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_story_view import event_view, pending_offer_view
from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import make_offer
from trpg.world.growth import as_run, world_library
from trpg.world.state import CharacterState, EventTrigger, PendingOffer
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


def _at_altar(char: CharacterState, *skills: str) -> CharacterState:
    hero = char.hero.model_copy(update={"skills": (*skills, *char.hero.skills[len(skills) :])})
    trigger = EventTrigger(
        region="cloud_ridge",
        location="old_pine_altar",
        skeleton="storm_altar",
        candidates=("storm_altar",),
        weather="rain",
        day_phase="night",
        at=NOON,
    )
    return char.model_copy(
        update={"hero": hero, "location": "old_pine_altar", "pending_event": trigger}
    )


def _opportunity(library: ContentLibrary, char: CharacterState) -> dict[str, object]:
    view = event_view(library, make_world(), char, NOON, ())
    assert view is not None
    found = next(s for s in view.solutions if s.kind == "opportunity")
    return {"available": found.available, "why": found.unavailable_zh}


def test_event_card_opportunity_availability(library: ContentLibrary) -> None:
    """5B-4c：事件卡的機遇照條件開放（同 ``event_solve`` 的檢查）。"""
    base = new_character(library, "alice", hero(library), region="cloud_ridge")
    without = _opportunity(library, _at_altar(base))
    assert without == {"available": False, "why": "要裝備帶「帶電」的技能"}
    charged = _at_altar(base, "skill_chain_lightning")
    assert _opportunity(library, charged) == {"available": True, "why": None}
    taken = charged.model_copy(update={"opportunities": ("storm_altar",)})
    assert _opportunity(library, taken) == {"available": False, "why": "這個機遇已經拿過了"}


def test_guaranteed_opportunity_offer_uses_guarantee_who(library: ContentLibrary) -> None:
    """5D-2b（玩法 PM 2026-11-03 代決）：保底機遇的三選一標題用「焦痕未冷的古松」。"""
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    offer = make_offer(world_library(library), as_run(char, seed=1), "level_up")
    pending = PendingOffer(
        quest="storm_altar",
        step="opportunity",
        offer=offer,
        source="opportunity",
        guaranteed=True,
    )
    char = char.model_copy(update={"pending_offers": (pending,)})
    view = pending_offer_view(library, make_world(), char)
    assert view is not None and view.quest_name_zh == "焦痕未冷的古松"
