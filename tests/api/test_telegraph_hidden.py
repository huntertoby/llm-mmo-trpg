"""HID-1b：環境預告不得帶出隱蔽且未揭露單位的 HP、護盾、狀態（實際跑引擎的表格測試）。

過濾只在 API 層（``telegraph_out``）；引擎的預告維持完整。已揭露、相鄰、一般敵人、我方的內容與
改前相同。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.engine.helpers import library, no_reactions
from tests.engine.skill_helpers import SID, U2, U3, battle
from tests.engine.test_time_bomb import bomb_skill
from trpg.api.hidden_info import hidden_unit_ids, mask_telegraph_changes
from trpg.api.schemas import TelegraphOut
from trpg.api.telegraph import telegraph_out
from trpg.engine.environment import Telegraph, TelegraphChange, telegraph
from trpg.engine.state import BattleState, StatusInstance
from trpg.engine.traps import strip_hidden_traps
from trpg.narrative.telegraph import change_text
from trpg.shared.types import Team, UnitId

HP = 317
"""不會和座標、半徑撞號的 HP。"""
SHIELD = 73

BARREL = ((5, 2, "oil_barrel"),)
FIRE = ((5, 1, "fire"),)
EFFECTS = ("explosion", "shield", "downed", "status_expiry", "bomb")
HIDDEN_STATUS_IDS = ("concealed", "shielded", "burning", "time_bomb")


def _base(subject: str, hp: int, effect: str) -> tuple[BattleState, UnitId]:
    """主角 (3, 3)；``subject`` 站在 (5, 3)；回傳戰場與該單位 ID（還沒上狀態）。"""
    tank = (5, 3, no_reactions("bandit", max_hp=hp))
    barrel = effect in ("explosion", "shield", "downed")
    scenery: dict[str, Any] = {"objects": BARREL, "surfaces": FIRE} if barrel else {}
    if subject == "ally":
        state = battle(bomb_skill(), [(0, 0, no_reactions("bandit"))], allies=[(5, 3)], **scenery)
        state.units[U2].hp = hp
        return state, U2
    if subject == "adjacent":
        return battle(bomb_skill(), [tank], allies=[(4, 3)], **scenery), U3
    return battle(bomb_skill(), [tank], **scenery), U2


def _scene(subject: str, effect: str) -> tuple[BattleState, UnitId]:
    state, uid = _base(subject, 1 if effect == "downed" else HP, effect)
    unit = state.units[uid]
    if subject != "plain":
        unit.statuses.append(StatusInstance("concealed", 3))
    if subject == "revealed":
        unit.statuses.append(StatusInstance("revealed", 2))
    if effect == "shield":
        unit.statuses.append(StatusInstance("shielded", 3, amount=SHIELD))
    if effect == "status_expiry":
        unit.statuses.append(StatusInstance("burning", 1))
    if effect == "bomb":
        bomb = StatusInstance("time_bomb", 1, source_id=state.active_unit, skill_id=SID)
        unit.statuses.append(bomb)
    return state, uid


def _raw(state: BattleState) -> Telegraph:
    return telegraph(strip_hidden_traps(state, Team.ALLY))


def _unmasked_rows(state: BattleState) -> list[dict[str, object]]:
    """改前的輸出：引擎的項目＋全知文字。"""
    lib = library()

    def name(template_id: str) -> str:
        template = lib.units.get(template_id)
        return template_id if template is None else template.name_zh

    return [
        {**c.model_dump(mode="json"), "text": change_text(state, c, name)}
        for c in _raw(state).changes
    ]


def _rows(out: TelegraphOut) -> list[dict[str, object]]:
    return [c.model_dump(mode="json") for c in out.changes]


def _out(state: BattleState) -> TelegraphOut:
    return telegraph_out(state, library(), Team.ALLY)


def test_every_effect_really_produces_the_change_it_is_meant_to() -> None:
    """表格的前提：引擎真的產生對應的預告（避免情境失效後測試空轉）。"""
    expected = {
        "explosion": "unit_damaged",
        "shield": "unit_damaged",
        "downed": "unit_downed",
        "bomb": "bomb_exploded",
    }
    for effect, kind in expected.items():
        state, uid = _scene("hidden", effect)
        assert any(c.kind == kind and c.unit_id == uid for c in _raw(state).changes), effect


@pytest.mark.parametrize("effect", EFFECTS)
@pytest.mark.parametrize("subject", ["adjacent", "revealed", "plain", "ally"])
def test_visible_units_keep_the_exact_telegraph(subject: str, effect: str) -> None:
    state, uid = _scene(subject, effect)
    assert uid not in hidden_unit_ids(state, Team.ALLY)
    assert _rows(_out(state)) == _unmasked_rows(state)


@pytest.mark.parametrize("effect", EFFECTS)
def test_hidden_unit_entries_carry_no_numbers_or_status_names(effect: str) -> None:
    state, uid = _scene("hidden", effect)
    assert uid in hidden_unit_ids(state, Team.ALLY)
    for c in (c for c in _out(state).changes if c.unit_id == uid):
        assert (c.before, c.after, c.amount) == (None, None, None), c
        assert not any(word in c.text for word in ("定時炸彈", "半徑", "倒下", "點傷害")), c.text
        assert str(HP) not in c.text and str(SHIELD) not in c.text


@pytest.mark.parametrize("effect", EFFECTS)
def test_serialized_hidden_telegraph_has_no_hp_shield_or_status_ids(effect: str) -> None:
    state, uid = _scene("hidden", effect)
    response = _out(state).model_dump_json()
    assert str(HP) not in response and str(SHIELD) not in response
    data = json.loads(response)
    del data["burning"]  # 欄位名（著火的物件）和狀態 ID 同名，內容與單位無關
    scanned = json.dumps(data)
    for status_id in HIDDEN_STATUS_IDS:
        assert status_id not in scanned
    assert all(c["amount"] is None for c in data["changes"] if c["unit_id"] == uid)


def test_downed_forecast_is_withheld_for_hidden_but_engine_keeps_it() -> None:
    state, uid = _scene("hidden", "downed")
    assert any(c.kind == "unit_downed" and c.unit_id == uid for c in _raw(state).changes)
    assert not any(c.kind == "unit_downed" and c.unit_id == uid for c in _out(state).changes)


def test_hidden_damage_keeps_the_warning_position_but_not_the_number() -> None:
    state, uid = _scene("hidden", "shield")
    raw = next(c for c in _raw(state).changes if c.kind == "unit_damaged" and c.unit_id == uid)
    assert raw.amount is not None  # 引擎的預告維持完整
    out = next(c for c in _out(state).changes if c.kind == "unit_damaged" and c.unit_id == uid)
    assert out.pos == raw.pos and out.amount is None and out.text.endswith("將受到傷害")


def test_hidden_bomb_keeps_the_blast_tiles_without_naming_the_status() -> None:
    state, uid = _scene("hidden", "bomb")
    raw = next(c for c in _raw(state).changes if c.kind == "bomb_exploded")
    assert raw.unit_id == uid and raw.amount is not None
    out = next(c for c in _out(state).changes if c.kind == "bomb_exploded")
    assert out.pos == raw.pos and out.tiles == raw.tiles and out.amount is None
    assert "爆炸" in out.text


def test_status_expiry_is_not_part_of_the_changes() -> None:
    """查證：狀態到期（``status_removed``）不是環境回合的事件，預告的 ``changes`` 沒有這一類。"""
    state, uid = _scene("hidden", "status_expiry")
    assert [c for c in _raw(state).changes if c.unit_id == uid] == []


def test_mask_leaves_unrelated_changes_alone_and_returns_new_objects() -> None:
    other = TelegraphChange(kind="unit_damaged", unit_id=U2, amount=5)
    mine = TelegraphChange(kind="unit_damaged", unit_id=U3, amount=5)
    masked = mask_telegraph_changes((other, mine), frozenset({U3}))
    assert masked[0] is other and masked[1].amount is None and mine.amount == 5
