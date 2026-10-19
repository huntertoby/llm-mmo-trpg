"""整場戰鬥、重播一致、網頁與 CLI 一致、確定性（Phase 3-2 4.5）。"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.api.helpers import Chooser, first_non_end_turn, play, utility_chooser
from trpg.cli.battle import cmd_replay
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import EVENT_LIST_ADAPTER
from trpg.engine.runner import BattleLog, replay
from trpg.engine.state import state_to_json

CASES = [
    ("open_plain", 7, "build_fire", "utility"),
    ("frozen_lake", 3, "build_guardian", "first"),
    ("narrow_halls", 11, "build_trapper", "utility"),
]


def _chooser(kind: str, library: ContentLibrary) -> Chooser:
    if kind == "utility":
        return utility_chooser(UtilityAI(library.ai_profiles))
    return first_non_end_turn


@pytest.mark.parametrize(("map_id", "seed", "hero", "kind"), CASES)
def test_a_full_battle_through_the_api_replays_identically(
    *,
    client: TestClient,
    library: ContentLibrary,
    tmp_path: Path,
    map_id: str,
    seed: int,
    hero: str,
    kind: str,
) -> None:
    played = play(
        client,
        store_of(client),
        {"map_id": map_id, "seed": seed, "hero_build": hero},
        _chooser(kind, library),
    )
    assert played.final["awaiting"] == "ended"
    assert played.final["outcome"] is not None
    raw = client.get(f"/api/battles/{played.battle_id}/log").text
    log = BattleLog.model_validate_json(raw)
    assert log.seed == seed
    run = replay(log.setup, log.seed, log.actions)
    assert state_to_json(run.state) == state_to_json(log.final_state)
    assert EVENT_LIST_ADAPTER.dump_json(run.events) == EVENT_LIST_ADAPTER.dump_json(log.events)  # type: ignore[arg-type]
    # 工作階段的目前狀態 ＝ setup ＋ seed ＋ 步驟列表的重播
    session = store_of(client).get(played.battle_id)
    assert state_to_json(run.state) == state_to_json(session.state)
    # 網頁與 CLI 一致：同一份紀錄用 trpg battle replay 驗證
    path = tmp_path / "web.json"
    path.write_text(raw, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()


def test_hero_reaction_prompts_alternate_and_still_replay(
    prompt_client: TestClient, prompt_library: ContentLibrary, tmp_path: Path
) -> None:
    """主角的反應改為 ``prompt``（測試用內容庫）：詢問時交替接受與拒絕，紀錄仍可重播。"""
    answers: list[bool] = []
    for map_id, seed, hero, kind in [*CASES, ("ruined_fort", 5, "build_tank", "utility")]:
        played = play(
            prompt_client,
            store_of(prompt_client),
            {"map_id": map_id, "seed": seed, "hero_build": hero},
            _chooser(kind, prompt_library),
            decision_offset=len(answers),
        )
        answers += [bool(body["accept"]) for k, body in played.requests if k == "decision"]
        path = tmp_path / f"{map_id}.json"
        path.write_text(
            prompt_client.get(f"/api/battles/{played.battle_id}/log").text, encoding="utf-8"
        )
        assert cmd_replay(path, io.StringIO()) == 0
    assert set(answers) == {True, False}  # 接受與拒絕都走過


def _strip_id(text: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(text)
    data.pop("battle_id")
    return data


def test_same_inputs_give_the_same_responses(client: TestClient, library: ContentLibrary) -> None:
    create = {"map_id": "open_plain", "seed": 21, "hero_build": "build_storm"}
    first = play(client, store_of(client), create, _chooser("utility", library))
    created = client.post("/api/battles", json=create)
    second_id = created.json()["battle_id"]
    assert second_id != first.battle_id
    texts = [created.text]
    for kind, body in first.requests:
        path = "decision" if kind == "decision" else "actions"
        reply = client.post(f"/api/battles/{second_id}/{path}", json=body)
        assert reply.status_code == 200
        texts.append(reply.text)
    assert [_strip_id(t) for t in texts] == [_strip_id(t) for t in first.texts]
    log_a = client.get(f"/api/battles/{first.battle_id}/log").text
    log_b = client.get(f"/api/battles/{second_id}/log").text
    assert log_a == log_b
