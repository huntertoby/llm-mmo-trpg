"""Phase 3-26b：分歧進化的 API（兩支比較、門檻原因、送出選擇、進化後的技能卡）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.roguelite import RunState, auto_play, new_run
from trpg.roguelite.state import LevelUpNode
from trpg.skillgen.usage import SkillUsage

BUILD = "build_fire"


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _ready(client: TestClient, library: ContentLibrary) -> tuple[str, str]:
    """開一輪、換成 AI 代打到第一次升級的樣子，並讓第一個主動技能用過 3 次、有 4 點。"""
    created = client.post("/api/runs", json={"build": BUILD, "seed": 0})
    assert created.status_code == 201, created.text
    run_id: str = created.json()["run_id"]

    def stop(run: RunState, _battle: Any) -> bool:
        return isinstance(run.node, LevelUpNode)

    run, _ = auto_play(library, new_run(library, BUILD, 0), stop=stop)
    skill = next(s for s in run.hero.skills if library.skills[s].kind == "active")
    usage = run.skill_usage.get(skill, SkillUsage()).model_copy(update={"uses": 3})
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    runs.get(run_id).run = run.model_copy(
        update={"skill_points": 4, "skill_usage": {**run.skill_usage, skill: usage}}
    )
    return run_id, skill


def test_the_hero_lists_two_evolutions_with_cards(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id, skill = _ready(client, library)
    hero = _ok(client.get(f"/api/runs/{run_id}"))["hero"]
    assert hero["skill_growth"]["evolve_uses"] == 3
    (choice,) = [c for c in hero["evolutions"] if c["skill_id"] == skill]
    options = choice["options"]
    assert [o["index"] for o in options] == [0, 1]
    assert {o["label_zh"] for o in options} <= {"加深", "橋接"}
    for option in options:
        card = option["card"]
        assert card["id"] != skill and card["name_zh"].endswith("・" + choice["name_zh"])
        assert card["icon"] and option["summary_zh"]
    card = next(c for c in hero["skills"] if c["id"] == skill)
    assert card["growth"]["uses"] == 3 and card["growth"]["blocked_text"] is None
    # 前一次（同一個狀態）的兩支一樣
    again = _ok(client.get(f"/api/runs/{run_id}"))["hero"]["evolutions"]
    assert again == hero["evolutions"]


def test_spending_to_level_three_needs_a_pick_and_evolves_the_skill(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id, skill = _ready(client, library)
    url = f"/api/runs/{run_id}/choice"
    options = next(
        c["options"]
        for c in _ok(client.get(f"/api/runs/{run_id}"))["hero"]["evolutions"]
        if c["skill_id"] == skill
    )
    missing = client.post(url, json={"kind": "spend", "levels": {skill: 3}})
    assert missing.status_code == 422 and "要選一支進化" in missing.json()["detail"]
    reply = _ok(
        client.post(url, json={"kind": "spend", "levels": {skill: 3}, "evolve": {skill: 1}})
    )
    evolved = options[1]["card"]["id"]
    card = next(c for c in reply["hero"]["skills"] if c["id"] == evolved)
    assert card["growth"]["level"] == 3 and card["growth"]["evolved_from_zh"]
    assert skill not in [c["id"] for c in reply["hero"]["skills"]]
    assert all(c["skill_id"] != skill for c in reply["hero"]["evolutions"])
    assert reply["node"]["kind"] == "level_up"
