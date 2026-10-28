"""新開局的 API（Phase 3-24b2）：開局選項、起始技能預覽、開發者起始包、玩家介面不出現流派名。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.roguelite import new_keyword_run


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _ok(reply: Any) -> Any:
    assert reply.status_code in (200, 201), reply.text
    return reply.json()


def _school_names(library: ContentLibrary) -> set[str]:
    return {p.label_zh for p in library.dev_starters.packs}


def test_start_options_list_every_weapon_and_keyword(
    client: TestClient, library: ContentLibrary
) -> None:
    options = _ok(client.get("/api/runs/start-options"))
    assert [w["id"] for w in options["weapons"]] == sorted(
        w for w, d in library.weapons.items() if not d.summon_only
    )
    assert [k["id"] for k in options["keywords"]] == list(library.keywords.start_ids())
    # 3-54c：毒種子補齊後，中毒和其他關鍵字一樣出現在開局選單
    assert "poisoned" in [k["id"] for k in options["keywords"]]
    assert "poisoned" in library.keywords.ids()
    assert options["keyword_count"] == 2
    sword = next(w for w in options["weapons"] if w["id"] == "one_handed_sword")
    assert sword["weapon_class"] == "melee" and sword["hp"] > 0
    text = str(options)
    assert not any(name in text for name in _school_names(library))


def test_preview_matches_the_created_run(client: TestClient, library: ContentLibrary) -> None:
    body = {"weapon": "lightning_staff", "seed": 5, "keywords": []}
    first = _ok(client.post("/api/runs/start-preview", json=body))
    by_kw = {o["keyword"]["id"]: o for o in first["options"]}
    assert set(by_kw) == set(library.keywords.start_ids())
    assert not any(o["selected"] for o in first["options"])
    pick_a = by_kw["wet"]["skill"]["id"]
    second = _ok(client.post("/api/runs/start-preview", json={**body, "keywords": ["wet"]}))
    by_kw2 = {o["keyword"]["id"]: o for o in second["options"]}
    assert by_kw2["wet"]["selected"] and by_kw2["wet"]["skill"]["id"] == pick_a
    pick_b = by_kw2["charged"]["skill"]["id"]
    assert pick_b != pick_a
    run = _ok(
        client.post(
            "/api/runs",
            json={"weapon": "lightning_staff", "keywords": ["wet", "charged"], "seed": 5},
        )
    )
    assert [c["id"] for c in run["hero"]["skills"]] == [pick_a, pick_b]
    assert [k["id"] for k in run["hero"]["start_keywords"]] == ["wet", "charged"]
    assert run["hero"]["build_id"] == "" and run["hero"]["dev_pack"] is None
    expected = new_keyword_run(library, "lightning_staff", ("wet", "charged"), 5)
    assert tuple(c["id"] for c in run["hero"]["skills"]) == expected.hero.skills


def test_preview_marks_keywords_every_weapon_can_reach(client: TestClient) -> None:
    preview = _ok(
        client.post("/api/runs/start-preview", json={"weapon": "bow", "seed": 1, "keywords": []})
    )
    wet = next(o for o in preview["options"] if o["keyword"]["id"] == "wet")
    assert wet["skill"] is not None  # 3-24c 4b：不限武器的潮濕技能讓弓也能選潮濕
    ignite = next(o for o in preview["options"] if o["keyword"]["id"] == "ignite")
    assert ignite["skill"] is not None


def test_dev_packs_endpoint_and_start(client: TestClient, library: ContentLibrary) -> None:
    packs = _ok(client.get("/api/runs/dev-packs"))
    assert len(packs) == 29 and {p["label_zh"] for p in packs} == _school_names(library)
    run = _ok(client.post("/api/runs", json={"dev_pack": packs[0]["id"], "seed": 3}))
    assert run["hero"]["dev_pack"] == packs[0]["id"]
    # 一輪的回應（玩家介面）不出現流派名
    text = str(run["hero"])
    assert not any(name in text for name in _school_names(library))
    saves = _ok(client.get("/api/runs/saves"))
    assert saves[0]["build_name_zh"].count("・") == 1
    assert not any(name in saves[0]["build_name_zh"] for name in _school_names(library))
