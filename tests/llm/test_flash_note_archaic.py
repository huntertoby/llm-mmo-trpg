"""6L-2b：閃現變化的 ``note_zh`` 也做古風詞檢查（規則照 6L-1 定稿：中性區 27 詞；「施主」任何區都
不行；「訣」只限雲嶺）。區域是原技能取得地點的界域（``FlashRequest.region``）。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world import load_world_style
from trpg.llm import MockLLMClient
from trpg.llm.flash_propose import FlashProposalRecord, LlmFlashSource, note_checker
from trpg.llm.naming import check_archaic_text
from trpg.skillgen.flash_offer import FlashRequest, make_offer, skill_before
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage

WET = Variation(source="minor", template="keyword_imbue", category="element", keyword="wet")
GOOD = "風裡帶著水氣，地面跟著濕透。"


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return load_library()


def _request(lib: ContentLibrary, region: str | None) -> FlashRequest:
    state = acquire("skill_air_burst").model_copy(update={"used": True})
    return FlashRequest(lib.skills["skill_air_burst"], state, SkillUsage(), 7, region=region)


def _codes(lib: ContentLibrary, region: str | None, note: str) -> list[str]:
    request = _request(lib, region)
    check = note_checker(lib, request, skill_before(lib, request))
    return [p.code for p in check(WET, note)]


def test_neutral_region_rejects_all_27_terms(lib: ContentLibrary) -> None:
    rules = load_world_style().naming
    assert len(rules.archaic.terms) == 27
    for term in rules.archaic.terms:
        found = check_archaic_text("note_zh", f"地面濕透，{term}", rules, archaic_ok=False)
        assert [p.code for p in found] == ["note_zh.archaic"], term
    assert _codes(lib, None, GOOD) == []
    assert _codes(lib, "capital", "濕透的地面運起真氣。") == ["note_zh.archaic"]


def test_shizhu_is_rejected_everywhere(lib: ContentLibrary) -> None:
    for region in (None, "capital", "cloud_ridge", "ashen_waste"):
        assert "note_zh.archaic" in _codes(lib, region, "施主，地面濕透了。"), region


def test_jue_only_in_cloud_ridge(lib: ContentLibrary) -> None:
    note = "濕透的地面暗藏水訣。"
    assert _codes(lib, "cloud_ridge", note) == []
    assert _codes(lib, None, note) == ["note_zh.archaic"]
    assert _codes(lib, "ashen_waste", note) == ["note_zh.archaic"]
    # 雲嶺可以帶東方味（古風詞本身允許）
    assert _codes(lib, "cloud_ridge", "濕透的地面運起真氣。") == []


def _item(note: str) -> dict[str, Any]:
    return {"category": "element", "template": "keyword_imbue", "keyword": "wet",
            "element": None, "shape": None, "note_zh": note}  # fmt: skip


def test_archaic_note_is_retried_with_feedback(lib: ContentLibrary) -> None:
    """不合格的 note 帶錯誤碼重試（照 4-L11 的流程）；重試後合格的才用。"""
    request = _request(lib, None)
    bad = json.dumps({"variations": [_item("濕透的地面運起真氣。")]}, ensure_ascii=False)
    good = json.dumps({"variations": [_item(GOOD)]}, ensure_ascii=False)
    records: list[Any] = []
    source = LlmFlashSource(MockLLMClient([bad, good, good]), max_attempts=3, sink=records.append)
    make_offer(lib, request, source)
    record = records[-1]
    assert isinstance(record, FlashProposalRecord)
    assert "flash.note_zh.archaic" in record.codes[0]
    assert record.attempts >= 2 and WET in record.accepted  # 第二次合格才收
