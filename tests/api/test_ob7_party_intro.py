"""#154 預設隊友的出場（Phase OB-7）：開局只帶賽倫、加入台詞 ``WorldView.party_intro``、隊伍面板的
來歷 ``PartyMemberView.backstory_zh``。台詞與來歷讀 ``content/world/mercenaries.yaml``。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, make_world, with_rules
from trpg.api.world import WorldStore
from trpg.api.world_party_intro import intro_seen_id, party_intro
from trpg.api.world_party_view import party_view
from trpg.content.library import ContentLibrary
from trpg.world.party import ESCORT_PARTED
from trpg.world.state import CharacterState

pytestmark = pytest.mark.capital_spawn

NEW = {"name": "小隊", "seed": 7, "race": "human"}
SEREN = "merc_tiebi"
AYUE = "companion_ayue"


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> WorldStore:
    app: Any = client.app
    store = app.state.world
    assert isinstance(store, WorldStore)
    return store


def _library(client: TestClient) -> ContentLibrary:
    return _store(client).library


def _lines(library: ContentLibrary, member: str) -> list[dict[str, str]]:
    table = library.world_mercenaries
    assert table is not None
    if member == SEREN:
        assert table.escort is not None
        lines = table.escort.intro
    else:
        lines = table.companion_by_id()[member].join_lines
    return [{"speaker_zh": x.speaker_zh, "text_zh": x.text_zh} for x in lines]


def test_new_character_starts_with_seren_only(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    char = _store(client).character(view["character"]["character_id"])
    assert char.mercenaries == (SEREN,)
    assert view["party_intro"] is None  # 還在選大類：確定出發後才播


def test_seren_intro_after_departure_then_seen(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    after = _ok(client.post(url, json={"kind": "opening_class", "weapon_class": "melee"}))
    intro = after["party_intro"]
    assert intro == {
        "seen_id": intro_seen_id(SEREN),
        "member": SEREN,
        "name_zh": "賽倫",
        "lines": _lines(_library(client), SEREN),
    }
    assert [x["speaker_zh"] for x in intro["lines"]] == ["守印人", "賽倫"]
    seen = _ok(client.post(url, json={"kind": "hint_seen", "ids": [intro["seen_id"]]}))
    assert seen["party_intro"] is None


def _starter_char(client: TestClient) -> tuple[ContentLibrary, CharacterState]:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    _ok(client.post(url, json={"kind": "opening_class", "weapon_class": "melee"}))
    char = _store(client).character(cid)
    return _library(client), char.model_copy(update={"hints_seen": (intro_seen_id(SEREN),)})


def test_ayue_intro_when_he_joins(client: TestClient) -> None:
    library, char = _starter_char(client)
    assert party_intro(library, char) is None
    joined = char.model_copy(update={"companions": (AYUE,)})
    intro = party_intro(library, joined)
    assert intro is not None and intro.member == AYUE and intro.name_zh == "阿岳"
    assert [x.model_dump() for x in intro.lines] == _lines(library, AYUE)
    seen = joined.model_copy(
        update={"hints_seen": tuple(sorted({*char.hints_seen, intro.seen_id}))}
    )
    assert party_intro(library, seen) is None


def test_finished_opening_does_not_replay_intro(client: TestClient) -> None:
    library, char = _starter_char(client)
    old = char.model_copy(update={"opening": None, "hints_seen": (), "companions": (AYUE,)})
    assert party_intro(library, old) is None  # #154 第 4 點：舊角色不補播


def test_backstory_lines_for_seren_and_ayue(client: TestClient) -> None:
    library, char = _starter_char(client)
    table = library.world_mercenaries
    assert table is not None and table.escort is not None
    ayue = table.companion_by_id()[AYUE]
    with_ayue = char.model_copy(update={"companions": (AYUE,)})
    members = party_view(library, make_world(), with_ayue, in_battle=False).members
    stories = {m.mercenary or m.companion: m.backstory_zh for m in members}
    assert stories == {
        None: None,  # 主角
        SEREN: table.escort.backstory_zh,
        AYUE: ayue.backstory_zh,
    }
    # 換下過賽倫再雇回來：不是「開局帶來的那一位」，不顯示來歷
    parted = char.model_copy(update={"story_flags": (ESCORT_PARTED,)})
    members = party_view(library, make_world(), parted, in_battle=False).members
    assert [m.backstory_zh for m in members if m.mercenary == SEREN] == [None]
    old = char.model_copy(update={"opening": None})  # 舊角色：來歷照樣顯示
    members = party_view(library, make_world(), old, in_battle=False).members
    assert [m.backstory_zh for m in members if m.mercenary == SEREN] == [table.escort.backstory_zh]
