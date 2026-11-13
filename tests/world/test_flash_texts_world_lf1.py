"""Phase LF-1：大世界閃現的 LLM 名稱與描述——記進日誌（``trpg-wlog/10``）、重播只讀日誌、選了之後
技能用 LLM 名稱（Mock，不需網路）。"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.llm import flash_propose
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import MockLLMClient
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_client
from trpg.roguelite.state import FlashLlmRecord
from trpg.skillgen.flash_offer import FlashRequest
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import FlashAction, FlashPickAction, FlashPickedEvent
from trpg.world.generated import FlashGen, GenRequest, using_generated
from trpg.world.growth import world_library
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import WLOG_FORMAT, dumps_log, dumps_log_entry, loads_log
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SKILL = "skill_frost_shackle"
NOTE = "寒氣更重，凍得更牢。"


@pytest.fixture(autouse=True)
def lenient_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    """描述的一致性檢查（4-L11）換成一律通過：這裡只測描述與名稱的資料流。"""
    monkeypatch.setattr(flash_propose, "note_checker", lambda *_a, **_k: lambda _v, _n: [])


def _noted_client(lib: ContentLibrary, request: FlashRequest, seed: int) -> MockLLMClient:
    data = json.loads(mock_flash_client(lib, request, seed, 1).complete([]))
    for item in data["variations"]:
        item["note_zh"] = NOTE
    return MockLLMClient([json.dumps(data, ensure_ascii=False)] * 3)


class Supplier:
    """當場用 Mock 生成（描述＋命名），記下呼叫次數。"""

    def __init__(self, library: ContentLibrary) -> None:
        self.view = world_library(library)
        self.calls = 0

    def __call__(self, request: GenRequest) -> FlashGen | None:
        assert request.kind == "flash"
        self.calls += 1
        view = self.view
        source = LlmFlashSource(
            lambda req, seed: _noted_client(view, req, seed),
            naming=lambda skill, seed: mock_naming_client(view, skill, seed),
        )
        flash = request.request
        source.proposed(view, flash, flash.current or flash.base)
        record = FlashLlmRecord.model_validate(source.records[-1].model_dump(mode="json"))
        return FlashGen(key=request.key, record=record)


def _never(request: GenRequest) -> None:
    raise AssertionError(f"重播不可以呼叫 LLM：{request.key}")


def _used(char: CharacterState, skill: str) -> CharacterState:
    flash = dict(char.flash)
    flash[skill] = flash.get(skill, acquire(skill)).model_copy(update={"used": True})
    return char.model_copy(update={"flash": flash})


def _at_major(library: ContentLibrary, char: CharacterState) -> tuple[CharacterState, str]:
    """沒有 LLM 先閃兩次（小變化），停在第 3 次（大變化）之前。"""
    char = _used(char.model_copy(update={"insight": 6}), SKILL)
    skill = SKILL
    for _ in range(2):
        opened = world_step(library, make_world(), char, FlashAction(skill=skill), NOON)
        picked = world_step(library, make_world(), opened.char, FlashPickAction(pick=0), NOON)
        skill = next(e for e in picked.events if isinstance(e, FlashPickedEvent)).new_skill
        char = _used(picked.char, skill)
    return char, skill


def test_major_flash_names_and_notes_are_logged_and_replayed(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char, skill = _at_major(library, make_char())
    supplier = Supplier(library)
    action = FlashAction(skill=skill)
    with using_generated(supplier) as used:
        live = world_step(library, make_world(), char, action, NOON)
    assert supplier.calls == 1
    pending = live.char.pending_flash
    assert pending is not None and pending.offer.major
    (gen,) = used
    assert isinstance(gen, FlashGen) and gen.record.texts
    named = [o for o in pending.offer.options if o.variation.name_zh]
    assert named  # 至少一個大變化或轉型拿到 LLM 名稱
    assert all(o.skill.name_zh == o.variation.name_zh for o in named)
    assert all(o.variation.source != "minor" for o in named)
    noted = [o for o in pending.offer.options if o.variation.note_zh == NOTE]
    assert noted
    # 日誌往返（新格式標頭）；重播只讀日誌
    entry = WorldLogEntry(
        seq=1, now=NOON, character_id=char.character_id, action=action, generated=tuple(used)
    )
    text = dumps_log((entry,))
    assert json.loads(text.splitlines()[0])["format"] == WLOG_FORMAT == "trpg-wlog/10"
    assert '"texts"' in dumps_log_entry(entry)
    (loaded,) = loads_log(text)
    with using_generated(_never):
        out = replay(library, make_world(), {char.character_id: char}, [loaded])
    assert out.characters[char.character_id].pending_flash == pending
    # 選了之後技能用 LLM 名稱；之後的歷程也留著名稱
    index = pending.offer.options.index(named[0])
    picked = world_step(library, make_world(), live.char, FlashPickAction(pick=index), NOON)
    new = next(e for e in picked.events if isinstance(e, FlashPickedEvent)).new_skill
    state = picked.char.flash[new]
    assert state.records[-1].variation.name_zh == named[0].variation.name_zh


def test_old_log_without_texts_replays_with_template_names(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """``/9`` 的日誌（紀錄沒有 ``texts``）照讀，名稱照舊是組合式。"""
    char, skill = _at_major(library, make_char())
    action = FlashAction(skill=skill)
    with using_generated(Supplier(library)) as used:
        world_step(library, make_world(), char, action, NOON)
    (gen,) = used
    assert isinstance(gen, FlashGen)
    bare = gen.model_copy(update={"record": gen.record.model_copy(update={"texts": ()})})
    entry = WorldLogEntry(
        seq=1, now=NOON, character_id=char.character_id, action=action, generated=(bare,)
    )
    line = dumps_log_entry(entry)
    assert '"texts"' not in line
    (loaded,) = loads_log('{"format": "trpg-wlog/9"}\n' + line + "\n")
    with using_generated(_never):
        out = replay(library, make_world(), {char.character_id: char}, [loaded])
    pending = out.characters[char.character_id].pending_flash
    assert pending is not None
    assert all(
        o.variation.name_zh is None and o.variation.note_zh is None for o in pending.offer.options
    )
