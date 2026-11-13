"""RG-7：符籙師的定身符要瞄準（18）、噴岩龜的熔岩彈燃燒 2 回合不留火（19）。

使用者對 ``docs/玩法PM交接.md`` 4.1.1 A 段「都照建議」（#162 細節，玩法 PM 809c61f5b）。內容在 RG-1
已改好、AF-1 核對過；這裡用正式內容實際跑引擎補行為測試：施放＝瞄準（不擲骰、不生效），施放者下一個
自己的回合開始才擲出；熔岩彈打中只上 2 回合燃燒、不改任何格子的表面。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from tests.engine.test_dual_dagger_skills_dd1 import HIT, d20s
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.actions import EndTurn
from trpg.engine.events import (
    AttackRolled,
    EventBase,
    FollowupCharged,
    StatusApplied,
    SurfaceChanged,
)
from trpg.engine.lock_on import lock_target_of
from trpg.shared.types import Team, UnitId

CASTER, HERO = UnitId("unit_0001"), UnitId("unit_0002")
TALISMAN, LAVA = "skill_binding_talisman", "skill_lava_bomb"
ROW = "0" * 12


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def arena(unit: str, skill: str) -> BattleState:
    """``unit``（敵方，只帶 ``skill``）在 (1, 4)；主角（我方，不反應、HP 多）在 (5, 4)。"""
    m = make_map("\n".join([ROW] * 9), ally=[(5, 4)], enemy=[(1, 4)])
    caster = template(unit, reactions=[], skills=(skill,))
    hero = template("bandit", max_hp=300, reactions=[], speed=0)
    state = make_state(m, [spawn(Team.ENEMY, (1, 4), caster), spawn(Team.ALLY, (5, 4), hero)])
    return give_turn(state, CASTER)


def to_caster_turn(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    events: list[EventBase] = []
    s = state
    for _ in range(8):
        assert s.active_unit is not None
        result = resolve(s, EndTurn(unit_id=s.active_unit))
        events += result.events
        s = result.state
        if s.active_unit == CASTER:
            return s, events
    raise AssertionError("沒有輪回施放者")


@pytest.mark.parametrize(
    ("unit", "skill", "status", "duration"),
    [
        ("sect_talisman_caster", TALISMAN, "root", 1),
        ("lava_tortoise", LAVA, "burning", 2),
    ],
)
def test_the_shot_is_telegraphed_then_lands_on_the_next_turn(
    monkeypatch: pytest.MonkeyPatch, unit: str, skill: str, status: str, duration: int
) -> None:
    state = arena(unit, skill)
    d20s(monkeypatch, [], rest=HIT)
    cast = resolve(state, UseSkill(unit_id=CASTER, skill_id=skill, target_id=HERO))
    (charged,) = of(cast.events, FollowupCharged)
    assert charged.lock_target_id == HERO
    assert lock_target_of(cast.state.units[CASTER]) == HERO
    assert not [e for e in of(cast.events, AttackRolled) if e.skill_id == skill]
    assert not of(cast.events, StatusApplied)  # 瞄準當下不生效
    _, events = to_caster_turn(cast.state)
    applied = [e for e in of(events, StatusApplied) if e.target_id == HERO]
    assert [(e.status_id, e.duration) for e in applied] == [(status, duration)]


def test_the_lava_bomb_leaves_no_fire_on_the_ground(monkeypatch: pytest.MonkeyPatch) -> None:
    state = arena("lava_tortoise", LAVA)
    d20s(monkeypatch, [], rest=HIT)
    cast = resolve(state, UseSkill(unit_id=CASTER, skill_id=LAVA, target_id=HERO))
    after, events = to_caster_turn(cast.state)
    assert any(e.status_id == "burning" for e in of(events, StatusApplied))
    assert not of(cast.events + events, SurfaceChanged)
    assert [t.surface for t in after.tiles] == [t.surface for t in state.tiles]


def test_the_lava_bomb_content_is_burning_two_rounds_without_a_surface() -> None:
    lava = library().skills[LAVA]
    assert lava.lock_on and lava.enemy_only
    kinds = [e.type for e in lava.effects]
    assert "create_surface" not in kinds
    burns = [e for e in lava.effects if e.type == "apply_status"]
    assert [(e.status, e.duration) for e in burns] == [("burning", 2)]
    assert "skill_fire_wall" not in library().unit("lava_tortoise").skills
