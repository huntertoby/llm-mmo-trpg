"""Phase 4-L11：敘事對齊效果（詞表一致性檢查、閃現加上的效果要提到）與世界觀詞用量。

全部用 ``MockLLMClient``，不需網路與金鑰。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.effect_words import load_effect_words
from trpg.content.skills import EffectSpec, SkillDef
from trpg.content.world import WorldTermRules, load_world_style
from trpg.llm import MockLLMClient
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.consistency import (
    added_facts,
    check_added,
    check_mentions,
    check_world_terms,
    effect_phrases,
    skill_facts,
    world_term_count,
)
from trpg.llm.flash_propose import LlmFlashSource, name_offer, note_checker
from trpg.llm.naming import CONSISTENCY_SUFFIXES, NamingText, check_naming, name_skill
from trpg.llm.prompts.naming import build_naming_messages
from trpg.skillgen.flash_offer import FlashRequest, make_offer, skill_before, try_variation
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage

LIB = library()
WORDS = load_effect_words()
RULES = load_world_style().naming
FIRE_ARROW = LIB.skills["skill_fire_arrow"]


def _reply(
    name: str = "赤羽流矢", concept: str = "火焰凝成箭矢。", flavor: str = "弦響火起。"
) -> str:
    return json.dumps(
        {"name_zh": name, "concept": concept, "cast_flavor": flavor}, ensure_ascii=False
    )


def _with_burning(skill: SkillDef) -> SkillDef:
    burn = EffectSpec.model_validate({"type": "apply_status", "status": "burning", "duration": 1})
    return skill.model_copy(update={"effects": (*skill.effects, burn)})


# -- 詞表 ---------------------------------------------------------------------


def test_vocabulary_refers_to_existing_content() -> None:
    rules = LIB.ruleset
    statuses = {s.id for s in rules.statuses.statuses}
    primitives = {p.id for p in rules.primitives.primitives} | {"knock_prone", "push_aside"}
    elements = {e.id for e in LIB.elements.elements}
    surfaces = {s.id for s in rules.surfaces.surfaces}
    units = set(rules.summons.by_id())
    for group in WORDS.groups:
        m = group.matches
        assert set(m.statuses) <= statuses, group.id
        assert set(m.primitives) <= primitives, group.id
        assert set(m.elements) <= elements, group.id
        assert set(m.surfaces) <= surfaces, group.id
        assert set(m.units) <= units, group.id


def test_effect_summary_never_contradicts_itself() -> None:
    """效果摘要（給 prompt 的 effect_summary）本身不會被一致性檢查擋下。"""
    for skill in LIB.skills.values():
        facts = skill_facts(LIB, skill)
        for phrase in effect_phrases(LIB, skill):
            assert check_mentions("x", phrase, facts, WORDS) == [], (skill.id, phrase)


def test_facts_cover_status_element_surface_and_summon() -> None:
    facts = skill_facts(LIB, LIB.skills["skill_summon_vine"])
    assert "primitive:summon" in facts and "unit:summon_vine" in facts
    assert {"element:fire", "primitive:damage"} <= skill_facts(LIB, FIRE_ARROW)
    assert "status:burning" in skill_facts(LIB, _with_burning(FIRE_ARROW))


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        ("火焰凝成的箭。", True),
        ("藤蔓破地而出。", False),  # 4-L9 樣本「青藤十字印」：毒傷害卻寫藤蔓
        ("寒霜覆上箭鏃。", False),
        ("召喚一道火光。", False),
        ("敵人被擊退倒地。", False),
        ("怒火化成一箭。", True),  # ignore：怒火不算火
    ],
)
def test_mentions_must_exist_in_effects(text: str, ok: bool) -> None:
    errors = check_mentions("concept", text, skill_facts(LIB, FIRE_ARROW), WORDS)
    assert (errors == []) is ok
    if not ok:
        assert errors[0].code == "concept.effect_mismatch" and "「" in errors[0].message


def test_added_effects_must_be_mentioned() -> None:
    after = _with_burning(FIRE_ARROW)
    added = added_facts(LIB, FIRE_ARROW, after)
    assert added == {"status:burning", "primitive:apply_status"}
    missing = check_added(["一箭射穿。"], added, WORDS, code="narrative.missing_added")
    assert missing and missing[0].code == "narrative.missing_added"
    assert check_added(["一箭燃起烈焰。"], added, WORDS, code="x") == []


# -- 世界觀詞 -----------------------------------------------------------------


def test_world_term_count_is_longest_first_and_counts_repeats() -> None:
    terms = RULES.world_terms.terms
    assert world_term_count("源晶的頻率", terms) == 2
    assert world_term_count("晶頻率", terms) == 1  # 「晶頻」先吃掉，剩「率」
    assert world_term_count("碎界碎界", terms) == 2
    assert world_term_count("火焰箭矢", terms) == 0


@pytest.mark.parametrize(
    ("name", "texts", "code"),
    [
        ("源晶護環", {}, "name_zh.world_prefix"),
        ("晶頻護環", {}, "name_zh.world_prefix"),
        ("裂頻斬", {}, "name_zh.world_prefix"),  # 前 2 字有「頻」
        ("寒光源晶碎界", {}, "name_zh.world_terms"),
        (None, {"concept": "源晶碎片的頻率凝成護盾。"}, "concept.world_terms"),
        (None, {"cast_flavor": "碎界碎界。"}, "cast_flavor.world_terms"),
    ],
)
def test_world_term_limits(name: str | None, texts: dict[str, str], code: str) -> None:
    codes = {e.code for e in check_world_terms(name, texts, RULES.world_terms)}
    assert code in codes


def test_world_term_limits_allow_one_term_away_from_the_head() -> None:
    assert check_world_terms("護環源晶", {"concept": "源晶碎片凝成護盾。"}, RULES.world_terms) == []
    assert check_world_terms("源晶", {}, WorldTermRules()) == []  # 沒設定＝不檢查


def test_check_naming_reports_world_terms() -> None:
    text = NamingText(name_zh="晶頻斬", concept="源晶的頻率。", cast_flavor="好。")
    codes = {e.code for e in check_naming(text, RULES)}
    assert {"name_zh.world_prefix", "concept.world_terms"} <= codes


# -- 命名：重試與退回 ---------------------------------------------------------


def test_mismatch_is_retried_with_feedback_and_counted() -> None:
    client = MockLLMClient([_reply(concept="藤蔓纏繞的火箭。"), _reply()])
    outcome = name_skill(client, LIB, FIRE_ARROW)
    assert outcome.source == "llm" and outcome.attempts == 2
    assert "concept.effect_mismatch" in outcome.codes and outcome.consistency_retries == 1
    second = client.calls[1][1]["content"]
    assert "<errors>" in second and "concept.effect_mismatch" in second


def test_world_prefix_is_retried() -> None:
    client = MockLLMClient([_reply(name="晶頻火矢"), _reply()])
    outcome = name_skill(client, LIB, FIRE_ARROW)
    assert outcome.source == "llm" and outcome.codes == ("name_zh.world_prefix",)


def test_exhausted_retries_fall_back_to_template_text() -> None:
    client = MockLLMClient([_reply(flavor="冰霜召喚藤蔓。")] * 3)
    outcome = name_skill(client, LIB, FIRE_ARROW)
    assert outcome.source == "fallback" and outcome.consistency_retries == 3
    assert outcome.text.cast_flavor == "力量依你的意志成形。"


def test_added_effect_from_flash_must_be_named() -> None:
    after = _with_burning(FIRE_ARROW)
    client = MockLLMClient([_reply(concept="箭矢穿透。", flavor="弦響。"), _reply()])
    outcome = name_skill(client, LIB, after, before=FIRE_ARROW)
    assert outcome.source == "llm" and outcome.codes == ("narrative.missing_added",)
    first = client.calls[0][1]["content"]
    assert "added_effects" in first and "燃燒" in first
    # 沒給變化前的技能（一般升級）：不要求提到
    plain = name_skill(MockLLMClient([_reply(concept="箭矢穿透。")]), LIB, after)
    assert plain.source == "llm"


def test_prompt_has_effect_summary_and_rules() -> None:
    from trpg.llm.naming import skill_summary  # noqa: PLC0415

    summary = skill_summary(LIB, FIRE_ARROW)
    assert summary["effect_summary"] == ["火焰傷害"]
    system = build_naming_messages(summary)[0]["content"]
    assert "只描述 effect_summary 裡有的效果" in system
    assert "added_effects" in system and "源晶" in system and "「晶」「頻」" in system


@pytest.mark.parametrize("skill_id", sorted(LIB.skills)[:60])
def test_mock_naming_client_passes_consistency(skill_id: str) -> None:
    skill = LIB.skills[skill_id]
    outcome = name_skill(mock_naming_client(LIB, skill, 3), LIB, skill)
    assert not any(c.endswith(CONSISTENCY_SUFFIXES) for c in outcome.codes), outcome.codes


# -- 閃現：note_zh 與變化名稱 -------------------------------------------------


def _flash_request() -> FlashRequest:
    state = acquire("skill_air_burst").model_copy(update={"used": True})
    return FlashRequest(LIB.skills["skill_air_burst"], state, SkillUsage(), 7)


WET = Variation(source="minor", template="keyword_imbue", category="element", keyword="wet")


def test_note_check_requires_added_effects_and_rejects_strangers() -> None:
    request = _flash_request()
    before = skill_before(LIB, request)
    option = try_variation(LIB, request, WET)
    assert option is not None and "surface:water" in added_facts(LIB, before, option.skill)
    check = note_checker(LIB, request, before)
    assert check(WET, "風裡帶著水氣，地面跟著濕透。") == []
    assert [p.code for p in check(WET, "加強這招的用法。")] == ["note_zh.missing_added"]
    codes = [p.code for p in check(WET, "濕地上燃起火焰。")]
    assert codes == ["note_zh.effect_mismatch"]
    assert [p.code for p in check(WET, "源晶頻率帶來潮濕。")] == ["note_zh.world_terms"]


def _item(note: str | None) -> dict[str, Any]:
    return {"category": "element", "template": "keyword_imbue", "keyword": "wet",
            "element": None, "shape": None, "note_zh": note}  # fmt: skip


def test_bad_note_is_rejected_and_retried() -> None:
    request = _flash_request()
    bad = json.dumps({"variations": [_item("帶來烈焰。")]}, ensure_ascii=False)
    good = json.dumps({"variations": [_item("讓地面濕透。")]}, ensure_ascii=False)
    client = MockLLMClient([bad, good, good])
    source = LlmFlashSource(client, max_attempts=3)
    make_offer(LIB, request, source)
    record = source.records[0]
    assert "flash.note_zh.effect_mismatch" in record.codes[0]
    assert any(v.template == "keyword_imbue" for v in record.accepted)
    assert "flash.note_zh.effect_mismatch" in client.calls[1][1]["content"]


def test_name_offer_passes_the_skill_before_the_flash() -> None:
    """閃現大變化命名時，名稱或敘事沒提到變化加上的效果算不一致（重試後才採用）。"""
    request = _flash_request()
    before = skill_before(LIB, request)
    option = try_variation(LIB, request, WET)
    assert option is not None
    major = option.model_copy(update={"variation": WET.model_copy(update={"source": "major"})})
    offer = make_offer(LIB, request, LlmFlashSource(MockLLMClient(["{}"] * 3)))
    offer = offer.model_copy(update={"options": (major,)})
    namer = MockLLMClient(
        [
            _reply(name="環撞", concept="旋起疾風撞開敵人。", flavor="疾風環身。"),
            _reply(name="濕風環撞", concept="疾風夾帶水氣撞開敵人。", flavor="疾風環身。"),
        ]
    )
    named, records = name_offer(offer, namer, LIB, seed=1, taken=set(), before=before)
    assert records[0].source == "llm" and records[0].consistency_retries == 1
    assert "narrative.missing_added" in records[0].codes
    assert named.options[0].skill.name_zh == "濕風環撞"
