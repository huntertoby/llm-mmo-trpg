"""``/api/world`` 的朋友的影子（Phase 5C-2；``docs/phases/Phase5計畫.md`` 23.8）。

兩個角色：A 在城鎮休息存成影子 → B 的雇用清單看得到 A → B 借用、開戰的單位有 A 的影子 → 打完 →
A 的 ``my_shadow`` 有戰報與任務幣。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client, _finish_battle
from tests.world.helpers import with_rules
from trpg.content.library import ContentLibrary


@pytest.fixture(scope="module")
def ambush(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})


@pytest.fixture
def client(ambush: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(ambush, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient, name: str) -> tuple[str, dict[str, Any]]:
    view = _ok(client.post("/api/world/characters", json={**START, "name": name}), 201)
    return view["character"]["character_id"], view


def _act(client: TestClient, cid: str, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{cid}/actions", json=action)


def test_borrow_shadow_and_owner_sees_report(client: TestClient, ambush: ContentLibrary) -> None:
    a, view_a = _create(client, "阿霧")
    b, view_b = _create(client, "小美")
    assert view_a["my_shadow"]["saved"] is False
    assert view_b["party"]["shadows"] == []

    rested = _ok(_act(client, a, kind="rest"))
    assert any("存成影子" in e for e in rested["events"])
    assert rested["my_shadow"]["saved"] is True
    assert rested["my_shadow"]["saved_zh"] == "霧渡鎮・Lv 1"

    seen = _ok(client.get(f"/api/world/characters/{b}"))
    shadows = seen["party"]["shadows"]
    assert [s["owner"] for s in shadows] == [a]
    shadow = shadows[0]
    assert shadow["name_zh"] == "阿霧"
    assert shadow["level"] == 1 and shadow["capped"] is False
    assert shadow["skills_zh"]
    assert "火焰法杖" in shadow["role_zh"]
    assert seen["party"]["ai_choices"]

    hired = _ok(
        _act(client, b, kind="hire", mercenaries=["merc_tiebi"], shadows=[a], ai={a: "guard"})
    )
    party = hired["party"]
    assert [m["name_zh"] for m in party["members"]] == ["小美", "鐵壁", "阿霧的影子"]
    assert party["members"][2]["shadow"] == a
    assert party["members"][2]["ai_zh"] == "守衛"
    assert party["season_boss_ok"] is False
    assert any("借用阿霧的影子" in e for e in hired["events"])

    met = _ok(_act(client, b, kind="travel", to="ferry_steps"))
    assert met["encounter"]["allies_zh"].endswith("＋鐵壁、阿霧的影子")
    opened = _ok(client.post(f"/api/world/characters/{b}/battle"))
    allies = [u["name_zh"] for u in opened["battle"]["view"]["units"] if u["team"] == "ally"]
    assert "阿霧" in allies
    _finish_battle(client, opened["battle"], ambush)
    _ok(client.get(f"/api/world/characters/{b}"))  # 同步回寫

    owner = _ok(client.get(f"/api/world/characters/{a}"))["my_shadow"]
    assert owner["coins"] == 1
    assert len(owner["reports_zh"]) == 1
    assert "你的影子" in owner["reports_zh"][0] and "小美" in owner["reports_zh"][0]


def test_shadow_rules_over_api(client: TestClient) -> None:
    a, _ = _create(client, "阿霧")
    refused = _act(client, a, kind="hire", shadows=[a])
    assert refused.status_code == 422
    missing = _act(client, a, kind="hire", shadows=["cnobody"])
    assert missing.status_code == 422
    solo = _ok(_act(client, a, kind="hire"))
    assert any("獨行" in e for e in solo["events"])
    assert [m["title_zh"] for m in solo["party"]["members"]] == ["主角"]
    ai = _ok(_act(client, a, kind="shadow_ai", profile="support"))
    assert ai["my_shadow"]["ai"] == "support"
    assert ai["my_shadow"]["ai_zh"] == "支援"
    bad = _act(client, a, kind="shadow_ai", profile="idle")
    assert bad.status_code == 422
