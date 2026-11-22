"""KD-1 第 8 項（E5 美術小修、08 8.29 E5 第 7 點）：沒有套用到某招的裝備變形，寫在那招說明卡最後的灰字。

測試修正技與詞條沿用 ``test_reshape_gate_e5``（只在測試裡，不進 ``content/``）。
"""

from __future__ import annotations

from typing import Any

from tests.engine.test_reshape_gate_e5 import BOUNCE, PUSHY, STRIKE, U1, gear_library, scene
from trpg.engine.modifiers import gear_reshapes_left_out
from trpg.engine.state import BattleState
from trpg.engine.view import project_for
from trpg.shared.types import Team


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
