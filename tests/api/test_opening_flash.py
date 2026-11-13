"""#150 第 6 點：開局還沒結束的角色 4 級前不能閃現（Phase OB-3；21 21.5、09 9.6.9）。

- 世界動作 ``flash`` 在 4 級前被擋、4 級後可以；靈感照常累積（不扣點）。
- 閃現的預先生成（:mod:`trpg.api.world_pregen`）在不能閃現時跳過：Mock LLM 一次都沒被呼叫。
- 成長面板的按鈕狀態與原因（``GrowthView.can_flash``、``flash_blocked_zh``）。
- 已完成開局的舊角色（``opening is None``）照舊：1 級就能閃、照舊預先生成。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, hero, make_world
from tests.world.test_opening_reselect import _chosen
from tests.world.test_opening_stages import _starter
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world_growth_view import growth_view
from trpg.api.world_pregen import (
    WorldPregen,
    flash_wait_request,
    predicted_requests,
    provider_generators,
)
from trpg.content.library import ContentLibrary
from trpg.llm.client import MockLLMClient
from trpg.llm.flash_propose import (
    DEFAULT_FLASH_ATTEMPTS,
    LlmFlashSource,
    RecordSink,
    mock_flash_client,
)
from trpg.roguelite.llm_hook import FlashSourceFactory
from trpg.roguelite.state import FlashChoice
from trpg.skillgen.flash_offer import FlashRequest
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import FlashAction, FlashOfferedEvent
from trpg.world.errors import WorldActionError
from trpg.world.growth import OPENING_END_LEVEL, flash_blocked_zh
from trpg.world.state import CharacterState
from trpg.world.step import new_character, world_step

type MakeChar = Callable[..., CharacterState]

BLOCKED = "到 4 級才能閃現"
FLASHABLE = "skill_frost_shackle"  # FL-1a：hero.skills[0] 戰歌已沒有閃現選項（蓄力不再只多冷卻）


@pytest.fixture
def make_char(library: ContentLibrary) -> MakeChar:
    def factory(character_id: str = "alice", **updates: object) -> CharacterState:
        char = new_character(library, character_id, hero(library), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    return factory


def _used(char: CharacterState, insight: int = 3) -> CharacterState:
    """裝備中的招都上場用過、手上有靈感（可以閃現的狀態）。"""
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in char.hero.skills}
    return char.model_copy(update={"flash": dict(sorted(flash.items())), "insight": insight})


def _flash(library: ContentLibrary, char: CharacterState) -> CharacterState:
    skills = char.hero.skills
    action = FlashAction(skill=FLASHABLE if FLASHABLE in skills else skills[0])
    result = world_step(library, make_world(), char, action, NOON)
    assert any(isinstance(e, FlashOfferedEvent) for e in result.events)
    return result.char


class _CountingProvider(MockLlmProvider):
    """閃現提議用的 Mock LLM 全部留下來，數它們被呼叫幾次。"""

    def __init__(self) -> None:
        super().__init__()
        self.clients: list[MockLLMClient] = []

    def flash_source(self, library: ContentLibrary) -> FlashSourceFactory | None:
        def client(request: FlashRequest, seed: int) -> MockLLMClient:
            made = mock_flash_client(library, request, seed, DEFAULT_FLASH_ATTEMPTS)
            self.clients.append(made)
            return made

        def factory(sink: RecordSink | None) -> LlmFlashSource:
            return LlmFlashSource(client, max_attempts=DEFAULT_FLASH_ATTEMPTS, sink=sink)

        return factory

    def llm_calls(self) -> int:
        return sum(len(c.calls) for c in self.clients)


def _pregen_calls(library: ContentLibrary, char: CharacterState) -> int:
    provider = _CountingProvider()
    pregen = WorldPregen(provider_generators(provider), enabled=lambda: True)
    try:
        pregen.prefetch(library, make_world(), char)
        pregen.drain(timeout=60)
    finally:
        pregen.shutdown()
    return provider.llm_calls()


def test_flash_blocked_before_level_4(library: ContentLibrary, make_char: MakeChar) -> None:
    """正式選定後、4 級前：閃現被擋（靈感不扣）；到 4 級就可以。"""
    chosen = _used(_chosen(library, make_char))
    assert chosen.level == 3 and chosen.opening is not None
    assert BLOCKED in (flash_blocked_zh(chosen) or "")
    with pytest.raises(WorldActionError, match=BLOCKED):
        _flash(library, chosen)
    view = growth_view(library, chosen, in_battle=False)
    assert view.can_spend and not view.can_flash
    assert BLOCKED in (view.flash_blocked_zh or "") and view.blocked_zh is None
    assert view.insight == chosen.insight == 3  # 靈感照常留著
    grown = chosen.model_copy(update={"level": OPENING_END_LEVEL})
    assert flash_blocked_zh(grown) is None
    flashed = _flash(library, grown)
    assert flashed.pending_flash is not None and flashed.insight < grown.insight
    view = growth_view(library, grown, in_battle=False)
    assert view.can_flash and view.flash_blocked_zh is None


def test_starter_stage_shows_the_same_reason(library: ContentLibrary, make_char: MakeChar) -> None:
    """入門期本來就被開局閘門擋；面板的原因和閘門回的是同一句（OB-5 定稿「到 4 級才能閃現」）。"""
    starter = _used(_starter(library, make_char))
    with pytest.raises(WorldActionError, match=BLOCKED):
        _flash(library, starter)
    view = growth_view(library, starter, in_battle=False)
    assert not view.can_flash and BLOCKED in (view.flash_blocked_zh or "")


def test_old_characters_flash_as_before(library: ContentLibrary, make_char: MakeChar) -> None:
    """已完成開局的舊角色不受影響：1 級在城鎮就能閃；野外的原因照舊是地點。"""
    old = _used(make_char())
    assert old.opening is None and old.level == 1 and flash_blocked_zh(old) is None
    view = growth_view(library, old, in_battle=False)
    assert view.can_flash and view.flash_blocked_zh is None
    assert _flash(library, old).pending_flash is not None
    field = growth_view(
        library, old.model_copy(update={"location": "ferry_steps"}), in_battle=False
    )
    assert not field.can_flash and field.flash_blocked_zh is None
    assert field.blocked_zh == "這裡不是城鎮或營火"


def test_pregen_skipped_while_flash_is_blocked(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """4 級前不預先生成閃現（Mock LLM 沒被呼叫）；4 級後照常；舊角色照舊。"""
    world = make_world()
    chosen = _used(_chosen(library, make_char))
    skill = chosen.hero.skills[0]
    field = chosen.model_copy(update={"location": "ferry_steps"})
    for char in (chosen, field):
        assert flash_wait_request(library, world, char, FlashChoice(skill=skill)) is None
        assert not [r for r in predicted_requests(library, world, char) if r.kind == "flash"]
    assert _pregen_calls(library, field) == 0
    grown = field.model_copy(update={"level": OPENING_END_LEVEL})
    assert [r for r in predicted_requests(library, world, grown) if r.kind == "flash"]
    assert _pregen_calls(library, grown) > 0
    old = _used(make_char("bob")).model_copy(update={"location": "ferry_steps"})
    assert [r for r in predicted_requests(library, world, old) if r.kind == "flash"]
    assert _pregen_calls(library, old) > 0
