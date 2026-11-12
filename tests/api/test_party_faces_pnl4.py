"""隊友加入對話框的說話者頭像（PNL-4，OB-8；``docs/art/資訊面板-移植需求.md`` 2.4 最後一列、3.5）與
隊伍面板劇情夥伴的頭像（PNL-1a 驗收可修 3）：伺服器照說話者名字對到頭像與頭像框區域，
前端不再用名字查。"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, make_world, with_rules
from trpg.api.world import WorldStore
from trpg.api.world_party_intro import intro_seen_id, party_intro
from trpg.api.world_party_view import companion_face, party_view
from trpg.api.world_range import keeper_speaker
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import CompanionDef
from trpg.world.narration import region_npcs
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


def _library(client: TestClient) -> ContentLibrary:
    app: Any = client.app
    store = app.state.world
    assert isinstance(store, WorldStore)
    return store.library


def _starter(client: TestClient) -> tuple[ContentLibrary, CharacterState, dict[str, Any]]:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    after = _ok(client.post(url, json={"kind": "opening_class", "weapon_class": "melee"}))
    app: Any = client.app
    return _library(client), app.state.world.character(cid), after


def _ayue(library: ContentLibrary) -> CompanionDef:
    table = library.world_mercenaries
    assert table is not None
    return table.companion_by_id()[AYUE]


def test_seren_intro_lines_carry_keeper_and_seren_faces(client: TestClient) -> None:
    library, _, after = _starter(client)
    lines = after["party_intro"]["lines"]
    keeper = keeper_speaker(library)
    assert keeper is not None and keeper.portrait is not None
    table = library.world_mercenaries
    assert table is not None
    seren = table.by_id()[SEREN]
    assert seren.portrait is not None
    assert [(x["speaker_zh"], x["region"]) for x in lines] == [
        ("守印人", CAPITAL_REGION),
        ("賽倫", seren.origin),  # 傭兵＝出身區（和隊伍面板、HUD 隊友小卡同一個框色）
    ]
    assert lines[0]["portrait"] == keeper.portrait.model_dump(mode="json")
    assert lines[1]["portrait"] == seren.portrait.model_dump(mode="json")


def test_ayue_join_line_carries_npc_card_face(client: TestClient) -> None:
    library, char, _ = _starter(client)
    joined = char.model_copy(update={"companions": (AYUE,), "hints_seen": (intro_seen_id(SEREN),)})
    intro = party_intro(library, joined)
    assert intro is not None and intro.member == AYUE
    card = region_npcs(library, "cloud_ridge")[_ayue(library).npc]
    assert card.portrait is not None
    assert [(x.speaker_zh, x.portrait, x.region) for x in intro.lines] == [
        ("阿岳", card.portrait, "cloud_ridge")
    ]


def test_unknown_speaker_has_no_face(client: TestClient) -> None:
    library, char, _ = _starter(client)
    ayue = _ayue(library)
    renamed = ayue.model_copy(
        update={"join_lines": (ayue.join_lines[0].model_copy(update={"speaker_zh": "路人"}),)}
    )
    table = library.world_mercenaries
    assert table is not None
    patched = dataclasses.replace(
        library, world_mercenaries=table.model_copy(update={"companions": (renamed,)})
    )
    joined = char.model_copy(update={"companions": (AYUE,), "hints_seen": (intro_seen_id(SEREN),)})
    intro = party_intro(patched, joined)
    assert intro is not None
    assert [(x.speaker_zh, x.portrait, x.region) for x in intro.lines] == [("路人", None, None)]


def test_party_member_companion_face(client: TestClient) -> None:
    library, char, _ = _starter(client)
    with_ayue = char.model_copy(update={"companions": (AYUE,)})
    members = party_view(library, make_world(), with_ayue, in_battle=False).members
    faces = {m.mercenary or m.companion: (m.portrait, m.region) for m in members}
    card = region_npcs(library, "cloud_ridge")[_ayue(library).npc]
    assert faces == {
        None: (None, None),  # 主角：前端用主角外觀
        SEREN: (None, None),  # 傭兵：前端用傭兵名單（PartyView.mercenaries）
        AYUE: (card.portrait, "cloud_ridge"),
    }
    assert companion_face(library, _ayue(library)) == (card.portrait, "cloud_ridge")
    missing = _ayue(library).model_copy(update={"npc": "nobody_here"})
    assert companion_face(library, missing) == (None, None)
