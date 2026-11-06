"""LLM-1：prompt 的固定內容在前、每題變動的在後，讓本機模型的 KV 前綴快取吃得到。

LLM-1A（使用者選 A）：提議與閃現的目錄恢復每題依種子打亂（多樣性優先），所以跨題的共同前綴不再
保證；仍保證同題重試、CLI（沒有 menu_seed，不打亂）與說書人跨場景的前綴。

「共同前綴」照 LM Studio 的比對方式算：``[system]`` 內容＋``[user]`` 內容串起來，從頭算起相同的
字元數 ÷ 最長的那份。只用 ``MockLLMClient``／純組裝函式，不連模型。
"""

from __future__ import annotations

import html
import json
import re
from functools import cache

from trpg.cli.llm import ProposeArgs, propose_requests
from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.llm.client import ChatMessage, MockLLMClient
from trpg.llm.flash_propose import propose_variations
from trpg.llm.prompts.flash import build_flash_messages
from trpg.llm.prompts.proposal import LOCAL_CONTEXT_TOKENS, build_proposal_prompt
from trpg.llm.prompts.storyteller import STORY_TASKS, story_system
from trpg.skillgen.flash_catalog import build_catalog
from trpg.skillgen.flash_offer import FlashRequest, skill_before, try_variation
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.proposal import ProposalError, feedback_payload
from trpg.skillgen.proposal_subset import ProposalRequest, catalog_payload
from trpg.skillgen.proposal_topic import TopicRequest, make_topic
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.usage import SkillUsage

MAX_OUTPUT_TOKENS = 1024
"""``config/llm.toml`` 的 ``max_tokens``。"""


@cache
def _lib() -> ContentLibrary:
    return default_library()


def _flat(messages: list[ChatMessage]) -> str:
    return "".join(f"[{m['role']}]\n{m['content']}\n" for m in messages)


def _common_prefix(texts: list[str]) -> int:
    """從頭算起相同的字元數（伺服器的前綴快取就是逐 token 從頭比對）。"""
    first = min(texts, key=len)
    for i, ch in enumerate(first):
        if any(t[i] != ch for t in texts):
            return i
    return len(first)


def _prefix_ratio(samples: list[list[ChatMessage]]) -> float:
    flats = [_flat(m) for m in samples]
    return _common_prefix(flats) / max(len(f) for f in flats)


def _cli_questions() -> list[ProposalRequest]:
    """``trpg llm propose --count 3 --seed 0`` 的三題（稀有度與關鍵字各不同）。"""
    return [req for req, _ in propose_requests(_lib(), ProposeArgs(count=3, seed=0))]


def test_three_cli_questions_share_the_prefix() -> None:
    """``trpg llm propose`` 沒有 menu_seed（與 LLM-1 之前相同不打亂），目錄依 ID 排序。"""
    samples = [build_proposal_prompt(_lib(), req).messages for req in _cli_questions()]
    assert _prefix_ratio(samples) >= 0.80
    # 同種類的固定全目錄與固定說明在前，題目在後
    user = samples[0][1]["content"]
    assert user.index("<guide>") < user.index("<available>") < user.index("<request>")


def test_retry_of_the_same_question_shares_the_prefix() -> None:
    req = _cli_questions()[0]
    first = build_proposal_prompt(_lib(), req)
    err = ProposalError(stage="rules", path="", code="budget.weak", message="效果總強度過弱。")
    retry = build_proposal_prompt(
        _lib(),
        req,
        previous_proposal='{"layout":"standard","effects":[{"type":"damage"}]}' * 8,
        errors=feedback_payload([err], 1, 3),
    )
    assert retry.subset == first.subset
    assert _prefix_ratio([first.messages, retry.messages]) >= 0.90


def test_menu_seed_shuffles_the_catalog_per_question() -> None:
    """LLM-1A：有 menu_seed 的題目（一輪／大世界的 ``make_topic``、skill_eval）每題打亂目錄；
    不同種子目錄順序不同，同種子相同；沒有建議清單 ``suggested``。"""
    lib = _lib()
    composable = [k.id for k in lib.keywords.keywords if k.composable][:6]
    catalogs: set[str] = set()
    seed = 100
    while len(catalogs) < 3 and seed < 200:
        topic = TopicRequest(
            tier=2,
            keywords=(composable[seed % len(composable)],),
            seed=seed,
            uses={},
            weapon_class="melee",
            region="cloud_ridge",
        )
        made = make_topic(lib, topic)
        seed += 1
        if made is None:
            continue
        user = build_proposal_prompt(lib, made[0]).messages[1]["content"]
        assert user == build_proposal_prompt(lib, made[0]).messages[1]["content"]
        assert '"suggested"' not in user
        catalogs.add(user.split("<available>")[1].split("</available>")[0])
    assert len(catalogs) == 3


def test_fixed_catalog_fits_the_local_context() -> None:
    """固定全目錄（主動技最大）＋題目＋重試回饋＋輸出要放得進本機模型的 16k 上下文。"""
    req = ProposalRequest(tier=3, rarity="epic", keywords=("ignite", "wet"))
    prompt = build_proposal_prompt(
        _lib(),
        req,
        previous_proposal='{"effects":[{"type":"damage"}]}' * 40,
        errors='{"errors":[{"path":"effects[0]","message":"錯"}]}' * 10,
    )
    assert prompt.tokens + MAX_OUTPUT_TOKENS <= LOCAL_CONTEXT_TOKENS


def _available(prompt_user: str) -> dict[str, object]:
    block = prompt_user.split("<available>\n")[1].split("\n</available>", maxsplit=1)[0]
    loaded: dict[str, object] = json.loads(html.unescape(block))
    return loaded


def test_menu_seed_only_changes_the_catalog_order() -> None:
    """打亂只影響 ``<available>`` 的呈現順序：內容與依 ID 排序的全目錄相同，只是順序不同。"""
    req = ProposalRequest(tier=2, rarity="rare", keywords=("ignite",), menu_seed=7)
    prompt = build_proposal_prompt(_lib(), req)
    shown = _available(prompt.messages[1]["content"])
    fixed = catalog_payload(_lib(), prompt.subset.kind)
    assert shown == catalog_payload(_lib(), prompt.subset.kind, order_seed=7)
    assert json.dumps(shown) != json.dumps(fixed)
    assert shown.keys() == fixed.keys()
    for key, items in fixed.items():
        if isinstance(items, list):
            other = shown[key]
            assert isinstance(other, list)
            key_of = lambda x: json.dumps(x, sort_keys=True)  # noqa: E731
            assert sorted(map(key_of, items)) == sorted(map(key_of, other))


# ---------------------------------------------------------------------------
# 閃現
# ---------------------------------------------------------------------------


def _flash_request(skill_id: str = "skill_fire_bolt") -> FlashRequest:
    state = acquire(skill_id).model_copy(update={"used": True})
    return FlashRequest(_lib().skills[skill_id], state, SkillUsage(), 7)


def test_flash_system_has_no_count_and_catalog_comes_first() -> None:
    lib = _lib()
    request = _flash_request()
    before = skill_before(lib, request)
    catalog = build_catalog(lib, request, before, major=False)
    by_count = [
        build_flash_messages(lib, request, before, catalog, count=n, major=False) for n in (4, 1)
    ]
    assert by_count[0][0] == by_count[1][0]  # system 不隨還要幾個而變
    assert not re.search(r"\d+ 個不同的變化", by_count[0][0]["content"])
    user = by_count[0][1]["content"]
    assert user.index("<catalog>") < user.index("<skill>") < user.index("<request>")
    assert '"count":4' in user.split("<request>")[1]


def test_flash_retry_shares_the_prefix() -> None:
    lib = _lib()
    request = _flash_request()
    client = MockLLMClient(
        ['{"variations": [{"category": "x", "template": "y"}]}', '{"variations": []}']
    )
    propose_variations(client, lib, request, max_attempts=2)
    assert len(client.calls) == 2
    assert _prefix_ratio([client.calls[0], client.calls[1]]) >= 0.80
    request_block = client.calls[0][1]["content"].split("<request>")[1]
    assert "suggested_order" not in request_block


def test_flash_catalog_is_shuffled_unless_disabled() -> None:
    """LLM-1A：預設整份目錄依種子打亂；``shuffle_catalog=False`` 才依 build_catalog 固定排序。"""
    lib = _lib()
    request = _flash_request()
    fixed = MockLLMClient(['{"variations": []}'])
    propose_variations(fixed, lib, request, max_attempts=1, shuffle_catalog=False)
    shuffled = MockLLMClient(['{"variations": []}'])
    propose_variations(shuffled, lib, request, max_attempts=1)
    assert fixed.schemas[0] is not None and shuffled.schemas[0] is not None
    templates = fixed.schemas[0]["properties"]["variations"]["items"]["properties"]["template"]
    # 固定順序＝build_catalog 的順序（eval_flash_diversity 量位置偏好用的同一個順序）
    before = skill_before(lib, request)
    full = build_catalog(
        lib,
        request,
        before,
        major=False,
        applicable=lambda v: try_variation(lib, request, v) is not None,
    )
    assert tuple(templates["enum"]) == full.templates()
    other = shuffled.schemas[0]["properties"]["variations"]["items"]["properties"]["template"]
    assert set(other["enum"]) == set(templates["enum"])
    assert fixed.calls[0][1] != shuffled.calls[0][1]


def test_flash_prefix_across_skills() -> None:
    """不同招之間：system＋目錄不一定相同（目錄依套得上的模板），但 system 一定相同。"""
    lib = _lib()
    systems = set()
    for sid in [s.id for s in player_skills(lib).values() if s.kind == "active"][:3]:
        client = MockLLMClient(['{"variations": []}'])
        propose_variations(client, lib, _flash_request(sid), max_attempts=1)
        if client.calls:
            systems.add(client.calls[0][0]["content"])
    assert len(systems) == 1


# ---------------------------------------------------------------------------
# 說書人
# ---------------------------------------------------------------------------


def test_story_scenes_share_the_system_prefix() -> None:
    systems = [story_system(s, world_name="碎界", summary="摘要") for s in STORY_TASKS]
    assert _common_prefix(systems) / max(len(s) for s in systems) >= 0.60
    for system in systems:
        assert system.index("安全規則") < system.index("任務：")
