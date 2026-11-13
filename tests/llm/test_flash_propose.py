"""Phase 3W-7：閃現變化的 LLM 提議——schema 沒有數值、驗證與退回、數量與類別規則、重試、重播不呼叫、
開關、命名、統計。全部用 ``MockLLMClient``，不需網路與金鑰。"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.llm import LLMConfig, MockLLMClient
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import OpenAICompatClient
from trpg.llm.errors import LLMUnavailable
from trpg.llm.flash_eval import evaluate_flash, pick_skills
from trpg.llm.flash_propose import (
    FlashProposalRecord,
    FlashProposalStats,
    LlmFlashSource,
    RecordedSource,
    judge_items,
    mock_flash_client,
    mock_flash_source,
    name_offer,
    propose_variations,
    select_flash_source,
)
from trpg.llm.naming import DEFAULT_NAMING_ATTEMPTS
from trpg.llm.prompts.flash import (
    FLASH_PROMPT_VERSION,
    MAX_SCHEMA_BRANCHES,
    build_flash_messages,
    flash_prompt_record,
    flash_schema,
)
from trpg.skillgen.flash_catalog import build_catalog
from trpg.skillgen.flash_merge import merge_options
from trpg.skillgen.flash_offer import (
    FlashOffer,
    FlashRequest,
    UsageSource,
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


def _third_flash_state(seed: int = SEED) -> SkillFlash:
    """已閃 2 次（下一次是第 3 次大變化）。"""
    state = _used(acquire(FIRE_BOLT))
    for _ in range(2):
        offer = make_offer(LIB, _request(state, seed=seed))
        state, _skill = choose(state, offer, 0)
        state = _used(state)
    return state


def _item(template: str, category: str, **extra: Any) -> dict[str, Any]:
    return {"category": category, "template": template, "keyword": None, "element": None,
            "shape": None, "note_zh": None, **extra}  # fmt: skip


def _text(*items: dict[str, Any]) -> str:
    return json.dumps({"variations": list(items)}, ensure_ascii=False)


GOOD4 = (
    _item("range_plus", "area"),
    _item("multi_hit", "combo"),
    _item("cost_charge", "cost"),
    _item("keyword_exploit", "element", keyword="wet"),
)


def _source(*responses: str | Exception, attempts: int = 3) -> LlmFlashSource:
    client = MockLLMClient(list(responses))
    source = LlmFlashSource(client, max_attempts=attempts)
    source.mock = client  # type: ignore[attr-defined]
    return source


def _client(source: LlmFlashSource) -> MockLLMClient:
    return source.mock  # type: ignore[attr-defined,no-any-return]


def _variations(offer: FlashOffer) -> list[str]:
    return [o.variation.key() for o in offer.options]


def _schema_templates(schema: dict[str, Any]) -> list[str]:
    """schema 列出的模板（LF-2：每個模板一個 oneOf 分支，依目錄順序）。"""
    items = schema["properties"]["variations"]["items"]
    return [branch["properties"]["template"]["const"] for branch in items["oneOf"]]


# ---------------------------------------------------------------------------
# schema 與 prompt
# ---------------------------------------------------------------------------


def test_schema_has_no_numeric_fields_and_enums_come_from_the_catalog() -> None:
    request = _request()
    catalog = build_catalog(LIB, request, skill_before(LIB, request), major=False)
    schema = flash_schema(catalog, 4)
    assert schema["properties"]["variations"]["maxItems"] == 4
    branches = schema["properties"]["variations"]["items"]["oneOf"]
    assert _schema_templates(schema) == list(catalog.templates())
    for branch, entry in zip(branches, catalog.entries, strict=True):
        assert branch["additionalProperties"] is False
        props = branch["properties"]
        assert props["template"] == {"const": entry.template}
        assert props["category"] == {"const": entry.category}
        assert "name_zh" not in props  # 小變化題目不取名
        for name, node in props.items():
            kind = str(node.get("type"))
            assert "integer" not in kind and "number" not in kind, name
    # 不含轉型、形態、種族這類不是模板的東西
    assert not any(t.startswith("to_") for t in catalog.templates())


def test_schema_binds_each_template_to_its_own_parameter_menu() -> None:
    """LF-2 第 4 點：每個模板一個分支，參數只列該模板的選單（必填），沒有選單的分支沒有該欄位；
    ``oneof_as_anyof`` 開時送出的是 ``anyOf``、關時保留 ``oneOf``。"""
    request = _request()
    before = skill_before(LIB, request)
    catalog = build_catalog(LIB, request, before, major=False, applicable=_applicable(request))
    schema = flash_schema(catalog, 4)
    by_template = {
        b["properties"]["template"]["const"]: b
        for b in schema["properties"]["variations"]["items"]["oneOf"]
    }
    exploit = by_template["keyword_exploit"]
    entry = catalog.entry("keyword_exploit")
    assert entry is not None
    assert exploit["properties"]["keyword"] == {"enum": list(entry.keywords)}
    assert exploit["required"] == ["category", "template", "keyword"]
    assert "element" not in exploit["properties"] and "shape" not in exploit["properties"]
    plain = by_template["range_plus"]
    assert set(plain["properties"]) == {"category", "template", "note_zh"}
    assert plain["required"] == ["category", "template"]
    snapshot = {t: (b["required"], sorted(b["properties"])) for t, b in sorted(by_template.items())}
    assert snapshot == {
        "cost_charge": (["category", "template"], ["category", "note_zh", "template"]),
        "cost_light": (["category", "template"], ["category", "note_zh", "template"]),
        "keyword_exploit": (
            ["category", "template", "keyword"],
            ["category", "keyword", "note_zh", "template"],
        ),
        "keyword_imbue": (
            ["category", "template", "keyword"],
            ["category", "keyword", "note_zh", "template"],
        ),
        "multi_hit": (["category", "template"], ["category", "note_zh", "template"]),
        "range_plus": (["category", "template"], ["category", "note_zh", "template"]),
        "refine": (["category", "template"], ["category", "note_zh", "template"]),
    }
    anyof = OpenAICompatClient(LLMConfig(oneof_as_anyof=True))._prepare_schema(schema)
    strict = OpenAICompatClient(LLMConfig(oneof_as_anyof=False))._prepare_schema(schema)
    assert "anyOf" in anyof["properties"]["variations"]["items"]
    assert "oneOf" not in anyof["properties"]["variations"]["items"]
    assert (
        strict["properties"]["variations"]["items"] == schema["properties"]["variations"]["items"]
    )
    # 大變化題目每個分支多一個選填的 name_zh
    major = flash_schema(catalog, 4, major=True)
    for branch in major["properties"]["variations"]["items"]["oneOf"]:
        assert branch["properties"]["name_zh"]["maxLength"] == 12
        assert "name_zh" not in branch["required"]


def test_schema_falls_back_to_flat_enums_with_too_many_templates() -> None:
    request = _request()
    catalog = build_catalog(LIB, request, skill_before(LIB, request), major=False)
    many = replace(
        catalog, entries=catalog.entries * (MAX_SCHEMA_BRANCHES // len(catalog.entries) + 1)
    )
    item = flash_schema(many, 4)["properties"]["variations"]["items"]
    assert "oneOf" not in item
    assert set(item["properties"]) == {
        "category",
        "template",
        "keyword",
        "element",
        "shape",
        "note_zh",
    }


def test_prompt_is_versioned_and_data_is_escaped() -> None:
    request = _request(held_keywords={"<b>x</b>": 3})
    catalog = build_catalog(LIB, request, skill_before(LIB, request), major=False)
    messages = build_flash_messages(
        LIB, request, skill_before(LIB, request), catalog, count=4, major=False
    )
    assert [m["role"] for m in messages] == ["system", "user"]
    user = messages[1]["content"]
    for tag in ("request", "skill", "usage", "held_keywords", "catalog"):
        assert f"<{tag}>" in user
    assert "<b>" not in user and "&lt;b&gt;" in user
    assert "不要填任何數值" in messages[0]["content"]
    record = flash_prompt_record(messages)
    assert record["prompt_version"] == FLASH_PROMPT_VERSION == "flash-variation/6"
    assert user.index("<catalog>") < user.index("<request>")  # LLM-1：固定目錄在前
    assert len(record["system_hash"]) == 12


# ---------------------------------------------------------------------------
# 合格提議：數量、類別、順序
# ---------------------------------------------------------------------------


def test_good_proposal_fills_four_options_across_categories() -> None:
    source = _source(_text(*GOOD4))
    offer = make_offer(LIB, _request(), source)
    record = source.records[0]
    assert record.source == "llm" and record.attempts == 1 and record.codes == ((),)
    assert record.prompt_version == FLASH_PROMPT_VERSION
    assert record.tag == "flash/skill_fire_bolt/1/0"
    assert len(offer.options) == 4 and offer.cost == 1
    assert [o.variation.template for o in offer.options] == [v["template"] for v in GOOD4]
    assert len({o.variation.category for o in offer.options}) >= 2
    assert len(_client(source).calls) == 1


def test_focused_proposal_gives_three_in_the_category_and_costs_two() -> None:
    items = (
        _item("keyword_imbue", "element", keyword="charged"),
        _item("keyword_exploit", "element", keyword="wet"),
        _item("range_plus", "area"),  # 類別不符：被擋
    )
    source = _source(_text(*items), attempts=1)
    offer = make_offer(LIB, _request(category="element"), source)
    assert offer.cost == 2 and offer.category == "element"
    assert len(offer.options) == 3
    assert all(o.variation.category == "element" for o in offer.options)
    assert [o.variation.keyword for o in offer.options][:2] == ["charged", "wet"]
    assert source.records[0].source == "partial"
    assert "flash.category_not_available" in source.records[0].codes[0]


def test_major_flash_keeps_the_transform_guarantee() -> None:
    # BAL-10e 重挑種子：種子 7 的前兩次會選到精煉（拿掉燃燒），之後「恆久」沒有狀態可延長
    seed = 5
    state = _third_flash_state(seed)
    request = _request(state, seed=seed)
    items = (
        _item("major_intensify", "deepen", keyword="ignite"),
        _item("major_reshape", "deepen"),
        _item("major_extend", "deepen"),
        _item("major_delayed_burst", "deepen"),
    )
    source = _source(_text(*items), attempts=1)
    offer = make_offer(LIB, request, source)
    assert offer.major and len(offer.options) == 4
    assert sum(o.variation.source == "transform" for o in offer.options) == 1
    # 提議的前 3 個都在（第 4 個讓位給轉型保底）
    assert [o.variation.template for o in offer.options if o.variation.source == "major"] == [
        "major_intensify",
        "major_reshape",
        "major_extend",
    ]
    # 模型不能提議轉型：轉型由資料保底
    sneaky = _source(_text(_item("to_summon", "transform")), attempts=1)
    again = make_offer(LIB, request, sneaky)
    assert "flash.unknown_category" in sneaky.records[0].codes[0]
    assert sum(o.variation.source == "transform" for o in again.options) == 1


def test_proposals_crowded_into_one_category_still_cover_two_categories() -> None:
    items = (
        _item("keyword_imbue", "element", keyword="charged"),
        _item("keyword_exploit", "element", keyword="wet"),
        _item("keyword_exploit", "element", keyword="charged"),
        _item("keyword_exploit", "element", keyword="frozen"),
    )
    source = _source(_text(*items), attempts=1)
    offer = make_offer(LIB, _request(), source)
    assert len(offer.options) == 4
    assert len({o.variation.category for o in offer.options}) >= 2
    assert offer.options[0].variation.template == "keyword_imbue"


# ---------------------------------------------------------------------------
# 驗證與退回
# ---------------------------------------------------------------------------

BAD_ITEMS = {
    "flash.unknown_template": _item("beast_form", "area"),  # 形態原語
    "flash.template_not_available": _item("to_passive_on_hit", "area"),  # 轉型不可提議
    "flash.unknown_category": _item("beast_form", "race_orc"),  # 種族類別（模板也不在目錄）
    "flash.param_missing": _item("keyword_exploit", "element"),  # 選單有 6 個：不能代填
    "flash.param_not_offered": _item("keyword_imbue", "element", keyword="no_such_keyword"),
    "flash.extra_field": {**_item("range_plus", "area"), "damage": 30},  # 數值欄位
    "flash.schema": {"category": 1, "template": 2},
}


@pytest.mark.parametrize(("code", "bad"), sorted(BAD_ITEMS.items()))
def test_each_kind_of_bad_item_is_rejected_with_its_code(code: str, bad: dict[str, Any]) -> None:
    client = MockLLMClient([_text(bad)] * 3)
    record = propose_variations(client, LIB, _request(), max_attempts=3)
    assert record.source == "template" and record.accepted == ()
    assert record.attempts == 3 and len(client.calls) == 3
    assert all(code in codes for codes in record.codes)


def test_bad_responses_are_rejected_as_a_whole() -> None:
    for text, code in (
        ("不是 JSON", "flash.not_json"),
        ("[1, 2]", "flash.schema"),
        (json.dumps({"variations": []}), "flash.schema"),
        (json.dumps({"variations": [GOOD4[0]], "damage": 5}), "flash.extra_field"),
    ):
        client = MockLLMClient([text])
        record = propose_variations(client, LIB, _request(), max_attempts=1)
        assert code in record.codes[0], text


def test_think_tags_and_code_fences_are_cleaned() -> None:
    wrapped = "<think>想一想</think>\n```json\n" + _text(GOOD4[0]) + "\n```"
    record = propose_variations(MockLLMClient([wrapped]), LIB, _request(), max_attempts=1)
    assert [v.template for v in record.accepted] == ["range_plus"]


def test_not_applicable_variation_is_rejected_by_the_engine() -> None:
    """目錄裡有、但這招套不上（引擎真的套一次才知道）的變化被擋下：用一個假的「永遠套不上」。"""
    request = _request()
    catalog = build_catalog(LIB, request, skill_before(LIB, request), major=False)
    items = [_item("range_plus", "area"), _item("multi_hit", "combo")]
    accepted, issues = judge_items(items, catalog, LIB, lambda v: v.template != "range_plus", set())
    assert [v.template for v in accepted] == ["multi_hit"]
    assert [i.code for i in issues] == ["flash.not_applicable"]


def test_duplicates_are_dropped() -> None:
    record = propose_variations(
        MockLLMClient([_text(GOOD4[0], GOOD4[0], GOOD4[1])]), LIB, _request(), max_attempts=1
    )
    assert [v.template for v in record.accepted] == ["range_plus", "multi_hit"]
    # LF-2：重複的直接丟掉，不算錯（記修正碼）
    assert record.codes[0] == ("flash.repaired.duplicate",) and record.rejected == ()


def test_retry_accumulates_valid_items_and_gives_feedback() -> None:
    first = _text(GOOD4[0], BAD_ITEMS["flash.extra_field"], BAD_ITEMS["flash.unknown_template"])
    second = _text(GOOD4[1], GOOD4[2], GOOD4[3])
    client = MockLLMClient([first, second])
    record = propose_variations(client, LIB, _request(), max_attempts=3)
    assert record.source == "llm" and record.attempts == 2
    assert [v.template for v in record.accepted] == [
        "range_plus", "multi_hit", "cost_charge", "keyword_exploit",
    ]  # fmt: skip
    assert record.codes[0] == ("flash.extra_field", "flash.unknown_template")
    retry = client.calls[1][1]["content"]
    assert "<errors>" in retry and "flash.extra_field" in retry
    assert "<previous_proposal>" in retry and "<already>" in retry
    assert client.schemas[1] is not None
    assert client.schemas[1]["properties"]["variations"]["maxItems"] == 3  # 只再要 3 個


def test_all_failures_fall_back_to_the_template_offer() -> None:
    baseline = make_offer(LIB, _request(), UsageSource())
    source = _source("垃圾", "垃圾", "垃圾")
    offer = make_offer(LIB, _request(), source)
    assert _variations(offer) == _variations(baseline)
    record = source.records[0]
    assert record.source == "template" and record.attempts == 3
    assert record.codes == (("flash.not_json",),) * 3


def test_unavailable_model_stops_at_once_and_falls_back() -> None:
    baseline = make_offer(LIB, _request(), UsageSource())
    source = _source(LLMUnavailable("連不上"))
    offer = make_offer(LIB, _request(), source)
    assert _variations(offer) == _variations(baseline)
    record = source.records[0]
    assert record.attempts == 1 and record.codes == (("llm.unavailable",),)
    assert record.reason is not None and "連不上" in record.reason


# ---------------------------------------------------------------------------
# 確定性、重播、開關
# ---------------------------------------------------------------------------


def test_replay_uses_the_record_and_never_calls_the_llm() -> None:
    source = _source(_text(*GOOD4))
    request = _request()
    offer = make_offer(LIB, request, source)
    record = FlashProposalRecord.model_validate_json(source.records[0].model_dump_json())
    replay = RecordedSource([record])
    again = make_offer(LIB, request, replay)
    assert again == offer
    assert len(_client(source).calls) == 1  # 重播沒有再呼叫（RecordedSource 根本沒有 client）
    # 選擇後的技能與原本一致
    state, skill = choose(request.state, offer, 0)
    state2, skill2 = choose(request.state, again, 0)
    assert (state, skill) == (state2, skill2)


def test_recorded_source_without_a_record_equals_the_template_offer() -> None:
    assert make_offer(LIB, _request(), RecordedSource([])) == make_offer(
        LIB, _request(), UsageSource()
    )


def test_mock_source_is_deterministic_and_valid() -> None:
    records: list[FlashProposalRecord] = []
    source = mock_flash_source(LIB, sink=records.append)
    first = make_offer(LIB, _request(), source)
    second = make_offer(LIB, _request(), mock_flash_source(LIB))
    assert first == second
    assert records[0].source == "llm" and records[0].attempts == 1
    assert len(first.options) == 4
    assert len({o.variation.category for o in first.options}) >= 2
    client = mock_flash_client(LIB, _request(), SEED, 2)
    assert client.complete([], json_schema=None) == client.complete([], json_schema=None)


def test_source_switch_follows_the_generate_flag() -> None:
    off = select_flash_source(LLMConfig(generate=False))
    assert type(off) is UsageSource
    on = select_flash_source(
        LLMConfig(generate=True, max_retries=2), client=MockLLMClient([_text(GOOD4[0])])
    )
    assert isinstance(on, LlmFlashSource) and on.max_attempts == 2


def test_default_source_is_unchanged_without_proposals() -> None:
    """沒有提議的來源（預設 UsageSource）出的題目與以前完全一樣。"""
    request = _request()
    assert make_offer(LIB, request) == make_offer(LIB, request, UsageSource())


def test_second_flash_after_a_pick_uses_the_new_nth_in_the_tag() -> None:
    state = _used(acquire(FIRE_BOLT))
    offer = make_offer(LIB, _request(state), mock_flash_source(LIB))
    state, _ = choose(state, offer, 0)
    source = mock_flash_source(LIB)
    make_offer(LIB, _request(_used(state)), source)
    assert source.records[0].tag == "flash/skill_fire_bolt/2/0"


# ---------------------------------------------------------------------------
# 命名（4-L7）
# ---------------------------------------------------------------------------


def _naming_client(name: str) -> MockLLMClient:
    text = {"name_zh": name, "concept": "火光凝成利刃。", "cast_flavor": "火光一閃而逝。"}
    return MockLLMClient([json.dumps(text, ensure_ascii=False)] * DEFAULT_NAMING_ATTEMPTS)


def test_major_options_are_named_and_minor_options_keep_the_prefix_name() -> None:
    state = _third_flash_state()
    offer = make_offer(LIB, _request(state), mock_flash_source(LIB))
    named, records = name_offer(
        offer,
        lambda skill, seed: _naming_client("曜光" + "斷章餘燼迴響"[: 2 + len(skill.id) % 4]),
        LIB,
        seed=SEED,
        taken=set(),
    )
    majors = [o for o in offer.options if o.variation.source != "minor"]
    assert len(records) == len(majors) and records
    for before, after in zip(offer.options, named.options, strict=True):
        assert after.variation == before.variation
        if before.variation.source == "minor":
            assert after == before
        else:
            assert (
                after.skill.name_zh.startswith("曜光")
                or after.skill.name_zh == before.skill.name_zh
            )
            assert after.skill.effects == before.skill.effects  # 只換文字
    assert "llm" in {r.source for r in records}
    assert any(o.skill.name_zh.startswith("曜光") for o in named.options)


def test_naming_failure_keeps_the_prefix_name() -> None:
    state = _third_flash_state()
    offer = make_offer(LIB, _request(state), mock_flash_source(LIB))
    named, records = name_offer(
        offer, MockLLMClient([LLMUnavailable("沒有模型")]), LIB, seed=SEED, taken=set()
    )
    assert all(r.source == "fallback" for r in records)
    for before, after in zip(offer.options, named.options, strict=True):
        assert after.skill.name_zh == before.skill.name_zh


# ---------------------------------------------------------------------------
# 統計（4-L9 評估）
# ---------------------------------------------------------------------------


def test_stats_summary_counts_pass_fallback_categories_and_templates() -> None:
    records = [
        propose_variations(MockLLMClient([_text(*GOOD4)]), LIB, _request(), max_attempts=1),
        propose_variations(MockLLMClient([_text(GOOD4[0])] * 2), LIB, _request(), max_attempts=2),
        propose_variations(MockLLMClient(["垃圾"] * 2), LIB, _request(), max_attempts=2),
    ]
    stats = FlashProposalStats.of(records, alert_permille=200)
    assert (stats.total, stats.first_pass) == (3, 1)
    assert stats.sources["llm"] == 1 and stats.sources["partial"] == 1
    assert stats.sources["template"] == 1
    assert stats.pass_permille == 333 and stats.fallback_permille == 333 and stats.alert
    assert stats.categories["area"] == 2 and stats.templates["range_plus"] == 2
    assert stats.codes["flash.not_json"] == 2
    lines = "\n".join(stats.summary_lines())
    assert "通過率" in lines and "退回率" in lines and "提醒" in lines


def test_merge_options_unit() -> None:
    class Opt:
        def __init__(self, template: str, category: str) -> None:
            self.variation = Variation(source="minor", template=template, category=category)

    proposed = [Opt("a", "x"), Opt("b", "x"), Opt("c", "x")]
    filler = [Opt("d", "y"), Opt("e", "z"), Opt("a", "x")]
    out = merge_options(proposed, filler, 4, min_categories=2)
    assert len(out) == 4 and {o.variation.category for o in out} >= {"x", "y"}
    assert out[0].variation.template == "a"
    assert merge_options([], filler, 2) == filler[:2]


def _flashable(skill_id: str) -> bool:
    request = FlashRequest(LIB.skills[skill_id], _used(acquire(skill_id)), SkillUsage(), SEED)
    return bool(make_offer(LIB, request, UsageSource()).options)


def test_evaluation_entry_runs_on_the_mock_and_reports() -> None:
    # FL-1a：蓄力不再出「只多冷卻」的選項後，殘影之誓（排序第一）一個閃現選項都沒有了，
    # 評估取前 3 招會變成兩題全退回模板；這裡只挑真的閃得出東西的招
    skills = [s for s in pick_skills(LIB, 10) if _flashable(s)][:3]
    assert len(skills) == 3
    result = evaluate_flash(
        LIB,
        mock_flash_source(LIB),
        skills,
        naming=lambda skill_id, seed: mock_naming_client(LIB, LIB.skills[skill_id], seed),
    )
    stats = result.stats
    assert stats.total == len(result.rows) >= 6
    assert stats.pass_permille > 0 and not stats.alert
    assert result.csv_lines()[0].startswith("skill,scenario")
    assert stats.name_samples


# ---------------------------------------------------------------------------
# 4-L10a F1／F2：目錄只列套得上的模板
# ---------------------------------------------------------------------------


def _applicable(request: FlashRequest) -> Any:
    return lambda v: try_variation(LIB, request, v) is not None


def _flash_skills() -> list[str]:
    return [s for s in pick_skills(LIB, 12) if s in LIB.skills]


@pytest.mark.parametrize("category", [None, "area", "element", "cost"])
def test_catalog_lists_only_applicable_variations(category: str | None) -> None:
    """套得上的篩選後：目錄的每個變化引擎都套得上，模板的參數選單只留套得上的值；指定類別時只有
    該類（F2）。"""
    dropped = 0
    for skill_id in _flash_skills():
        state = _used(acquire(skill_id))
        request = FlashRequest(LIB.skills[skill_id], state, SkillUsage(), SEED, category=category)
        before = skill_before(LIB, request)
        full = build_catalog(LIB, request, before, major=False)
        catalog = build_catalog(LIB, request, before, major=False, applicable=_applicable(request))
        applicable = {k for k, v in full.pool.items() if try_variation(LIB, request, v)}
        assert set(catalog.pool) == applicable, skill_id
        for entry in catalog.entries:
            variations = [v for v in catalog.pool.values() if v.template == entry.template]
            assert variations, entry.template
            assert set(entry.keywords) == {v.keyword for v in variations} - {None}
        assert set(catalog.categories) == {e.category for e in catalog.entries}
        if category is not None:
            assert set(catalog.categories) <= {category}
        dropped += len(full.pool) - len(catalog.pool)
    assert dropped > 0  # 篩選確實拿掉了套不上的變化


def test_unfiltered_catalog_is_unchanged() -> None:
    request = _request()
    before = skill_before(LIB, request)
    full = build_catalog(LIB, request, before, major=False)
    same = build_catalog(LIB, request, before, major=False, applicable=lambda _v: True)
    assert full.entries == same.entries and full.categories == same.categories
    assert list(full.pool) == list(same.pool)


def test_proposal_prompt_and_schema_use_the_filtered_catalog() -> None:
    """LLM 提議送出的 schema 列舉與 prompt 目錄只有套得上的模板（F1）。"""
    for skill_id in _flash_skills():
        for category in (None, "element"):
            state = _used(acquire(skill_id))
            request = FlashRequest(
                LIB.skills[skill_id], state, SkillUsage(), SEED, category=category
            )
            client = MockLLMClient(['{"variations": []}'])
            propose_variations(client, LIB, request, max_attempts=1)
            if not client.schemas:
                continue  # 目錄是空的：不呼叫模型
            schema = client.schemas[0]
            assert schema is not None
            templates = _schema_templates(schema)
            before = skill_before(LIB, request)
            full = build_catalog(LIB, request, before, major=False)
            for template in templates:
                assert any(
                    try_variation(LIB, request, v)
                    for v in full.pool.values()
                    if v.template == template
                ), (skill_id, category, template)


# ---------------------------------------------------------------------------
# BAL-10c：目錄依種子打亂（呈現順序），不影響驗證
# ---------------------------------------------------------------------------


def _full_catalog() -> Any:
    request = _request()
    return build_catalog(LIB, request, skill_before(LIB, request), major=False)


def test_shuffled_catalog_is_deterministic_per_seed_and_differs_between_seeds() -> None:
    catalog = _full_catalog()
    assert catalog.shuffled(5, "tag") == catalog.shuffled(5, "tag")  # 同種子同順序
    orders = {catalog.shuffled(s, "tag").templates() for s in range(1, 9)}
    assert len(orders) > 1  # 不同種子不同順序
    assert catalog.shuffled(5, "tag").templates() != catalog.shuffled(5, "other").templates()


def test_shuffling_changes_only_the_presentation() -> None:
    catalog = _full_catalog()
    shown = catalog.shuffled(9, "tag")
    assert shown.pool is catalog.pool
    assert set(shown.templates()) == set(catalog.templates())
    assert set(shown.categories) == set(catalog.categories)

    def params(c: Any) -> dict[str, Any]:
        return {e.template: (set(e.keywords), set(e.elements), set(e.shapes)) for e in c.entries}

    assert params(shown) == params(catalog)
    # 驗證結果不變：每個變化都解得回同一個變化
    for variation in catalog.pool.values():
        args = (
            variation.template,
            variation.keyword,
            variation.element,
            variation.shape.type if variation.shape is not None else None,
        )
        assert shown.resolve(*args) == catalog.resolve(*args)
    # schema 分支與 prompt 目錄用的是同一個順序
    assert _schema_templates(flash_schema(shown, 4)) == list(shown.templates())
    flat = flash_schema(shown, 4)
    assert flat["properties"]["variations"]["maxItems"] == 4


def _template_order(seed: int, *, shuffle: bool) -> tuple[tuple[str, ...], str]:
    request = FlashRequest(LIB.skills[FIRE_BOLT], _used(acquire(FIRE_BOLT)), SkillUsage(), seed)
    client = MockLLMClient(['{"variations": []}'])
    propose_variations(client, LIB, request, max_attempts=1, shuffle_catalog=shuffle)
    again = MockLLMClient(['{"variations": []}'])
    propose_variations(again, LIB, request, max_attempts=1, shuffle_catalog=shuffle)
    assert client.schemas == again.schemas and client.calls == again.calls
    schema = client.schemas[0]
    assert schema is not None
    block = client.calls[0][1]["content"].split("<request>")[1].split("</request>")[0]
    return tuple(_schema_templates(schema)), block


def test_catalog_order_follows_the_question_seed_by_default() -> None:
    """LLM-1A（使用者選 A）：預設回到 BAL-10c 的整份目錄打亂，不同種子不同順序、同種子相同；
    沒有 suggested_order。``shuffle_catalog=False`` 時目錄固定排序。"""
    shuffled = [_template_order(seed, shuffle=True) for seed in range(1, 7)]
    assert len({order for order, _ in shuffled}) > 1
    assert all("suggested_order" not in json.loads(block) for _, block in shuffled)
    fixed = {_template_order(seed, shuffle=False)[0] for seed in range(1, 7)}
    assert len(fixed) == 1


def test_shuffled_catalog_does_not_change_which_proposals_pass() -> None:
    """同樣的回覆，不管目錄怎麼排，都收下同一組合格的變化（四個提議都合格）。"""
    for seed in (1, 2, 3):
        request = FlashRequest(LIB.skills[FIRE_BOLT], _used(acquire(FIRE_BOLT)), SkillUsage(), seed)
        source = _source(_text(*GOOD4))
        offer = make_offer(LIB, request, source)
        assert source.records[0].source == "llm"
        assert [o.variation.template for o in offer.options] == [v["template"] for v in GOOD4]
