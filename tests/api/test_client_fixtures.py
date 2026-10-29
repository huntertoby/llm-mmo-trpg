"""Phase 3E-2e：前端測試用的內容快照沒有過期（重產見 scripts/export_client_fixtures.py）。"""

from __future__ import annotations

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.api.fixtures import (
    glossary_fixture_text,
    race_looks_fixture_text,
    unit_dolls_fixture_text,
)

_HINT = "過期了：uv run python scripts/export_client_fixtures.py"


def test_glossary_fixture_is_up_to_date() -> None:
    path = PROJECT_ROOT / "client" / "src" / "battle" / "fixtures" / "glossary.json"
    assert path.read_text(encoding="utf-8") == glossary_fixture_text(library()), (
        f"glossary.json {_HINT}"
    )


def test_unit_dolls_fixture_is_up_to_date() -> None:
    path = PROJECT_ROOT / "client" / "src" / "render" / "fixtures" / "unitDolls.json"
    assert path.read_text(encoding="utf-8") == unit_dolls_fixture_text(library()), (
        f"unitDolls.json {_HINT}"
    )


def test_race_looks_fixture_is_up_to_date() -> None:
    path = PROJECT_ROOT / "client" / "src" / "render" / "fixtures" / "raceLooks.json"
    assert path.read_text(encoding="utf-8") == race_looks_fixture_text(library()), (
        f"raceLooks.json {_HINT}"
    )
