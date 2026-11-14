"""NW-3d（玩法 PM 交接 4.1.16）：技能工坊 API 給前端的造牆物件選單＝組合器候選；
送出冷卻井、油桶會被擋。

前端（``client/src/ui/workshop/FieldEditor.tsx``）照 API 給的 ``choices`` 畫選單，
沒有自己的物件清單。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from tests.skillgen.test_obstacle_choices_nw3d import BANNED, WALL_DRAFT
from trpg.skillgen.composer_parts import obstacle_candidates


def _object_menu(body: dict[str, Any]) -> list[str]:
    for step in body["steps"]:
        for field in step["fields"]:
            for choice in field["choices"]:
                if choice["value"] == "create_obstacle":
                    (obj,) = [p for p in choice["params"] if p["field"] == "object"]
                    return [c["value"] for c in obj["choices"]]
    raise AssertionError("效果步驟沒有「產生障礙」")


def test_workshop_api_menu_and_check(client: TestClient) -> None:
    body = client.post("/api/workshop/options", json={"skill": WALL_DRAFT}).json()
    menu = _object_menu(body)
    assert sorted(menu) == list(obstacle_candidates(library()))
    assert not set(BANNED) & set(menu)
    for obj in BANNED:
        draft = {**WALL_DRAFT, "effects": [{"type": "create_obstacle", "object": obj}]}
        problems = client.post("/api/workshop/options", json={"skill": draft}).json()["problems"]
        assert any("物件不在可選範圍內" in p for p in problems), problems
