"""PB-1c：頭目部位的 API（``UnitView.parts``、``BattleResponse.part_options``、帶 ``target_part`` 的
動作與預覽、頭目資訊被隱藏時藏部位數字）。

規格 ``docs/phases/PhasePB-1計畫.md`` 第 7 節第 1、8 點；隱藏規則是 PB-1a 待決 3 的開發 PM 裁定
（``api/hidden_info.py`` 登記）。正式內容：霧鎖真人（拂塵、氣海、長劍）。
"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library, with_rolls
from tests.engine.test_mist_lock_parts_pb1 import HERO, MASTER, arena
from trpg.api.hidden_info import event_hidden_fields, hidden_unit_ids
from trpg.api.presenter import (
    event_out,
    part_options_out,
    preview_response,
    team_events_out,
    traits_view,
)
from trpg.engine import legal_actions, resolve
from trpg.engine.actions import Attack, EndTurn
from trpg.engine.events import PartDamaged
from trpg.engine.preview import preview
from trpg.engine.state import BattleState, StatusInstance
from trpg.engine.view import UnitView, project_for
from trpg.shared.types import Team


def _master(state: BattleState) -> UnitView:
    view = traits_view(state, Team.ALLY, library(), HERO)
    return next(u for u in view.units if u.id == MASTER)


def _hidden(state: BattleState) -> BattleState:
    """真人隱蔽、主角離開相鄰（看不到資訊）。"""
    out = state.clone()
    out.units[MASTER].statuses.append(StatusInstance("concealed", 3))
    out.units[HERO].pos = out.units[HERO].pos.model_copy(update={"x": 0})
    return out


def test_unit_view_lists_parts_by_id_with_hp_exposure_and_break_lines() -> None:
    state = arena(phase="mist_lock")
    parts = _master(state).parts
    assert parts is not None
    assert [p.id for p in parts] == ["dantian", "sword", "whisk"]
    by_id = {p.id: p for p in parts}
    hp = state.units[MASTER].part_hp
    assert {p.id: (p.hp, p.max_hp) for p in parts} == {k: (v, v) for k, v in hp.items()}
    assert {p.id: p.exposed for p in parts} == {"dantian": True, "sword": False, "whisk": True}
    assert by_id["dantian"].reach == "behind" and by_id["whisk"].reach == "any"
    assert by_id["whisk"].name_zh == "拂塵"
    assert by_id["whisk"].break_lines_zh == ("封住「霧遁」（正在蓄力就一起打斷）",)
    assert by_id["sword"].break_lines_zh == ("造成的傷害降為 75%", "打斷正在蓄力的強招")
    assert not any(p.broken for p in parts)


def test_units_without_parts_have_no_parts_field() -> None:
    state = arena()
    hero = next(u for u in project_for(state, Team.ALLY).units if u.id == HERO)
    assert hero.parts is None
    assert "parts" not in hero.model_dump(exclude_none=True)


def test_broken_parts_show_zero_and_broken() -> None:
    state = arena()
    state.units[MASTER].part_hp["whisk"] = 0
    state.units[MASTER].broken_parts = ("whisk",)
    whisk = next(p for p in _master(state).parts or () if p.id == "whisk")
    assert (whisk.hp, whisk.broken) == (0, True)
    assert whisk.max_hp is not None and whisk.max_hp > 0


def test_part_options_cover_the_attack_on_the_master_only() -> None:
    state = arena(phase="mist_lock")
    legal = tuple(legal_actions(state))
    out = part_options_out(state, legal)
    assert out is not None
    attack = next(o for o in out if o.type == "attack")
    assert (attack.target_id, attack.skill_id) == (MASTER, None)
    assert [(o.part_id, o.ok, o.reason_zh) for o in attack.options] == [
        ("dantian", False, "要從背後近戰才打得到"),
        ("sword", False, "這個階段還沒露出"),
        ("whisk", True, None),
    ]
    # 每一項都對到 legal_actions 裡某個帶 target_id 的動作；沒有部位的目標、移動、結束回合都不列
    assert all(o.target_id == MASTER for o in out)
    assert len({(o.type, o.skill_id, o.target_id) for o in out}) == len(out)


def test_part_options_are_none_without_part_targets() -> None:
    assert part_options_out(arena(), (EndTurn(unit_id=HERO),)) is None


def test_an_action_with_target_part_hits_that_part() -> None:
    state = with_rolls(arena(), [(20, 15)])  # 第一擲必中
    result = resolve(state, Attack(unit_id=HERO, target_id=MASTER, target_part="whisk"))
    hits = [e for e in result.events if isinstance(e, PartDamaged)]
    assert [e.part_id for e in hits] == ["whisk"]
    assert result.state.units[MASTER].part_hp["whisk"] == hits[0].hp_after
    out = [d for d in team_events_out(result.events, result.state, Team.ALLY)]
    shown = next(d for d in out if d["type"] == "part_damaged")
    assert shown["hp_after"] == hits[0].hp_after and "text" in shown


def test_preview_with_target_part_lists_part_damage_events() -> None:
    state = arena()
    action = Attack(unit_id=HERO, target_id=MASTER, target_part="whisk")
    out = preview_response(preview(state, action), state)
    kinds_min = [e["type"] for e in out.min_events]
    kinds_max = [e["type"] for e in out.max_events]
    assert "part_damaged" in kinds_min and "part_damaged" in kinds_max
    low = next(e for e in out.min_events if e["type"] == "part_damaged")
    assert low["part_id"] == "whisk" and isinstance(low["hp_after"], int)


def _part_event(state: BattleState) -> PartDamaged:
    return PartDamaged(
        seq=1,
        round=state.round,
        target_id=MASTER,
        part_id="whisk",
        name_zh="拂塵",
        amount=3,
        hp_before=20,
        hp_after=17,
    )


def test_hidden_master_hides_part_numbers_in_view() -> None:
    state = _hidden(arena())
    assert MASTER in hidden_unit_ids(state, Team.ALLY)
    master = _master(state)
    assert master.hidden_info is True and master.parts is not None
    assert all((p.hp, p.max_hp) == (None, None) for p in master.parts)
    # 名稱、破了沒、露出沒、「破掉會」照常
    assert [p.name_zh for p in master.parts] == ["氣海", "長劍", "拂塵"]
    assert all(p.break_lines_zh for p in master.parts)


def test_hidden_master_hides_part_hp_in_events_but_keeps_the_amount() -> None:
    state = _hidden(arena())
    hidden = hidden_unit_ids(state, Team.ALLY)
    event = _part_event(state)
    assert event_hidden_fields(event, hidden) == ("hp_before", "hp_after")
    data: dict[str, Any] = event_out(event, state, hidden)
    assert (data["hp_before"], data["hp_after"], data["amount"]) == (None, None, 3)
    assert "17" not in data.get("text", "") and "20" not in data.get("text", "")


def test_visible_master_keeps_part_numbers() -> None:
    state = arena()
    data = event_out(_part_event(state), state, hidden_unit_ids(state, Team.ALLY))
    assert (data["hp_before"], data["hp_after"]) == (20, 17)
    assert all(p.hp is not None for p in _master(state).parts or ())
