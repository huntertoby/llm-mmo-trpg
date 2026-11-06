"""稱謂中性的真模型煙霧測試（6R-2b；09 9.6.10 #137）。預設不跑，用 ``-m llm`` 手動執行::

    TRPG_LLM_CONFIG=config/llm.local.toml uv run pytest -q tests/llm -m llm -n 0 --timeout=900

說書人 event／chat 各 2 題、情境判定 2 題，主角叫「青禾」。斷言：

- 一定是模型的輸出（``source == "llm"``，不是降級模板）；情境判定的提議通過既有 pydantic 驗證與
  靜態檢查（``source == "llm"`` 就代表通過）。
- 說書人的輸出有稱呼到主角：名字、該 NPC／該區的稱謂，或對玩家說話的「你」（系統指令要求「對玩家
  說話用『你』」，旁白直接對玩家說，所以「你」也算）。
- 不用「他」「她」指稱主角。判斷法（比「完全不含他／她」準，因為事件裡的行商、NPC 本來就可以用
  他／她）：先拿掉不是單數人稱的詞（其他、他人、他們、她們、其它…），剩下的「他」「她」所在的句子
  （以。！？…切）如果也提到主角的名字或稱謂，就算指稱主角（失敗）；只提到 NPC 的句子不算。
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import replace

import pytest

from tests.llm.test_situation_propose import _request as situation_request
from tests.narrative.test_storyteller import _npc, _skeleton, chat_request, event_request
from trpg.content.library import ContentLibrary
from trpg.content.world_address import address_for
from trpg.content.world_narration import StoryAllowed
from trpg.llm import OpenAICompatClient
from trpg.llm.config import load_llm_config
from trpg.llm.situation import propose_situation
from trpg.narrative.storyteller import StoryRequest, tell_story

pytestmark = pytest.mark.llm

NAME = "青禾"
_NOT_SINGULAR = ("其他", "其它", "他人", "他們", "她們", "他鄉", "他處", "他日", "吉他", "他者")
_SENTENCE = re.compile(r"[^。！？…\n]+")


@pytest.fixture(scope="module")
def client() -> Iterator[OpenAICompatClient]:
    real = OpenAICompatClient(load_llm_config())
    try:
        yield real
    finally:
        real.close()


def pronoun_problems(text: str, refs: tuple[str, ...]) -> list[str]:
    """``text`` 裡用「他」「她」指稱主角的句子（``refs``＝主角的名字與稱謂）。"""
    out = []
    for sentence in _SENTENCE.findall(text):
        cleaned = sentence
        for word in _NOT_SINGULAR:
            cleaned = cleaned.replace(word, "")
        if ("他" in cleaned or "她" in cleaned) and any(r and r in sentence for r in refs):
            out.append(sentence)
    return out


def test_pronoun_rule_examples() -> None:
    refs = (NAME, "這位")
    assert pronoun_problems("青禾點點頭，她轉身離開。", refs)
    assert pronoun_problems("行商看著青禾，說他不該來。", refs)
    assert not pronoun_problems("行商抱著腿，他的傷口還在滲血。青禾蹲下來。", refs)
    assert not pronoun_problems("青禾和其他旅人一起等船。", refs)


def _check_story(client: OpenAICompatClient, request: StoryRequest, refs: tuple[str, ...]) -> str:
    outcome = tell_story(client, request)
    assert outcome.source == "llm", outcome.errors
    text = outcome.story.text_zh + outcome.story.more_zh
    assert any(r in text for r in (*refs, "你")), f"沒有稱呼到主角：{text}"
    assert not pronoun_problems(text, refs), f"用他／她指稱主角：{text}"
    return text


@pytest.mark.parametrize(
    ("default", "weather", "day_phase"),
    [("lost_acolyte", "fog", "day"), ("gang_toll", "rain", "night")],
)
def test_event_story(
    library: ContentLibrary,
    client: OpenAICompatClient,
    default: str,
    weather: str,
    day_phase: str,
) -> None:
    address = address_for(library.world_address, "cloud_ridge", "", NAME)
    request = event_request(
        library,
        default_skeleton=default,
        weather=weather,
        day_phase=day_phase,
        player_name=NAME,
        player_address=address,
    )
    _check_story(client, request, (NAME, address))


@pytest.mark.parametrize(
    ("npc", "text"),
    [
        ("granny_du", "婆婆，最近渡口有什麼怪事嗎？"),
        ("daoist_qingya", "道長，北坡的霧狼是怎麼回事？我該怎麼走比較安全？"),
    ],
)
def test_chat_story(
    library: ContentLibrary, client: OpenAICompatClient, npc: str, text: str
) -> None:
    card = _npc(library, npc)
    address = address_for(library.world_address, "cloud_ridge", card.address_zh, NAME)
    base = chat_request(library, text)
    request = replace(
        base,
        npcs=(card,),
        allowed=StoryAllowed(npcs=(npc,), locations=base.allowed.locations),
        player_name=NAME,
        player_address=address_for(library.world_address, "cloud_ridge", "", NAME),
        npc_address={npc: address},
    )
    _check_story(client, request, (NAME, address))


@pytest.mark.parametrize(
    "answer", ["我沿著狼的足跡反方向走", "我先問行商狼群從哪邊來，再帶他繞開那一邊"]
)
def test_situation_proposal(
    library: ContentLibrary, client: OpenAICompatClient, answer: str
) -> None:
    address = address_for(library.world_address, "cloud_ridge", "", NAME)
    request = replace(situation_request(library, answer), player_name=NAME, player_address=address)
    outcome = propose_situation(client, request)
    assert outcome.source == "llm", outcome.errors


def test_skeleton_fixture_exists(library: ContentLibrary) -> None:
    assert _skeleton(library, "gang_toll").id == "gang_toll"
