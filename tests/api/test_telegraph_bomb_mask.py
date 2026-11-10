"""HID-1c：定時炸彈預告（``BombOut``）對隱蔽且未揭露的攜帶者的遮罩（實際跑引擎的表格測試）。

5.1.2 第 7 條：倒數、半徑不送，文字通用；單位、位置、波及格子、``explodes`` 保留。引擎預告維持完整，
已揭露與我方的內容和改前相同。
"""

from __future__ import annotations

import json

import pytest

from tests.engine.helpers import library, no_reactions
from tests.engine.skill_helpers import SID, U2, battle
from tests.engine.test_time_bomb import bomb_skill
from trpg.api.hidden_info import hidden_unit_ids
from trpg.api.schemas import BombOut, TelegraphOut
from trpg.api.telegraph import telegraph_out
from trpg.engine.environment import TelegraphBomb, telegraph
from trpg.engine.state import BattleState, StatusInstance
from trpg.engine.traps import strip_hidden_traps
from trpg.narrative.events import cells_text, xy_text
from trpg.narrative.telegraph import bomb_text
from trpg.shared.types import Team, UnitId

FORBIDDEN_WORDS = ("定時炸彈", "半徑", "次環境回合爆炸", "time_bomb")
"""未揭露項目的文字不得出現的字（狀態名、倒數、半徑）。"""


def _scene(subject: str, turns: int) -> tuple[BattleState, UnitId]:
    """主角 (3, 3)；``subject`` 站在 (5, 3) 身上帶定時炸彈，還要 ``turns`` 次環境回合爆炸。"""
    if subject == "ally":
        state = battle(bomb_skill(), [(0, 0, no_reactions("bandit"))], allies=[(5, 3)])
    else:
        state = battle(bomb_skill(), [(5, 3, no_reactions("bandit"))])
    unit = state.units[U2]
    if subject in ("hidden", "revealed"):
        unit.statuses.append(StatusInstance("concealed", 9))
    if subject == "revealed":
        unit.statuses.append(StatusInstance("revealed", 9))
    unit.statuses.append(
        StatusInstance("time_bomb", turns, source_id=state.active_unit, skill_id=SID)
    )
    return state, U2


def _engine_bomb(state: BattleState, uid: UnitId) -> TelegraphBomb:
    bombs = telegraph(strip_hidden_traps(state, Team.ALLY)).bombs
    return next(b for b in bombs if b.unit_id == uid)


def _out(state: BattleState) -> TelegraphOut:
    return telegraph_out(state, library(), Team.ALLY)


def _bomb(state: BattleState, uid: UnitId) -> BombOut:
    return next(b for b in _out(state).bombs if b.unit_id == uid)


@pytest.mark.parametrize("turns", [1, 3])
@pytest.mark.parametrize("subject", ["revealed", "ally"])
def test_visible_carriers_keep_the_exact_bomb(subject: str, turns: int) -> None:
    state, uid = _scene(subject, turns)
    assert uid not in hidden_unit_ids(state, Team.ALLY)
    raw = _engine_bomb(state, uid)
    assert raw.remaining == turns and raw.radius > 0  # 情境的前提
    assert _bomb(state, uid) == BombOut(**raw.model_dump(), text=bomb_text(state, raw))
    assert "定時炸彈" in _bomb(state, uid).text


@pytest.mark.parametrize(
    ("turns", "explodes", "when"),
    [(1, True, "下一次環境回合將發生爆炸"), (3, False, "有爆炸危險")],
)
def test_hidden_carrier_sends_only_position_area_and_timing_flag(
    turns: int, explodes: bool, when: str
) -> None:
    state, uid = _scene("hidden", turns)
    assert uid in hidden_unit_ids(state, Team.ALLY)
    raw = _engine_bomb(state, uid)
    assert (raw.remaining, raw.explodes) == (turns, explodes)  # 引擎的預告維持完整
    assert raw.radius > 0
    bomb = _bomb(state, uid)
    assert (bomb.remaining, bomb.radius) == (None, None)
    assert (bomb.unit_id, bomb.pos, bomb.tiles, bomb.explodes) == (
        raw.unit_id,
        raw.pos,
        raw.tiles,
        raw.explodes,
    )
    assert bomb.text == f"{xy_text(raw.pos)} {when}（{cells_text(raw.tiles)}）"


@pytest.mark.parametrize("turns", [1, 3])
def test_serialized_hidden_bomb_has_no_countdown_radius_or_status_name(turns: int) -> None:
    state, uid = _scene("hidden", turns)
    data = json.loads(_bomb(state, uid).model_dump_json())
    assert data["remaining"] is None and data["radius"] is None
    for word in FORBIDDEN_WORDS:
        assert word not in data["text"], word
    assert f"{turns} 次" not in data["text"]
    assert "time_bomb" not in json.dumps(json.loads(_out(state).model_dump_json())["bombs"])
