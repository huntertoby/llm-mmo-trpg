"""說書人敘述的 schema 與降級模板（Phase 5B-3；``docs/phases/Phase5計畫.md`` 15.2、15.7）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import load_library
from trpg.content.world_narration import (
    StoryAllowed,
    StoryTemplates,
    StoryText,
    allowed_problems,
    fill_template,
    load_story_templates,
    sentence_count,
    story_problems,
)
from trpg.shared.errors import ContentError

TEMPLATES: dict[str, Any] = {
    "tones": {"cloud_ridge": "古風"},
    "event_text": "在{location}，{who}擋在你面前。",
    "event_more": "{who}想要{want}。擋在中間的是{obstacle}。",
    "event_more_no_obstacle": "{who}想要{want}。",
    "situation_text": "你打算{approach}。",
    "situation_more": "賭上的是{stakes}。",
    "outcome_text": {"success": "成了。", "partial": "一半。", "failure": "沒成。"},
    "chat_text": "{name}沒有多說。",
}


def test_cloud_ridge_templates_load() -> None:
    library = load_library()
    story = library.world_event_content.story
    assert story is not None
    assert "cloud_ridge" in story.tones
    assert set(story.outcome_text) == {"success", "partial", "failure"}
    assert any(p.name == "narration.yaml" for p, _ in library.files)


def test_region_tones_6l1() -> None:
    """6L-1 C2～C4（#127）：主城中性奇幻；雲嶺只有青霧觀修士用文言；另外三區先放語氣。"""
    story = load_library().world_event_content.story
    assert story is not None
    assert set(story.tones) == {
        "arcane_hub",
        "ashen_waste",
        "capital",
        "cloud_ridge",
        "crystal_crown",
        "frost_tide",
    }
    assert story.tones["capital"].startswith("中性奇幻城邦")
    assert "青霧觀" in story.tones["cloud_ridge"]
    assert "古風" not in story.tones["cloud_ridge"]


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"event_text": "{who}和{gold}"}, "不認得的佔位符：gold"),
        ({"chat_text": "{who}沒說話"}, "chat_text 有不認得的佔位符：who"),
        ({"outcome_text": {"success": "成了。"}}, "outcome_text 缺少"),
        ({"situation_text": "{approach"}, "格式錯誤"),
        ({"tones": {"cloud_ridge": " "}}, "不可空白"),
    ],
)
def test_bad_templates_rejected(updates: dict[str, Any], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        StoryTemplates.model_validate({**TEMPLATES, **updates})


def test_tones_region_must_exist(tmp_path: Path) -> None:
    path = tmp_path / "narration.yaml"
    path.write_text(
        "tones: {nowhere: 古風}\nevent_text: a\nevent_more: b\nevent_more_no_obstacle: c\n"
        "situation_text: d\noutcome_text: {success: e, partial: f, failure: g}\nchat_text: h\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="nowhere"):
        load_story_templates(path, regions=("cloud_ridge",))
    assert load_story_templates(path, regions=("cloud_ridge", "nowhere")).tones


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("", 0),
        ("霧很濃", 1),
        ("霧很濃。", 1),
        ("霧很濃。風停了！", 2),
        ("他說：「走吧！」你跟上。", 2),
        ("一。二。三。四", 4),
        ("真的嗎？？是的", 2),
    ],
)
def test_sentence_count(text: str, count: int) -> None:
    assert sentence_count(text) == count


def test_story_text_limits() -> None:
    StoryText(text_zh="一。二。三。")
    with pytest.raises(ValidationError, match="最多 3 句"):
        StoryText(text_zh="一。二。三。四。")
    with pytest.raises(ValidationError):
        StoryText(text_zh="長" * 151)
    with pytest.raises(ValidationError):
        StoryText(text_zh="  ")
    with pytest.raises(ValidationError, match="不可重複"):
        StoryText(text_zh="好。", npcs=("granny_du", "granny_du"))
    with pytest.raises(ValidationError):
        StoryText(text_zh="好。", npcs=("a", "b", "c", "d", "e"))
    with pytest.raises(ValidationError, match="ID 格式"):
        StoryText(text_zh="好。", threads=("Bad ID",))
    with pytest.raises(ValidationError):
        StoryText.model_validate({"text_zh": "好。", "reward": {"xp": 100}})
    with pytest.raises(ValidationError):
        StoryText(text_zh="好。", actor_zh="長" * 25)


def test_story_problems() -> None:
    assert story_problems("event", StoryText(text_zh="好。"))  # 缺骨架、角色、動機
    ok = StoryText(skeleton="gang_toll", actor_zh="哨兵", motive_zh="收錢", text_zh="好。")
    assert story_problems("event", ok) == []
    assert story_problems("chat", ok)  # 聊天不可挑骨架
    assert story_problems("chat", StoryText(text_zh="好。")) == []


def test_allowed_problems() -> None:
    allowed = StoryAllowed(
        skeletons=("gang_toll",),
        npcs=("granny_du",),
        skeleton_npcs={"gang_toll": ("scarface",)},
        locations=("mist_ferry",),
        threads=("peddler_owes_you",),
        forbidden=("丹爐洞",),
    )
    good = StoryText(
        skeleton="gang_toll",
        actor_zh="哨兵",
        motive_zh="收錢",
        text_zh="好。",
        npcs=("granny_du", "scarface"),
        locations=("mist_ferry",),
        threads=("peddler_owes_you",),
    )
    assert allowed_problems("event", good, allowed) == []
    assert allowed.all_npcs() == ("granny_du", "scarface")
    bad = good.model_copy(update={"skeleton": "bear_den", "more_zh": "丹爐洞"})
    problems = allowed_problems("event", bad, allowed)
    assert any("候選" in p for p in problems)
    assert any("scarface" in p for p in problems)  # 換了骨架，那個骨架的 NPC 不再允許
    assert any("丹爐洞" in p for p in problems)


def test_fill_template() -> None:
    assert fill_template("{who}來了。", {"who": "行商"}, limit=10) == "行商來了。"
    assert fill_template("{who}{want}", {"who": "行商"}, limit=10) == "行商"
    assert fill_template("{who}", {"who": "長" * 20}, limit=5) == "長" * 5
