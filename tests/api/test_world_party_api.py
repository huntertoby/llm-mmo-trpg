"""``/api/world`` 的隊伍與系統傭兵（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22.6）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client
from trpg.content.library import ContentLibrary
from trpg.world.save import loads_log


@pytest.fixture
def client(ambush: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(ambush, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient) -> tuple[str, dict[str, Any]]:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    return view["character"]["character_id"], view


def _act(client: TestClient, cid: str, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{cid}/actions", json=action)


def test_party_view_in_town(client: TestClient) -> None:
    _, view = _create(client)
    party = view["party"]
    assert party["can_hire"] is True
    assert party["hire_problem_zh"] is None
    assert party["max_hired"] == 2
    # 新角色預設只帶賽倫（5C-3；OB-7，#154）
    assert [m["title_zh"] for m in party["members"]] == ["主角", "盾衛・守護"]
    roster = party["mercenaries"]
    assert len(roster) == 9
    tiebi = next(m for m in roster if m["id"] == "merc_tiebi")
    assert tiebi["name_zh"] == "賽倫"
    assert tiebi["role_zh"] == "守護"
    assert tiebi["theme_zh"]
    assert "挑釁怒吼" in tiebi["skills_zh"]
    # UI-E3b：技能 ID 和中文名同順序、同長度，每個都查得到技能卡
    assert len(tiebi["skill_ids"]) == len(tiebi["skills_zh"])
    for sid, name in zip(tiebi["skill_ids"], tiebi["skills_zh"], strict=True):
        card = client.get(f"/api/skills/{sid}")
        assert card.status_code == 200, sid
        assert card.json()["name_zh"] == name
    assert tiebi["hired"] is True  # 預設隊伍（5C-3）
    assert tiebi["origin"] == "crystal_crown"  # #131
    assert tiebi["portrait"]["extras"] == ["crest"]  # RT-4


def test_hire_and_fight_with_mercenaries(client: TestClient, tmp_path: Path) -> None:
    cid, _ = _create(client)
    hired = _ok(_act(client, cid, kind="hire", mercenaries=["merc_tiebi", "merc_huichun"]))
    party = hired["party"]
    assert [m["name_zh"] for m in party["members"][1:]] == ["賽倫", "回春"]
    assert party["members"][1]["title_zh"] == "盾衛・守護"
    assert {m["id"] for m in party["mercenaries"] if m["hired"]} == {"merc_tiebi", "merc_huichun"}
    assert any("賽倫、回春" in e for e in hired["events"])

    met = _ok(_act(client, cid, kind="travel", to="ferry_steps"))
    assert met["party"]["can_hire"] is False
    assert met["party"]["hire_problem_zh"] == "還有沒處理的遭遇"
    assert met["encounter"]["allies_zh"].endswith("＋賽倫、回春")
    refused = _act(client, cid, kind="hire", mercenaries=["merc_qingfeng"])
    assert refused.status_code == 422

    opened = _ok(client.post(f"/api/world/characters/{cid}/battle"))
    allies = [u["name_zh"] for u in opened["battle"]["view"]["units"] if u["team"] == "ally"]
    assert "賽倫" in allies
    assert "回春" in allies
    assert opened["world"]["party"]["hire_problem_zh"] == "戰鬥中"

    log = loads_log((tmp_path / "saves" / "world" / "log.jsonl").read_text(encoding="utf-8"))
    assert [e.action.kind for e in log] == ["hire", "travel"]


def test_hire_rejected_in_the_field(client: TestClient) -> None:
    cid, _ = _create(client)
    met = _ok(_act(client, cid, kind="travel", to="ferry_steps"))
    _ok(_act(client, cid, kind="retreat"))
    assert met["encounter"] is not None
    # 撤退回城後可以雇；超過 2 名不行
    too_many = _act(
        client, cid, kind="hire", mercenaries=["merc_tiebi", "merc_panshi", "merc_chiyan"]
    )
    assert too_many.status_code == 422
    none = _ok(_act(client, cid, kind="hire", mercenaries=[]))
    assert any("獨行" in e for e in none["events"])


# ---------------------------------------------------------------------------
# 5C-3：劇情夥伴
# ---------------------------------------------------------------------------


def test_companion_in_party_view(client: TestClient) -> None:
    cid, view = _create(client)
    assert view["party"]["free_slots"] == 2 and view["party"]["companion_zh"] is None
    # OB-7（#154）：預設只帶賽倫；替換與還原照舊，先自己雇滿 2 名（OB-7 前的預設）
    _ok(_act(client, cid, kind="hire", mercenaries=["merc_tiebi", "merc_huichun"]))
    starter = _ok(_act(client, cid, kind="accept_quest", quest="starter_ferry"))
    names = [m["name_zh"] for m in starter["party"]["members"][1:]]
    assert names == ["賽倫", "回春"]  # 新手任務：阿岳等第 1 步打完才入隊
    accepted = _ok(_act(client, cid, kind="accept_quest", quest="main_mist_rift"))
    party = accepted["party"]
    assert [m["name_zh"] for m in party["members"][1:]] == ["賽倫", "阿岳"]
    ayue = party["members"][2]
    assert ayue["companion"] == "companion_ayue" and ayue["title_zh"] == "獵戶・劇情夥伴"
    assert ayue["note_zh"] == "劇情夥伴：任務結束後離隊"
    assert party["free_slots"] == 1
    assert party["companion_zh"] == "阿岳（霧中裂痕）跟著你，佔 1 個隊友位；任務結束後離隊"
    assert any(e.startswith("阿岳加入隊伍（替下回春）") for e in accepted["events"])
    assert {m["id"] for m in party["mercenaries"] if m["hired"]} == {"merc_tiebi"}
    too_many = _act(client, cid, kind="hire", mercenaries=["merc_tiebi", "merc_huichun"])
    assert too_many.status_code == 422 and "劇情夥伴" in too_many.json()["detail"]
    met = _ok(_act(client, cid, kind="travel", to="ferry_steps"))
    assert met["encounter"]["allies_zh"].endswith("＋賽倫、阿岳")
