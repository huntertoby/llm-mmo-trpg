"""Phase 3H-3：角色面板用有效屬性、屬性影響的招、開局建議屬性、營火重配屬性的 API。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.roguelite.helpers import full_library
from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play, new_run
from trpg.roguelite.state import BattleNode, CampfireNode

BODY: dict[str, Any] = {"weapon": "one_handed_sword", "keywords": ["ignite", "prone"], "seed": 3}


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _ok(reply: Any) -> Any:
    assert reply.status_code in (200, 201), reply.text
    return reply.json()


def test_panel_perk_tiers_use_the_effective_attribute_with_gear(
    client: TestClient, library: ContentLibrary
) -> None:
    """基礎力量 12（0 階）＋ 裝備力量 +2 ＝ 有效 14（1 階）：面板的階數依有效屬性，與引擎一致。"""
    body = {
        **BODY,
        "attributes": {"str": 2, "dex": 2},
        "test_mode": True,
        "test_equipment": {"main_hand": "item_test_sword"},
    }
    hero = _ok(client.post("/api/runs", json=body))["hero"]
    assert hero["attributes"]["str"] == 12  # 基礎值（配點用）
    assert hero["effective_attributes"]["str"] == 14
    strength = next(p for p in hero["attribute_perks"] if p["attr"] == "str")
    perks = library.ruleset.core.attribute_perks
    assert strength["tier"] == perks.tier(14) == 1
    # 沒有裝備時有效屬性＝基礎屬性
    plain = _ok(client.post("/api/runs", json={**BODY, "attributes": {"str": 2, "dex": 2}}))["hero"]
    assert plain["effective_attributes"] == plain["attributes"]


def test_hero_lists_which_skills_each_attribute_affects(client: TestClient) -> None:
    hero = _ok(client.post("/api/runs", json=BODY))["hero"]
    affects = {a["attr"]: a["lines_zh"] for a in hero["attribute_affects"]}
    assert set(affects) == {"str", "dex", "con", "int", "wis", "wil"}
    names = {c["name_zh"] for c in hero["skills"]}
    listed = {line for lines in affects.values() for line in lines}
    assert names <= listed  # 每一招都至少出現在一個屬性底下
    assert any("的普攻" in line for lines in affects.values() for line in lines)


def test_start_preview_suggests_the_attribute_most_skills_scale_with(
    client: TestClient,
) -> None:
    preview = _ok(
        client.post(
            "/api/runs/start-preview",
            json={"weapon": "one_handed_sword", "seed": 3, "keywords": ["ignite", "prone"]},
        )
    )
    suggestion = preview["suggestion"]
    assert suggestion["attr"] in {"str", "dex", "con", "int", "wis", "wil"}
    assert suggestion["reason_zh"]
    picked = [o["skill"] for o in preview["options"] if o["selected"]]
    assert len(picked) == 2
    # 建議和「自動配點」同一個規則：開局省略配點時點在同一個屬性
    hero = _ok(client.post("/api/runs", json=BODY))["hero"]
    assert hero["attributes"][suggestion["attr"]] == 14  # 4 點自由配點全在建議的屬性
    assert any(a["lines_zh"] for a in preview["attribute_affects"])
    empty = _ok(
        client.post(
            "/api/runs/start-preview",
            json={"weapon": "one_handed_sword", "seed": 3, "keywords": []},
        )
    )
    assert empty["suggestion"] is not None  # 只有武器時用武器的屬性


def _campfire_session(client: TestClient, library: ContentLibrary) -> str:
    created = _ok(client.post("/api/runs", json={"build": "build_fire", "seed": 0}))
    run_id: str = created["run_id"]
    # AI 代打走完整技能三選一才活得到營火（預設的白板三選一較弱，3W-4）
    skilled = full_library()
    run, _ = auto_play(
        skilled,
        new_run(skilled, "build_fire", 0),
        stop=lambda r, b: isinstance(r.node, CampfireNode),
    )
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    runs.get(run_id).run = run
    return run_id


def test_campfire_attribute_respec_and_allocate_over_the_api(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _campfire_session(client, library)
    before = _ok(client.get(f"/api/runs/{run_id}"))["hero"]
    spent = sum(before["attribute_spent"].values())
    assert spent > 0 and before["attribute_points"] == 0
    refunded = _ok(client.post(f"/api/runs/{run_id}/choice", json={"kind": "respec_attributes"}))
    assert refunded["node"]["kind"] == "campfire"
    assert refunded["hero"]["attribute_points"] == spent
    assert refunded["hero"]["attribute_spent"] == {}
    assert set(refunded["hero"]["attributes"].values()) == {10}
    again = _ok(
        client.post(
            f"/api/runs/{run_id}/choice", json={"kind": "allocate", "attributes": {"wis": spent}}
        )
    )
    assert again["hero"]["attributes"]["wis"] == 10 + spent
    assert again["hero"]["attribute_points"] == 0
    too_many = client.post(
        f"/api/runs/{run_id}/choice", json={"kind": "allocate", "attributes": {"wis": 1}}
    )
    assert too_many.status_code == 422


def test_attribute_respec_is_campfire_only_and_blocked_in_battle(
    client: TestClient, library: ContentLibrary
) -> None:
    created = _ok(client.post("/api/runs", json={"build": "build_fire", "seed": 0}))
    run_id = created["run_id"]
    assert (
        client.post(f"/api/runs/{run_id}/choice", json={"kind": "respec_attributes"}).status_code
        == 409
    )
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs.get(run_id).run.node, BattleNode)
    _ok(client.post(f"/api/runs/{run_id}/battle"))
    blocked = client.post(
        f"/api/runs/{run_id}/choice", json={"kind": "allocate", "attributes": {"str": 1}}
    )
    assert blocked.status_code == 409
