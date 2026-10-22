"""召喚物操控（Phase 3-33c，``docs/design/06-技能.md`` 6.29.2）：0 AP 模式切換（集火／守護我／
跟隨／待命）、1 AP 指揮（指定移動＋普攻）、四種模式的 AI 行為、我方 AI 自動切換、AI 估值納入
成長與灌注。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, of
from trpg.content.environment import SummonAiRules
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, legal_actions, project_for, resolve
from trpg.engine.actions import ACTION_ADAPTER, Attack, CommandSummon, Move, SetSummonMode
from trpg.engine.ai.summon import (
    auto_mode_action,
    effective_mode,
    filter_by_mode,
    mode_orders,
    summon_gains,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.events import (
    DamageDealt,
    SummonCommanded,
    SummonModeSet,
    UnitMoved,
    UnitSummoned,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.summon_control import command_options
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1 = UnitId("unit_0001")
SKELETON = "summon_skeleton_warrior"
TOTEM = "summon_war_totem"
SKILL_ID = "skill_t_summon"


def summon_skill(unit: str = SKELETON, duration: int = 4) -> SkillDef:
    return make_skill(
        SKILL_ID,
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": unit, "duration": duration}],
    )


def pos(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def arena(
    foes: Sequence[tuple[int, int]] = ((6, 3),),
    *,
    summon_at: tuple[int, int] = (2, 3),
    unit: str = SKELETON,
    foe_overrides: dict[str, Any] | None = None,
    foe_tags: Sequence[str] = (),
    owner: dict[str, Any] | None = None,
) -> tuple[BattleState, UnitId]:
    """U1 是施放者（站在 (0, 3)），已在 ``summon_at`` 召喚 ``unit``；之後是不反應的敵人。回傳
    （輪到召喚者的狀態，召喚物 ID）。"""
    skill = summon_skill(unit)
    m = make_map(FLAT7, ally=[(0, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill.id], **(owner or {})))]
    for xy in foes:
        spawns.append(
            spawn(
                Team.ENEMY,
                xy,
                no_reactions(max_hp=300, tags=list(foe_tags), **(foe_overrides or {})),
            )
        )
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_pos=pos(*summon_at)))
    [event] = of(result, UnitSummoned)
    return give_turn(result.state, U1), event.unit_id


def rules() -> SummonAiRules:
    return library().ai_profiles.by_id()["brute"].summon


def ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def as_summon(state: BattleState, sid: UnitId) -> BattleState:
    """輪到召喚物（給滿 AP 與移動點數）。"""
    return give_turn(state, sid)


def set_mode(
    state: BattleState, sid: UnitId, mode: Any, target: UnitId | None = None
) -> BattleState:
    return resolve(
        state, SetSummonMode(unit_id=U1, summon_id=sid, mode=mode, target_id=target)
    ).state


def foe_ids(state: BattleState) -> list[UnitId]:
    return [u.id for u in state.units_sorted() if u.team is Team.ENEMY]


# ---------------------------------------------------------------------------
# 預設模式
# ---------------------------------------------------------------------------


def test_new_summons_default_to_follow_and_totems_to_hold() -> None:
    state, sid = arena()
    assert state.units[sid].summon_mode == "follow"
    totem_state, tid = arena(unit=TOTEM)
    assert totem_state.units[tid].summon_mode == "hold"  # 6.29.5「AI 預設」＝不動


def test_the_view_shows_the_mode_but_not_for_totems_or_ordinary_units() -> None:
    state, sid = arena()
    views = {u.id: u for u in project_for(state, Team.ALLY).units}
    assert views[sid].summon_mode == "follow" and views[U1].summon_mode is None
    assert views[sid].summon_target_id is None and views[sid].commanded is False
    totem_state, tid = arena(unit=TOTEM)
    assert {u.id: u for u in project_for(totem_state, Team.ALLY).units}[tid].summon_mode is None


# ---------------------------------------------------------------------------
# 0 AP 模式切換
# ---------------------------------------------------------------------------


def test_switching_modes_costs_no_ap_and_emits_an_event() -> None:
    state, sid = arena()
    ap = state.units[U1].ap
    result = resolve(state, SetSummonMode(unit_id=U1, summon_id=sid, mode="hold"))
    assert result.state.units[U1].ap == ap and result.state.active_unit == U1
    assert result.state.units[sid].summon_mode == "hold"
    [event] = of(result, SummonModeSet)
    assert (event.unit_id, event.owner_id, event.mode, event.reason) == (sid, U1, "hold", "order")


def test_focus_needs_a_target_and_other_modes_forbid_one() -> None:
    with pytest.raises(ValidationError):
        SetSummonMode(unit_id=U1, summon_id=UnitId("unit_0003"), mode="focus")
    with pytest.raises(ValidationError):
        SetSummonMode(unit_id=U1, summon_id=UnitId("unit_0003"), mode="guard", target_id=U1)
    parsed = ACTION_ADAPTER.validate_python(
        {"type": "set_summon_mode", "unit_id": U1, "summon_id": "unit_0003", "mode": "guard"}
    )
    assert isinstance(parsed, SetSummonMode)


def test_focus_stores_the_target_and_logs_it() -> None:
    state, sid = arena(foes=((6, 3), (6, 5)))
    foe = foe_ids(state)[1]
    result = resolve(state, SetSummonMode(unit_id=U1, summon_id=sid, mode="focus", target_id=foe))
    unit = result.state.units[sid]
    assert (unit.summon_mode, unit.summon_target_id) == ("focus", foe)
    [event] = of(result, SummonModeSet)
    assert event.target_id == foe


@pytest.mark.parametrize(
    ("mode", "target"),
    [("focus", U1), ("focus", "unit_9999"), ("follow", None)],
)
def test_illegal_mode_changes(mode: str, target: str | None) -> None:
    state, sid = arena()
    with pytest.raises(IllegalActionError):
        resolve(
            state,
            SetSummonMode(
                unit_id=U1,
                summon_id=sid,
                mode=mode,  # type: ignore[arg-type]
                target_id=None if target is None else UnitId(target),
            ),
        )


def test_only_your_own_living_non_totem_summons_can_be_switched() -> None:
    state, sid = arena()
    foe = foe_ids(state)[0]
    with pytest.raises(IllegalActionError, match="不是你的召喚物"):
        resolve(state, SetSummonMode(unit_id=U1, summon_id=foe, mode="hold"))
    with pytest.raises(IllegalActionError, match="找不到召喚物"):
        resolve(state, SetSummonMode(unit_id=U1, summon_id=UnitId("unit_9999"), mode="hold"))
    totem_state, tid = arena(unit=TOTEM)
    with pytest.raises(IllegalActionError, match="圖騰"):
        resolve(totem_state, SetSummonMode(unit_id=U1, summon_id=tid, mode="guard"))
    gone = state.clone()
    gone.units[sid].dismissed = True
    with pytest.raises(IllegalActionError, match="不在戰場"):
        resolve(gone, SetSummonMode(unit_id=U1, summon_id=sid, mode="hold"))


def test_mode_changes_are_not_legal_actions_and_only_in_your_own_turn() -> None:
    state, sid = arena()
    assert not any(isinstance(a, SetSummonMode | CommandSummon) for a in legal_actions(state))
    other = give_turn(state, sid)
    with pytest.raises(IllegalActionError):
        resolve(other, SetSummonMode(unit_id=U1, summon_id=sid, mode="hold"))


def test_a_downed_focus_target_sends_the_summon_back_to_follow() -> None:
    state, sid = arena(foes=((6, 3), (6, 5)))
    foe = foe_ids(state)[0]
    state = set_mode(state, sid, "focus", foe)
    ctx = Ctx(state.clone())
    events = down_unit(ctx, ctx.state.units[foe])
    unit = ctx.state.units[sid]
    assert (unit.summon_mode, unit.summon_target_id) == ("follow", None)
    [event] = [e for e in events if isinstance(e, SummonModeSet)]
    assert (event.reason, event.mode, event.target_id) == ("target_gone", "follow", foe)


def test_a_focus_target_that_is_gone_is_treated_as_follow_by_the_ai() -> None:
    state, sid = arena()
    foe = foe_ids(state)[0]
    state = set_mode(state, sid, "focus", foe)
    assert effective_mode(state, state.units[sid]) == "focus"
    broken = state.clone()
    broken.units[foe].downed = True
    assert effective_mode(broken, broken.units[sid]) == "follow"
    assert mode_orders(broken, broken.units[sid], rules())


# ---------------------------------------------------------------------------
# AI：四種模式
# ---------------------------------------------------------------------------


def acted(state: BattleState, sid: UnitId) -> Any:
    return ai()(as_summon(state, sid))


def test_hold_stays_put_and_ignores_non_adjacent_enemies() -> None:
    state, sid = arena(foes=((4, 3),))  # 距離 2：follow 會走過去打
    assert isinstance(acted(state, sid), Move | Attack)
    held = set_mode(state, sid, "hold")
    assert not isinstance(acted(held, sid), Move | Attack)  # 原地守護或結束回合


def test_hold_still_hits_an_adjacent_enemy() -> None:
    state, sid = arena(foes=((3, 3),))
    held = set_mode(state, sid, "hold")
    action = acted(held, sid)
    assert isinstance(action, Attack) and action.target_id == foe_ids(held)[0]
    result = resolve(as_summon(held, sid), action)
    assert any(isinstance(e, DamageDealt) for e in result.events)
    assert result.state.units[sid].xy == (2, 3)


def test_hold_filter_removes_every_way_to_move() -> None:
    state, sid = arena(foes=((4, 3),))
    held = as_summon(set_mode(state, sid, "hold"), sid)
    actions = filter_by_mode(held, held.units[sid], legal_actions(held), rules())
    assert actions and not any(isinstance(a, Move) for a in actions)


def test_guard_never_wanders_more_than_the_radius_from_the_owner() -> None:
    state, sid = arena(foes=((6, 3),))
    guarded = as_summon(set_mode(state, sid, "guard"), sid)
    kept = filter_by_mode(guarded, guarded.units[sid], legal_actions(guarded), rules())
    owner_xy = guarded.units[U1].xy
    moves = [a for a in kept if isinstance(a, Move)]
    assert moves  # 還是可以在 2 格內調整位置
    for m in moves:
        dest = (m.path[-1].x, m.path[-1].y)
        assert abs(dest[0] - owner_xy[0]) + abs(dest[1] - owner_xy[1]) <= rules().guard_radius
    # 跟隨模式的對照：可以走得更遠
    followed = filter_by_mode(
        as_summon(state, sid), state.units[sid], legal_actions(as_summon(state, sid)), rules()
    )
    assert any(
        abs(a.path[-1].x - owner_xy[0]) + abs(a.path[-1].y - owner_xy[1]) > rules().guard_radius
        for a in followed
        if isinstance(a, Move)
    )


def test_guard_hits_the_enemy_threatening_the_owner_first() -> None:
    # 兩個不動的敵人：A 緊貼施放者（威脅），B 只貼著召喚物（離施放者 3 格，射程＋速度＋1 ＝ 2）
    state, sid = arena(foes=((1, 3), (2, 2)), foe_overrides={"speed": 0}, summon_at=(2, 3))
    threat, far = foe_ids(state)
    guarded = as_summon(set_mode(state, sid, "guard"), sid)
    tight = rules().model_copy(update={"guard_threat_range": 1})
    actions = filter_by_mode(guarded, guarded.units[sid], legal_actions(guarded), tight)
    targets = {a.target_id for a in actions if isinstance(a, Attack)}
    assert targets == {threat} and far not in targets
    # 跟隨模式兩個都打得到
    free = as_summon(state, sid)
    all_targets = {a.target_id for a in legal_actions(free) if isinstance(a, Attack)}
    assert {threat, far} <= all_targets


def test_focus_attacks_only_the_chosen_target_when_it_is_in_reach() -> None:
    state, sid = arena(foes=((3, 3), (2, 2)))  # 兩個都貼著召喚物
    first, second = foe_ids(state)
    focused = as_summon(set_mode(state, sid, "focus", second), sid)
    kept = filter_by_mode(focused, focused.units[sid], legal_actions(focused), rules())
    assert {a.target_id for a in kept if isinstance(a, Attack)} == {second}
    action = ai()(focused)
    assert isinstance(action, Attack) and action.target_id == second
    # 換成集火第一個
    other = as_summon(set_mode(state, sid, "focus", first), sid)
    action = ai()(other)
    assert isinstance(action, Attack) and action.target_id == first


def test_focus_walks_toward_a_far_target_instead_of_hitting_others() -> None:
    state, sid = arena(foes=((3, 3), (6, 6)))  # 第一個貼著、第二個很遠
    near, far = foe_ids(state)
    focused = as_summon(set_mode(state, sid, "focus", far), sid)
    kept = filter_by_mode(focused, focused.units[sid], legal_actions(focused), rules())
    assert not any(isinstance(a, Attack) and a.target_id == near for a in kept)
    action = ai()(focused)
    assert isinstance(action, Move)
    start = abs(2 - 6) + abs(3 - 6)
    assert abs(action.path[-1].x - 6) + abs(action.path[-1].y - 6) < start


def test_follow_has_a_soft_leash_to_the_owner() -> None:
    state, sid = arena()
    orders = mode_orders(state, state.units[sid], rules())
    [hold] = orders
    assert hold.kind == "hold_position" and hold.radius == rules().follow_radius


def test_summon_orders_ignore_team_orders() -> None:
    from trpg.engine.ai.orders import FocusTarget, OrderSet  # noqa: PLC0415

    state, sid = arena(foes=((6, 3), (6, 5)))
    foe = foe_ids(state)[1]
    team = OrderSet(team_orders=(FocusTarget(target=foe),))
    engine = UtilityAI(library().ai_profiles, orders=lambda s, u: team.for_unit(u))
    ctx = engine.order_context(as_summon(state, sid), state.units[sid])
    assert ctx is not None and ctx.focus is None  # 模式（跟隨）取代陣營指令


# ---------------------------------------------------------------------------
# 1 AP 指揮
# ---------------------------------------------------------------------------


def command(
    state: BattleState,
    sid: UnitId,
    path: Sequence[tuple[int, int]] = (),
    target: UnitId | None = None,
) -> Any:
    action = CommandSummon(
        unit_id=U1, summon_id=sid, path=tuple(pos(*p) for p in path), target_id=target
    )
    return resolve(state, action)


def test_command_moves_and_attacks_for_one_ap_without_using_the_summons_turn() -> None:
    state, sid = arena(foes=((5, 3),))
    foe = foe_ids(state)[0]
    summon = state.units[sid]
    kept = (summon.ap, summon.move_points, summon.moved_this_turn)
    ap = state.units[U1].ap
    result = command(state, sid, [(2, 3), (3, 3), (4, 3)], foe)
    after = result.state
    assert after.units[U1].ap == ap - 1  # 1 AP
    assert after.units[sid].xy == (4, 3)
    assert (
        after.units[sid].ap,
        after.units[sid].move_points,
        after.units[sid].moved_this_turn,
    ) == kept
    assert after.units[sid].commanded_round == after.round
    [commanded] = of(result, SummonCommanded)
    assert (commanded.unit_id, commanded.owner_id, commanded.target_id) == (sid, U1, foe)
    assert commanded.dest == pos(4, 3)
    assert any(isinstance(e, UnitMoved) and e.unit_id == sid for e in result.events)
    assert any(
        isinstance(e, DamageDealt) and e.source_id == sid and e.target_id == foe
        for e in result.events
    )


def test_command_can_only_move_or_only_attack() -> None:
    state, sid = arena(foes=((3, 3),))
    foe = foe_ids(state)[0]
    moved = command(state, sid, [(2, 3), (2, 4)])
    assert moved.state.units[sid].xy == (2, 4) and not of(moved, DamageDealt)
    hit = command(state, sid, (), foe)
    assert hit.state.units[sid].xy == (2, 3) and of(hit, DamageDealt)
    with pytest.raises(ValidationError):
        CommandSummon(unit_id=U1, summon_id=sid)  # 移動與攻擊至少一個
    with pytest.raises(ValidationError):
        CommandSummon(unit_id=U1, summon_id=sid, path=(pos(2, 3),))


def test_command_move_is_limited_by_the_summons_movement() -> None:
    state, sid = arena(foes=((6, 6),))
    speed = state.units[sid].speed
    walk = [(2 + i, 3) for i in range(5)]  # (2,3) → (6,3)：4 步
    assert speed >= 1
    longer = [(2, 3)] + [(2, 3 - i) for i in range(1, 4)] + [(3, 0), (4, 0), (5, 0), (6, 0)]
    if len(longer) - 1 > speed:
        with pytest.raises(IllegalActionError, match="移動點數不足"):
            command(state, sid, longer)
    within = walk[: min(speed, 4) + 1]
    assert command(state, sid, within).state.units[sid].xy == within[-1]


def test_command_attack_must_be_in_reach_after_the_move() -> None:
    state, sid = arena(foes=((6, 3),))
    foe = foe_ids(state)[0]
    with pytest.raises(IllegalActionError):
        command(state, sid, (), foe)  # 骷髏在 (2, 3)，打不到 (6, 3)
    with pytest.raises(IllegalActionError):
        command(state, sid, [(2, 3), (3, 3)], foe)


def test_a_summon_can_be_commanded_once_per_round() -> None:
    state, sid = arena(foes=((3, 3),))
    foe = foe_ids(state)[0]
    first = command(state, sid, (), foe).state
    assert first.units[U1].ap == state.units[U1].ap - 1
    with pytest.raises(IllegalActionError, match="本輪已經被指揮過"):
        command(first, sid, (), foe)
    assert project_for(first, Team.ALLY).units[1].commanded or any(
        u.commanded for u in project_for(first, Team.ALLY).units
    )
    nxt = first.clone()
    nxt.round += 1  # 下一輪又可以指揮
    nxt.units[U1].ap = 3
    assert command(nxt, sid, (), foe).state.units[sid].commanded_round == nxt.round


def test_command_needs_enough_ap() -> None:
    state, sid = arena(foes=((3, 3),))
    foe = foe_ids(state)[0]
    broke = state.clone()
    broke.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        command(broke, sid, (), foe)


def test_command_rejects_foreign_totem_and_stunned_summons() -> None:
    state, sid = arena(foes=((3, 3),))
    foe = foe_ids(state)[0]
    with pytest.raises(IllegalActionError, match="不是你的召喚物"):
        command(state, foe, (), foe)
    totem_state, tid = arena(unit=TOTEM)
    with pytest.raises(IllegalActionError, match="圖騰"):
        command(totem_state, tid, [(2, 3), (2, 4)])
    stunned = state.clone()
    from trpg.engine.state import StatusInstance  # noqa: PLC0415

    stunned.units[sid].statuses.append(StatusInstance(status_id="stun", remaining=1))
    with pytest.raises(IllegalActionError, match="暈眩"):
        command(stunned, sid, (), foe)


def test_command_is_deterministic_and_replayable() -> None:
    state, sid = arena(foes=((5, 3),))
    foe = foe_ids(state)[0]
    a = command(state, sid, [(2, 3), (3, 3), (4, 3)], foe)
    b = command(state, sid, [(2, 3), (3, 3), (4, 3)], foe)
    from trpg.engine import state_to_json  # noqa: PLC0415

    assert state_to_json(a.state) == state_to_json(b.state)
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


def test_command_options_list_reachable_tiles_and_what_can_be_hit() -> None:
    state, sid = arena(foes=((4, 3),))
    foe = foe_ids(state)[0]
    options = command_options(state, U1, sid)
    assert options[0].dest == pos(2, 3) and options[0].path == (pos(2, 3),)
    assert options[0].targets == ()  # 原地打不到距離 2 的敵人
    by_dest = {(o.dest.x, o.dest.y): o for o in options}
    assert by_dest[(3, 3)].targets == (foe,)
    assert by_dest[(3, 3)].path == (pos(2, 3), pos(3, 3))
    # 每個選項的路徑都能被指揮動作接受
    for option in options[1:6]:
        target = option.targets[0] if option.targets else None
        out = resolve(
            state,
            CommandSummon(unit_id=U1, summon_id=sid, path=option.path, target_id=target),
        )
        assert out.state.units[sid].pos == option.dest
    broke = state.clone()
    broke.units[U1].ap = 0
    with pytest.raises(IllegalActionError):
        command_options(broke, U1, sid)


# ---------------------------------------------------------------------------
# 我方 AI 自動切換、估值
# ---------------------------------------------------------------------------


def test_ally_ai_focuses_the_boss_and_guards_when_hurt() -> None:
    state, sid = arena(foes=((6, 3), (6, 5)), foe_tags=("boss",))
    first = auto_mode_action(state, state.units[U1], rules())
    assert isinstance(first, SetSummonMode) and first.mode == "focus"
    assert first.target_id == foe_ids(state)[0]  # 有 boss 標籤的最小單位 ID（兩個都有，取第一個）
    done = resolve(state, first).state
    assert auto_mode_action(done, done.units[U1], rules()) is None  # 已符合就不再切換
    hurt = done.clone()
    hurt.units[U1].hp = 1
    second = auto_mode_action(hurt, hurt.units[U1], rules())
    assert isinstance(second, SetSummonMode) and second.mode == "guard" and second.summon_id == sid


def test_no_boss_and_healthy_means_no_switch_and_enemies_never_switch() -> None:
    state, _ = arena()
    assert auto_mode_action(state, state.units[U1], rules()) is None
    boss, _ = arena(foe_tags=("boss",))
    foe = boss.units[foe_ids(boss)[0]]
    assert auto_mode_action(boss, foe, rules()) is None
    off = rules().model_copy(update={"auto_focus_boss": False, "auto_guard_hp_permille": 0})
    assert auto_mode_action(boss, boss.units[U1], off) is None


def test_the_utility_ai_issues_the_switch_before_acting() -> None:
    state, sid = arena(foes=((6, 3),), foe_tags=("boss",))
    action = ai()(state)
    assert isinstance(action, SetSummonMode) and action.summon_id == sid
    after = resolve(state, action).state
    assert not isinstance(ai()(after), SetSummonMode)  # 只切一次，不會卡住


def test_summon_valuation_counts_growth_and_infusion() -> None:
    from trpg.content.summons import summon_dpr  # noqa: PLC0415

    summon = library().ruleset.summon_def(SKELETON)
    assert summon_dpr(summon, flat=2) == summon_dpr(summon) + 2
    assert summon_dpr(summon, bonus_permille=500) == summon_dpr(summon) * 3 / 2

    def gain(level: int) -> Any:
        state, _ = arena(owner={"level": level})
        state = state.clone()
        state.units[U1].cooldowns = {}
        preview_events = resolve(
            state, UseSkill(unit_id=U1, skill_id=SKILL_ID, target_pos=pos(1, 3))
        ).events
        return summon_gains(
            state, state.units[U1], preview_events, library().ai_profiles.profiles[0]
        )

    assert gain(9) > gain(1)


def test_the_new_events_have_log_text() -> None:
    from trpg.narrative.events import describe_event  # noqa: PLC0415

    def describe_events(st: BattleState, events: Any) -> list[str]:
        return [t for e in events if (t := describe_event(e, st)) is not None]

    state, sid = arena(foes=((3, 3),))
    foe = foe_ids(state)[0]
    mode = resolve(state, SetSummonMode(unit_id=U1, summon_id=sid, mode="focus", target_id=foe))
    text = "\n".join(describe_events(state, mode.events))
    assert "切換為集火" in text and "→" in text
    cmd = command(state, sid, [(2, 3), (2, 4)], None)
    text = "\n".join(describe_events(state, cmd.events))
    assert "指揮" in text and "移動到" in text


def test_a_boss_battle_with_mode_switches_replays_identically() -> None:
    """我方 AI 對 Boss 自動集火（set_summon_mode 是動作列表的一部分）：初始狀態 ＋ 動作列表重播得到
    同一個終局，事件序列也相同。"""
    from trpg.engine.runner import replay, run_battle  # noqa: PLC0415
    from trpg.engine.state import state_to_json  # noqa: PLC0415
    from trpg.sim.summon_report import _spec  # noqa: PLC0415

    lib = library()
    spec, _ = _spec(lib, "dev_summoner", "boss", 1, 30)
    seed = spec.seeds[0]
    run = run_battle(spec.setup, seed, UtilityAI(lib.ai_profiles))
    again = replay(spec.setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
    switches = [a for a in run.actions if isinstance(a, SetSummonMode)]
    assert switches and all(a.mode in ("focus", "guard") for a in switches)
    assert any(isinstance(e, SummonModeSet) for e in run.events)
