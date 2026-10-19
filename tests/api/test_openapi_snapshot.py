"""OpenAPI 快照（Phase 3-3 5.2）：前端型別 ``client/src/api/schema.d.ts`` 由 ``client/openapi.json``
產生；API 改了而沒有重新產生就失敗。"""

from __future__ import annotations

import json
from pathlib import Path

from trpg.api.app import create_app

CLIENT = Path(__file__).resolve().parents[2] / "client"

REGENERATE = (
    "API 的 OpenAPI 與 client/openapi.json 不一致；請執行 "
    "`uv run python scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api`，"
    "並把兩個檔案一起 commit。"
)


def test_openapi_matches_the_client_snapshot() -> None:
    saved = json.loads((CLIENT / "openapi.json").read_text(encoding="utf-8"))
    assert saved == create_app().openapi(), REGENERATE


def test_the_generated_schema_exists() -> None:
    schema = CLIENT / "src" / "api" / "schema.d.ts"
    assert schema.is_file(), REGENERATE
    assert "BattleResponse" in schema.read_text(encoding="utf-8")
