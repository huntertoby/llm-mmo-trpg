"""表面歸屬 ``creator`` 與 ``on_enter_surface``（Phase 3C-3b 5.1）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from tests.engine.test_passive_triggers import always, passive, triggered
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.engine import BattleState, EndTurn, Move, project_for, resolve
from trpg.engine.effects import (
    CreateSurfaceEffect,
    ElementTouchEffect,
    MoveUnitEffect,
    PushEffect,
    run_effects,
)
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    SkillTriggered,
    SurfaceChanged,
    TriggerLimitReached,
    UnitMoved,
)
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

U3 = UnitId("unit_0003")
OWNER_XY, FOE_XY, ALLY_XY = (3, 3), (4, 3), (3, 4)
OIL_XY = (5, 3)

_PUSH_EAST = {"type": "push", "distance": 1, "affects": "enemies"}


def enter_passive(
    surface: Surface | None = None,
    skill_id: str = "skill_t_enter",
    target: str = "other",
    effects: Sequence[dict[str, Any]] | None = None,
) -> SkillDef:
    spec: dict[str, Any] = {"event": "on_enter_surface", "target": target, "max_per_round": 3}
    if surface is not None:
        spec["surface"] = surface
    base = passive(skill_id, "on_hit", target=target, effects=effects)
    return base.model_copy(update={"trigger": TriggerSpec.model_validate(spec)})


def scene(
    skills: Sequence[SkillDef] = (),
    *,
    owner_xy: tuple[int, int] = OWNER_XY,
    foe_xy: tuple[int, int] = FOE_XY,
    max_trigger_depth: int | None = None,
) -> BattleState:
    """U1 我方（持有者）、U2 敵人、U3 我方隊友。"""
    m = make_map(FLAT7, ally=[owner_xy, ALLY_XY], enemy=[foe_xy])
    owner = caster_template(skills, base="hero_fighter", max_hp=60)
    core: dict[str, Any] = {}
    if max_trigger_depth is not None:
        core["max_trigger_depth"] = max_trigger_depth
    state = make_state(
        m,
        [
            spawn(Team.ALLY, owner_xy, owner),
            spawn(Team.ENEMY, foe_xy, no_reactions(max_hp=999)),
            spawn(Team.ALLY, ALLY_XY, no_reactions(max_hp=999)),
        ],
        skills=list(skills),
        **core,
    )
    return give_turn(state, U1)


def with_oil(
    state: BattleState, creator: UnitId | None = U1, xy: tuple[int, int] = OIL_XY
) -> BattleState:
    """直接把 ``xy`` 設為油表面（``creator`` 為造出它的單位；``None`` 模擬地圖原有的表面）。"""
    s = state.clone()
    s.set_tile(*xy, replace(s.tile(*xy), surface=Surface.OIL, surface_creator=creator))
    return s


def walk(state: BattleState, unit: UnitId, *path: tuple[int, int]) -> Any:
    steps = tuple(Pos(x=x, y=y) for x, y in path)
    return resolve(give_turn(state, unit), Move(unit_id=unit, path=steps))


def entered(events: Sequence[EventBase]) -> list[str]:
    return [e.trigger for e in triggered(events)]


def create_oil(source: UnitId | None, xy: tuple[int, int], surface: Surface = Surface.OIL) -> Any:
    return CreateSurfaceEffect(
        source_id=source, pos=xy, surface=surface, team=Team.ALLY, react=False
    )


# ---------------------------------------------------------------------------
# 表面 creator
# ---------------------------------------------------------------------------


def test_a_skill_created_surface_records_its_creator_and_team() -> None:
    result = run_effects(scene(), [create_oil(U1, OIL_XY)])
    tile = result.state.tile(*OIL_XY)
    assert (tile.surface, tile.surface_creator, tile.surface_team) == (Surface.OIL, U1, Team.ALLY)


def test_environment_surfaces_have_no_creator() -> None:
    """蔓延、天氣、地圖原有的表面沒有 creator。"""
    m = make_map(FLAT7, ally=[OWNER_XY], enemy=[FOE_XY], surfaces=[(1, 1, "oil")])
    state = make_state(m, [spawn(Team.ALLY, OWNER_XY, "hero_fighter"), spawn(Team.ENEMY, FOE_XY)])
    assert state.tile(1, 1).surface_creator is None
    weather = CreateSurfaceEffect(pos=(5, 5), surface=Surface.WATER, cause="weather")
    assert run_effects(state, [weather]).state.tile(5, 5).surface_creator is None


def test_replacing_a_surface_takes_the_new_creator_and_clearing_it_drops_the_creator() -> None:
    state = with_oil(scene(), creator=U2)
    assert state.tile(*OIL_XY).surface_creator == U2
    replaced = run_effects(state, [create_oil(U1, OIL_XY, Surface.WATER)])
    assert replaced.state.tile(*OIL_XY).surface_creator == U1
    cleared = run_effects(replaced.state, [create_oil(U1, OIL_XY, Surface.NONE)])
    assert cleared.state.tile(*OIL_XY).surface_creator is None


def test_interaction_surfaces_keep_the_source_that_touched_them() -> None:
    """環境互動產生的表面沿用觸及它的來源：U2 的油被 U1 的火元素觸及，變成 U1 的火。"""
    state = with_oil(scene(), creator=U2)
    touch = ElementTouchEffect(source_id=U1, pos=(5, 3), element=Element.FIRE)
    result = run_effects(state, [touch])
    assert [e.after for e in result.events if isinstance(e, SurfaceChanged)] == [Surface.FIRE]
    assert result.state.tile(*OIL_XY).surface_creator == U1


def test_the_view_exposes_the_surface_creator_and_it_survives_cloning() -> None:
    state = with_oil(scene())
    view = project_for(state, Team.ALLY)
    tile = next(t for t in view.tiles if (t.x, t.y) == OIL_XY)
    assert tile.surface_creator == U1
    assert state.clone().tile(*OIL_XY).surface_creator == U1
    assert view.model_dump(mode="json")["tiles"][3 * 7 + 5]["surface_creator"] == U1


# ---------------------------------------------------------------------------
# on_enter_surface
# ---------------------------------------------------------------------------


def test_an_enemy_walking_into_the_holders_surface_triggers_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]))
    result = walk(state, U2, FOE_XY, OIL_XY)
    (fired,) = triggered(result.events)
    assert (fired.unit_id, fired.trigger, fired.other_id, fired.trigger_depth) == (
        U1,
        "on_enter_surface",
        U2,
        1,
    )
    assert [d.target_id for d in result.events if isinstance(d, DamageDealt)] == [U2]
    assert fired.seq > max(e.seq for e in result.events if isinstance(e, UnitMoved))


def test_a_forced_move_into_the_surface_triggers_it(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]))
    push = PushEffect(source_id=U1, target_id=U2, direction=(1, 0), distance=1)
    assert entered(run_effects(state, [push]).events) == ["on_enter_surface"]


def test_a_friendly_unit_entering_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]), xy=(3, 5))
    result = walk(state, U3, ALLY_XY, (3, 5))
    assert any(isinstance(e, UnitMoved) for e in result.events)
    assert triggered(result.events) == []


def test_the_holders_own_walk_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive(target="self")]), xy=(2, 3))
    assert triggered(walk(state, U1, OWNER_XY, (2, 3)).events) == []


def test_a_surface_with_no_creator_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]), creator=None)
    assert triggered(walk(state, U2, FOE_XY, OIL_XY).events) == []


def test_someone_elses_surface_does_not_trigger_the_holder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """表面是隊友 U3 造的，持有者 U1 的被動不觸發。"""
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]), creator=U3)
    assert triggered(walk(state, U2, FOE_XY, OIL_XY).events) == []


def test_the_surface_parameter_filters_by_surface_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    fire_only = scene([enter_passive(Surface.FIRE)])
    assert triggered(walk(with_oil(fire_only), U2, FOE_XY, OIL_XY).events) == []
    oil_only = scene([enter_passive(Surface.OIL)])
    assert entered(walk(with_oil(oil_only), U2, FOE_XY, OIL_XY).events) == ["on_enter_surface"]


def test_a_surface_appearing_under_a_unit_or_standing_on_it_does_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    made = run_effects(scene([enter_passive()]), [create_oil(U1, FOE_XY)])
    assert made.state.tile(*FOE_XY).surface_creator == U1 and triggered(made.events) == []
    # 敵人回合開始時站在上面、原地結束回合也不算
    ended = resolve(give_turn(made.state, U2), EndTurn(unit_id=U2))
    assert triggered(ended.events) == []


def test_a_teleport_into_the_surface_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = with_oil(scene([enter_passive()]))
    effect = MoveUnitEffect(source_id=U2, unit_id=U2, dest=OIL_XY, mode="teleport")
    assert triggered(run_effects(state, [effect]).events) == []


def test_enter_surface_chains_stop_at_the_depth_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """持有者的被動把敵人推向下一格油，又觸發自己：停在 ``max_trigger_depth`` 並發出
    ``TriggerLimitReached``（戰鬥照常結算完）。"""
    always(monkeypatch)
    skill = enter_passive(effects=[_PUSH_EAST])
    state = scene([skill], owner_xy=(0, 3), foe_xy=(1, 3), max_trigger_depth=2)
    for x in (2, 3, 4, 5, 6):
        state = with_oil(state, xy=(x, 3))
    result = walk(state, U2, (1, 3), (2, 3))
    fired = [e for e in result.events if isinstance(e, SkillTriggered)]
    assert [e.trigger_depth for e in fired] == [1, 2]
    limit = [e for e in result.events if isinstance(e, TriggerLimitReached)]
    assert [(e.skill_id, e.depth) for e in limit] == [(skill.id, 3)]
    assert result.state.units[U2].xy == (4, 3)
