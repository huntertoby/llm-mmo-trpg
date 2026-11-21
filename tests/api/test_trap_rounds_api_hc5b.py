"""HC-5b（HC-5a 裁定 5）：工坊 API 的檢查與匯出，陷阱草稿沒寫輪數時補 2，和 HC-5a 之前相同。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from trpg.skillgen.draft import draft_id


def _drafts() -> tuple[dict[str, Any], dict[str, Any]]:
    """內容庫第一個輪數是 2 的陷阱技：沒寫輪數的草稿、寫了 2 的草稿。"""
    lib = library()
    skill = next(
        s for _, s in sorted(lib.skills.items()) if s.trap is not None and s.trap.rounds == 2
    )
    data = skill.model_dump(mode="json", exclude_none=True)
    data.pop("id")
    filled = {**data, "trap": dict(data["trap"])}
    del data["trap"]["rounds"]
    filled["id"] = draft_id(data)  # ID 照補值前的內容（同 HC-5a 之前）
    return data, filled


def test_check_and_export_fill_the_missing_rounds(client: TestClient) -> None:
    bare, filled = _drafts()
    for path, extra in (
        ("/api/workshop/check", {}),
        ("/api/workshop/export", {"allow_illegal": True}),
    ):
        got = client.post(path, json={"skill": bare, **extra})
        want = client.post(path, json={"skill": filled, **extra})
        assert got.status_code == want.status_code == 200, (path, got.text)
        assert got.json() == want.json(), path
