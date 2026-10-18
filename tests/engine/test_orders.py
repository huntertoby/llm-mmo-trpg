"""戰術指令、控制分派與指揮官包裝器（Phase 2C-2 驗收 2–6）。"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from trpg.engine import Attack, BattleState, Move
from trpg.engine.actions import Action
from trpg.engine.ai import Policy
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.orders import (
    ORDER_ADAPTER,
    FocusTarget,
    HoldPosition,
    OrderRecord,
    OrderSet,
    Protect,
    RetreatTo,
    TacticalOrder,
    UseEnvironment,
    validate_order,
)
from trpg.engine.ai.simple import choose_action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import ObjectId, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))


def ai(*orders: TacticalOrder, profile: str = "brute") -> UtilityAI:
    return UtilityAI(library().ai_profiles, override=profile, orders=lambda _s, _u: orders)


def _end(action: Action) -> tuple[int, int]:
    assert isinstance(action, Move)
    last = action.path[-1]
    return (last.x, last.y)


# ---------------------------------------------------------------------------
# schema 與驗證
# ---------------------------------------------------------------------------


def test_orders_have_no_numeric_outcome_fields() -> None:
    """守則 3：指令只有目標與格子；多餘的欄位（數值、骰子、結果）一律被拒絕。"""
    for kind, extra in (("focus_target", {"target": "unit_0002"}), ("use_environment", {})):
        with pytest.raises(ValidationError):
            ORDER_ADAPTER.validate_python({"kind": kind, **extra, "damage": 99})
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python({"kind": "hold_position", "at": (1, 1), "radius": 4})
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python({"kind": "teleport", "at": (1, 1)})
    assert HoldPosition(at=(1, 1)).radius == 1


def test_order_set_rules() -> None:
    with pytest.raises(ValidationError):  # 每種 kind 最多一個
        OrderSet(team_orders=(FocusTarget(target=U2), FocusTarget(target=U3)))
    with pytest.raises(ValidationError):
        OrderSet(unit_orders={U1: (UseEnvironment(), UseEnvironment())})
    both = OrderSet(
        team_orders=(FocusTarget(target=U3),),
        unit_orders={U1: (UseEnvironment(),), U2: ()},
    )
    assert both.for_unit(U1) == (UseEnvironment(),)  # 單位自己的指令完全取代陣營指令
    assert both.for_unit(U2) == ()  # 即使是空的也取代
    assert both.for_unit(U4) == (FocusTarget(target=U3),)
    restored = OrderSet.model_validate_json(both.model_dump_json())
    assert restored == both


def test_validate_order() -> None:
    m = make_map("0000\n0000", "..x#\n....", ally=[(0, 0)], enemy=[(3, 1)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ALLY, (1, 0), "hero_archer"),
            spawn(Team.ENEMY, (3, 1), "bandit"),
            spawn(Team.ENEMY, (2, 1), "bandit"),
        ],
    )
    state.units[U4].hp = 0
    state.units[U4].downed = True
    ally = Team.ALLY
    assert validate_order(state, ally, FocusTarget(target=U3)) is None
    assert "已倒下" in (validate_order(state, ally, FocusTarget(target=U4)) or "")
    assert "不是敵人" in (validate_order(state, ally, FocusTarget(target=U2)) or "")
    assert "不存在" in (validate_order(state, ally, FocusTarget(target=UnitId("ghost"))) or "")
    assert validate_order(state, ally, Protect(ward=U2)) is None
    assert "不是友方" in (validate_order(state, ally, Protect(ward=U3)) or "")
    assert validate_order(state, ally, HoldPosition(at=(1, 1))) is None
    assert "超出地圖" in (validate_order(state, ally, HoldPosition(at=(9, 9))) or "")
    assert "無法站立" in (validate_order(state, ally, RetreatTo(at=(2, 0))) or "")  # 深淵
    assert "無法站立" in (validate_order(state, ally, RetreatTo(at=(3, 0))) or "")  # 牆
    assert validate_order(state, ally, UseEnvironment()) is None


# ---------------------------------------------------------------------------
# 控制分派
# ---------------------------------------------------------------------------


def test_controller_precedence_unit_then_team_then_default() -> None:
    m = make_map("0000\n0000", ally=[(0, 0)], enemy=[(3, 1)])
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ALLY, (0, 1), "hero_archer"),
            spawn(Team.ENEMY, (3, 1), "bandit"),
            spawn(Team.ENEMY, (3, 0), "bandit"),
        ],
        max_rounds=2,
    )
    calls: dict[str, list[UnitId]] = {"default": [], "ally": [], "unit": []}

    def make(name: str) -> Policy:
        def policy(state: BattleState) -> Action:
            assert state.active_unit is not None
            calls[name].append(state.active_unit)
            return choose_action(state)

        return policy

    run_battle(
        setup,
        1,
        make("default"),
        controllers={Team.ALLY: make("ally"), U1: make("unit")},
    )
    assert calls["unit"] and set(calls["unit"]) == {U1}  # 單位 ID 優先於陣營
    assert calls["ally"] and U1 not in calls["ally"]
    assert {u for u in calls["ally"]} == {U2}  # 陣營優先於預設
    assert calls["default"] and {u for u in calls["default"]} <= {U3, U4}  # 其餘用預設
    # 重播不受控制分派影響
    first = run_battle(setup, 1, choose_action)
    mixed = run_battle(setup, 1, choose_action, controllers={Team.ENEMY: choose_action})
    assert first.actions == mixed.actions


# ---------------------------------------------------------------------------
# 五種指令的行為改變
# ---------------------------------------------------------------------------


def _two_targets() -> BattleState:
    m = make_map("\n".join(["00000000"] * 6))
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), "hero_fighter"),
            spawn(Team.ENEMY, (4, 3), "bandit"),
            spawn(Team.ENEMY, (3, 2), "bandit"),
        ],
    )
    state = give_turn(state, U1)
    state.units[U2].hp = 8  # 殘血的 A：預設會打它
    return state


def test_focus_target_changes_the_attack_target() -> None:
    state = _two_targets()
    assert ai()(state) == Attack(unit_id=U1, target_id=U2)
    assert ai(FocusTarget(target=U3))(state) == Attack(unit_id=U1, target_id=U3)


def test_focus_target_makes_approach_follow_the_target() -> None:
    m = make_map("\n".join(["0" * 12] * 6), ally=[(5, 3)], enemy=[(0, 3)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (5, 3), "hero_fighter"),
                spawn(Team.ENEMY, (7, 3), no_reactions()),  # 近
                spawn(Team.ENEMY, (0, 0), no_reactions()),  # 遠，在另一個方向
            ],
        ),
        U1,
    )
    plain = _end(ai()(state))
    focused = _end(ai(FocusTarget(target=U3))(state))
    far = state.units[U3].xy
    assert manhattan(focused, far) < manhattan((5, 3), far)
    assert manhattan(focused, far) < manhattan(plain, far)


def _far_apart() -> BattleState:
    m = make_map("\n".join(["0" * 12] * 8), ally=[(2, 4)], enemy=[(11, 4)])
    return give_turn(
        make_state(m, [spawn(Team.ALLY, (2, 4), "hero_fighter"), spawn(Team.ENEMY, (11, 4))]), U1
    )


def test_hold_position_keeps_the_unit_near_the_spot() -> None:
    state = _far_apart()
    assert manhattan(_end(ai()(state)), (2, 4)) > 1  # 沒有指令：前進
    for radius in (0, 1, 2):
        action = ai(HoldPosition(at=(2, 4), radius=radius))(state)
        end = _end(action) if isinstance(action, Move) else (2, 4)
        assert manhattan(end, (2, 4)) <= radius


def test_retreat_to_moves_toward_the_spot_instead_of_the_enemy() -> None:
    state = _far_apart()
    plain = _end(ai()(state))
    retreat = _end(ai(RetreatTo(at=(0, 0)))(state))
    enemy = state.units[U2].xy
    assert manhattan(retreat, (0, 0)) < manhattan((2, 4), (0, 0))
    assert manhattan(retreat, enemy) > manhattan((2, 4), enemy)
    assert manhattan(plain, enemy) < manhattan((2, 4), enemy)


def test_protect_moves_toward_the_ward() -> None:
    m = make_map("\n".join(["0" * 12] * 8), ally=[(4, 4)], enemy=[(11, 1)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (4, 4), "hero_fighter"),
                spawn(Team.ALLY, (1, 7), "hero_archer"),
                spawn(Team.ENEMY, (11, 1)),
            ],
        ),
        U1,
    )
    ward = state.units[U2].xy
    plain = _end(ai()(state))
    guarded = _end(ai(Protect(ward=U2))(state))
    assert manhattan(plain, ward) > manhattan((4, 4), ward)  # 預設：衝向敵人
    assert manhattan(guarded, ward) < manhattan((4, 4), ward)  # 指令：靠近 ward


def test_protect_overrides_the_default_ward() -> None:
    """預設的保護對象是 HP 比例最低的友方；指令固定為 ward。"""
    m = make_map("\n".join(["0" * 12] * 8), ally=[(4, 4)], enemy=[(11, 1)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (4, 4), "hero_fighter"),
                spawn(Team.ALLY, (1, 7), "hero_archer"),
                spawn(Team.ALLY, (10, 7), "hero_mage"),
                spawn(Team.ENEMY, (11, 1)),
            ],
        ),
        U1,
    )
    state.units[U2].hp = 5  # 預設會保護 U2
    toward_u3 = _end(ai(Protect(ward=U3), profile="guard")(state))
    toward_u2 = _end(ai(profile="guard")(state))
    assert manhattan(toward_u3, state.units[U3].xy) < manhattan(toward_u2, state.units[U3].xy)


def _barrel_scene() -> BattleState:
    """直接攻擊（23.4 分）與引爆油桶（沒有指令時 21.5 分）很接近：桶旁有兩名友方。"""
    m = make_map(
        "\n".join(["000000000"] * 5),
        objects=[(5, 2, "oil_barrel")],
        ally=[(0, 2)],
        enemy=[(5, 0)],
    )
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 2), "hero_mage"),
                spawn(Team.ALLY, (4, 2), no_reactions(max_hp=500)),
                spawn(Team.ALLY, (6, 2), no_reactions(max_hp=500)),
                spawn(Team.ENEMY, (5, 1), no_reactions(max_hp=200)),
                spawn(Team.ENEMY, (1, 2), no_reactions()),
            ],
        ),
        U1,
    )
    state.units[UnitId("unit_0004")].hp = 200
    return state


def test_use_environment_prefers_detonating_the_barrel() -> None:
    state = _barrel_scene()
    barrel = Attack(unit_id=U1, target_object_id=ObjectId("obj_0001"))
    direct = Attack(unit_id=U1, target_id=UnitId("unit_0005"))
    plain = {s.action: s.score for s in ai(profile="cunning").rank(state)}
    assert plain[direct] > plain[barrel] > 0  # 兩者接近，預設打人
    assert ai(profile="cunning")(state) == direct
    assert ai(UseEnvironment(), profile="cunning")(state) == barrel


# ---------------------------------------------------------------------------
# 無效指令與「沒有指令時完全相同」
# ---------------------------------------------------------------------------


def _scores(policy: UtilityAI, state: BattleState) -> list[tuple[str, object]]:
    return [(repr(s.action), s.score) for s in policy.rank(state)]


def test_invalid_orders_behave_exactly_like_no_orders() -> None:
    state = _two_targets()
    state.units[U3].hp = 0
    state.units[U3].downed = True
    invalid: tuple[TacticalOrder, ...] = (
        FocusTarget(target=U3),  # 已倒下
        FocusTarget(target=U1),  # 不是敵人
        Protect(ward=U2),  # 不是友方
        Protect(ward=U1),  # 保護自己
        HoldPosition(at=(40, 40)),
        RetreatTo(at=(60, 60)),
    )
    baseline = _scores(ai(), state)
    for order in invalid:
        assert _scores(ai(order), state) == baseline, order
    assert _scores(ai(*invalid), state) == baseline


def _battle_scores(setup_args: tuple[str, int], factory: object) -> list[list[tuple[str, object]]]:
    map_id, seed = setup_args
    lib = library()
    encounter = lib.map(map_id).encounter
    assert encounter is not None
    setup = build_setup(lib, map_id, encounter.allies, encounter.enemies, max_rounds=30)
    policy_ai = factory() if callable(factory) else None
    assert isinstance(policy_ai, UtilityAI)
    seen: list[list[tuple[str, object]]] = []

    def policy(state: BattleState) -> Action:
        seen.append(_scores(policy_ai, state))
        return policy_ai(state)

    run_battle(setup, seed, policy)
    return seen


@pytest.mark.parametrize("map_id", ["bridge_chasm", "oil_depot", "swamp", "ruined_fort"])
def test_no_orders_scores_match_plain_utility_ai_per_action(map_id: str) -> None:
    """沒有指令（或指揮官回傳空指令）時，整場戰鬥每個決策的每個動作分數完全相同。"""
    profiles = library().ai_profiles
    plain = _battle_scores((map_id, 3), lambda: UtilityAI(profiles))
    empty_source = _battle_scores(
        (map_id, 3), lambda: UtilityAI(profiles, orders=lambda _s, _u: ())
    )

    def commanded() -> UtilityAI:
        inner = UtilityAI(profiles)
        CommandedAI(
            inner,
            {Team.ALLY: lambda _s, _t: OrderSet(), Team.ENEMY: lambda _s, _t: OrderSet()},
        )
        return inner

    via_commander = _battle_scores((map_id, 3), commanded)
    assert plain == empty_source == via_commander


# ---------------------------------------------------------------------------
# CommandedAI：呼叫時機與紀錄
# ---------------------------------------------------------------------------


def test_commander_called_once_per_round_and_when_counts_change() -> None:
    m = make_map("\n".join(["0" * 8] * 4), ally=[(0, 1)], enemy=[(7, 1)])
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (0, 1), "hero_fighter"),
            spawn(Team.ALLY, (0, 2), "hero_archer"),
            spawn(Team.ENEMY, (7, 1), "bandit"),
            spawn(Team.ENEMY, (7, 2), "bandit"),
        ],
        max_rounds=3,
    )
    calls: list[tuple[int, Team]] = []

    def enemy_commander(state: BattleState, team: Team) -> OrderSet | None:
        calls.append((state.round, team))
        return OrderSet(team_orders=(FocusTarget(target=U1),)) if len(calls) == 1 else None

    commanded = CommandedAI(UtilityAI(library().ai_profiles), {Team.ENEMY: enemy_commander})
    run = run_battle(setup, 5, commanded)
    rounds = sorted({r for r, _ in calls})
    assert rounds == list(range(1, rounds[-1] + 1))  # 每一輪（敵方有行動的）都至少呼叫一次
    assert run.state.round >= rounds[-1]
    assert all(team is Team.ENEMY for _, team in calls)
    per_round = [sum(1 for r, _ in calls if r == n) for n in rounds]
    assert min(per_round) >= 1
    # 只有第一次回傳指令（其餘 None＝沿用）；紀錄只記下真正下達的
    assert [r.round for r in run.orders] == [1]
    assert run.orders[0].orders.team_orders == (FocusTarget(target=U1),)
    assert run.orders == commanded.order_log


def test_commander_called_again_when_a_unit_falls() -> None:
    m = make_map("\n".join(["0" * 6] * 3), ally=[(0, 1)], enemy=[(5, 1)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 1), "hero_fighter"),
                spawn(Team.ENEMY, (5, 1), "bandit"),
                spawn(Team.ENEMY, (5, 2), "bandit"),
            ],
        ),
        U1,
    )
    calls: list[int] = []

    def commander(state: BattleState, team: Team) -> OrderSet | None:
        calls.append(sum(1 for u in state.living_units()))
        return None

    commanded = CommandedAI(UtilityAI(library().ai_profiles), {Team.ALLY: commander})
    commanded(state)
    commanded(state)  # 同一輪、數量沒變：不再呼叫
    assert calls == [3]
    fallen = state.clone()
    fallen.units[U3].downed = True
    fallen.units[U3].hp = 0
    commanded(fallen)  # 敵方少一人：再呼叫
    assert calls == [3, 2]


def test_ignored_orders_are_recorded_with_reasons() -> None:
    state = _two_targets()
    state.units[U3].downed = True
    state.units[U3].hp = 0
    ghost = UnitId("ghost")
    issued = OrderSet(
        team_orders=(FocusTarget(target=U3), HoldPosition(at=(50, 50))),
        unit_orders={U1: (RetreatTo(at=(0, 0)),), ghost: (UseEnvironment(),)},
    )
    seen: list[OrderRecord] = []
    commanded = CommandedAI(
        UtilityAI(library().ai_profiles, override="brute"),
        {Team.ALLY: lambda _s, _t: issued},
        on_order=lambda record, _state: seen.append(record),
    )
    expected = ai(RetreatTo(at=(0, 0)))(state)  # U1 有自己的指令：完全取代陣營指令
    assert commanded(state) == expected
    [record] = commanded.order_log
    assert seen == [record]
    assert {(i.scope, i.order.kind) for i in record.ignored} == {
        ("team", "focus_target"),
        ("team", "hold_position"),
        ("ghost", "use_environment"),
    }
    reasons = {i.order.kind: i.reason for i in record.ignored}
    assert "已倒下" in reasons["focus_target"] and "超出地圖" in reasons["hold_position"]


def test_unit_orders_replace_team_orders_in_scoring() -> None:
    state = _two_targets()
    ward_less = OrderSet(
        team_orders=(FocusTarget(target=U3),),
        unit_orders={U1: ()},  # U1 不受陣營指令影響
    )
    commanded = CommandedAI(
        UtilityAI(library().ai_profiles, override="brute"), {Team.ALLY: lambda _s, _t: ward_less}
    )
    assert commanded(state) == ai()(state) == Attack(unit_id=U1, target_id=U2)
    team_only = CommandedAI(
        UtilityAI(library().ai_profiles, override="brute"),
        {Team.ALLY: lambda _s, _t: OrderSet(team_orders=(FocusTarget(target=U3),))},
    )
    assert team_only(state) == Attack(unit_id=U1, target_id=U3)


# ---------------------------------------------------------------------------
# 紀錄與重播
# ---------------------------------------------------------------------------


def test_orders_are_written_to_the_log_and_replay_matches() -> None:
    lib = library()
    encounter = lib.map("swamp").encounter
    assert encounter is not None
    setup = build_setup(lib, "swamp", encounter.allies, encounter.enemies, max_rounds=30)

    def focus_first_ally(state: BattleState, team: Team) -> OrderSet | None:
        foes = [u for u in state.living_units() if u.team is not team]
        return OrderSet(team_orders=(FocusTarget(target=foes[0].id),)) if foes else None

    commanded = CommandedAI(UtilityAI(lib.ai_profiles), {Team.ENEMY: focus_first_ally})
    run = run_battle(setup, 4, commanded)
    assert run.orders
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    assert log.orders == run.orders
    again = replay(log.setup, log.seed, log.actions)
    assert again.actions == run.actions
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


def test_old_log_without_orders_still_loads() -> None:
    lib = library()
    encounter = lib.map("swamp").encounter
    assert encounter is not None
    setup = build_setup(lib, "swamp", encounter.allies, encounter.enemies, max_rounds=3)
    run = run_battle(setup, 1, UtilityAI(lib.ai_profiles))
    raw = json.loads(run.to_log().model_dump_json())
    del raw["orders"]
    log = BattleLog.model_validate(raw)
    assert log.orders == []
    assert replay(log.setup, log.seed, log.actions).state.round == run.state.round


def test_order_bonuses_are_loaded_from_content() -> None:
    bonuses = library().ai_profiles.orders
    assert bonuses.focus_permille == 1500
    assert (bonuses.hold_weight, bonuses.retreat_weight, bonuses.protect_min) == (20, 15, 12)
    assert bonuses.environment_permille == 2000
