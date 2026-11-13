"""Phase LF-2：減少閃現提議白白重問——數量不超過目錄、說明不合格只丟說明、本地修正、限制寫進
prompt、提議時順便取名（少一次往返）、評估統計。全部用 ``MockLLMClient``，不需網路與金鑰。"""

from __future__ import annotations

import json
from typing import Any

from tests.engine.helpers import library
from trpg.llm import MockLLMClient
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import ChatMessage
from trpg.llm.flash_propose import (
    FlashProposalStats,
    LlmFlashSource,
    name_checker,
    note_words,
    propose_variations,
)
from trpg.llm.flash_repair import normalize_name, normalize_note
from trpg.skillgen.flash_catalog import build_catalog
from trpg.skillgen.flash_offer import (
    FlashRequest,
    choose,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage

LIB = library()
FIRE_BOLT = "skill_fire_bolt"
SEED = 7


def _used(state: SkillFlash) -> SkillFlash:
    return state.model_copy(update={"used": True})


def _request(state: SkillFlash | None = None, *, seed: int = SEED, **fields: Any) -> FlashRequest:
    state = state or _used(acquire(FIRE_BOLT))
    return FlashRequest(LIB.skills[FIRE_BOLT], state, SkillUsage(), seed, **fields)


def _item(template: str, category: str, **extra: Any) -> dict[str, Any]:
    return {"category": category, "template": template, **extra}


def _text(*items: dict[str, Any]) -> str:
    return json.dumps({"variations": list(items)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 本地修正（4.3 第 1 點）
# ---------------------------------------------------------------------------


def test_fixable_mistakes_are_repaired_locally_without_a_retry() -> None:
    long_note = "蓄滿力量再出手，" + "火光" * 20 + "，一口氣燒穿敵陣。"
    items = (
        _item("range_plus", "combo", keyword="wet"),  # 類別填錯＋不用填的參數
        _item("multi_hit", "combo"),
        _item("multi_hit", "combo"),  # 重複
        _item("keyword_imbue", "element"),  # 選單只有 charged：代填
        _item(" cost_charge ", "cost", note_zh=long_note),  # 前後空白＋說明超長
    )
    client = MockLLMClient([_text(*items)] * 3)
    record = propose_variations(client, LIB, _request(), max_attempts=3)
    assert record.source == "llm" and record.attempts == 1 and len(client.calls) == 1
    assert [v.key() for v in record.accepted] == [
        Variation(source="minor", template="range_plus", category="area").key(),
        Variation(source="minor", template="multi_hit", category="combo").key(),
        Variation(
            source="minor", template="keyword_imbue", category="element", keyword="charged"
        ).key(),
        Variation(source="minor", template="cost_charge", category="cost").key(),
    ]
    assert record.rejected == ()
    assert record.codes[0] == (
        "flash.repaired.category",
        "flash.repaired.param_dropped",
        "flash.repaired.duplicate",
        "flash.repaired.param_filled",
        "flash.repaired.space",
        "flash.repaired.note_cut",
    )
    # 截到最後一個標點（逗號換成句號），截完仍過檢查才留下
    assert [t.note_zh for t in record.texts] == ["蓄滿力量再出手。"]


def test_note_normalisation() -> None:
    assert normalize_note(" 火焰更旺. ") == (
        "火焰更旺。",
        ("flash.repaired.note_space", "flash.repaired.note_width"),
    )
    assert normalize_note("多燒1回合。。") == (
        "多燒１回合。",
        ("flash.repaired.note_width", "flash.repaired.note_period"),
    )
    cut, codes = normalize_note("火焰" * 10 + "，" + "燃燒" * 20)
    assert cut == "火焰" * 10 + "。" and codes == ("flash.repaired.note_cut",)
    # 上限內沒有標點：截不了，照常交給檢查（之後丟掉）
    assert normalize_note("火" * 45) == ("火" * 45, ())
    assert normalize_name(" 赤羽·連星 ") == (
        "赤羽・連星",
        ("flash.repaired.name_space", "flash.repaired.name_width"),
    )


# ---------------------------------------------------------------------------
# 說明不合格只丟說明（4.3 第 2 點）
# ---------------------------------------------------------------------------


def test_bad_notes_are_dropped_and_only_structure_errors_are_retried() -> None:
    first = _text(
        _item("range_plus", "area", note_zh="use range_plus"),  # 英文：丟說明
        _item("multi_hit", "combo", note_zh="範圍 +1"),  # 半形空白：丟說明
        _item("beast_form", "area"),  # 不在目錄：結構錯誤
    )
    second = _text(_item("cost_charge", "cost"), _item("cost_light", "cost"))
    client = MockLLMClient([first, second])
    record = propose_variations(client, LIB, _request(), max_attempts=3)
    assert record.source == "llm" and record.attempts == 2
    assert [v.template for v in record.accepted] == [
        "range_plus",
        "multi_hit",
        "cost_charge",
        "cost_light",
    ]
    assert "flash.note_dropped.english" in record.codes[0]
    assert "flash.note_dropped.charset" in record.codes[0]
    assert "flash.unknown_template" in record.codes[0]
    assert record.rejected == ("beast_form",)
    assert record.texts == ()
    retry = client.calls[1][1]["content"]
    assert "flash.unknown_template" in retry and "note_dropped" not in retry
    assert client.schemas[1] is not None
    assert client.schemas[1]["properties"]["variations"]["maxItems"] == 2  # 只為還缺的數量


def test_good_notes_are_kept() -> None:
    request = _request()
    catalog = build_catalog(
        LIB,
        request,
        skill_before(LIB, request),
        major=False,
        applicable=lambda v: try_variation(LIB, request, v) is not None,
    )
    words = note_words(LIB, request, skill_before(LIB, request), catalog)
    charged = Variation(
        source="minor", template="keyword_imbue", category="element", keyword="charged"
    )
    word = words[charged.key()][0].split("／")[0]
    note = f"火光裡多了{word}。"
    client = MockLLMClient(
        [_text(_item("keyword_imbue", "element", keyword="charged", note_zh=note))]
    )
    record = propose_variations(client, LIB, request, max_attempts=1)
    assert [(t.key, t.note_zh) for t in record.texts] == [(charged.key(), note)]


# ---------------------------------------------------------------------------
# 數量不超過目錄（4.3 第 3 點）
# ---------------------------------------------------------------------------


def test_focused_question_asks_only_for_what_the_catalog_has() -> None:
    request = _request(category="cost")  # 火焰箭的費用類只有蓄力、輕巧兩個
    client = MockLLMClient([_text(_item("cost_charge", "cost"), _item("cost_light", "cost"))])
    record = propose_variations(client, LIB, request, max_attempts=3)
    assert record.wanted == 2 and record.source == "llm" and record.attempts == 1
    assert client.schemas[0] is not None
    assert client.schemas[0]["properties"]["variations"]["maxItems"] == 2
    request_block = client.calls[0][1]["content"].split("<request>")[1].split("</request>")[0]
    header = json.loads(request_block)
    assert header["count"] == 2
    assert header["categories"] == ["cost"]
    assert header["choices"] == {"cost_charge": 1, "cost_light": 1}


# ---------------------------------------------------------------------------
# 限制寫進 prompt（第 5 點）
# ---------------------------------------------------------------------------


def _user(messages: list[ChatMessage]) -> str:
    return messages[1]["content"]


def test_prompt_lists_choices_and_the_words_the_note_must_use() -> None:
    client = MockLLMClient([_text(_item("range_plus", "area"))])
    propose_variations(client, LIB, _request(), max_attempts=1)
    user = _user(client.calls[0])
    catalog = json.loads(user.split("<catalog>")[1].split("</catalog>")[0])
    exploit = next(r for r in catalog if r["template"] == "keyword_exploit")
    assert isinstance(exploit.get("note_words"), dict)  # 有參數：依參數列
    header = json.loads(user.split("<request>")[1].split("</request>")[0])
    assert header["choices"]["keyword_exploit"] == len(exploit["keyword"])
    assert header["choices"]["range_plus"] == 1
    system = client.calls[0][0]["content"]
    assert "note_words" in system and "name_zh" in system and "choices" in system


# ---------------------------------------------------------------------------
# 命名併進提議（第 7 點）
# ---------------------------------------------------------------------------


def _third_flash_state(seed: int) -> SkillFlash:
    state = _used(acquire(FIRE_BOLT))
    for _ in range(2):
        offer = make_offer(LIB, _request(state, seed=seed))
        state, _skill = choose(state, offer, 0)
        state = _used(state)
    return state


class _CountingNamer:
    def __init__(self) -> None:
        self.skills: list[str] = []

    def __call__(self, skill: Any, seed: int) -> MockLLMClient:
        self.skills.append(skill.id)
        return mock_naming_client(LIB, skill, seed)


def test_names_given_with_the_proposal_skip_the_naming_call() -> None:
    seed = 5  # 同 test_flash_propose 的大變化題目
    request = _request(_third_flash_state(seed), seed=seed)
    before = skill_before(LIB, request)
    catalog = build_catalog(
        LIB,
        request,
        before,
        major=True,
        applicable=lambda v: try_variation(LIB, request, v) is not None,
    )
    words = note_words(LIB, request, before, catalog)
    picked = [v for v in catalog.pool.values() if v.template in {"major_reshape", "major_extend"}]
    assert len(picked) == 2
    names = iter(["赤羽長弧", "Fire Arrow"])  # 第二個名稱不合格：丟名稱、照 LF-1 另外命名
    items = []
    for variation in picked:
        choices = words.get(variation.key(), ())
        note = (
            "火光一路延伸。"
            if not choices
            else "多了" + "、".join(c.split("／")[0] for c in choices) + "。"
        )
        items.append(
            _item(
                variation.template,
                variation.category,
                note_zh=note,
                name_zh=next(names),
                **({"keyword": variation.keyword} if variation.keyword else {}),
            )
        )
    namer = _CountingNamer()
    source = LlmFlashSource(MockLLMClient([_text(*items)] * 3), max_attempts=3, naming=namer)
    offer = make_offer(LIB, request, source)
    record = source.records[0]
    first, second = (v.key() for v in picked)
    by_key = {t.key: t for t in record.texts}
    assert by_key[first].name_zh == "赤羽長弧"
    assert second not in by_key or by_key[second].name_zh != "Fire Arrow"
    assert any(c.startswith("flash.name_dropped.") for codes in record.codes for c in codes)
    merged = [n for n in record.names if n.attempts == 0]
    assert [n.template for n in merged] == [picked[0].template]
    # 提議時取好的名稱不另呼叫命名；其他大變化與轉型照 LF-1 命名
    option = next(o for o in offer.options if o.variation.key() == first)
    assert option.skill.name_zh == "赤羽長弧"
    assert option.skill.id not in namer.skills
    assert len(namer.skills) == len([o for o in offer.options if o.variation.source != "minor"]) - 1
    stats = FlashProposalStats.of([record])
    assert stats.names_merged == 1 and stats.naming_calls >= len(namer.skills)


def test_minor_questions_ignore_names() -> None:
    client = MockLLMClient([_text(_item("range_plus", "area", name_zh="赤羽長弧"))])
    record = propose_variations(client, LIB, _request(), max_attempts=1)
    assert record.texts == ()
    assert client.schemas[0] is not None
    branches = client.schemas[0]["properties"]["variations"]["items"]["oneOf"]
    assert all("name_zh" not in b["properties"] for b in branches)


# ---------------------------------------------------------------------------
# 評估統計（第 8 點）
# ---------------------------------------------------------------------------


def test_stats_report_round_trips_dropped_notes_and_repairs() -> None:
    first = _text(
        _item("range_plus", "combo", note_zh="use it"),
        _item("multi_hit", "combo"),
        _item("multi_hit", "combo"),
        _item("cost_charge", "cost"),
        _item("cost_light", "cost"),
    )
    record = propose_variations(MockLLMClient([first]), LIB, _request(), max_attempts=1)
    stats = FlashProposalStats.of([record])
    assert stats.notes_dropped == 1 and stats.repairs == 2  # 類別、重複
    assert stats.mean_round_trips == 1.0
    lines = "\n".join(stats.summary_lines())
    assert "每題往返次數" in lines and "丟掉的說明" in lines and "本地修正" in lines


def test_merged_names_allow_at_most_one_dot_and_none_at_the_ends() -> None:
    """實測語法約束截斷的名稱（「焰息・延燒一瞬・雲嶺版・」）不採用，照 LF-1 另外命名。"""
    request = _request()
    check = name_checker(LIB, request, skill_before(LIB, request))
    variation = Variation(source="major", template="major_reshape", category="deepen")
    for bad in ("焰息・延燒一瞬・雲嶺版・", "・赤羽", "赤羽・"):
        assert "name_zh.dots" in [p.code for p in check(variation, bad, None, ())], bad
