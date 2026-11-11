"""PERF-3：大世界三選一的背景預先計算（``trpg.api.offer_prefetch``）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.world.helpers import NOON, hero, make_world
from trpg.api.offer_prefetch import OfferPrefetcher, predicted_offers
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.roguelite import offers
from trpg.roguelite.offers import using_offer_cache
from trpg.roguelite.state import SkillOffer
from trpg.world.actions import EventSolveAction
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState, EventTrigger, OpeningState, QuestState
from trpg.world.step import new_character, world_step

OPPORTUNITY = 0  # storm_altar 的第 0 個解法＝機遇（要帶「帶電」的技能）


def _at_altar(library: ContentLibrary, character_id: str = "alice") -> CharacterState:
    char = new_character(library, character_id, hero(library), region="cloud_ridge")
    skills = ("skill_chain_lightning", *char.hero.skills[1:])
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
        update={
            "hero": char.hero.model_copy(update={"skills": skills}),
            "location": "old_pine_altar",
            "pending_event": trigger,
        }
    )


def _boom(*_args: object, **_kwargs: object) -> SkillOffer:
    raise AssertionError("應該從背景算好的快取拿")


def test_opportunity_prefetched_matches_sync(
    library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    """機遇一出現就在背景算好；選機遇時直接拿，結果和同步計算逐字相同。"""
    world, char = make_world(), _at_altar(library)
    action = EventSolveAction(solution=OPPORTUNITY)
    plain = world_step(library, world, char, action, NOON)
    prefetcher = OfferPrefetcher(library)
    try:
        submitted = prefetcher.prefetch(world, char)
        assert len(submitted) == 1
        # 5B-4d：機遇的預測帶指定關鍵字（快取鍵含它，所以要和 solutions._opportunity 一致）
        assert [j.pinned_keyword for j in predicted_offers(library, world, char)] == ["charged"]
        prefetcher.wait(timeout=600)
        assert prefetcher.prefetch(world, char) == []  # 已經算好的不再丟
        monkeypatch.setattr(offers, "_compute_offer", _boom)
        with using_offer_cache(prefetcher.cache):
            cached = world_step(library, world, char, action, NOON)
    finally:
        prefetcher.shutdown()
    assert cached.char.model_dump_json() == plain.char.model_dump_json()
    assert cached.events == plain.events


def test_nothing_to_prefetch_without_opportunity(library: ContentLibrary) -> None:
    char = new_character(library, "bob", hero(library), region="cloud_ridge")
    assert predicted_offers(library, make_world(), char) == []
    taken = _at_altar(library).model_copy(update={"opportunities": ("storm_altar",)})
    assert predicted_offers(library, make_world(), taken) == []


def test_quest_step_offer_predicted(library: ContentLibrary) -> None:
    """進行中任務的下一步給三選一：預測同樣的參數（白板的組成、至少幾張被動）。"""
    char = new_character(library, "carol", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"quests": (QuestState(quest="starter_ferry", started_at=NOON),)})
    jobs = predicted_offers(library, make_world(), char)
    assert jobs
    # 6F-4（#130）：第 1 步＝加深、橋接、新方向各 1
    assert {(j.reason, j.mix, j.min_passive) for j in jobs} == {("level_up", (1, 1, 1), 1)}


def test_deferred_starter_offer_not_predicted(library: ContentLibrary) -> None:
    """OB-2（#150）：入門期的新手三選一延到正式選定才出題，不預先算；正式選定後照舊。"""
    char = new_character(library, "carol", hero(library), region="cloud_ridge")
    quests = (QuestState(quest="starter_ferry", started_at=NOON),)
    starter = OpeningState(seed=7, stage="starter", weapon_class="melee")
    waiting = char.model_copy(update={"quests": quests, "opening": starter})
    assert predicted_offers(library, make_world(), waiting) == []
    chosen = starter.model_copy(update={"stage": "chosen"})
    after = char.model_copy(update={"quests": quests, "opening": chosen})
    assert predicted_offers(library, make_world(), after)


def test_store_prefetches_and_serves(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WorldStore：角色讀進來時就預先算；之後的機遇動作從快取拿。"""
    store = WorldStore(library, SessionStore(library), tmp_path, clock=lambda: NOON)
    char = _at_altar(library, "c1")
    chars = tmp_path / "chars"
    chars.mkdir(parents=True, exist_ok=True)
    (chars / "c1.json").write_text(dumps_char(char), encoding="utf-8", newline="\n")
    plain = world_step(library, store.world(), char, EventSolveAction(solution=OPPORTUNITY), NOON)
    try:
        store.character("c1")
        store.offers.wait(timeout=600)
        monkeypatch.setattr(offers, "_compute_offer", _boom)
        outcome = store.act("c1", EventSolveAction(solution=OPPORTUNITY))
    finally:
        store.offers.shutdown()
    assert outcome.char.pending_offers == plain.char.pending_offers


def test_disabled_prefetcher_does_nothing(library: ContentLibrary) -> None:
    prefetcher = OfferPrefetcher(library, enabled=False)
    assert prefetcher.prefetch(make_world(), _at_altar(library)) == []
