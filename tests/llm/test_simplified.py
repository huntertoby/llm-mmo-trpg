"""Phase 4-L10a C4：敘事文字（concept／cast_flavor）的簡體字檢查。不需要網路與模型。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world import load_world_style
from trpg.llm import MockLLMClient
from trpg.llm.naming import NamingText, check_naming, name_skill
from trpg.llm.simplified import SIMPLIFIED_CHARS, simplified_chars

RULES = load_world_style().naming
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_finds_common_simplified_characters() -> None:
    assert simplified_chars("鎖定目标後發动") == ["标", "动"]
    assert simplified_chars("鎖定目標後發動") == []


@pytest.mark.parametrize("ch", ["后", "里", "干", "斗", "范", "冲", "烟", "脉", "着", "才", "云"])
def test_characters_also_used_in_traditional_are_not_listed(ch: str) -> None:
    assert ch not in SIMPLIFIED_CHARS


def test_no_false_positive_on_traditional_content(library: ContentLibrary) -> None:
    """內容庫（全部是繁體）的敘事與設計文件不會被誤判。"""
    for skill in library.skills.values():
        text = skill.name_zh + skill.narrative.concept + skill.narrative.cast_flavor
        assert simplified_chars(text) == [], skill.id
    for path in sorted((ROOT / "content").rglob("*.yaml")):
        assert simplified_chars(path.read_text(encoding="utf-8")) == [], path.name


def test_check_naming_reports_simplified_in_concept_and_flavor() -> None:
    text = NamingText(name_zh="霜脈斷章", concept="鎖定目标的寒氣。", cast_flavor="寒光一闪。")
    codes = {e.code: e.message for e in check_naming(text, RULES)}
    assert set(codes) == {"concept.simplified", "cast_flavor.simplified"}
    assert "标" in codes["concept.simplified"] and "闪" in codes["cast_flavor.simplified"]
    good = NamingText(name_zh="霜脈斷章", concept="鎖定目標的寒氣。", cast_flavor="寒光一閃。")
    assert check_naming(good, RULES) == []


def test_naming_retries_after_simplified_text(library: ContentLibrary) -> None:
    skill = library.skills["skill_fire_arrow"]
    bad = {"name_zh": "燼羽", "concept": "火焰鎖定目标。", "cast_flavor": "箭矢燃起火光。"}
    good = {**bad, "concept": "火焰鎖定目標。"}
    client = MockLLMClient(
        [json.dumps(bad, ensure_ascii=False), json.dumps(good, ensure_ascii=False)]
    )
    outcome = name_skill(client, library, skill)
    assert outcome.source == "llm" and outcome.attempts == 2
    assert outcome.codes == ("concept.simplified",)
    feedback = client.calls[1][1]["content"]
    assert "concept.simplified" in feedback
