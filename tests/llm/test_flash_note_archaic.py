"""6L-2b：閃現變化的 ``note_zh`` 也做古風詞檢查（規則照 6L-1 定稿：中性區 27 詞；「施主」任何區都
不行；「訣」只限雲嶺）。區域是原技能取得地點的界域（``FlashRequest.region``）。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from trpg.content.library import ContentLibrary
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
def lib(library: ContentLibrary) -> ContentLibrary:
    return library


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


def test_archaic_note_is_dropped_without_a_retry(lib: ContentLibrary) -> None:
    """LF-2：古風詞不合格的 note 只丟說明（``flash.note_dropped.archaic``），變化第一次就收下、
    不為說明重試。"""
    request = _request(lib, None)
    bad = json.dumps({"variations": [_item("濕透的地面運起真氣。")]}, ensure_ascii=False)
    records: list[Any] = []
    client = MockLLMClient([bad] * 3)
    source = LlmFlashSource(client, max_attempts=3, sink=records.append)
    make_offer(lib, request, source)
    record = records[-1]
    assert isinstance(record, FlashProposalRecord)
    assert "flash.note_dropped.archaic" in record.codes[0]
    assert WET in record.accepted and record.texts == ()
    # 重試只為還缺的數量（結構問題），錯誤回饋裡沒有說明的錯誤
    assert all("note_dropped" not in call[1]["content"] for call in client.calls[1:])
