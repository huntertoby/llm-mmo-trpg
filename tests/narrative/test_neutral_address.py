"""稱謂一律中性（Phase 6R-2，#137；09 9.6.10）：

- ``address.yaml``＋人設卡 ``address_zh`` 決定 NPC 怎麼稱呼玩家（雲嶺「這位」、修士「施主」、
  荒原「你這傢伙」、主城「旅人」、長輩叫名字）。
- 說書人與情境判定的資料區帶 ``<player>``（名字與稱謂），系統指令寫明不指定性別、不用他／她。
- 降級模板的 ``{name}``／``{address}`` 由引擎代入（模型關閉時一樣正確）。
"""

from __future__ import annotations

import json
import re
from dataclasses import replace

import pytest

from tests.narrative.test_storyteller import chat_request, event_request
from trpg.content.library import ContentLibrary
from trpg.content.world_address import AddressRules, address_for
from trpg.content.world_events import NpcCardDef
from trpg.content.world_narration import StoryTemplates
from trpg.llm import MockLLMClient
from trpg.llm.prompts.storyteller import STORY_STYLE
from trpg.narrative.storyteller import fallback_story, tell_story

RULE = "不要替玩家角色指定性別，也不要用「他」「她」稱呼玩家角色"


def _card(library: ContentLibrary, region: str, npc: str) -> NpcCardDef:
    return library.world_event_content.npcs[region].npc_by_id()[npc]


@pytest.mark.parametrize(
    ("region", "npc", "expected"),
    [
        ("cloud_ridge", None, "這位"),
        ("cloud_ridge", "daoist_qingya", "施主"),
        ("cloud_ridge", "acolyte_xiaolian", "施主"),
        ("cloud_ridge", "granny_du", "小美"),
        ("cloud_ridge", "hunter_ayue", "這位"),
        ("ashen_waste", None, "你這傢伙"),
        ("ashen_waste", "smith_lu", "小美"),
        ("capital", None, "旅人"),
        ("frost_tide", None, "小美"),  # 設計文件沒寫的區：叫名字
    ],
)
def test_address_table(
    library: ContentLibrary, region: str, npc: str | None, expected: str
) -> None:
    card = "" if npc is None else _card(library, region, npc).address_zh
    assert address_for(library.world_address, region, card, "小美") == expected


def test_address_without_file_uses_name() -> None:
    assert address_for(None, "cloud_ridge", "", "阿霧") == "阿霧"


def test_address_rejects_unknown_placeholder() -> None:
    with pytest.raises(ValueError, match="佔位符"):
        AddressRules.model_validate({"regions": {"capital": "{gender}旅人"}})


def test_story_prompt_has_player_block_and_rule(library: ContentLibrary) -> None:
    client = MockLLMClient(["{}"])
    request = chat_request(library, "你好")
    request = replace(
        request, player_name="小美", player_address="小美", npc_address={"granny_du": "小美"}
    )
    tell_story(client, request, attempts=1)
    system, user = client.calls[0][0]["content"], client.calls[0][1]["content"]
    assert RULE in system and RULE in STORY_STYLE
    block = re.search(r"<player>\n(.*)\n</player>", user)
    assert block is not None and json.loads(block.group(1)) == {"name": "小美", "address": "小美"}
    npcs = json.loads(re.search(r"<npcs>\n(.*)\n</npcs>", user).group(1))  # type: ignore[union-attr]
    assert npcs[0]["address"] == "小美"
    assert "gender" not in user and "性別" not in user


def test_fallback_templates_fill_name_and_address(library: ContentLibrary) -> None:
    story = library.world_event_content.story
    assert story is not None
    templates = StoryTemplates.model_validate(
        {
            **story.model_dump(),
            "event_text": "{who}擋住了{name}。",
            "chat_text": "{npc}對{address}點點頭。",
        }
    )
    event = event_request(library, player_name="小美", player_address="這位")
    assert fallback_story(event, templates).text_zh.endswith("擋住了小美。")
    chat = chat_request(library)
    chat = replace(chat, player_name="小美", player_address="小美")
    assert fallback_story(chat, templates).text_zh == "渡婆婆對小美點點頭。"


def test_bundled_chat_template_uses_npc_name(library: ContentLibrary) -> None:
    story = library.world_event_content.story
    assert story is not None and "{npc}" in story.chat_text
    assert fallback_story(chat_request(library), story).text_zh.startswith("渡婆婆")
