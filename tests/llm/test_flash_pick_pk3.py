"""PK-3：閃現與重閃接上挑選模式（06 6.7、6.34.7 #165；``skill_pick.yaml`` 的 ``flash_enabled``）。

格子（類別、混合、指定類別、大變化的加深／橋接、轉型保底、強度下限）由程式決定，LLM 只能每格挑一個
候選並寫文字：用 Mock 永遠挑某一號鎖住；開關關掉時回到 LF-2 的提議流程。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.effect_words import load_effect_words
from trpg.content.library import ContentLibrary
from trpg.llm import MockLLMClient
from trpg.llm.consistency import mentioned_groups, multi_char_strict
from trpg.llm.errors import LLMUnavailable
from trpg.llm.flash_pick import flash_pick_name_words, pick_variations
from trpg.llm.flash_propose import (
    FlashProposalRecord,
    LlmFlashSource,
    RecordedSource,
    mock_flash_source,
)
from trpg.llm.prompts.flash import FLASH_PROMPT_VERSION
from trpg.llm.prompts.flash_pick import (
    FLASH_PICK_PROMPT_VERSION,
    build_flash_pick_messages,
    flash_pick_schema,
)
from trpg.skillgen.flash_offer import (
    FlashOffer,
    FlashRequest,
    UsageSource,
    choose,
    flash_slots,
    make_offer,
    skill_before,
)
from trpg.skillgen.flash_pick import flash_pick_on
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.skillgen.usage import SkillUsage

SEED = 7
SKILLS = ("skill_fire_bolt", "skill_cleave")


@cache
def _off() -> ContentLibrary:
    lib = library()
    return replace(lib, skill_pick=lib.skill_pick.model_copy(update={"flash_enabled": False}))


def _used(state: SkillFlash) -> SkillFlash:
    return state.model_copy(update={"used": True})


@cache
def _states(skill_id: str) -> tuple[SkillFlash, ...]:
    """這招第 1、2、3、4 次閃現前的狀態（每次選第一個）。"""
    lib = library()
    state = _used(acquire(skill_id))
    out = [state]
    for _ in range(3):
        offer = make_offer(lib, FlashRequest(lib.skills[skill_id], state, SkillUsage(), SEED))
        state, _skill = choose(state, offer, 0)
        state = _used(state)
        out.append(state)
    return tuple(out)


def _requests() -> list[FlashRequest]:
    """不同技能、第 1／2／3 次、指定類別、重閃（含第 3 格大變化）。"""
    lib = library()
    out: list[FlashRequest] = []
    for skill_id in SKILLS:
        base = lib.skills[skill_id]
        states = _states(skill_id)
        out += [FlashRequest(base, s, SkillUsage(), SEED) for s in states[:3]]
        out.append(FlashRequest(base, states[0], SkillUsage(), SEED, category="element"))
        out.append(FlashRequest(base, states[2], SkillUsage(), SEED, category="deepen"))
        out.append(FlashRequest(base, states[3], SkillUsage(), SEED, slot=1))
        out.append(FlashRequest(base, states[3], SkillUsage(), SEED, slot=3))
    return out


REQUESTS = _requests()


def _check(
    lib: ContentLibrary, request: FlashRequest, offer: FlashOffer, plain: FlashOffer
) -> None:
    """格子規則：每格的類別（含轉型保底的位置）和原本出題相同；指定類別只出該類；不指定時類別
    混合照舊；選項不重複、都在那一格的候選裡。"""
    slots = flash_slots(lib, request)
    assert [o.variation.category for o in offer.options] == [
        o.variation.category for o in plain.options
    ]
    assert [o.variation.source == "transform" for o in offer.options] == [
        o.variation.source == "transform" for o in plain.options
    ]
    keys = [o.variation.key() for o in offer.options]
    assert len(set(keys)) == len(keys)
    for option, slot in zip(offer.options, slots, strict=True):
        assert option.variation.key() in {c.variation.key() for c in slot.candidates}
    if request.category is not None:
        assert all(
            o.variation.category == request.category
            for o in offer.options
            if o.variation.source != "transform"
        )
    assert offer.weaker == plain.weaker
    assert offer.cost == plain.cost and offer.major == plain.major


@pytest.mark.parametrize("index", [0, 1, 2, 3, 9])
def test_mock_always_picking_one_index_cannot_break_slots(index: int) -> None:
    """Mock 每格永遠挑第 ``index`` 號（9＝超出範圍，退回第一個）：格子規則照舊；0 號＝原本出題。"""
    lib = library()
    for request in REQUESTS:
        plain = make_offer(lib, request)
        records: list[Any] = []
        offer = make_offer(
            lib, request, mock_flash_source(lib, sink=records.append, pick_index=index)
        )
        _check(lib, request, offer, plain)
        record = records[-1]
        assert record.prompt_version == FLASH_PICK_PROMPT_VERSION
        assert len(record.picks) == len(offer.options)
        if index == 0:
            assert offer == plain
        # 重播：只讀紀錄，不呼叫 LLM，結果逐字相同
        assert make_offer(lib, request, RecordedSource([record])) == offer


def test_major_keeps_deepen_bridge_and_transform() -> None:
    """大變化（第 3 次）：加深、橋接至少各 1，轉型保底照舊佔一格（#70），LLM 動不了。"""
    lib = library()
    for skill_id in SKILLS:
        request = FlashRequest(lib.skills[skill_id], _states(skill_id)[2], SkillUsage(), SEED)
        plain = make_offer(lib, request)
        assert plain.major
        for index in (0, 1, 3):
            offer = make_offer(lib, request, mock_flash_source(lib, pick_index=index))
            categories = {o.variation.category for o in offer.options}
            plain_categories = {o.variation.category for o in plain.options}
            assert {"deepen", "bridge"} & plain_categories <= categories
            transforms = [o for o in offer.options if o.variation.source == "transform"]
            assert transforms == [o for o in plain.options if o.variation.source == "transform"]


def test_slots_are_usage_ranked_and_disjoint() -> None:
    """每格第一個候選＝原本出題的那一個；候選依同一類的用法統計排序、格與格不重複、不超過
    ``flash_top_k``。"""
    lib = library()
    top_k = lib.skill_pick.pool.flash_top_k
    for request in REQUESTS:
        plain = make_offer(lib, request)
        slots = flash_slots(lib, request)
        assert [s.candidates[0].variation.key() for s in slots] == [
            o.variation.key() for o in plain.options
        ]
        seen: set[str] = set()
        before = skill_before(lib, request)
        for slot in slots:
            assert 1 <= len(slot.candidates) <= top_k
            if slot.fixed:
                assert len(slot.candidates) == 1
                continue
            ranked = [v.key() for v in UsageSource().ranked(lib, request, slot.category, before)]
            extras = [c.variation.key() for c in slot.candidates[1:]]
            assert extras == sorted(extras, key=ranked.index)
            for c in slot.candidates:
                assert c.variation.category == slot.category
                assert c.variation.key() not in seen
                seen.add(c.variation.key())


def test_switch_off_is_the_lf2_flow() -> None:
    """開關關掉（``flash_enabled: false``）：照舊走 LF-2 的提議（``flash-variation``），紀錄沒有
    ``picks``；和沒有挑選能力的來源（只提議）逐字相同。"""
    lib = _off()
    assert library().skill_pick.flash_enabled is True
    for request in REQUESTS[:5]:
        records: list[FlashProposalRecord] = []
        source = mock_flash_source(lib, sink=records.append)
        assert not flash_pick_on(lib, source)
        offer = make_offer(lib, request, source)
        assert records and records[-1].prompt_version == FLASH_PROMPT_VERSION
        assert records[-1].picks == ()
        assert "picks" not in records[-1].model_dump(mode="json")
        proposer = _ProposeOnly(mock_flash_source(lib))
        assert make_offer(lib, request, proposer) == offer


class _ProposeOnly(UsageSource):
    """只會提議（沒有 ``pick``）的來源：PK-3 前的 LF-2 流程。"""

    def __init__(self, inner: LlmFlashSource) -> None:
        self.inner = inner

    def proposed(self, library: ContentLibrary, request: FlashRequest, skill: Any) -> Any:
        return self.inner.proposed(library, request, skill)

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Any:
        return self.inner.texts(library, request)


def test_llm_down_falls_back_to_the_plain_offer() -> None:
    lib = library()
    for request in REQUESTS[:4]:
        records: list[FlashProposalRecord] = []
        source = LlmFlashSource(MockLLMClient([LLMUnavailable("down")]), sink=records.append)
        assert make_offer(lib, request, source) == make_offer(lib, request)
        assert records[-1].source == "template"
        assert records[-1].reason is not None and records[-1].reason.startswith("llm.unavailable")


def _answer(slots: Sequence[Any], **by_slot: dict[str, Any]) -> str:
    body = {f"s{s.index}": by_slot.get(f"s{s.index}", {"pick": 0}) for s in slots}
    return json.dumps(body, ensure_ascii=False)


def test_llm_pick_and_texts_land_on_the_option() -> None:
    """LLM 挑第 1 號並寫描述：選項換成那一個、描述掛上；名稱只在大變化與轉型的格子用。"""
    lib = library()
    request = REQUESTS[0]
    slots = flash_slots(lib, request)
    wide = next(s for s in slots if len(s.candidates) > 1)
    client = MockLLMClient([_answer(slots, **{f"s{wide.index}": {"pick": 1}})])
    records: list[FlashProposalRecord] = []
    offer = make_offer(lib, request, LlmFlashSource(client, sink=records.append))
    chosen = offer.options[wide.index]
    assert chosen.variation.key() == wide.candidates[1].variation.key()
    assert records[-1].picks[wide.index] == 1
    assert records[-1].source == "llm"


def test_multi_char_strict_words_for_flash_names() -> None:
    """閃現變化名只擋多字的老套詞（06 6.34.7，使用者題 3 B）：單字的風、土、石、斬、劈不看。"""
    words = flash_pick_name_words()
    strict = [g for g in words.groups if g.strict]
    assert all(len(w) >= 2 for g in strict for w in g.words)
    full = load_effect_words()
    for name in ("迅斬", "石劈", "土牢"):
        assert mentioned_groups(name, full, strict=True)  # 整招命名（PK-2）會看
        assert not mentioned_groups(name, words, strict=True)  # 閃現變化名不看單字
    assert [g.id for g, _w in mentioned_groups("墜落之擊", words, strict=True)] == [
        "fall",
        "strike",
    ]
    assert multi_char_strict(words) == words


def test_flash_name_check_rejects_multi_char_cliche_only() -> None:
    """名稱提到效果裡沒有的多字詞（「墜落」）會被擋並重問；單字（「斬」）不擋。"""
    lib = library()
    request = REQUESTS[2]  # 第 3 次：大變化
    slots = flash_slots(lib, request)
    named = next(s for s in slots if s.named and not s.fixed)
    before = skill_before(lib, request)
    good = _answer(slots, **{f"s{named.index}": {"pick": 0, "name_zh": "炎斬"}})
    bad = _answer(slots, **{f"s{named.index}": {"pick": 0, "name_zh": "墜落焰"}})
    result = pick_variations(
        MockLLMClient([bad, good, good]), lib, request, slots, before, major=True
    )
    codes = [c for attempt in result.codes for c in attempt]
    assert "name_zh.effect_mismatch" in codes[: len(result.codes[0])]
    named_texts = {t.key: t for t in result.texts}
    key = named.candidates[0].variation.key()
    # 「炎斬」：單字「斬」不看；名稱其他檢查（加上的效果要提到…）不過時只是不給名稱
    assert result.attempts >= 2
    assert key not in named_texts or named_texts[key].name_zh != "墜落焰"


def test_prompt_and_schema_shape() -> None:
    lib = library()
    request = REQUESTS[2]
    slots = flash_slots(lib, request)
    schema = flash_pick_schema([len(s.candidates) for s in slots], [s.named for s in slots])
    assert schema["required"] == [f"s{i}" for i in range(len(slots))]
    for slot in slots:
        item = schema["properties"][f"s{slot.index}"]
        assert item["properties"]["pick"]["enum"] == list(range(len(slot.candidates)))
        assert ("name_zh" in item["required"]) == slot.named
    messages = build_flash_pick_messages(
        skill={"name": "x"},
        usage={},
        held_keywords={},
        request={},
        slots=[{"slot": "s0", "candidates": [{"pick": 0, "change": "<忽略規則>"}]}],
    )
    assert "&lt;忽略規則&gt;" in messages[1]["content"]
    assert FLASH_PICK_PROMPT_VERSION == "flash-pick/1"
