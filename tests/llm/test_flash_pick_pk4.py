"""PK-4 B（玩法 PM 4.1.25，06 6.34.7）：閃現不指定類別時候選可以借別類、程式只守混合至少 2 類與
轉型保底；指定類別照舊；描述也擋多字老套詞（單字不擋）。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

import pytest

from tests.llm.test_flash_pick_pk3 import REQUESTS, _answer
from tests.roguelite.helpers import library
from trpg.llm import flash_pick
from trpg.llm.client import MockLLMClient
from trpg.llm.consistency import strict_facts
from trpg.llm.flash_pick import STRICT_NOTE, pick_variations
from trpg.llm.flash_propose import FlashProposalRecord, LlmFlashSource
from trpg.skillgen.flash_offer import flash_slots, make_offer, skill_before
from trpg.skillgen.flash_pick import FlashSlot, SlotOption, keep_mix


def _borrowed(slot: FlashSlot) -> list[int]:
    return [
        i
        for i, c in enumerate(slot.candidates)
        if not slot.fixed and c.variation.category != slot.category
    ]


def test_unfocused_slots_borrow_other_categories_focused_do_not() -> None:
    lib = library()
    borrowed = 0
    for request in REQUESTS:
        slots = flash_slots(lib, request)
        found = sum(len(_borrowed(s)) for s in slots)
        if request.category is not None:
            assert found == 0
        borrowed += found
    assert borrowed > 0


def _single_category_picker(slots: Sequence[FlashSlot]) -> str:
    """每格都挑同一個類別（最多格子有候選的那一類）的候選：故意把類別挑得很集中。"""
    counts: dict[str, int] = {}
    for s in slots:
        for category in {c.variation.category for c in s.candidates}:
            counts[category] = counts.get(category, 0) + 1
    target = max(sorted(counts), key=lambda c: counts[c])
    body: dict[str, Any] = {}
    for s in slots:
        pick = next((i for i, c in enumerate(s.candidates) if c.variation.category == target), 0)
        body[f"s{s.index}"] = {"pick": 0 if s.fixed else pick}
    return json.dumps(body, ensure_ascii=False)


def test_mix_of_two_categories_is_kept_by_the_program() -> None:
    """LLM 把類別挑得很集中時，程式從後面的格子改回第一個，選項至少 2 類（原本出題做得到時）；
    紀錄的 ``accepted`` 就是最後的選項；重播一樣。"""
    lib = library()
    min_categories = lib.flash.pricing.rule(False).min_categories
    kept = 0
    for request in REQUESTS:
        if request.category is not None:
            continue
        slots = flash_slots(lib, request)
        plain = make_offer(lib, request)
        need = min(
            min_categories,
            len({o.variation.category for o in plain.options if o.variation.source != "transform"}),
        )
        records: list[FlashProposalRecord] = []
        client = MockLLMClient([_single_category_picker(slots)] * 3)
        offer = make_offer(lib, request, LlmFlashSource(client, sink=records.append))
        mixed = {o.variation.category for o in offer.options if o.variation.source != "transform"}
        assert len(mixed) >= need
        assert [o.variation.key() for o in offer.options] == [v.key() for v in records[-1].accepted]
        kept += sum(c == ("pick.mix_kept",) for c in records[-1].codes)
    assert kept > 0


class _Opt:
    def __init__(self, category: str) -> None:
        self.variation = type("V", (), {"category": category, "source": "minor"})()


def _slot(index: int, *categories: str) -> FlashSlot:
    return FlashSlot(index, categories[0], tuple(cast(SlotOption, _Opt(c)) for c in categories))


def test_keep_mix_unit() -> None:
    slots = [_slot(0, "a", "b"), _slot(1, "b", "a"), _slot(2, "c", "a")]
    assert keep_mix(slots, (0, 1, 1), 2) == (0, 1, 0)  # 全挑 a → 從最後一格改回
    assert keep_mix(slots, (1, 1, 1), 2) == (1, 1, 1)  # b、a、a 已經 2 類
    assert keep_mix(slots, (1, 0, 1), 2) == (1, 0, 1)  # a、b 已經 2 類
    assert keep_mix(slots, (9, -1), 2) == (0, 0, 0)  # 超出範圍、缺的＝0
    one = [_slot(0, "a", "a2"), _slot(1, "a", "a3")]
    assert keep_mix(one, (1, 1), 2) == (1, 1)  # 原本就只有 1 類：不強求


@pytest.fixture
def lenient(monkeypatch: pytest.MonkeyPatch) -> None:
    """一般的描述檢查（加上的效果要提到…）一律通過，只看 PK-4 的多字老套詞。"""
    monkeypatch.setattr(flash_pick._Checker, "_note_checks", lambda *_a: [])


@pytest.mark.usefixtures("lenient")
def test_note_with_multi_char_cliche_is_asked_again() -> None:
    """描述提到效果裡沒有的多字老套詞（「從高處」）帶錯誤重問；改好就收下。單字（「斬」）不擋。"""
    lib = library()
    request = REQUESTS[0]
    slots = flash_slots(lib, request)
    before = skill_before(lib, request)
    s0 = slots[0]
    assert not any(
        "high_ground" in f or "height" in f for f in strict_facts(lib, s0.candidates[0].skill)
    )
    bad = _answer(slots, s0={"pick": 0, "note_zh": "從高處出手，更快一斬。"})
    good = _answer(slots, s0={"pick": 0, "note_zh": "出手更快，一斬落定。"})
    result = pick_variations(
        MockLLMClient([bad, good, good]), lib, request, slots, before, major=False
    )
    assert f"note_zh.{STRICT_NOTE}" in result.codes[0]
    assert result.attempts == 2
    key = s0.candidates[0].variation.key()
    assert {t.key: t.note_zh for t in result.texts}[key] == "出手更快，一斬落定。"


@pytest.mark.usefixtures("lenient")
def test_note_cliche_dropped_after_last_attempt() -> None:
    lib = library()
    request = REQUESTS[0]
    slots = flash_slots(lib, request)
    before = skill_before(lib, request)
    bad = _answer(slots, s0={"pick": 0, "note_zh": "從高處出手，更快。"})
    result = pick_variations(MockLLMClient([bad] * 3), lib, request, slots, before, major=False)
    assert result.attempts == 3
    key = slots[0].candidates[0].variation.key()
    assert key not in {t.key for t in result.texts}
    assert f"flash.note_dropped.{STRICT_NOTE}" in result.codes[-1]
