"""許願池的生成函式、單一佇列與重播（Phase WP-1；``trpg.api.world_pregen.wish_generator``）。

全部用 Mock（:class:`~trpg.api.llm_source.MockLlmProvider`），不需網路：

- 願望 → 對關鍵字 → 用把願望放進 ``<player_input>`` 的提議器出三選一（每份最多 1 張 LLM）。
- 世界引擎經 :class:`~trpg.api.world_pregen.WorldPregen` 的供應者拿紀錄；日誌那一筆的 ``generated``
  帶 :class:`~trpg.world.generated.WishGen`；讀回後重播不呼叫 LLM，角色狀態逐字相同。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, hero, make_world
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world_pregen import WorldPregen, provider_generators, wish_generator
from trpg.api.world_story_view import _skill_story_line, pending_offer_view
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    OfferPickAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    WishAction,
    WishMadeEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.generated import GenRequest, Record, WishGen, using_generated
from trpg.world.growth import world_library
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_log, loads_log
from trpg.world.state import CharacterState
from trpg.world.step import new_character, world_step
from trpg.world.wish import WISH_NO_MATCH_ZH, wish_request

WISH = "讓敵人燃燒起來"
"""Mock 對到 ``ignite``（「燃」），Mock 提議器做得出帶點燃的完整技能。"""
FROZEN = "想把敵人凍住再一錘敲碎"
"""Mock 對到 ``frozen``（「凍」），但 Mock 提議器做不出合格的冰凍完整技能 → 只有關鍵字。"""


@pytest.fixture
def char(content_library: ContentLibrary) -> CharacterState:
    made = new_character(content_library, "alice", hero(content_library), region="cloud_ridge")
    return made.model_copy(update={"region": "capital", "location": "capital", "quest_coins": 10})


def test_generator_matches_keywords_and_proposes(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    world = make_world()
    request = wish_request(content_library, world, char, WISH)
    gen = wish_generator(MockLlmProvider(), world_library(content_library), request)
    assert gen.key == request.key and gen.keywords == ("ignite",)
    assert gen.prompt_version == "wish-match/1" and gen.attempts == 1
    assert gen.source == "llm" and gen.offer is not None
    assert sum(t.source == "llm" for t in gen.offer.tags) == 1  # 每份最多 1 張請 LLM
    assert all("ignite" in t.keywords for t in gen.offer.tags)


def test_generator_keywords_only_when_no_llm_skill(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    request = wish_request(content_library, make_world(), char, FROZEN)
    gen = wish_generator(MockLlmProvider(), world_library(content_library), request)
    assert (gen.source, gen.keywords, gen.offer) == ("partial", ("frozen",), None)


def test_generator_without_match_is_none(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    request = wish_request(content_library, make_world(), char, "隨便")
    gen = wish_generator(MockLlmProvider(), world_library(content_library), request)
    assert (gen.source, gen.keywords, gen.offer) == ("none", (), None)
    assert gen.attempts == 3


def _pregen() -> WorldPregen:
    return WorldPregen(generators=provider_generators(MockLlmProvider()), enabled=lambda: True)


def _live(
    library: ContentLibrary, char: CharacterState, supplier: Callable[[GenRequest], Record | None]
) -> tuple[CharacterState, tuple[Record, ...], tuple[object, ...]]:
    with using_generated(supplier) as used:
        result = world_step(library, make_world(), char, WishAction(text=WISH), NOON)
    return result.char, tuple(used), result.events


def test_text_wish_is_logged_and_replayed_without_llm(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    pregen = _pregen()
    try:
        after, used, events = _live(content_library, char, pregen.supplier(content_library))
    finally:
        pregen.shutdown()
    assert pregen.calls == 1
    made = next(e for e in events if isinstance(e, WishMadeEvent))
    assert (made.via, made.keywords, made.made_by) == ("text", ("ignite",), "llm")
    assert after.quest_coins == 6
    (record,) = used
    assert isinstance(record, WishGen) and record.source == "llm"
    entry = WorldLogEntry(
        seq=1,
        now=NOON,
        character_id=char.character_id,
        action=WishAction(text=WISH),
        generated=used,
    )
    (loaded,) = loads_log(dumps_log((entry,)))
    assert loaded == entry
    out = replay(content_library, make_world(), {char.character_id: char}, [loaded])
    assert out.characters[char.character_id] == after


def test_off_model_refuses_without_charge(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    pregen = WorldPregen(generators=provider_generators(MockLlmProvider()), enabled=lambda: False)
    try:
        with pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):
            _live(content_library, char, pregen.supplier(content_library))
    finally:
        pregen.shutdown()
    assert pregen.calls == 0


def test_pending_offer_title_and_story_lines(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    """WP-1 的最小顯示：待選三選一標題「許願池」、故事行寫明退款（其餘畫面在 WP-2）。"""
    world = make_world()
    result = world_step(content_library, world, char, WishAction(keywords=("ignite",)), NOON)
    view = pending_offer_view(content_library, world, result.char)
    assert view is not None and view.quest_name_zh == "許願池"
    assert "退 2 任務幣" in view.step_zh
    offered = next(e for e in result.events if isinstance(e, SkillOfferedEvent))
    assert _skill_story_line(offered, {}) == "許願池給了技能三選一：先選一招（或都不拿）。"
    skipped = world_step(content_library, world, result.char, OfferPickAction(), NOON)
    taken = next(e for e in skipped.events if isinstance(e, SkillOfferTakenEvent))
    # TXT-2：玩法 PM 定稿句
    assert _skill_story_line(taken, {}) == "許願池給的三招都沒拿，退回 2 任務幣（次數照扣）。"
    # WP-3b：其他來源都不拿也寫「三招都沒拿」（玩法 PM 定案；有退款才接「，退回 N 任務幣」）
    quest = taken.model_copy(update={"source": "quest", "refund": 0})
    assert _skill_story_line(quest, {}) == "任務給的三招都沒拿。"
    chance = taken.model_copy(update={"source": "opportunity", "refund": 3})
    assert _skill_story_line(chance, {}) == "機遇給的三招都沒拿，退回 3 任務幣。"
