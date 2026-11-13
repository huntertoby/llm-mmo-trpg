"""Phase LF-3：選變體 API 帶 LLM 的一句話描述（``note_zh``）與名稱來源（``name_source``）。

全部用 Mock，不需要網路。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.roguelite.helpers import library as run_library
from tests.roguelite.test_flash_llm_run import _gear, _ready
from trpg.api.flash_text import option_llm_text
from trpg.api.llm_source import MockLlmProvider
from trpg.api.run_presenter import pending_flash_out
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.llm import flash_propose
from trpg.llm.client import MockLLMClient
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_client
from trpg.roguelite import apply_choice, auto_play
from trpg.roguelite.llm_hook import use_flash_source
from trpg.roguelite.state import FlashChoice, GearOfferNode
from trpg.skillgen.flash_offer import (
    DataOrderSource,
    FlashOffer,
    FlashRequest,
    make_offer,
)
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.flash_text import VariationText
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.whiteboard import compose_whiteboard

NOTE = "出手更順，用得更多。"
NAME = "竹影焚心"


class _Texted(DataOrderSource):
    def __init__(self, texts: Mapping[str, VariationText]) -> None:
        self._texts = texts

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        del library, request
        return self._texts


def _major_offer(lib: ContentLibrary, name: str | None, note: str | None) -> FlashOffer:
    """點燃斬第 3 次（大變化，2 階）：每個選項都給同一組文字（名稱只會掛上第一個大變化或轉型）。"""
    base = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=lib)
    state = acquire(base.id)
    for template, category in (("range_plus", "area"), ("cost_charge", "cost")):
        state = with_flash(state, Variation(source="minor", template=template, category=category))
    request = FlashRequest(
        base=base, state=state.model_copy(update={"used": True}), usage=SkillUsage(), seed=7, tier=2
    )
    plain = make_offer(lib, request)
    first = plain.options[0].variation
    texts = {first.key(): VariationText(key=first.key(), name_zh=name, note_zh=note)}
    return make_offer(lib, request, _Texted(texts))


def test_llm_name_on_a_major_option_reports_llm_and_the_note() -> None:
    lib = run_library()
    offer = _major_offer(lib, NAME, NOTE)
    first, *others = offer.options
    assert first.variation.source in ("major", "transform")
    assert first.skill.name_zh == NAME
    assert option_llm_text(first.variation, first.skill) == (NOTE, "llm")
    # 沒有文字的選項：組合式名稱、沒有描述
    for option in others:
        assert option_llm_text(option.variation, option.skill) == (None, "template")


def test_bad_texts_fall_back_to_template_and_no_note() -> None:
    lib = run_library()
    offer = _major_offer(lib, "Bad Name", "this is english")
    first = offer.options[0]
    assert first.skill.name_zh != "Bad Name"
    assert option_llm_text(first.variation, first.skill) == (None, "template")


def test_engine_rechecks_text_on_the_way_out() -> None:
    """變化上帶著不合格的文字（例：手改存檔）也不送到畫面；小變化帶名稱不算 LLM 名稱。"""
    lib = run_library()
    first = _major_offer(lib, NAME, NOTE).options[0]
    bad = first.variation.model_copy(update={"note_zh": "x" * 80})
    assert option_llm_text(bad, first.skill) == (None, "llm")
    minor = Variation(source="minor", template="range_plus", category="area", name_zh=NAME)
    assert option_llm_text(minor, first.skill)[1] == "template"
    # 名稱合格但技能沒用上（例：後面還有別的大變化）也不算
    renamed = first.skill.model_copy(update={"name_zh": "別的名字"})
    assert option_llm_text(first.variation, renamed)[1] == "template"


def _noted_client(lib: ContentLibrary, request: FlashRequest, seed: int) -> MockLLMClient:
    data = json.loads(mock_flash_client(lib, request, seed, 1).complete([]))
    for item in data["variations"]:
        item["note_zh"] = NOTE
    return MockLLMClient([json.dumps(data, ensure_ascii=False)] * 3)


def test_run_pending_flash_carries_llm_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flash_propose, "note_checker", lambda *_a, **_k: lambda _v, _n: [])
    lib = run_library()
    run = _gear().model_copy(update={"llm": True})
    with use_flash_source(
        lambda sink: LlmFlashSource(lambda r, s: _noted_client(lib, r, s), sink=sink)
    ):
        opened = apply_choice(lib, run, FlashChoice(skill=_ready(run)))
    out = pending_flash_out(lib, opened)
    assert out is not None
    noted = [o for o in out.options if o.note_zh == NOTE]
    assert noted, "提議的選項要帶描述"
    # 第 1 次閃現全是小變化：名稱沿用原名，來源一律 template
    assert all(o.name_source == "template" for o in out.options)
    body = out.model_dump(mode="json")
    assert all("note_zh" in o and "name_source" in o for o in body["options"])


# ---- API（Mock 提供者，不命名、不寫描述）------------------------------------------------


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    return make_client(library, llm=MockLlmProvider())


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code in (200, 201), reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_api_options_have_the_two_new_fields(client: TestClient) -> None:
    run_id = _ok(client.post("/api/runs", json={"build": "build_fire", "seed": 6}))["run_id"]
    store = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(store, RunStore)
    session = store.get(run_id)
    session.run, _ = auto_play(
        store.library, session.run, stop=lambda r, _b: isinstance(r.node, GearOfferNode)
    )
    body = _ok(client.get(f"/api/runs/{run_id}"))
    skill = next(f["skill_id"] for f in body["hero"]["flash"] if f["can_flash"])
    opened = _ok(client.post(f"/api/runs/{run_id}/choice", json={"kind": "flash", "skill": skill}))
    for option in opened["pending_flash"]["options"]:
        assert option["name_source"] == "template"
        assert option["note_zh"] is None
