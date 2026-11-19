"""PK-4 許願池「願望驅動」的生成函式、日誌與重播、API（07 7.6「許願池：願望驅動」）。全部用 Mock。

- 生成函式：願望 → 需求標籤（Mock：名稱有字出現在願望裡）→ 照標籤做候選、Mock 挑選器挑 3 張。
- 世界引擎經預先生成的供應者拿紀錄；日誌的 ``generated`` 帶標籤與三選一；讀回後重播不呼叫 LLM。
- API：面板多標籤清單（開關關掉時沒有）、點選標籤許願、待選三選一帶願望原文與「做不到」那一行、
  選到後角色的魔導書扉頁（``skill_wishes``）。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_wish_api_wp2 import CID, _act, _client, _put, _store, _view
from tests.api.test_world_api import _ok
from tests.engine.helpers import wish_off
from tests.world.helpers import NOON, hero, make_world
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world_pregen import WorldPregen, provider_generators, wish_generator
from trpg.content.library import ContentLibrary
from trpg.world.actions import WishAction, WishMadeEvent
from trpg.world.errors import WorldActionError
from trpg.world.generated import WishGen, using_generated
from trpg.world.growth import world_library
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_log, loads_log
from trpg.world.state import CharacterState
from trpg.world.step import new_character, world_step
from trpg.world.wish import WISH_NO_MATCH_ZH, wish_request

WISH = "想要會點燃敵人的招"
"""Mock 翻成關鍵字 ``ignite``（「點」「燃」）。"""


@pytest.fixture
def char(content_library: ContentLibrary) -> CharacterState:
    made = new_character(content_library, "alice", hero(content_library), region="cloud_ridge")
    return made.model_copy(update={"region": "capital", "location": "capital", "quest_coins": 10})


def test_generator_tags_then_picks(content_library: ContentLibrary, char: CharacterState) -> None:
    request = wish_request(content_library, make_world(), char, WISH)
    assert request.tags_mode
    gen = wish_generator(MockLlmProvider(), world_library(content_library), request)
    assert gen.tags is not None and gen.tags.keywords == ("ignite",)
    assert gen.keywords == ("ignite",)
    assert gen.source == "llm" and gen.offer is not None
    assert len(gen.offer.candidates) == 3
    assert any(t.pick == "llm" for t in gen.offer.tags)


def test_text_wish_is_logged_and_replayed_without_llm(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    pregen = WorldPregen(generators=provider_generators(MockLlmProvider()), enabled=lambda: True)
    try:
        with using_generated(pregen.supplier(content_library)) as used:
            result = world_step(content_library, make_world(), char, WishAction(text=WISH), NOON)
    finally:
        pregen.shutdown()
    after = result.char
    made = next(e for e in result.events if isinstance(e, WishMadeEvent))
    assert (made.via, made.made_by) == ("text", "llm")
    assert made.tags is not None and made.tags.keywords == ("ignite",)
    pending = after.pending_offers[0]
    assert pending.wish is not None and pending.wish.text == WISH
    (record,) = used
    assert isinstance(record, WishGen) and record.tags is not None
    entry = WorldLogEntry(
        seq=1,
        now=NOON,
        character_id=char.character_id,
        action=WishAction(text=WISH),
        generated=tuple(used),
    )
    (loaded,) = loads_log(dumps_log((entry,)))
    assert loaded == entry
    out = replay(content_library, make_world(), {char.character_id: char}, [loaded])
    assert out.characters[char.character_id] == after


def test_off_model_refuses_without_charge(
    content_library: ContentLibrary, char: CharacterState
) -> None:
    pregen = WorldPregen(generators=provider_generators(MockLlmProvider()), enabled=lambda: False)
    try:
        with (
            using_generated(pregen.supplier(content_library)),
            pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH),
        ):
            world_step(content_library, make_world(), char, WishAction(text=WISH), NOON)
    finally:
        pregen.shutdown()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.fixture
def client(content_library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(content_library, tmp_path / "saves") as c:
        _ok(c.post("/api/world/llm", json={"enabled": True}))
        _put(c)
        yield c


def test_view_has_tag_groups(client: TestClient, content_library: ContentLibrary) -> None:
    groups = _view(client)["wish"]["tag_groups"]
    assert [g["id"] for g in groups] == ["keywords", "elements", "effects", "shapes", "kinds"]
    assert [g["max"] for g in groups] == [2, 1, 2, 1, 1]
    assert [g["label_zh"] for g in groups] == ["關鍵字", "元素", "效果類型", "形狀", "種類"]
    assert len(groups[0]["items"]) == 16 and groups[0]["items"][0]["description_zh"]
    assert [i["name_zh"] for i in groups[4]["items"]] == ["主動", "被動", "反應"]


def test_tag_groups_allow_two_elements_from_tier_two(content_library: ContentLibrary) -> None:
    """WC-2（#167，07 7.6 第 1 點）：角色 2 階起元素最多 2 個；1 階照舊 1 個。"""
    from trpg.api.world_wish_view import _tag_groups  # noqa: PLC0415 — 只有這個測試用私有函式

    assert [g.max for g in _tag_groups(content_library, 1)] == [2, 1, 2, 1, 1]
    assert [g.max for g in _tag_groups(content_library, 2)] == [2, 2, 2, 1, 1]


def test_view_without_switch_has_no_tag_groups(
    content_library: ContentLibrary, tmp_path: Path
) -> None:
    with _client(wish_off(content_library), tmp_path / "saves") as c:
        _put(c)
        assert _view(c)["wish"]["tag_groups"] == []


def _pending(after: dict[str, Any]) -> dict[str, Any]:
    pending: dict[str, Any] = after["pending_offer"]
    assert pending is not None and pending["source"] == "wish"
    return pending


def test_tag_wish_shows_honest_lines(client: TestClient) -> None:
    tags = {"keywords": ["frozen"], "elements": ["fire"]}
    after = _ok(_act(client, kind="wish", keywords=[], tags=tags))
    pending = _pending(after)
    assert pending["wish_text_zh"] is None
    assert pending["wish_tags_zh"] == ["冰凍", "火焰"]
    lines = [t["wish_miss_zh"] for t in pending["offer"]["tags"]]
    assert len(lines) == 3
    assert all(line is None or line.startswith("最接近你願望的一招：") for line in lines)
    assert after["wish"]["coins"] == 6


def test_text_wish_then_take_writes_the_grimoire_page(client: TestClient) -> None:
    after = _ok(_act(client, kind="wish", text=WISH))
    pending = _pending(after)
    assert pending["wish_text_zh"] == WISH and pending["wish_tags_zh"] == ["點燃"]
    taken = _ok(_act(client, kind="offer_pick", pick=0))
    hero_view = taken["character"]
    new = next(
        c["id"]
        for c in hero_view["skills"] + hero_view["bench"]
        if c["id"] in hero_view["skill_wishes"]
    )
    assert hero_view["skill_wishes"] == {new: WISH}
    char = _store(client).character(CID)
    assert char.skill_wishes == {new: WISH}


def test_empty_tags_are_refused(client: TestClient) -> None:
    refused = _act(client, kind="wish", keywords=[], tags={})
    assert refused.status_code == 422 and "至少要選一個標籤" in refused.text
    assert _store(client).character(CID).quest_coins == 10


def test_unknown_tag_shape_is_rejected_by_the_schema(client: TestClient) -> None:
    refused = _act(client, kind="wish", keywords=[], tags={"kinds": ["stance"]})
    assert refused.status_code == 422
