"""Phase 3E-1 #9：狀態與標籤常數集中在 ``trpg.engine.ids``，單位 ID 只有一個配發函式。"""

from __future__ import annotations

import re
from pathlib import Path

from tests.engine.helpers import library, make_map, make_state, no_reactions, spawn
from trpg.engine import ids
from trpg.shared.types import Team

SRC = Path(__file__).resolve().parents[2] / "src" / "trpg"
STATUS_CONSTANTS = ("CONCEALED", "DEFENDING", "PRONE", "REVEALED", "SHIELDED")


def test_status_constants_exist_in_statuses_yaml() -> None:
    known = {s.id for s in library().ruleset.statuses.statuses}
    for name in STATUS_CONSTANTS:
        assert getattr(ids, name) in known, name


def test_state_and_tag_constants_are_defined_only_in_ids() -> None:
    values = {
        getattr(ids, n): n
        for n in (*STATUS_CONSTANTS, "BOSS_TAG", "ELITE_TAG", "STEADFAST", "TOPPLABLE")
    }
    pattern = re.compile(r'^_?[A-Z][A-Z_0-9]* = "([a-z_]+)"\s*$', re.M)
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "ids.py" and path.parent.name == "engine":
            continue
        if "engine" not in path.parts:
            continue
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            assert match.group(1) not in values, f"{path} 重複定義 {values[match.group(1)]}"


def test_next_unit_id_follows_the_unit_count() -> None:
    m = make_map("\n".join(["000"] * 3), ally=[(0, 0)], enemy=[(2, 2)])
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), no_reactions()), spawn(Team.ENEMY, (2, 2), no_reactions())]
    )
    assert ids.next_unit_id(state) == "unit_0003"
