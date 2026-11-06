"""6L-2：主線劇情技能的 LLM 提議（``trpg.llm.story_skill``）——元素跟著玩家的關鍵字換，名稱與描述照
取得地點的界域（雲嶺＝東方，#126），骨架與預算不變；模型關閉或驗證失敗時用內容版。全部用 Mock。"""

from __future__ import annotations

import json

import pytest

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import MockLLMClient
from trpg.llm.errors import LLMUnavailable
from trpg.llm.prompts.story import STORY_PROMPT_VERSION, build_story_messages
from trpg.llm.story_skill import StorySkillRequest, mock_story_proposer, propose_story_skill
from trpg.roguelite.offers import as_complete, at_run_tier
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.story_theme import damage_elements, retheme, story_elements


@pytest.fixture(scope="module")
def mist(library: ContentLibrary) -> SkillDef:
    base = library.world_quests.quests["cloud_ridge"].story_skill_by_id()["skill_mist_breaker"]
    return as_complete(library, at_run_tier(library, base, 1))


def _request(skill: SkillDef, elements: tuple[str, ...]) -> StorySkillRequest:
    return StorySkillRequest(
        skill=skill,
        elements=elements,
        keywords=(("ignite", 2), ("frozen", 1)),
        region="cloud_ridge",
        weapon="法杖",
    )


def test_prompt_version() -> None:
    assert STORY_PROMPT_VERSION == "story-element/1"
    messages = build_story_messages({"options": [{"id": "fire"}]})
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "<request>" in messages[1]["content"]


def test_story_elements_follow_keywords(library: ContentLibrary) -> None:
    assert story_elements(library, {"ignite": 2, "frozen": 1})[:2] == ("fire", "ice")
    assert story_elements(library, {"frozen": 3, "ignite": 1})[0] == "ice"
    assert story_elements(library, {}) == ()


def test_retheme_keeps_skeleton_and_budget(library: ContentLibrary, mist: SkillDef) -> None:
    fire = retheme(library, mist, "fire")
    assert fire is not None
    assert damage_elements(fire) == ("fire",)
    assert "fire" in fire.tags
    assert fire.skeleton == mist.skeleton and fire.shape == mist.shape and fire.cost == mist.cost
    assert skill_budget(fire, library).total == skill_budget(mist, library).total
    assert retheme(library, mist, "holy") is None  # 元素相同
    assert retheme(library, mist, "plasma") is None  # 不是元素


def test_llm_picks_element_and_names_in_region_style(
    library: ContentLibrary, mist: SkillDef
) -> None:
    """驗收 3：元素換成玩家關鍵字的元素；命名的 prompt 帶雲嶺（東方）的風格。"""
    elements = ("fire", "ice")
    picker = MockLLMClient([json.dumps({"element": "fire"})])
    themed = retheme(library, mist, "fire")
    assert themed is not None
    naming = mock_naming_client(library, themed, 7)
    made = propose_story_skill(picker, library, _request(mist, elements), naming=naming)
    assert made.source == "llm" and made.element == "fire"
    assert made.name_zh and made.concept and made.cast_flavor
    assert "火焰" in picker.calls[0][1]["content"] and "點燃" in picker.calls[0][1]["content"]
    naming_prompt = naming.calls[0][1]["content"]
    assert "雲嶺" in naming_prompt and "東方山城" in naming_prompt  # #126：取得地點的界域
    assert made.prompt_version.startswith("story-element/1+skill-naming/")


def test_model_off_falls_back(library: ContentLibrary, mist: SkillDef) -> None:
    """驗收 2：模型關閉時用內容版。"""
    off = MockLLMClient([LLMUnavailable("關閉")])
    made = propose_story_skill(off, library, _request(mist, ("fire",)))
    assert made.source == "content" and "llm.unavailable" in made.codes


def test_invalid_element_falls_back(library: ContentLibrary, mist: SkillDef) -> None:
    """驗證失敗（一直挑選單外的元素）：重試用盡後用內容版。"""
    bad = MockLLMClient([json.dumps({"element": "shadow"})] * 3)
    made = propose_story_skill(bad, library, _request(mist, ("fire", "ice")))
    assert made.source == "content"
    assert made.codes.count("story.element_not_offered") == 3
    assert len(bad.calls) == 3
    assert "<errors>" in bad.calls[1][1]["content"]


def test_no_element_menu_still_renames(library: ContentLibrary, mist: SkillDef) -> None:
    """玩家沒有對得到元素的關鍵字：元素不換，名稱與描述照樣請 LLM（照界域風格）。"""
    naming = mock_naming_client(library, mist, 3)
    picker = MockLLMClient([])
    made = propose_story_skill(picker, library, _request(mist, ()), naming=naming)
    assert made.source == "llm" and made.element is None
    assert picker.calls == []


def test_mock_proposer_is_deterministic(library: ContentLibrary, mist: SkillDef) -> None:
    propose = mock_story_proposer(library)
    first = propose(_request(mist, ("ice", "shadow")))
    again = propose(_request(mist, ("ice", "shadow")))
    assert (first.element, first.name_zh, first.concept) == (
        again.element,
        again.name_zh,
        again.concept,
    )
    assert first.source == "llm" and first.element == "ice"
