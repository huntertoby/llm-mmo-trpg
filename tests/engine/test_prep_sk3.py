"""戰前佈置（SK-3，#166，06 6.38 第 11 點）。

開戰前（雙方都還沒行動）在我方起始區免費放 1 個自己的陷阱、刻印或表面；條件是裝備著會做這件事
的技能，放了就算那招用過（照常進冷卻）；每場 1 個。只有 ``BattleSetup.prep_placement``（網頁）
才開窗；沒有可放的技能時不開。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import caster_template, make_map, make_setup, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import (
    Attack,
    BattleSetup,
    BattleState,
    EndTurn,
    Move,
    Prepare,
    begin_battle,
    legal_actions,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.actions import ACTION_ADAPTER
from trpg.engine.events import (
    EventBase,
    PrepPlaced,
    PrepSkipped,
    RuneInscribed,
    SkillCooldownChanged,
    SurfaceChanged,
    TrapPlaced,
)
from trpg.engine.prep import prep_options
from trpg.engine.runner import replay
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Surface, Team

ZONE = [(0, 0), (1, 0), (0, 1), (1, 1)]
HERO_XY, FOE_XY = (0, 0), (6, 6)
TRAP, SIGIL, RAIN = "skill_bear_trap", "skill_hunt_sigil", "skill_downpour"


def setup(
    skills: Sequence[str] = (TRAP,), *, prep: bool = True, foe_first: bool = False
) -> BattleSetup:
    m = make_map(FLAT7, ally=ZONE, enemy=[FOE_XY, (5, 6)])
    hero = caster_template(list(skills), base="hero_mage", max_hp=60)
    base = make_setup(
        m,
        [spawn(Team.ALLY, HERO_XY, hero), spawn(Team.ENEMY, FOE_XY, no_reactions(max_hp=40))],
    )
    update: dict[str, Any] = {
        "prep_placement": prep,
        "first_team": Team.ENEMY if foe_first else Team.ALLY,
    }
    return base.model_copy(update=update)


def opened(skills: Sequence[str] = (TRAP,), **kw: Any) -> BattleState:
    return begin_battle(setup(skills, **kw), 1).state


def of[T: EventBase](events: Sequence[EventBase], kind: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def place(state: BattleState, skill: str | None, xy: tuple[int, int] | None) -> Any:
    pos = None if xy is None else Pos(x=xy[0], y=xy[1])
    return resolve(state, Prepare(unit_id=U1, skill_id=skill, target_pos=pos))


# ---------------------------------------------------------------------------
# 開窗
# ---------------------------------------------------------------------------


def test_the_window_opens_only_with_the_flag_and_an_eligible_skill() -> None:
    state = opened()
    assert state.prep is not None
    assert state.prep.unit_id == U1
    assert sorted((p.x, p.y) for p in state.prep.zone) == sorted(ZONE)
    assert opened(prep=False).prep is None
    assert opened(skills=()).prep is None  # 沒有可放的技能：直接跳過


def test_options_list_each_skill_and_the_free_zone_tiles() -> None:
    state = opened(skills=(TRAP, SIGIL, RAIN))
    found = {o.skill_id: (o.kind, o.tiles) for o in prep_options(state)}
    assert found[TRAP][0] == "trap" and HERO_XY not in found[TRAP][1]  # 陷阱不能放在有人的格子
    assert found[SIGIL] == ("rune", ((0, 0), (1, 0), (0, 1), (1, 1)))
    assert found[RAIN][0] == "surface"


def test_the_flag_does_not_change_an_ordinary_battle_when_the_window_stays_shut() -> None:
    """沒有可放的技能時，有沒有旗標的開場逐字相同。"""
    a = begin_battle(setup(skills=(), prep=True), 3)
    b = begin_battle(setup(skills=(), prep=False), 3)
    assert [e.model_dump(mode="json") for e in a.events] == [
        e.model_dump(mode="json") for e in b.events
    ]
    assert state_to_json(a.state) == state_to_json(b.state)


# ---------------------------------------------------------------------------
# 佈置
# ---------------------------------------------------------------------------


def test_placing_a_trap_is_free_and_puts_the_skill_on_cooldown() -> None:
    state = opened()
    hero = state.units[U1]
    ap, mana = hero.ap, hero.mana
    result = place(state, TRAP, (1, 1))
    (placed,) = of(result.events, PrepPlaced)
    assert (placed.skill_id, placed.kind, (placed.pos.x, placed.pos.y)) == (TRAP, "trap", (1, 1))
    assert [(t.pos.x, t.pos.y) for t in of(result.events, TrapPlaced)] == [(1, 1)]
    after = result.state.units[U1]
    assert (after.ap, after.mana) == (ap, mana)
    assert after.cooldowns[TRAP] == 2
    assert [e.remaining for e in of(result.events, SkillCooldownChanged)] == [2]
    assert result.state.prep is None


def test_placing_a_rune_and_a_surface() -> None:
    rune = place(opened(skills=(SIGIL,)), SIGIL, (0, 0))
    assert [(e.pos.x, e.pos.y, e.tag) for e in of(rune.events, RuneInscribed)] == [(0, 0, "hunt")]
    rain = place(opened(skills=(RAIN,)), RAIN, (1, 0))
    changed = of(rain.events, SurfaceChanged)
    assert [(e.pos.x, e.pos.y, e.after) for e in changed] == [(1, 0, Surface.WATER)]  # 只放 1 格
    assert rain.state.tile(1, 0).surface_creator == U1


def test_only_one_per_battle() -> None:
    result = place(opened(skills=(TRAP, SIGIL)), SIGIL, (0, 0))
    with pytest.raises(IllegalActionError, match="戰前佈置"):
        place(result.state, TRAP, (1, 1))


def test_skipping_closes_the_window() -> None:
    result = place(opened(), None, None)
    assert of(result.events, PrepSkipped) and result.state.prep is None
    with pytest.raises(IllegalActionError):
        place(result.state, TRAP, (1, 1))


@pytest.mark.parametrize(
    ("skill", "xy", "message"),
    [
        (TRAP, (3, 3), "起始區"),
        (TRAP, (0, 0), "起始區"),  # 主角站著的格子不能放陷阱
        (SIGIL, (0, 0), "不能拿來戰前佈置"),  # 沒裝備
        (TRAP, None, "選一格"),
    ],
)
def test_illegal_placements_are_rejected(
    skill: str, xy: tuple[int, int] | None, message: str
) -> None:
    with pytest.raises(IllegalActionError, match=message):
        place(opened(), skill, xy)


def test_any_other_action_closes_the_window() -> None:
    state = opened()
    assert state.active_unit == U1
    moved = resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=0), Pos(x=1, y=0))))
    assert moved.state.prep is None
    assert all(not isinstance(a, Prepare) for a in legal_actions(state))


def test_the_hero_can_place_before_an_enemy_who_goes_first() -> None:
    state = opened(foe_first=True)
    assert state.active_unit is not None and state.units[state.active_unit].team is Team.ENEMY
    assert state.prep is not None
    result = place(state, TRAP, (1, 1))
    assert of(result.events, TrapPlaced)
    assert result.state.active_unit == state.active_unit  # 不換手、不花對方的回合
    with pytest.raises(IllegalActionError):  # 一般動作仍要照行動順序
        resolve(result.state, Attack(unit_id=U1, target_id=U2))


def test_an_enemy_acting_first_closes_the_window() -> None:
    state = opened(foe_first=True)
    assert state.active_unit is not None
    after = resolve(state, EndTurn(unit_id=state.active_unit))
    assert after.state.prep is None


# ---------------------------------------------------------------------------
# 確定性、重播、序列化、文字
# ---------------------------------------------------------------------------


def test_state_json_round_trip_keeps_the_window() -> None:
    state = opened()
    again = state_from_json(state_to_json(state))
    assert again.prep == state.prep
    assert state.clone().prep == state.prep
    assert '"prep"' not in state_to_json(opened(prep=False))


def test_the_action_round_trips_and_replays() -> None:
    action = Prepare(unit_id=U1, skill_id=TRAP, target_pos=Pos(x=1, y=1))
    assert ACTION_ADAPTER.validate_json(ACTION_ADAPTER.dump_json(action)) == action
    s = setup()
    first = place(begin_battle(s, 1).state, TRAP, (1, 1))
    end = resolve(first.state, EndTurn(unit_id=U1))
    replayed = replay(s, 1, [action, EndTurn(unit_id=U1)])
    assert state_to_json(replayed.state) == state_to_json(end.state)


def test_same_input_same_result() -> None:
    state = opened(skills=(RAIN,))
    a, b = place(state, RAIN, (1, 1)), place(state, RAIN, (1, 1))
    assert [e.model_dump(mode="json") for e in a.events] == [
        e.model_dump(mode="json") for e in b.events
    ]
    assert state_to_json(a.state) == state_to_json(b.state)


def test_log_lines() -> None:
    state = opened()
    result = place(state, TRAP, (1, 1))
    (placed,) = of(result.events, PrepPlaced)
    assert "戰前佈置" in (describe_event(placed, result.state) or "")
    skipped = place(state, None, None)
    (event,) = of(skipped.events, PrepSkipped)
    assert "戰前佈置" in (describe_event(event, skipped.state) or "")
