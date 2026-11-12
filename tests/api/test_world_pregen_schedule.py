"""主題合併（R2）。

原 ``test_world_pregen_6l2b.py``：

6L-2b：預先生成的時機與數量（玩法 PM 照 #132）。全部用 Mock 與假時鐘，不需網路。

- 機遇的完整技能三選一每份最多 1 張請 LLM，其餘用組合器（roguelite 照舊）。
- 劇情技能（破霧）接到主線第 1 步就開始預先生成；完成那一步的動作最多靜默等 2 秒。
- 閃現在戰鬥結束、那招可以閃了就開始預先生成（不必先回城鎮），鍵和回城後出題相同。

原 ``test_world_pregen_6l2c.py``：

6L-2c：閃現預先生成的鍵不含用法統計（玩法 PM 決定）。全部用 Mock 與假生成函式，不需網路。

- 每打完一場用法統計都會變；暫存區的鍵不含它，連打很多場也只生成一次。
- 同一招同一次出題最多一個生成中的請求；已經在生成或做好的不重開。
- 第一次閃現（#132）仍然在渡口戰後就開始生成。
- 按下時給出去的是預先生成的那一份（鍵改成按下那一刻的鍵），日誌記下它，重播只讀日誌。
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from tests.api.test_offer_prefetch import OPPORTUNITY, _at_altar
from tests.api.test_world_pregen import FakeClock, Recorder, _never_run, _store, _town_char
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
from trpg.skillgen.usage import SkillUsage
from trpg.world.actions import FlashAction
from trpg.world.generated import FlashGen, FlashGenRequest, StoryGenRequest, flash_pregen_key
from trpg.world.growth import world_library
from trpg.world.replay import replay
from trpg.world.state import CharacterState, QuestState, WorldState
from trpg.world.step import new_character

# --- 原 test_world_pregen_6l2b.py ---

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

    return propose


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


# --- 原 test_world_pregen_6l2c.py ---


def _fought(char: CharacterState, fights: int) -> CharacterState:
    """又打了 ``fights`` 場：每招的用法統計都多了（只改統計，其他不變）。"""
    usage = {
        s: SkillUsage(uses=2 * fights, targets=3 * fights, distance=fights, kills=fights)
        for s in char.hero.skills
    }
    return char.model_copy(update={"skill_usage": usage})


def _request(
    library: ContentLibrary, char: CharacterState, skill: str, world: WorldState | None = None
) -> FlashGenRequest:
    world = make_world() if world is None else world
    request = flash_wait_request(library, world, char, FlashChoice(skill=skill))
    assert request is not None
    return request


def test_five_fights_generate_once(library: ContentLibrary) -> None:
    """連打 5 場：按下時的請求鍵每場都換，但暫存區的鍵不變，每招只生成 1 次。"""
    world, town = make_world(), _town_char(library)
    skill = town.hero.skills[0]
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        keys = set()
        for fights in range(1, 6):
            char = _fought(town, fights)
            pregen.prefetch(library, world, char)
            pregen.drain(timeout=60)
            keys.add(_request(library, char, skill).key)
        assert len(keys) == 5  # 統計確實每場都變（舊的鍵會重做 5 次）
        assert len(rec.calls) == len(set(rec.calls))  # 每招只生成 1 次
        first = _request(library, _fought(town, 1), skill)
        assert rec.calls.count(first.key) == 1  # 統計只在開始生成時讀一次：用第 1 場後的那份
        last = _request(library, _fought(town, 5), skill)
        got = pregen.supplier(library)(last)
        assert isinstance(got, FlashGen) and got.key == last.key  # 鍵改成按下那一刻的
        assert got.record.tag == first.key  # 內容是第 1 場後開始生成的那一份
        assert rec.calls.count(first.key) == 1 and last.key not in rec.calls
    finally:
        pregen.shutdown()


def test_one_request_per_skill_while_generating(library: ContentLibrary) -> None:
    """生成中又打了一場：不重開；按下時等那一個做完、直接用它。"""
    gate = threading.Event()
    rec = Recorder(gate)
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    world, town = make_world(), _town_char(library)
    skill = town.hero.skills[0]
    try:
        pregen.prefetch(library, world, _fought(town, 1))
        queued = pregen.pending(town.character_id)
        assert queued >= 1
        for fights in range(2, 5):
            pregen.prefetch(library, world, _fought(town, fights))
            assert pregen.pending(town.character_id) == queued  # 同一招不會多一個請求
        later = _request(library, _fought(town, 4), skill)
        slot = flash_pregen_key(town.character_id, later.request)
        assert sum(1 for k in pregen._entries if k == (town.character_id, slot)) == 1
        gate.set()
        got = pregen.supplier(library)(later)
        assert isinstance(got, FlashGen) and got.key == later.key
        pregen.drain(timeout=60)
        assert rec.max_active == 1
        assert len(rec.calls) == queued == len(set(rec.calls))
    finally:
        gate.set()
        pregen.shutdown()


def test_first_flash_starts_after_ferry_fight(library: ContentLibrary) -> None:
    """#132：渡口戰後（還在野外）就開始生成；再打一場、回城按下，用的是同一份、不重做。"""
    world, field = make_world(), _fought(_after_ferry_fight(library), 1)
    skill = field.hero.skills[0]
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        pregen.prefetch(library, world, field)
        pregen.drain(timeout=60)
        started = len(rec.calls)
        assert started >= 1
        town = _fought(field, 2).model_copy(update={"location": "mist_ferry"})
        pregen.prefetch(library, world, town)
        pressed = _request(library, town, skill)
        got = pregen.supplier(library)(pressed)
        assert isinstance(got, FlashGen) and got.key == pressed.key
        assert len(rec.calls) == started
    finally:
        pregen.shutdown()


def test_press_uses_pregen_and_replay_reads_log(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """生成開始後統計變了：按下時用預先生成的那一份，日誌記下它（鍵是按下那一刻的），重播不呼叫
    LLM、結果相同。"""
    town = _fought(_town_char(library, "c1"), 3)
    store = _store(library, tmp_path, town)
    rec = Recorder()
    store.pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    skill = "skill_frost_shackle"  # FL-1a：hero.skills[0] 戰歌已沒有閃現選項（蓄力不再只多冷卻）
    start = store.world()
    try:
        store.pregen.prefetch(library, start, _fought(town, 1))  # 前幾場後就開始生成
        store.pregen.drain(timeout=60)
        before = list(rec.calls)
        store.character("c1")  # 讀進來（統計已是第 3 場後）：不重做
        flashed = store.act("c1", FlashAction(skill=skill))
    finally:
        store.pregen.shutdown()
    assert rec.calls == before
    (entry,) = store.entries()
    (gen,) = entry.generated
    pressed = _request(library, town, skill, start)
    assert isinstance(gen, FlashGen) and gen.key == pressed.key
    assert gen.record.source == "llm"  # 預先生成的那一份（假生成函式標成 llm）
    assert gen.record.tag == _request(library, _fought(town, 1), skill, start).key
    monkeypatch.setattr("trpg.api.world_pregen.WorldPregen._run", _never_run)
    result = replay(library, start, {"c1": town}, store.entries())
    assert result.characters["c1"].pending_flash == flashed.char.pending_flash
    assert result.characters["c1"] == flashed.char
