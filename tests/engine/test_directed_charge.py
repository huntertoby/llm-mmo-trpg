"""Phase 3J-2：定向蓄力原語＋龍的蓄力吐息的行為一致測試（``docs/phases/Phase3J計畫.md`` 4.6）。

龍形態中普攻＝選方向開始蓄力；下一個自己的回合開始時以錐形（大小 3）釋放 1d8＋智力 × 0.3 的元素
傷害；蓄力中倒下、暈眩、冰凍、離開形態就取消；預告同環境預告。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import of
from tests.engine.test_delayed_followup import until_turn_of
from tests.engine.test_passive_triggers import always
from trpg.content.form_text import form_sentence
from trpg.content.rules import SkillSlots
from trpg.content.skills import CHARGING
from trpg.engine import (
    Attack,
    BattleState,
    EndStance,
    UseSkill,
    legal_actions,
    preview,
    project_for,
    resolve,
    telegraph,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.context import Ctx
from trpg.engine.delayed import charge_infos
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, DamageEffect
from trpg.engine.events import (
    DamageDealt,
    FollowupCancelled,
    FollowupCharged,
    FormLeft,
    SkillFollowup,
)
from trpg.engine.runner import replay
from trpg.engine.state import state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Team, UnitId

DRAGON = "skill_form_dragon"
U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
SLOTS = SkillSlots(active=12, passive=2, reaction=1, stance=2)
FLAT = "\n".join(["0000000000"] * 10)


def scene(*, foes: tuple[tuple[int, int], ...] = ((5, 3),)) -> BattleState:
    """U1（戰士，帶化身為龍）在 (3, 3) 手上有回合；敵人們各 999 HP、沒有反應。"""
    m = make_map(FLAT, ally=[(3, 3)], enemy=list(foes))
    owner = caster_template([DRAGON], base="hero_fighter", max_hp=999, stamina=40)
    spawns = [spawn(Team.ALLY, (3, 3), owner)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=999)) for xy in foes]
    state = give_turn(make_state(m, spawns, skill_slots=SLOTS), U1)  # type: ignore[arg-type]
    state.units[U1].mana = 40
    state.units[U1].stamina = 40
    state.units[U1].stamina_regen = 0
    return state


def in_dragon(state: BattleState, element: Element | None = None) -> BattleState:
    return resolve(state, UseSkill(unit_id=U1, skill_id=DRAGON, form_element=element)).state


def start_charge(state: BattleState, direction: str = "east") -> BattleState:
    return resolve(state, Attack(unit_id=U1, direction=direction)).state  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 資料與卡片句
# ---------------------------------------------------------------------------


def test_dragon_natural_weapon_is_a_charged_breath() -> None:
    weapon = library().ruleset.form_def("dragon").natural_weapon
    assert weapon.charge is not None and weapon.charge.size == 3
    assert (weapon.dice.count, weapon.dice.sides) == (1, 8)
    assert [a.value for a in weapon.attrs] == ["int"]
    assert set(weapon.element_choices) == {Element.FIRE, Element.ICE, Element.LIGHTNING}


def test_card_sentence_describes_the_charged_breath() -> None:
    rules = library().ruleset
    text = form_sentence(rules.forms, rules.form_def("dragon"), rules.core)
    assert "蓄力" in text and "錐形" in text and "大小 3" in text and "下回合" in text


# ---------------------------------------------------------------------------
# 開始蓄力
# ---------------------------------------------------------------------------


def test_basic_attack_in_dragon_form_starts_a_charge_in_that_direction() -> None:
    state = in_dragon(scene(), Element.ICE)
    ap = state.units[U1].ap
    result = resolve(state, Attack(unit_id=U1, direction="east"))
    (charged,) = of(result, FollowupCharged)
    assert charged.direction == "east" and charged.release == "next_turn"
    assert result.state.units[U1].ap == ap - 1  # 普攻的 AP
    assert result.state.units[U1].has_status(CHARGING)
    assert len(charged.tiles) == 9  # 錐形大小 3：1 + 3 + 5 格，全在正東
    assert all(t.x > 3 for t in charged.tiles)
    assert not of(result, DamageDealt)  # 這回合沒有傷害


@pytest.mark.parametrize(
    ("foe", "direction"),
    [((6, 3), "east"), ((0, 3), "west"), ((3, 6), "south"), ((3, 0), "north"), ((5, 4), "east")],
)
def test_attack_with_a_target_charges_toward_that_target(
    foe: tuple[int, int], direction: str
) -> None:
    state = in_dragon(scene(foes=(foe,)))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (charged,) = of(result, FollowupCharged)
    assert charged.direction == direction


def test_direction_is_only_for_charged_weapons() -> None:
    with pytest.raises(IllegalActionError):
        resolve(scene(), Attack(unit_id=U1, direction="east"))  # 沒進入龍形態：一般武器


def test_legal_actions_list_four_directions_and_none_while_charging() -> None:
    state = in_dragon(scene())
    dirs = [a.direction for a in legal_actions(state) if isinstance(a, Attack) and a.direction]
    assert dirs == ["north", "east", "south", "west"]
    assert not [a for a in legal_actions(start_charge(state)) if isinstance(a, Attack)]


def test_attack_requires_exactly_one_selection() -> None:
    with pytest.raises(ValueError, match="恰好"):
        Attack(unit_id=U1, direction="east", target_id=U2)
    with pytest.raises(ValueError, match="恰好"):
        Attack(unit_id=U1)


# ---------------------------------------------------------------------------
# 釋放：下一個自己的回合開始時
# ---------------------------------------------------------------------------


def test_released_at_next_turn_start_and_damage_matches_the_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=5)  # 命中、不暴擊、骰面 5
    state = in_dragon(scene(foes=((5, 3), (4, 3), (3, 1))), Element.FIRE)
    charging = start_charge(state)
    attr = charging.units[U1].attributes["int"]  # type: ignore[index]
    _, events = until_turn_of(charging, U1)
    assert len(of_events(events, SkillFollowup)) == 1
    hits = [e for e in of_events(events, DamageDealt) if e.source_id == U1]
    assert {e.target_id for e in hits} == {U2, U3}  # 東邊的兩個敵人；北邊的沒被打到
    assert all(e.element is Element.FIRE for e in hits)
    expected = 5 + attr * 300 // 1000  # 1d8（骰面 5）＋ 智力 × 0.3（卡片句的數字）
    assert all(e.amount == expected for e in hits)


def of_events(events: list[Any], kind: type) -> list[Any]:
    return [e for e in events if isinstance(e, kind)]


def test_the_element_chosen_on_entry_is_the_breath_element(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=3)
    for element in (Element.ICE, Element.LIGHTNING):
        charging = start_charge(in_dragon(scene(), element))
        _, events = until_turn_of(charging, U1)
        hits = [e for e in of_events(events, DamageDealt) if e.source_id == U1]
        assert hits and all(e.element is element for e in hits)


def test_release_clears_the_charge_and_logs_it() -> None:
    charging = start_charge(in_dragon(scene()))
    state, events = until_turn_of(charging, U1)
    assert not state.units[U1].has_status(CHARGING)
    (released,) = of_events(events, SkillFollowup)
    assert released.when == "delayed" and len(released.tiles) == 9


def test_release_uses_the_casters_current_position() -> None:
    charging = start_charge(in_dragon(scene()), "east")
    charging.units[U1].pos = Pos(x=2, y=3)  # 蓄力後被推開：範圍跟著施放者走
    (info,) = charge_infos(charging)
    assert all(t.x > 2 for t in info.tiles) and len(info.tiles) == 9


def test_a_wall_or_edge_can_shrink_the_cone() -> None:
    state = in_dragon(scene())
    state.units[U1].pos = Pos(x=8, y=3)
    result = resolve(state, Attack(unit_id=U1, direction="east"))
    (charged,) = of(result, FollowupCharged)
    assert 0 < len(charged.tiles) < 9  # 只含施放者看得到的格子（地圖邊緣）


# ---------------------------------------------------------------------------
# 取消：倒下、暈眩、冰凍、離開形態
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effect", "reason"),
    [
        (ApplyStatusEffect(target_id=U1, status_id="stun"), "controlled"),
        (ApplyStatusEffect(target_id=U1, status_id="frozen"), "controlled"),
        (DamageEffect(target_id=U1, cause="status", mode="lethal"), "downed"),
    ],
)
def test_downed_stunned_or_frozen_dragons_lose_the_charge(effect: Any, reason: str) -> None:
    state = start_charge(in_dragon(scene()))
    ctx = Ctx(state)
    execute(ctx, [effect])
    assert [e.reason for e in of_events(ctx.events, FollowupCancelled)] == [reason]
    assert not state.units[U1].has_status(CHARGING)
    if state.units[U1].alive:
        _, events = until_turn_of(state, U1)
        assert of_events(events, SkillFollowup) == []
    else:
        assert any(isinstance(e, FormLeft) for e in ctx.events)


def test_other_statuses_keep_the_charge() -> None:
    state = start_charge(in_dragon(scene()))
    ctx = Ctx(state)
    execute(ctx, [ApplyStatusEffect(target_id=U1, status_id="slow")])
    assert of_events(ctx.events, FollowupCancelled) == []
    assert state.units[U1].has_status(CHARGING)


def test_leaving_the_form_cancels_the_charge() -> None:
    result = resolve(start_charge(in_dragon(scene())), EndStance(unit_id=U1))
    assert [e.reason for e in of(result, FollowupCancelled)] == ["form_left"]
    assert not result.state.units[U1].has_status(CHARGING)


def test_charging_again_replaces_the_old_charge() -> None:
    from trpg.engine.delayed import start_directed_charge  # noqa: PLC0415

    state = start_charge(in_dragon(scene()), "east")
    ctx = Ctx(state)
    start_directed_charge(ctx, state.units[U1], "west")
    assert [e.reason for e in of_events(ctx.events, FollowupCancelled)] == ["replaced"]
    status = state.units[U1].get_status(CHARGING)
    assert status is not None and status.direction == "west"


# ---------------------------------------------------------------------------
# 預告、視圖、存檔、敘述、AI、重播
# ---------------------------------------------------------------------------


def test_telegraph_and_view_show_the_cone() -> None:
    charging = start_charge(in_dragon(scene()))
    tele = telegraph(charging)
    assert [(c.unit_id, len(c.tiles)) for c in tele.charges] == [(U1, 9)]
    view = project_for(charging, Team.ENEMY)
    unit = next(u for u in view.units if u.id == U1)
    status = next(s for s in unit.statuses if s.status_id == CHARGING)
    assert len(status.charge_tiles) == 9 and status.release == "next_turn"


def test_preview_of_a_directed_attack_shows_the_cone() -> None:
    p = preview(in_dragon(scene()), Attack(unit_id=U1, direction="north"))
    assert any(isinstance(e, FollowupCharged) for e in p.max_events)
    assert p.damage is None and len(p.affected_tiles) == 9


def test_state_roundtrips_while_charging() -> None:
    charging = start_charge(in_dragon(scene(), Element.LIGHTNING), "west")
    again = state_from_json(state_to_json(charging))
    status = again.units[U1].get_status(CHARGING)
    assert status is not None and status.direction == "west"
    assert state_to_json(again) == state_to_json(charging)


def test_narrative_lines_for_start_and_cancel() -> None:
    result = resolve(in_dragon(scene()), Attack(unit_id=U1, direction="east"))
    lines = [describe_event(e, result.state) for e in of(result, FollowupCharged)]
    assert lines[0] is not None and "蓄力" in lines[0] and "東" in lines[0]
    cancelled = resolve(result.state, EndStance(unit_id=U1))
    cancel_lines = [describe_event(e, cancelled.state) for e in of(cancelled, FollowupCancelled)]
    assert cancel_lines[0] is not None and "解除" in cancel_lines[0]


def test_ai_dragon_charges_toward_the_most_enemies() -> None:
    state = in_dragon(scene(foes=((6, 3), (6, 2), (6, 4), (3, 7))))
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, Attack)
    (charged,) = of(resolve(state, action), FollowupCharged)
    assert charged.direction == "east"


def test_a_charged_battle_replays_identically() -> None:
    m = make_map(FLAT, ally=[(3, 3)], enemy=[(5, 3), (4, 3)])
    owner = caster_template([DRAGON], base="hero_fighter", stamina=40)
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (3, 3), owner),
            spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=90)),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=90)),
        ],
    )
    state = start_battle(setup, 5)
    steps: list[Any] = []
    ai = UtilityAI(library().ai_profiles)
    for _ in range(80):
        if state.ended:
            break
        unit = state.active
        assert unit is not None
        action = UseSkill(unit_id=U1, skill_id=DRAGON) if not steps and unit.id == U1 else ai(state)
        steps.append(action)
        state = resolve(state, action).state
    run = replay(setup, 5, steps)
    assert state_to_json(run.state) == state_to_json(state)
    assert any(isinstance(e, FollowupCharged) and e.direction for e in run.events)
    assert any(isinstance(e, SkillFollowup) for e in run.events)
