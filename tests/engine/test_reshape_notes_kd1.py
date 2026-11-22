"""KD-1 第 8 項（E5 美術小修、08 8.29 E5 第 7 點）：沒有套用到某招的裝備變形，寫在說明卡最後。

測試修正技與詞條沿用 ``test_reshape_gate_e5``（只在測試裡，不進 ``content/``）。
"""

from __future__ import annotations

import dataclasses
from typing import Any

from tests.engine.test_reshape_gate_e5 import (
    BOUNCE,
    PUSHY,
    STRIKE,
    U1,
    _modifier,
    gear_library,
    scene,
)
from trpg.content.library import ContentLibrary
from trpg.engine.modifiers import gear_reshapes_left_out
from trpg.engine.state import BattleState
from trpg.engine.view import project_for
from trpg.shared.types import Team
from trpg.skillgen.reshape_gate import gate_library

BOUNCE2 = "skill_t_bounce2"


def _me(state: BattleState) -> Any:
    return next(u for u in project_for(state, Team.ALLY).units if u.id == U1)


def test_partly_blocked_bounce_notes_the_blocked_skill() -> None:
    lib = gear_library()
    state = scene(lib, skills=(STRIKE, PUSHY))
    assert gear_reshapes_left_out(state, state.units[U1], PUSHY) == ((BOUNCE, True),)
    assert gear_reshapes_left_out(state, state.units[U1], STRIKE) == ()
    name = lib.ruleset.skill_def(BOUNCE).name_zh
    assert _me(state).skill_notes_zh == {PUSHY: (f"{name}不會套用到這招",)}


def test_fully_blocked_bounce_adds_no_note() -> None:
    """整個擋下時修正技本身已經標灰，被擋的招不另外寫。"""
    state = scene(gear_library(), skills=(PUSHY,))
    assert _me(state).skill_notes_zh is None


def test_no_gear_reshape_no_notes() -> None:
    state = scene(gear_library(), gear=(), skills=(STRIKE, PUSHY))
    assert _me(state).skill_notes_zh is None


def _two_bounces() -> ContentLibrary:
    """兩件同樣會把技能變成連鎖的裝備變形（都過得了閘門）。"""
    lib = gear_library(gated=False)
    extra = _modifier(BOUNCE2, {"shape_to": "chain"}, {"all_skills": True})
    base = lib.affixes[f"affix_t_{BOUNCE}"]
    copy = base.model_copy(update={"id": f"affix_t_{BOUNCE2}", "skill": BOUNCE2})
    out = dataclasses.replace(
        lib,
        skills={**lib.skills, BOUNCE2: extra},
        affixes={**lib.affixes, f"affix_t_{BOUNCE2}": copy},
        ruleset=lib.ruleset.with_skills([extra]),
    )
    return gate_library(out)


def test_only_one_reshape_per_skill_the_other_gets_a_note() -> None:
    state = scene(_two_bounces(), gear=(BOUNCE, BOUNCE2), skills=(STRIKE,))
    assert gear_reshapes_left_out(state, state.units[U1], STRIKE) == ((BOUNCE2, False),)
    (line,) = (_me(state).skill_notes_zh or {})[STRIKE]
    assert line.startswith("已有其他變形，") and line.endswith(f"的{BOUNCE2}不會套用")
