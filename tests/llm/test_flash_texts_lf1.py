"""Phase LF-1：LLM 閃現提議的描述（``note_zh``）收進紀錄、大變化與轉型命名、重播只讀紀錄
（Mock）。"""

from __future__ import annotations

import json

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm import flash_propose
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.errors import LLMUnavailable
from trpg.llm.flash_propose import (
    FlashProposalRecord,
    LlmFlashSource,
    RecordedSource,
    mock_flash_client,
    mock_flash_source,
    propose_variations,
)
from trpg.roguelite.state import FlashLlmRecord
from trpg.skillgen.flash_offer import FlashOffer, FlashRequest, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage

FIRE_BOLT = "skill_fire_bolt"
SEED = 11
RANGE = Variation(source="minor", template="range_plus", category="area")
NOTE = "火光更盛，燒得更遠。"


def _request(state: SkillFlash) -> FlashRequest:
    lib = library()
    return FlashRequest(base=lib.skills[FIRE_BOLT], state=state, usage=SkillUsage(), seed=SEED)


def _first() -> SkillFlash:
    return acquire(FIRE_BOLT).model_copy(update={"used": True})


def _major() -> SkillFlash:
    records = (FlashRecord(nth=1, variation=RANGE), FlashRecord(nth=2, variation=RANGE))
    return SkillFlash(base_id=FIRE_BOLT, records=records, used=True)


def _noted_client(lib: ContentLibrary, request: FlashRequest, seed: int) -> MockLLMClient:
    """Mock 的合格提議，每一項都寫上同一句描述。"""
    text = mock_flash_client(lib, request, seed, 1).complete([])
    data = json.loads(text)
    for item in data["variations"]:
        item["note_zh"] = NOTE
    return MockLLMClient([json.dumps(data, ensure_ascii=False)] * 3)


@pytest.fixture
def lenient_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    """描述的一致性檢查（4-L11）換成一律通過：這裡只測描述有沒有被收下、掛上。"""
    monkeypatch.setattr(flash_propose, "note_checker", lambda *_a, **_k: lambda _v, _n: [])


def _source(*, naming: bool, notes: bool = False) -> LlmFlashSource:
    lib = library()
    if not notes:
        return mock_flash_source(lib, naming=naming)
    source = mock_flash_source(lib, naming=naming)
    source.client = lambda request, seed: _noted_client(lib, request, seed)
    return source


@pytest.mark.usefixtures("lenient_notes")
def test_accepted_notes_are_recorded_and_shown() -> None:
    lib = library()
    request = _request(_first())
    record = propose_variations(_noted_client(lib, request, SEED), lib, request)
    assert record.source == "llm"
    assert {t.key for t in record.texts} == {v.key() for v in record.accepted}
    assert all(t.note_zh == NOTE and t.name_zh is None for t in record.texts)
    source = _source(naming=False, notes=True)
    offer = make_offer(lib, request, source)
    proposed = {v.key() for v in record.accepted}
    for option in offer.options:
        want = NOTE if option.variation.key() in proposed else None
        assert option.variation.note_zh == want
    # 小變化不改名：名稱照舊
    assert all(o.skill.name_zh == lib.skills[FIRE_BOLT].name_zh for o in offer.options)


def _big_names(offer: FlashOffer) -> list[str]:
    return [o.skill.name_zh for o in offer.options if o.variation.source != "minor"]


def test_major_and_transform_options_are_named_and_replay_reads_the_record() -> None:
    lib = library()
    request = _request(_major())
    plain = make_offer(lib, request, _source(naming=False))
    source = _source(naming=True)
    named = make_offer(lib, request, source)
    assert [o.variation.key() for o in named.options] == [o.variation.key() for o in plain.options]
    (record,) = source.records
    by_template = {n.template: n.source for n in record.names}
    # Mock 命名的敘事沒寫到橋接加上的效果（4-L11），那一項退回組合式名稱；其餘都有名稱
    assert by_template["to_passive_on_hit"] == "llm"
    assert list(by_template.values()).count("llm") >= 2
    for before, after in zip(plain.options, named.options, strict=True):
        if after.variation.source == "minor":
            assert after.skill == before.skill
            continue
        assert "・" in before.skill.name_zh
        if by_template[after.variation.template] == "llm":
            assert "・" not in after.skill.name_zh
            assert after.variation.name_zh == after.skill.name_zh
        else:
            assert after.skill.name_zh == before.skill.name_zh
    names = _big_names(named)
    assert len(set(names)) == len(names)  # 同一題不重名
    assert {t.name_zh for t in record.texts if t.name_zh} == {n for n in names if "・" not in n}
    # 重播：只讀紀錄（經過一輪與世界共用的紀錄型別往返），不呼叫 LLM
    stored = FlashLlmRecord.model_validate(record.model_dump(mode="json"))
    back = FlashProposalRecord.model_validate(stored.model_dump(mode="json"))
    assert make_offer(lib, request, RecordedSource([back])) == named


def test_no_texts_keep_the_record_json_unchanged() -> None:
    lib = library()
    source = _source(naming=False)
    make_offer(lib, _request(_first()), source)
    (record,) = source.records
    assert record.texts == ()
    assert "texts" not in record.model_dump(mode="json")
    stored = FlashLlmRecord.model_validate(record.model_dump(mode="json"))
    assert "texts" not in stored.model_dump(mode="json")


class _Down(LLMClient):
    def complete(self, messages: object, *, json_schema: object = None) -> str:
        raise LLMUnavailable("連不上")


def test_naming_is_skipped_when_the_model_is_down() -> None:
    lib = library()

    def never(skill: SkillDef, seed: int) -> LLMClient:
        raise AssertionError("模型連不上時不應該再命名")

    source = LlmFlashSource(_Down(), naming=never)
    offer = make_offer(lib, _request(_major()), source)
    assert offer.options
    assert all("・" in n for n in _big_names(offer))
    (record,) = source.records
    assert record.source == "template" and record.texts == ()
