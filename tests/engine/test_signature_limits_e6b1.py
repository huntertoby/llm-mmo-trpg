"""E6-b1：改寫規則同時 1 個、招牌同時 3 個（08 8.27、8.30 第 4、5、10 點，#180）。"""

from __future__ import annotations

from collections.abc import Mapping

from tests.engine.helpers import give_turn, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_gear import Rolls
from tests.engine.test_gear_g3b import FIRE_MENDS, MOVE_ANY, U1, WAKE
from tests.engine.test_gear_g3b import _loadout as _g3b_loadout
from trpg.content.equipment import Loadout, chosen_key
from trpg.engine.activations import active_rule_change
from trpg.engine.state import BattleState, state_from_json, state_to_json
from trpg.shared.types import Team


def _arena(
    slots: Mapping[str, Rolls], chosen: tuple[str, ...] = (), *, team: Team = Team.ALLY
) -> BattleState:
    """U1 穿裝備（``chosen`` 是勾選）站在 (3, 3)，對面一個敵人。"""
    loadout: Loadout = _g3b_loadout(slots).model_copy(update={"chosen": chosen})
    m = make_map(FLAT7, None, ally=[(3, 3)], enemy=[(6, 6)])
    first = spawn(team, (3, 3), no_reactions("hero_fighter", max_hp=200)).model_copy(
        update={"equipment": loadout}
    )
    other = Team.ENEMY if team is Team.ALLY else Team.ALLY
    foe = spawn(other, (6, 6), no_reactions(max_hp=200))
    return give_turn(make_state(m, [first, foe]), U1)


def _rule_lines(state: BattleState) -> list[tuple[str, str, bool, str | None]]:
    gear = state.units[U1].gear
    return [
        (a.slot, a.affix.id, a.active, a.limited_by)
        for a in gear.affixes
        if a.affix.category == "rule"
    ]


# ---------------------------------------------------------------------------
# 第 1 項：改寫規則超過 1 條時標灰
# ---------------------------------------------------------------------------


def test_two_rules_keep_the_first_by_slot_order_and_grey_the_other() -> None:
    state = _arena({"neck": [FIRE_MENDS], "ring_1": [WAKE]})
    assert sorted(_rule_lines(state)) == [
        ("neck", FIRE_MENDS[0], True, None),
        ("ring_1", WAKE[0], False, "rule"),
    ]
    change = active_rule_change(state, state.units[U1])
    assert change is not None and change.rule.id == "fire_mends_allies"


def test_slot_order_not_affix_id_decides() -> None:
    """詞條 id 排序在前（bleeding_wake < fire_mends）也不影響：照欄位順序。"""
    state = _arena({"main_hand": [WAKE], "neck": [FIRE_MENDS]})
    change = active_rule_change(state, state.units[U1])
    assert change is not None and change.rule.id == "bleeding_wake"


def test_three_rules_keep_only_one() -> None:
    state = _arena({"body": [MOVE_ANY], "neck": [FIRE_MENDS], "ring_1": [WAKE]})
    active = [line for line in _rule_lines(state) if line[2]]
    assert [line[1] for line in active] == [MOVE_ANY[0]]


def test_the_chosen_rule_wins() -> None:
    slots = {"neck": [FIRE_MENDS], "ring_1": [WAKE]}
    state = _arena(slots, chosen=(chosen_key("ring_1", WAKE[0]),))
    assert sorted(_rule_lines(state)) == [
        ("neck", FIRE_MENDS[0], False, "rule"),
        ("ring_1", WAKE[0], True, None),
    ]
    change = active_rule_change(state, state.units[U1])
    assert change is not None and change.rule.id == "bleeding_wake"


def test_stale_choice_falls_back_to_slot_order() -> None:
    slots = {"neck": [FIRE_MENDS], "ring_1": [WAKE]}
    state = _arena(slots, chosen=(chosen_key("feet", WAKE[0]),))
    active = [line[1] for line in _rule_lines(state) if line[2]]
    assert active == [FIRE_MENDS[0]]


def test_same_rule_on_two_items_is_not_limited() -> None:
    state = _arena({"neck": [FIRE_MENDS], "ring_1": [FIRE_MENDS]})
    assert [line[3] for line in _rule_lines(state)] == [None, None]


def test_limited_by_survives_serialization_and_is_omitted_when_none() -> None:
    plain = _arena({"neck": [FIRE_MENDS]})
    assert "limited_by" not in state_to_json(plain)
    state = _arena({"neck": [FIRE_MENDS], "ring_1": [WAKE]})
    assert '"limited_by":"rule"' in state_to_json(state)
    assert state_to_json(state_from_json(state_to_json(state))) == state_to_json(state)
