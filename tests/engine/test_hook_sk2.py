"""鉤（SK-2，#166，06 6.38 第 8 點）：沿直線打中路上第一個單位，拉到施放者相鄰格；不拉進致命
地形；推拉 2 格上限的例外；巨型頭目照第 9 點算撞擊。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    spawn_giant,
    with_rolls,
)
from trpg.engine import BattleState, UseSkill, legal_actions, preview, resolve, state_to_json
from trpg.engine.events import AttackRolled, Collided, EventBase, UnitMoved
from trpg.narrative.skills import effect_summary
from trpg.shared.types import Team, UnitId
from trpg.skillgen.validate import validate_skill

SID = "skill_t_hook"
U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
FLAT = "\n".join(["0" * 9] * 9)
LINE5: dict[str, Any] = {"type": "line", "size": 5}
HOOK: dict[str, Any] = {"type": "hook"}


def hook_skill(*extra: dict[str, Any], cooldown: int = 3) -> Any:
    return make_skill(SID, LINE5, [*extra, HOOK], cost={"mana": 0, "cooldown": cooldown})


def arena(
    foes: Sequence[tuple[int, int]],
    *,
    allies: Sequence[tuple[int, int]] = (),
    terrain: str | None = None,
    skill: Any = None,
) -> BattleState:
    skill = skill or hook_skill()
    m = make_map(FLAT, terrain, ally=[(0, 4), *allies], enemy=list(foes) or [(8, 8)])
    spawns = [spawn(Team.ALLY, (0, 4), caster_template([skill]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return with_rolls(give_turn(make_state(m, spawns, skills=[skill]), U1), [(20, 19)])


def east(state: BattleState) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, direction="east"))


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def test_pulls_the_first_enemy_next_to_the_caster_beyond_the_two_tile_cap() -> None:
    state = arena([(4, 4), (5, 4)])
    result = east(state)
    assert [r.target_id for r in of(result.events, AttackRolled)] == [U2]  # 只打第一個
    assert result.state.units[U2].xy == (1, 4)  # 拉了 3 格
    assert result.state.units[U3].xy == (5, 4)
    assert of(result.events, Collided) == []


def test_an_ally_first_on_the_line_blocks_the_hook() -> None:
    state = arena([(4, 4)], allies=[(2, 4)])
    result = east(state)
    assert of(result.events, AttackRolled) == []
    assert result.state.units[U3].xy == (4, 4)


def test_stops_before_deadly_terrain() -> None:
    terrain = "\n".join("." * 9 if y != 4 else "..~......" for y in range(9))
    result = east(arena([(4, 4)], terrain=terrain))
    assert result.state.units[U2].xy == (3, 4)
    assert result.state.units[U2].alive
    assert of(result.events, Collided) == []


def test_out_of_reach_or_already_adjacent_does_nothing() -> None:
    far = east(arena([(6, 4)]))
    assert of(far.events, AttackRolled) == [] and far.state.units[U2].xy == (6, 4)
    near = east(arena([(1, 4)]))
    assert near.state.units[U2].xy == (1, 4)
    assert not [m for m in of(near.events, UnitMoved) if m.unit_id == U2]


def test_the_giant_boss_does_not_move_and_takes_one_collision() -> None:
    skill = hook_skill()
    m = make_map(FLAT, None, ally=[(0, 4)], enemy=[(5, 4)])
    spawns = [spawn(Team.ALLY, (0, 4), caster_template([skill])), spawn_giant(Team.ENEMY, (5, 4))]
    state = with_rolls(give_turn(make_state(m, spawns, skills=[skill]), U1), [(20, 19)])
    giant = next(u for u in state.units.values() if u.footprint == 3)
    result = east(state)
    assert result.state.units[giant.id].xy == (5, 4)
    assert [(c.unit_id, c.obstacle, c.shortfall) for c in of(result.events, Collided)] == [
        (giant.id, "immovable", 1)
    ]


def test_damage_on_the_same_skill_only_hits_the_hooked_unit() -> None:
    fire = {"type": "damage", "dice": "1d4", "element": "fire"}
    state = arena([(3, 4), (4, 4)], skill=hook_skill(fire))
    result = east(with_rolls(state, [(20, 19), (4, 2)]))
    damaged = {e.target_id for e in result.events if getattr(e, "type", "") == "damage_dealt"}
    assert damaged == {U2}


def test_legal_actions_preview_and_determinism() -> None:
    state = arena([(4, 4)])
    action = UseSkill(unit_id=U1, skill_id=SID, direction="east")
    assert action in legal_actions(state)
    before = state_to_json(state)
    assert preview(state, action) is not None
    assert state_to_json(state) == before
    first, second = east(state), east(state)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]


@pytest.mark.parametrize(
    ("skill", "rule"),
    [
        (hook_skill(cooldown=2), "cap.hook_cooldown"),
        (make_skill(SID, {"type": "single", "range": 5}, [HOOK], cost={"cooldown": 3}), None),
    ],
)
def test_validation(skill: Any, rule: str | None) -> None:
    violations = validate_skill(skill, library())
    if rule is None:
        assert any("只能搭配形狀" in v.message for v in violations)
    else:
        assert rule in {v.rule for v in violations}
    assert "cap.hook_cooldown" not in {v.rule for v in validate_skill(hook_skill(), library())}


def test_card_text() -> None:
    skill = hook_skill()
    text = effect_summary(library(), skill, skill.effects[0])
    assert "第一個敵人" in text and "拉到你身邊" in text
