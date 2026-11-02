"""預覽的誓約警告（Phase 5C-3b）：引擎判定、API 照樣帶出來（不靠前端猜）。"""

from __future__ import annotations

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.api.presenter import preview_response
from trpg.content.world_oaths import OathCheck
from trpg.engine import EndTurn, build_setup, resolve
from trpg.engine.battle import begin_battle
from trpg.engine.oaths import OathSetup
from trpg.engine.preview import preview
from trpg.engine.state import BattleState


def _state(check: OathCheck | None) -> BattleState:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    if check is not None:
        oath = OathSetup(
            template="oath_attack_each_turn",
            check=check,
            bonus_status="oath_bonus_medium",
            penalty_status="oath_broken",
            label_zh="每回合都要攻擊",
        )
        setup = setup.model_copy(update={"oath": oath})
    state = begin_battle(setup, 2).state
    for _ in range(50):
        holder = None if state.oath is None else state.oath.holder
        if state.active_unit == holder or (holder is None and state.active_unit is not None):
            return state
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    raise AssertionError("輪不到主角")


def test_preview_out_carries_engine_oath_warning() -> None:
    state = _state(OathCheck(kind="attack_each_turn"))
    assert state.active_unit is not None
    end = EndTurn(unit_id=state.active_unit)
    out = preview_response(preview(state, end), state)
    assert out.oath_warning is not None
    assert "每回合都要攻擊" in out.oath_warning and "破誓 2 回合" in out.oath_warning


def test_no_warning_without_oath() -> None:
    state = _state(None)
    assert state.active_unit is not None
    out = preview_response(preview(state, EndTurn(unit_id=state.active_unit)), state)
    assert out.oath_warning is None
