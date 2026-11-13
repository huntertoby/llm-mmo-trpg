"""Phase LF-1：一輪的閃現——LLM 描述進選項、提議紀錄（``flash_llm_log``）帶文字、存檔往返
（Mock）。"""

from __future__ import annotations

import json

import pytest

from tests.roguelite.helpers import library
from tests.roguelite.test_flash_llm_run import _gear, _ready
from trpg.content.library import ContentLibrary
from trpg.llm import flash_propose
from trpg.llm.client import MockLLMClient
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_client
from trpg.roguelite import RunSave, apply_choice, dumps_save, loads_save
from trpg.roguelite.flashes import comparable_run
from trpg.roguelite.llm_hook import use_flash_source
from trpg.roguelite.state import FlashChoice, FlashPickChoice
from trpg.skillgen.flash_offer import FlashRequest

NOTE = "出手更順，用得更多。"


def _noted_client(lib: ContentLibrary, request: FlashRequest, seed: int) -> MockLLMClient:
    data = json.loads(mock_flash_client(lib, request, seed, 1).complete([]))
    for item in data["variations"]:
        item["note_zh"] = NOTE
    return MockLLMClient([json.dumps(data, ensure_ascii=False)] * 3)


def test_notes_reach_the_offer_the_log_and_the_save(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flash_propose, "note_checker", lambda *_a, **_k: lambda _v, _n: [])
    lib = library()
    run = _gear().model_copy(update={"llm": True})
    skill = _ready(run)
    with use_flash_source(
        lambda sink: LlmFlashSource(lambda r, s: _noted_client(lib, r, s), sink=sink)
    ):
        opened = apply_choice(lib, run, FlashChoice(skill=skill))
    (record,) = opened.flash_llm_log
    assert record.texts and all(t.note_zh == NOTE for t in record.texts)
    offer = opened.pending_flash.offer  # type: ignore[union-attr]
    noted = [o for o in offer.options if o.variation.note_zh == NOTE]
    assert {o.variation.key() for o in noted} == {t.key for t in record.texts}
    back = loads_save(dumps_save(RunSave(run_id="lf1", run=opened))).run
    assert comparable_run(back) == comparable_run(opened)
    # 選了之後，描述跟著變化歷程存下來
    index = offer.options.index(noted[0])
    picked = apply_choice(lib, opened, FlashPickChoice(pick=index))
    new = next(s for s in picked.hero.skills if s not in run.hero.skills)
    assert picked.flash[new].records[-1].variation.note_zh == NOTE
