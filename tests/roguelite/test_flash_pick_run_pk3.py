"""PK-3：一輪的閃現走挑選模式——LLM 挑的位置與描述進選項、提議紀錄（``flash_llm_log``，帶
``picks``）、存檔往返；讀檔與重播不呼叫 LLM（Mock）。"""

from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from tests.roguelite.helpers import library
from tests.roguelite.test_flash_llm_run import _gear, _ready
from trpg.llm import flash_pick
from trpg.llm.client import MockLLMClient
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_client
from trpg.roguelite import RunSave, apply_choice, dumps_save, loads_save
from trpg.roguelite.flashes import comparable_run
from trpg.roguelite.llm_hook import use_flash_source
from trpg.roguelite.state import FlashChoice, FlashPickChoice
from trpg.skillgen.flash_offer import FlashRequest
from trpg.skillgen.flash_pick import FlashSlot

NOTE = "出手更順，用得更多。"


def _picker(request: FlashRequest, slots: Sequence[FlashSlot], seed: int) -> MockLLMClient:
    """每格挑最後一個候選並寫同一句描述。"""
    body = {
        f"s{s.index}": {"pick": len(s.candidates) - 1 if not s.fixed else 0, "note_zh": NOTE}
        for s in slots
    }
    return MockLLMClient([json.dumps(body, ensure_ascii=False)] * 3)


def test_picks_and_notes_reach_the_offer_the_log_and_the_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(flash_pick._Checker, "_note_checks", lambda *_a: [])
    lib = library()
    assert lib.skill_pick.flash_enabled
    run = _gear().model_copy(update={"llm": True})
    skill = _ready(run)
    with use_flash_source(
        lambda sink: LlmFlashSource(
            lambda r, s: mock_flash_client(lib, r, s, 3), sink=sink, pick_client=_picker
        )
    ):
        opened = apply_choice(lib, run, FlashChoice(skill=skill))
    (record,) = opened.flash_llm_log
    assert record.picks and len(record.picks) == len(record.accepted)
    assert record.prompt_version == "flash-pick/1"
    assert record.texts and all(t.note_zh == NOTE for t in record.texts)
    offer = opened.pending_flash.offer  # type: ignore[union-attr]
    assert [o.variation.key() for o in offer.options] == [v.key() for v in record.accepted]
    assert all(o.variation.note_zh == NOTE for o in offer.options)
    back = loads_save(dumps_save(RunSave(run_id="pk3", run=opened))).run
    assert comparable_run(back) == comparable_run(opened)
    picked = apply_choice(lib, opened, FlashPickChoice(pick=0))
    new = next(s for s in picked.hero.skills if s not in run.hero.skills)
    assert picked.flash[new].records[-1].variation.note_zh == NOTE


def test_without_llm_the_flash_offer_is_unchanged() -> None:
    """一輪沒開 LLM：照舊用法統計出題（挑選模式不影響），不寫提議紀錄。"""
    lib = library()
    run = _gear()
    opened = apply_choice(lib, run, FlashChoice(skill=_ready(run)))
    assert opened.flash_llm_log == ()
