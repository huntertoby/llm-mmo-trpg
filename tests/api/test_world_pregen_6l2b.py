"""6L-2b：預先生成的時機與數量（玩法 PM 照 #132）。全部用 Mock 與假時鐘，不需網路。

- 機遇的完整技能三選一每份最多 1 張請 LLM，其餘用組合器（roguelite 照舊）。
- 劇情技能（破霧）接到主線第 1 步就開始預先生成；完成那一步的動作最多靜默等 2 秒。
- 閃現在戰鬥結束、那招可以閃了就開始預先生成（不必先回城鎮），鍵和回城後出題相同。
"""

from __future__ import annotations

import threading

from tests.api.test_offer_prefetch import OPPORTUNITY, _at_altar
from tests.api.test_world_pregen import FakeClock, Recorder
from tests.world.helpers import NOON, hero, make_world
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world_pregen import (
    OPPORTUNITY_LLM_CARDS,
    STORY_WAIT_SECONDS,
    WAIT_SECONDS,
    WorldPregen,
    flash_wait_request,
    opportunity_wait_request,
    predicted_requests,
    provider_generators,
)
from trpg.content.library import ContentLibrary
from trpg.roguelite.llm_hook import use_proposer
from trpg.roguelite.offers import make_offer
from trpg.roguelite.state import FlashChoice
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.proposal_topic import LlmAttempt, LlmProposer
from trpg.skillgen.random_composer import compose_random_skill
from trpg.world.generated import StoryGenRequest
from trpg.world.growth import world_library
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import new_character

MAIN = "main_mist_rift"
"""雲嶺主線第 1 章：第 2 步（``enter_temple``）給劇情技能「破霧」。"""


# ---------------------------------------------------------------------------
# 1. 機遇：每份最多 1 張請 LLM
# ---------------------------------------------------------------------------


def _counting_proposer(library: ContentLibrary, calls: list[int]) -> LlmProposer:
    """假提議器：記下呼叫，用組合器做一個帶題目關鍵字的技能（當作合格的提議）。"""

    def propose(request: ProposalRequest, _ctx: object, seed: int) -> LlmAttempt:
        calls.append(seed)
        skill = compose_random_skill(
            seed, tier=request.tier, library=library, keyword=request.keywords[0]
        )
        return LlmAttempt(skill, 1)

    return propose  # type: ignore[return-value]


class _CountingProvider(MockLlmProvider):
    def __init__(self, calls: list[int]) -> None:
        super().__init__()
        self.calls = calls

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        return _counting_proposer(library, self.calls)


def test_opportunity_asks_llm_for_at_most_one_card(library: ContentLibrary) -> None:
    world, char = make_world(), _at_altar(library)
    request = opportunity_wait_request(library, world, char, OPPORTUNITY)
    assert request is not None
    view = world_library(library)
    calls: list[int] = []
    gens = provider_generators(_CountingProvider(calls))
    assert gens.offer is not None
    made = gens.offer(view, request)
    assert OPPORTUNITY_LLM_CARDS == 1
    assert len(calls) == 1  # 這個種子擲到請 LLM；上限 1 張
    assert made.source == "llm" and made.offer is not None
    assert sum(t.source == "llm" for t in made.offer.tags) == 1
    assert len(made.offer.candidates) == 3  # 其餘照常用組合器與技能池補滿

    # roguelite 照舊：同樣的題目不設上限時每種候選各請一次
    plain: list[int] = []
    with use_proposer(_counting_proposer(view, plain)):
        make_offer(
            view,
            request.run.model_copy(update={"llm": True}),
            "complete",
            region_keywords=request.region_keywords,
            tier_bonus=request.tier_bonus,
            pinned_keyword=request.pinned_keyword,
            region=request.region,
        )
    assert len(plain) > 1


# ---------------------------------------------------------------------------
# 2. 劇情技能：接主線第 1 步就開始；完成時最多等 2 秒
# ---------------------------------------------------------------------------


def _on_main(library: ContentLibrary, steps_done: int) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    quest = QuestState(quest=MAIN, steps_done=steps_done, started_at=NOON)
    return char.model_copy(update={"quests": (quest,)})


def test_story_skill_predicted_from_first_step(library: ContentLibrary) -> None:
    for steps_done in (0, 1):
        requests = predicted_requests(library, make_world(), _on_main(library, steps_done))
        stories = [r for r in requests if isinstance(r, StoryGenRequest)]
        assert stories, steps_done
        assert {r.skill.id for r in stories} == {"skill_mist_breaker"}
    # 已經過了那一步：不再預測
    assert not [
        r
        for r in predicted_requests(library, make_world(), _on_main(library, 2))
        if isinstance(r, StoryGenRequest)
    ]


def test_story_wait_is_two_seconds(library: ContentLibrary) -> None:
    """完成那一步的動作沒有等待提示：沒趕上最多靜默等 2 秒（假時鐘），之後給內容版（``None``）。"""
    assert STORY_WAIT_SECONDS == 2.0 < WAIT_SECONDS
    gate = threading.Event()
    rec = Recorder(gate)
    clock = FakeClock(step=0.25)
    pregen = WorldPregen(rec.generators(), enabled=lambda: True, clock=clock, poll_seconds=0.001)
    world, char = make_world(), _on_main(library, 1)
    try:
        story = next(
            r for r in predicted_requests(library, world, char) if isinstance(r, StoryGenRequest)
        )
        start = clock.now
        assert pregen.supplier(library)(story) is None
        waited = clock.now - start
        assert STORY_WAIT_SECONDS <= waited < STORY_WAIT_SECONDS + 1
    finally:
        gate.set()
        pregen.shutdown()


# ---------------------------------------------------------------------------
# 4. 閃現：戰後就開始（走回城鎮的路上也在生成）
# ---------------------------------------------------------------------------


def _after_ferry_fight(library: ContentLibrary) -> CharacterState:
    """新手第 1 步（渡口石階）打贏後：還在野外、技能用過、拿到 1 點靈感。"""
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in char.hero.skills}
    return char.model_copy(update={"flash": flash, "insight": 1, "location": "ferry_steps"})


def test_flash_pregen_starts_after_battle_in_the_field(library: ContentLibrary) -> None:
    world, field = make_world(), _after_ferry_fight(library)
    skill = field.hero.skills[0]
    assert flash_wait_request(library, world, field, FlashChoice(skill=skill)) is None  # 還不能閃
    flashes = [r for r in predicted_requests(library, world, field) if r.kind == "flash"]
    assert flashes  # 但已經開始預先生成
    town = field.model_copy(update={"location": "mist_ferry"})
    at_town = flash_wait_request(library, world, town, FlashChoice(skill=skill))
    assert at_town is not None and at_town.key == flashes[0].key  # 回城後出題用同一把鍵

    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        pregen.prefetch(library, world, field)
        pregen.drain(timeout=60)
        assert at_town.key in rec.calls
        pregen.prefetch(library, world, town)  # 走回城鎮：預測相同，不重做
        assert pregen.supplier(library)(at_town) is not None
        assert rec.calls.count(at_town.key) == 1
    finally:
        pregen.shutdown()


def test_no_flash_pregen_without_insight_or_during_encounter(library: ContentLibrary) -> None:
    world, field = make_world(), _after_ferry_fight(library)
    broke = field.model_copy(update={"insight": 0})
    assert not [r for r in predicted_requests(library, world, broke) if r.kind == "flash"]
    unused = field.model_copy(update={"flash": {}})
    assert not [r for r in predicted_requests(library, world, unused) if r.kind == "flash"]
