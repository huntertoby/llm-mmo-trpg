"""遊戲名稱（Phase UI-E1）：`content/ui/game.yaml` 的 schema、登記，以及前端只從這一處讀名稱。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.loader import load_content_file
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.content.ui_game import GameInfo

GAME_FILE = PROJECT_ROOT / "content" / "ui" / "game.yaml"


def test_the_file_loads() -> None:
    info = load_content_file(GAME_FILE, GameInfo)
    assert info.title_zh != ""
    assert info.tagline_zh != ""
    assert info.title_zh in info.summary()


def test_registered_for_content_check() -> None:
    assert any(
        f.relative_path == "ui/game.yaml" and f.model is GameInfo for f in KNOWN_CONTENT_FILES
    )


@pytest.mark.parametrize(
    "data",
    [
        {"title_zh": "", "tagline_zh": "x"},
        {"title_zh": "x"},
        {"title_zh": "x", "tagline_zh": "y", "subtitle": "z"},
        {"title_zh": "x" * 25, "tagline_zh": "y"},
    ],
)
def test_bad_files_are_rejected(data: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        GameInfo.model_validate(data)


def test_client_reads_the_name_from_this_file_only() -> None:
    """前端的遊戲名稱只從 `content/ui/game.yaml` 來：原始碼裡不再寫死舊標題。"""
    src = PROJECT_ROOT / "client" / "src"
    title = load_content_file(GAME_FILE, GameInfo).title_zh
    hits = []
    for path in sorted(src.rglob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        if "LLM-MMO-TRPG" in text or title in text:
            hits.append(path.name)
    assert hits == []
