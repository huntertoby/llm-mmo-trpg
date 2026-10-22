"""單場戰鬥的新開局（Phase 3-28）：武器＋關鍵字／開發者起始包建立戰鬥，與一輪開局的主角一致。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.roguelite import new_keyword_run


@pytest.fixture
def client(library: ContentLibrary) -> Iterator[TestClient]:
    with TestClient(create_app(library)) as c:
        yield c


def _body(library: ContentLibrary, **extra: Any) -> dict[str, Any]:
    return {"map_id": "open_plain", "seed": 7, **extra}


def test_weapon_and_keywords_start_matches_a_run_hero(
    client: TestClient, library: ContentLibrary
) -> None:
    run = new_keyword_run(library, "lightning_staff", ["wet", "charged"], 7)
    reply = client.post(
        "/api/battles", json=_body(library, weapon="lightning_staff", keywords=["wet", "charged"])
    )
    assert reply.status_code == 201, reply.text
    data = reply.json()
    hero = next(u for u in data["view"]["units"] if u["id"] == data["hero_id"])
    assert hero["name_zh"] == "冒險者"
    assert hero["max_mana"] == run.hero.max_mana
    assert len(data["view"]["units"]) >= 4  # 主角＋2 名隊友＋敵人


def test_dev_pack_start(client: TestClient, library: ContentLibrary) -> None:
    pack = library.dev_starters.packs[0].id
    reply = client.post("/api/battles", json=_body(library, dev_pack=pack))
    assert reply.status_code == 201, reply.text


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"weapon": "lightning_staff", "keywords": ["wet"]},
        {"weapon": "nope", "keywords": ["wet", "charged"]},
        {"dev_pack": "nope"},
        {"hero_build": "x", "weapon": "lightning_staff"},
    ],
)
def test_bad_starts_are_rejected(
    client: TestClient, library: ContentLibrary, extra: dict[str, Any]
) -> None:
    assert client.post("/api/battles", json=_body(library, **extra)).status_code == 422


def test_gear_check_accepts_the_new_start(client: TestClient) -> None:
    reply = client.post(
        "/api/gear/check", json={"weapon": "lightning_staff", "keywords": ["wet", "charged"]}
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["legal"] is True
