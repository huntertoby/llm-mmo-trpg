"""Phase 2E-3 5.2：陷阱（放置、隱藏、enter／delay 觸發、過期、放置者離場、深度、重播、AI）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of, script_rolls
from tests.engine.test_passive_triggers import always
from trpg.content.environment import AiProfileTable, TrapAiRules
from trpg.engine import Attack, BattleState, EndTurn, Move, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.events import (
    DamageDealt,
    StatusApplied,
    TrapExpired,
    TrapPlaced,
    TrapTriggered,
    TriggerLimitReached,
    UnitDowned,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.preview import preview
from trpg.engine.traps import strip_hidden_traps, visible_traps
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

CINDER, BEAR = "skill_cinder_mine", "skill_bear_trap"


def scene(max_depth: int = 3) -> BattleState:
    """U1（法師，我方）在 (2, 3) 手上有回合；U2（敵人）在 (6, 3)；U3（我方弓手）在 (0, 0)。"""
    m = make_map(FLAT7, ally=[(2, 3), (0, 0)], enemy=[(6, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 3), caster_template([CINDER, BEAR])),
            spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=999)),
            spawn(Team.ALLY, (0, 0), no_reactions("hero_archer")),
        ],
        max_trigger_depth=max_depth,
    )
    return give_turn(state, U1)


def place(state: BattleState, skill: str, xy: tuple[int, int]) -> BattleState:
    return resolve(
        state, UseSkill(unit_id=U1, skill_id=skill, target_pos=Pos(x=xy[0], y=xy[1]))
    ).state


def walk(state: BattleState, *cells: tuple[int, int]):  # type: ignore[no-untyped-def]
    path = tuple(Pos(x=x, y=y) for x, y in cells)
    return resolve(give_turn(state, U2), Move(unit_id=U2, path=path))


def end_turns(state: BattleState, count: int) -> tuple[BattleState, list]:  # type: ignore[type-arg]
    events: list = []  # type: ignore[type-arg]
    for _ in range(count):
        result = resolve(state, EndTurn(unit_id=state.active_unit))  # type: ignore[arg-type]
        state, events = result.state, [*events, *result.events]
    return state, events


def test_placing_a_trap_stores_it_and_snapshots_the_owner_attributes() -> None:
    state = scene()
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BEAR, target_pos=Pos(x=4, y=3)))
    (placed,) = of(result, TrapPlaced)
    assert (placed.owner_id, placed.skill_id, placed.trigger, placed.rounds) == (
        U1,
        BEAR,
        "enter",
        3,
    )
    (trap,) = result.state.traps
    assert trap.xy == (4, 3) and trap.team is Team.ALLY and trap.owner_id == U1
    assert trap.attributes and not of(result, DamageDealt)


def test_a_tile_holds_only_one_trap_and_must_be_free() -> None:
    state = place(scene(), BEAR, (4, 3))
    state = give_turn(state, U1)
    with pytest.raises(IllegalActionError):
        place(state, CINDER, (4, 3))
    with pytest.raises(IllegalActionError):
        place(state, CINDER, (6, 3))  # 有單位（也超出射程）
    cells = {
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_pos is not None and a.skill_id == CINDER
    }
    assert (4, 3) not in cells and (3, 3) in cells


def test_traps_are_hidden_from_the_other_team() -> None:
    state = place(scene(), BEAR, (4, 3))
    assert len(visible_traps(state, Team.ALLY)) == 1 and visible_traps(state, Team.ENEMY) == []
    assert strip_hidden_traps(state, Team.ENEMY).traps == []
    assert strip_hidden_traps(state, Team.ALLY) is state
    assert len(state.traps) == 1  # 原狀態不變


def test_an_enemy_stepping_on_an_enter_trap_triggers_it(monkeypatch: pytest.MonkeyPatch) -> None:
    state = place(scene(), BEAR, (4, 3))
    script_rolls(monkeypatch, [5, 19])  # 傷害骰 5、定身檢定 19（施加成功）
    result = walk(state, (6, 3), (5, 3), (4, 3), (3, 3))
    (triggered,) = of(result, TrapTriggered)
    assert (triggered.unit_id, triggered.cause, triggered.owner_id) == (U2, "enter", U1)
    assert triggered.trigger_depth == 1
    (dealt,) = of(result, DamageDealt)
    assert dealt.target_id == U2 and dealt.source_id == U1
    assert any(e.status_id == "root" for e in of(result, StatusApplied))
    assert result.state.traps == []
    assert result.state.units[U2].pos == Pos(x=4, y=3)  # 被定身：移動在陷阱格停下


def test_a_trap_does_not_trigger_for_the_owners_team() -> None:
    state = place(scene(), BEAR, (4, 3))
    state = give_turn(state, U3)
    state.units[U3].pos = Pos(x=3, y=3)
    result = resolve(state, Move(unit_id=U3, path=(Pos(x=3, y=3), Pos(x=4, y=3), Pos(x=4, y=4))))
    assert not of(result, TrapTriggered) and len(result.state.traps) == 1


def test_a_delay_trap_explodes_on_the_owners_second_turn_start() -> None:
    state = place(scene(), CINDER, (5, 3))  # 十字範圍包含敵人 (6, 3)
    assert state.traps[0].remaining == 2
    state, events = end_turns(state, 3)  # 回到 U1 的下一個回合 → 剩 1
    assert (
        state.traps
        and state.traps[0].remaining == 1
        and not any(isinstance(e, TrapTriggered) for e in events)
    )
    state = give_turn(state, U1)
    state, events = end_turns(state, 3)  # 再回到 U1 → 引爆
    (triggered,) = [e for e in events if isinstance(e, TrapTriggered)]
    assert triggered.cause == "delay" and triggered.unit_id is None
    assert state.traps == []
    hurt = {e.target_id for e in events if isinstance(e, DamageDealt)}
    assert U2 in hurt and U1 not in hurt


def test_an_enter_trap_expires_after_its_rounds() -> None:
    state = place(scene(), BEAR, (4, 3))
    expired: list[TrapExpired] = []
    for _ in range(3):
        state, events = end_turns(give_turn(state, state.active_unit), 3)  # type: ignore[arg-type]
        expired += [e for e in events if isinstance(e, TrapExpired)]
    assert [e.reason for e in expired] == ["timeout"] and state.traps == []


def test_the_traps_disappear_when_the_owner_goes_down(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=8)
    state = place(scene(), BEAR, (4, 3))
    state.units[U1].hp = 1
    state = give_turn(state, U2)
    state.units[U2].pos = Pos(x=3, y=3)
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert of(result, UnitDowned)
    assert [e.reason for e in of(result, TrapExpired)] == ["source_lost"]
    assert result.state.traps == []


def test_down_unit_returns_the_trap_expired_event_without_duplicating_it() -> None:
    """驗收條件 5：remove_traps_of 的 TrapExpired 出現在 down_unit 的回傳值中，且不重複
    （ctx.events 裡只有一筆，不是「回傳值裡有、ctx.events 又多寫一次」）。"""
    state = place(scene(), BEAR, (4, 3))
    ctx = Ctx(state.clone())
    owner = ctx.state.units[U1]
    events = down_unit(ctx, owner)
    returned = [e for e in events if isinstance(e, TrapExpired)]
    logged = [e for e in ctx.events if isinstance(e, TrapExpired)]
    assert len(returned) == 1 and returned[0].reason == "source_lost"
    assert logged == returned  # 同一筆事件物件，不是重複發出的兩筆


def test_a_trap_over_the_trigger_depth_limit_stays_in_place() -> None:
    state = place(scene(max_depth=0), BEAR, (4, 3))
    result = walk(state, (6, 3), (5, 3), (4, 3), (3, 3))
    assert of(result, TriggerLimitReached) and not of(result, TrapTriggered)
    assert len(result.state.traps) == 1


def test_the_preview_does_not_reveal_hidden_traps_but_the_real_move_triggers_them() -> None:
    state = give_turn(place(scene(), BEAR, (4, 3)), U2)
    move = Move(unit_id=U2, path=(Pos(x=6, y=3), Pos(x=5, y=3), Pos(x=4, y=3), Pos(x=3, y=3)))
    seen = preview(state, move)
    assert not [o for o in seen.certain + seen.possible if o.kind.startswith("trap")]
    assert state.traps  # 預覽不修改狀態
    assert of(resolve(state, move), TrapTriggered)


def test_traps_replay_identically() -> None:
    state = place(scene(), BEAR, (4, 3))
    a, b = walk(state, (6, 3), (5, 3), (4, 3), (3, 3)), walk(state, (6, 3), (5, 3), (4, 3), (3, 3))
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


def test_the_ai_places_traps_near_enemies_but_not_on_its_own_side() -> None:
    state = scene()
    state.units[U2].pos = Pos(x=5, y=3)
    ai = UtilityAI(library().ai_profiles)
    cells = [
        s.action
        for s in ai.rank(state)
        if isinstance(s.action, UseSkill) and s.action.skill_id in (CINDER, BEAR)
    ]
    assert cells
    for action in cells:
        assert action.target_pos is not None
        dist = abs(action.target_pos.x - 5) + abs(action.target_pos.y - 3)
        assert 1 <= dist <= 3


def test_the_ai_never_places_a_cross_trap_over_an_ally() -> None:
    state = scene()
    state.units[U2].pos = Pos(x=4, y=3)
    ai = UtilityAI(library().ai_profiles)
    for s in ai.rank(state):
        action = s.action
        if isinstance(action, UseSkill) and action.skill_id == CINDER:
            assert action.target_pos is not None
            near_self = abs(action.target_pos.x - 2) + abs(action.target_pos.y - 3) <= 1
            assert not near_self


def _move_with_effect(state: BattleState, mode: str):  # type: ignore[no-untyped-def]
    from trpg.engine.context import Ctx  # noqa: PLC0415
    from trpg.engine.effects import execute  # noqa: PLC0415
    from trpg.engine.effects.models import MoveUnitEffect  # noqa: PLC0415

    ctx = Ctx(state.clone())
    ctx.state.units[U2].pos = Pos(x=5, y=3)
    execute(ctx, [MoveUnitEffect(unit_id=U2, dest=(4, 3), mode=mode)])  # type: ignore[arg-type]
    return ctx


def test_forced_movement_triggers_a_trap_but_teleporting_does_not() -> None:
    state = place(scene(), BEAR, (4, 3))
    assert any(isinstance(e, TrapTriggered) for e in _move_with_effect(state, "forced").events)
    teleported = _move_with_effect(state, "teleport")
    assert not any(isinstance(e, TrapTriggered) for e in teleported.events)
    assert len(teleported.state.traps) == 1


def test_the_enemy_ai_decides_the_same_with_or_without_the_hidden_traps() -> None:
    state = give_turn(place(scene(), BEAR, (4, 3)), U2)
    state.units[U2].pos = Pos(x=5, y=3)
    ai = UtilityAI(library().ai_profiles)
    stripped = strip_hidden_traps(state, Team.ENEMY)
    assert stripped.traps == [] and state.traps
    assert ai(state) == ai(stripped)
    assert [s.score for s in ai.rank(state)] == [s.score for s in ai.rank(stripped)]


def test_traps_and_stacks_survive_a_json_round_trip() -> None:
    from trpg.engine.state import state_from_json, state_to_json  # noqa: PLC0415

    state = place(scene(), BEAR, (4, 3))
    state.units[U1].stacks = {"static_charge": 2}
    state.units[U1].stack_expiry = {"static_charge": 5}
    dumped = state_to_json(state)
    back = state_from_json(dumped)
    assert back == state and back.traps == state.traps and state_to_json(back) == dumped


def test_the_ai_trap_numbers_live_in_the_content_with_their_original_values() -> None:
    table = library().ai_profiles
    assert table.trap.max_active == 2 and table.trap.near == 3
    assert table.trap.shape_factor("single") == 1
    assert table.trap.shape_factor("cross") == Fraction(3, 2)
    assert table.trap.shape_factor("square3") == 2
    assert all(p.trap == table.trap for p in table.profiles)  # 每個行為模式共用表格層級的數值


def test_an_unknown_trap_shape_uses_the_default_factor_instead_of_raising() -> None:
    rules = TrapAiRules(shape_factor_permille={"single": 1000}, default_factor_permille=1250)
    assert rules.shape_factor("never_heard_of_it") == Fraction(5, 4)
    # AI 端：把所有形狀係數都清空，十字陷阱走預設係數，rank 不可 KeyError。
    data = library().ai_profiles.model_dump()
    for profile in data["profiles"]:
        del profile["trap"]
    data["trap"] = {"shape_factor_permille": {}}
    ai = UtilityAI(AiProfileTable.model_validate(data))
    state = scene()
    state.units[U2].pos = Pos(x=5, y=3)
    assert any(
        isinstance(s.action, UseSkill) and s.action.skill_id == CINDER for s in ai.rank(state)
    )


def test_changing_the_content_trap_limit_changes_the_ai_candidates() -> None:
    data = library().ai_profiles.model_dump()
    for profile in data["profiles"]:
        del profile["trap"]
    data["trap"] = {"near": 1}
    ai = UtilityAI(AiProfileTable.model_validate(data))
    state = scene()
    state.units[U2].pos = Pos(x=5, y=3)
    for s in ai.rank(state):
        action = s.action
        if isinstance(action, UseSkill) and action.skill_id in (CINDER, BEAR):
            assert action.target_pos is not None
            assert abs(action.target_pos.x - 5) + abs(action.target_pos.y - 3) <= 1
