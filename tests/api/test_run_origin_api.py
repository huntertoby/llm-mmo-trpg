"""開局選種族與出身（Phase 3R-3a）的 API：開局選項、`race`／`origin`、英雄面板。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary, load_library

START: dict[str, Any] = {"weapon": "one_handed_sword", "keywords": ["ignite", "prone"]}


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _create(client: TestClient, **over: Any) -> dict[str, Any]:
    reply = client.post("/api/runs", json={**START, "seed": 7, **over})
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_start_options_list_races_and_origins_with_skill_and_passive_text(
    client: TestClient,
) -> None:
    options: dict[str, Any] = client.get("/api/runs/start-options").json()
    races = {r["id"]: r for r in options["races"]}
    assert len(races) == 10 and races["elf"]["skill_name_zh"] == "林隱"
    assert races["elf"]["passive_name_zh"] == "林間視野" and races["elf"]["skill_uses"] == 2
    assert races["elf"]["home_realm_name_zh"] and races["elf"]["skill_description_zh"]
    origins = {o["id"]: o for o in options["origins"]}
    assert len(origins) == 5
    assert origins["origin_cloud_ridge"]["realm_name_zh"] == "雲嶺"
    assert origins["origin_cloud_ridge"]["description_zh"]


def test_a_run_records_race_and_origin_and_the_hero_panel_shows_them(client: TestClient) -> None:
    run = _create(client, race="fox", origin="origin_frost_tide")
    hero = run["hero"]
    assert (hero["race_id"], hero["origin_id"]) == ("fox", "origin_frost_tide")
    assert hero["race_name_zh"] and hero["origin_name_zh"] == "霜潮海境出身"
    store = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(store, RunStore)
    session = store.get(run["run_id"])
    assert session.run.origin == "origin_frost_tide" and session.run.hero.race == "fox"
    plain = _create(client)["hero"]
    assert plain["race_id"] is None and plain["origin_id"] is None and plain["origin_name_zh"] == ""


def test_the_battle_hero_carries_the_chosen_race(client: TestClient) -> None:
    run = _create(client, race="dwarf", origin="origin_arcane_hub")
    battle = client.post(f"/api/runs/{run['run_id']}/battle").json()["battle"]
    heroes = [u for u in battle["view"]["units"] if u["team"] == "ally" and u["race"] is not None]
    assert [u["race"]["id"] for u in heroes] == ["dwarf"]


def test_a_run_rejects_unknown_origins(client: TestClient) -> None:
    reply = client.post("/api/runs", json={**START, "seed": 7, "origin": "nowhere"})
    assert reply.status_code == 422 and "未知的出身" in reply.text
