"""玩家看得到的字不出現設計編號（TXT-1；玩法 PM 11-12，`docs/art/資訊面板版面提案.md` 第 10 節）。

掃描範圍：

- ``content/`` 底下**所有** YAML／JSON 的字串值（YAML 註解不是值、不在掃描內）。
  比「只掃 ``*_zh``」更嚴：新增欄位不用登記也會被擋。
  下列欄位判定為玩家看不到，排除（理由見 ``NOT_PLAYER_VISIBLE``）。
- 顏色碼（``#4a6a5a``、全數字的 ``#103030``）不算設計編號。
- 後端送進 API 的字串（``src/trpg`` 裡非 docstring 的字串常數）：只有數值工坊
  （開發用、``TRPG_TUNING=1`` 才掛路由）的「#149 例外」允許，見 ``NOT_PLAYER_VISIBLE_PY``。
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator
from pathlib import Path

import yaml

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_story_view import event_view
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState, EventTrigger
from trpg.world.step import new_character

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
SRC = ROOT / "src" / "trpg"

DESIGN_NUMBER = re.compile(r"(?<![0-9A-Za-z&])[#＃]\d+(?![0-9A-Za-z])")
COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")

NOT_PLAYER_VISIBLE: dict[str, frozenset[str]] = {
    # 原語的程式化說明：只在工坊開發者模式（?dev=1）顯示；
    # 玩家模式顯示 workshop_text.yaml 的 player 或原語的 player_description。
    "skill_primitives.yaml": frozenset({"description_zh"}),
    # 同上的原文（查表用的鍵，必須和 skill_primitives.yaml 逐字相同）。
    "workshop_text.yaml": frozenset({"source"}),
    # NPC 人設卡的 hooks_zh：送說書人前一律換成好感度能給的內容（api/world_story.py::_card_for）。
    "world/npcs/cloud_ridge.yaml": frozenset({"hooks_zh"}),
    "world/npcs/ashen_waste.yaml": frozenset({"hooks_zh"}),
}

NOT_PLAYER_VISIBLE_PY: frozenset[str] = frozenset(
    {
        "api/tuning/service.py",  # 數值工坊（開發用）
        "api/tuning/writeback.py",  # 數值工坊的 commit 內文
    }
)


def _strings(value: object, key: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, str(k))
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, key)
    elif isinstance(value, str):
        yield key, value


def _content_hits() -> list[str]:
    hits: list[str] = []
    for path in sorted(CONTENT.rglob("*")):
        if path.suffix not in (".yaml", ".yml", ".json"):
            continue
        rel = path.relative_to(CONTENT).as_posix()
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
        skip = NOT_PLAYER_VISIBLE.get(rel, frozenset())
        for key, value in _strings(data):
            if key in skip or COLOR.match(value):
                continue
            if DESIGN_NUMBER.search(value):
                hits.append(f"{rel}::{key}：{value}")
    return hits


def test_content_strings_have_no_design_numbers() -> None:
    assert _content_hits() == []


def test_scan_catches_design_numbers() -> None:
    """掃描本身會抓：設計編號抓得到、顏色碼不算。"""
    assert DESIGN_NUMBER.search("說服（不加數值，#138）")
    assert DESIGN_NUMBER.search("（＃85）")
    assert COLOR.match("#103030") and COLOR.match("#4a6a5a")
    assert not DESIGN_NUMBER.search("#4a6a5a")


def _docstrings(tree: ast.AST) -> set[int]:
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }


def test_backend_strings_have_no_design_numbers() -> None:
    """``src/trpg`` 的字串常數（不含 docstring 與註解）不帶設計編號；數值工坊除外。"""
    hits: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel in NOT_PLAYER_VISIBLE_PY:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstrings(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skip
                and DESIGN_NUMBER.search(node.value)
            ):
                hits.append(f"{rel}:{node.lineno}：{node.value[:80]}")
    assert hits == []


def test_excluded_files_exist() -> None:
    """排除清單沒有過期（檔案改名時要跟著改）。"""
    for rel in NOT_PLAYER_VISIBLE:
        assert (CONTENT / rel).is_file(), rel
    for rel in NOT_PLAYER_VISIBLE_PY:
        assert (SRC / rel).is_file(), rel


def _at_fox(char: CharacterState) -> CharacterState:
    trigger = EventTrigger(
        region="cloud_ridge",
        location="north_slope",
        skeleton="fox_traveler",
        candidates=("fox_traveler",),
        weather="clear",
        day_phase="day",
        at=NOON,
    )
    return char.model_copy(update={"location": "north_slope", "pending_event": trigger})


def test_event_card_hint_goes_to_api(library: ContentLibrary) -> None:
    """玩法 PM 的範例：主字「說服」、說明卡「獸耳族主角有專屬的對話」。"""
    char = _at_fox(new_character(library, "alice", hero(library), region="cloud_ridge"))
    view = event_view(library, make_world(), char, NOON, ())
    assert view is not None
    lines = [(s.note_zh, s.hint_zh) for s in view.solutions]
    assert ("說服", "獸耳族主角有專屬的對話") in lines
    assert all(not DESIGN_NUMBER.search(note + hint) for note, hint in lines)


def test_tavern_answer_wording(library: ContentLibrary) -> None:
    """「文字回答＋用心清單（#85）」→ 主字「用自己的話回答」、
    說明卡「回答得用心可以加分（最多 +2）」。"""
    found = [
        (s.note_zh, s.hint_zh)
        for region in library.world_event_content.events.values()
        for skeleton in region.skeletons
        for s in skeleton.solutions
        if s.note_zh == "用自己的話回答"
    ]
    assert found == [("用自己的話回答", "回答得用心可以加分（最多 +2）")] * 2
