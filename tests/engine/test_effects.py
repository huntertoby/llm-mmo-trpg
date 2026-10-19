"""效果佇列、致命地形、狀態（驗收條件 7 與 3.4 節）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.engine import BattleState, EndTurn, resolve, triggers
from trpg.engine.context import Ctx
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    MoveUnitEffect,
    RemoveStatusEffect,
    register_effect,
    run_effects,
)
from trpg.engine.effects.queue import handler_for
from trpg.engine.events import (
    ChainLimitReached,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    MoveBlocked,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.state import StatusInstance, state_to_json
from trpg.shared.errors import TrpgError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")


def _pit_state(victim: str = "bandit", **overrides: object) -> BattleState:
    """3×3，中央 (1, 1) 是深淵；受害者在 (0, 0)，英雄在 (2, 2)。"""
    m = make_map("000\n000\n000", "...\n.x.\n...", ally=[(2, 2)], enemy=[(0, 0)])
    return make_state(
        m,
        [
            spawn(Team.ENEMY, (0, 0), template(victim, **overrides)),
            spawn(Team.ALLY, (2, 2), "hero_fighter"),
        ],
    )


# ---------------------------------------------------------------------------
# 致命地形
# ---------------------------------------------------------------------------


def test_normal_unit_forced_into_chasm_dies() -> None:
    state = _pit_state()
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 1))])
    types = [type(e) for e in result.events]
    assert EnteredDeadlyTerrain in types and UnitDowned in types
    dealt = next(e for e in result.events if isinstance(e, DamageDealt))
    assert dealt.cause == "deadly_terrain" and dealt.hp_after == 0
    assert result.state.units[U1].downed
    assert U1 not in result.state.turn_order
    assert result.state.ended and result.state.winner is Team.ALLY


def test_normal_unit_into_lava_dies() -> None:
    m = make_map("000", ".~.", ally=[(2, 0)], enemy=[(0, 0)])
    state = make_state(
        m, [spawn(Team.ENEMY, (0, 0), "bandit"), spawn(Team.ALLY, (2, 0), "hero_fighter")]
    )
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 0))])
    assert result.state.units[U1].downed


def test_elite_takes_30_percent_and_moves_to_nearest_safe_tile() -> None:
    state = _pit_state("bandit_boss")
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 1))])
    boss = result.state.units[U1]
    assert not boss.downed
    assert boss.hp == 80 - 24  # 80 × 30%
    # 距離 1 的候選：(1,0)、(0,1)、(2,1)、(1,2)；依 y 再依 x → (1, 0)
    assert boss.pos == Pos(x=1, y=0)
    moves = [e for e in result.events if isinstance(e, UnitMoved)]
    assert [m.mode for m in moves] == ["forced", "teleport"]
    damage = next(e for e in result.events if isinstance(e, DamageDealt))
    assert damage.element_mod_ppm == 1_000_000  # 不套用物理抗性


def test_elite_safe_tile_tie_order_skips_occupied() -> None:
    m = make_map("000\n000\n000", "...\n.x.\n...", ally=[(2, 2)], enemy=[(0, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ENEMY, (0, 0), "bandit_boss"),
            spawn(Team.ALLY, (1, 0), "hero_fighter"),
            spawn(Team.ALLY, (2, 2), "hero_mage"),
        ],
    )
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 1))])
    # (1, 0) 有人 → 下一個是 (0, 1)（y=1 中 x 最小）
    assert result.state.units[U1].pos == Pos(x=0, y=1)


def test_elite_killed_by_terrain_damage_is_not_relocated() -> None:
    state = _pit_state("bandit_boss")
    s = state.clone()
    s.units[U1].hp = 10
    result = run_effects(s, [MoveUnitEffect(unit_id=U1, dest=(1, 1))])
    assert result.state.units[U1].downed
    assert [e.mode for e in result.events if isinstance(e, UnitMoved)] == ["forced"]


def test_forced_move_blocked() -> None:
    state = _pit_state()
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(2, 2))])
    assert isinstance(result.events[0], MoveBlocked) and result.events[0].reason == "occupied"
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(9, 0))])
    assert isinstance(result.events[0], MoveBlocked)
    assert result.events[0].reason == "out_of_bounds"


# ---------------------------------------------------------------------------
# 佇列
# ---------------------------------------------------------------------------


def test_queue_orders_simultaneous_effects() -> None:
    m = make_map("0000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=200)),
            spawn(Team.ENEMY, (1, 0), template("bandit", max_hp=200)),
            spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=200)),
        ],
    )
    effects: list[EffectBase] = [
        DamageEffect(target_id=U3, flat=1, source_id=U2),
        DamageEffect(target_id=U2, flat=1, source_id=U1),
        DamageEffect(target_id=U3, flat=1),
        DamageEffect(target_id=U1, flat=1),
        DamageEffect(target_id=U2, flat=1, source_id=U1),
    ]
    result = run_effects(state, effects)
    order = [(e.source_id, e.target_id) for e in result.events if isinstance(e, DamageDealt)]
    # 來源 ID（無來源排最前）→ 目標 ID；鍵相同時保留原順序
    assert order == [(None, U1), (None, U3), (U1, U2), (U1, U2), (U2, U3)]


def test_chain_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試用觸發：每次治療都再觸發一次治療 → 深度 0–3 結算，第 4 層停止。"""

    def heal_again(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
        assert isinstance(event, Healed)
        return [HealEffect(depth=depth, target_id=event.target_id, flat=1)]

    monkeypatch.setitem(triggers._TRIGGERS, "healed", [heal_again])
    state = _pit_state()
    s = state.clone()
    s.units[U1].hp = 1
    result = run_effects(s, [HealEffect(target_id=U1, flat=1)])
    heals = [e for e in result.events if isinstance(e, Healed)]
    limits = [e for e in result.events if isinstance(e, ChainLimitReached)]
    assert len(heals) == 4
    assert len(limits) == 1 and limits[0].depth == 4 and limits[0].effect_kind == "heal"
    assert result.state.units[U1].hp == 5


def test_registry_errors() -> None:
    with pytest.raises(TrpgError, match="已註冊"):
        register_effect("damage")(handler_for("damage"))
    with pytest.raises(TrpgError, match="未註冊"):
        handler_for("summon_dragon")


def test_run_effects_is_pure() -> None:
    state = _pit_state()
    before = state_to_json(state)
    run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 1))])
    assert state_to_json(state) == before


# ---------------------------------------------------------------------------
# 治療與狀態
# ---------------------------------------------------------------------------


def test_heal_caps_at_max_and_ignores_downed() -> None:
    state = _pit_state()
    s = state.clone()
    s.units[U1].hp = 5
    result = run_effects(s, [HealEffect(target_id=U1, flat=1000)])
    healed = next(e for e in result.events if isinstance(e, Healed))
    assert result.state.units[U1].hp == 30 and healed.amount == 25
    dead = run_effects(s, [DamageEffect(target_id=U1, mode="lethal")]).state
    assert run_effects(dead, [HealEffect(target_id=U1, flat=5)]).events == []


def test_apply_refresh_and_remove_status() -> None:
    state = _pit_state()
    r1 = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id="burning", duration=1)])
    assert r1.state.units[U1].get_status("burning").remaining == 1  # type: ignore[union-attr]
    r2 = run_effects(r1.state, [ApplyStatusEffect(target_id=U1, status_id="burning")])
    applied = next(e for e in r2.events if isinstance(e, StatusApplied))
    assert applied.refreshed and applied.duration == 2
    assert [s.status_id for s in r2.state.units[U1].statuses] == ["burning"]  # 不疊加
    r3 = run_effects(r2.state, [RemoveStatusEffect(target_id=U1, status_id="burning")])
    assert not r3.state.units[U1].statuses
    assert isinstance(r3.events[0], StatusRemoved)
    assert (
        run_effects(r3.state, [RemoveStatusEffect(target_id=U1, status_id="burning")]).events == []
    )


def _reapply(existing: int | None, new: int) -> tuple[StatusApplied, StatusInstance]:
    """受害者 U1 已有 ``concealed``（來源 U2、剩餘 ``existing``），再由 U3 施加 ``new`` 回合。"""
    state = _pit_state()
    state.units[U1].statuses.append(
        StatusInstance(status_id="concealed", remaining=existing, source_id=U2)
    )
    result = run_effects(
        state,
        [ApplyStatusEffect(target_id=U1, status_id="concealed", duration=new, source_id=U3)],
    )
    applied = next(e for e in result.events if isinstance(e, StatusApplied))
    status = result.state.units[U1].get_status("concealed")
    assert status is not None
    return applied, status


def test_reapply_status_keeps_longer_remaining() -> None:
    applied, status = _reapply(4, 2)
    assert status.remaining == 4 and status.source_id == U2  # 舊的較長：保留舊來源
    assert applied.duration == 4 and applied.refreshed  # 事件填生效後的剩餘回合


def test_reapply_status_takes_longer_new_duration() -> None:
    applied, status = _reapply(1, 3)
    assert status.remaining == 3 and status.source_id == U3
    assert applied.duration == 3 and applied.refreshed


def test_reapply_finite_status_keeps_permanent() -> None:
    applied, status = _reapply(None, 3)
    assert status.remaining is None and status.source_id == U2
    assert applied.duration is None


def _end(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    assert state.active_unit is not None
    result = resolve(state, EndTurn(unit_id=state.active_unit))
    return result.state, result.events


def test_burning_ticks_twice_then_expires() -> None:
    m = make_map("0000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=100)),
            spawn(Team.ENEMY, (3, 0), template("bandit_archer", max_hp=100)),
        ],
    )
    state = give_turn(state, "unit_0001")
    state = run_effects(
        state, [ApplyStatusEffect(target_id=U2, status_id="burning", source_id=U1)]
    ).state
    ticks: list[DamageDealt] = []
    removed: list[StatusRemoved] = []
    for _ in range(6):  # 雙方各 3 個回合
        state, events = _end(state)
        ticks += [e for e in events if isinstance(e, DamageDealt)]
        removed += [e for e in events if isinstance(e, StatusRemoved)]
    assert len(ticks) == 2
    for tick in ticks:
        assert tick.cause == "status" and tick.element.value == "fire" and tick.source_id == U1
        assert len(tick.rolls) == 1 and 1 <= tick.rolls[0] <= 6
        # 盜賊弓手火焰弱點 +25%
        assert tick.element_mod_ppm == 1_250_000
        assert tick.amount == max(1, tick.rolls[0] * 1250 // 1000)
    assert len(removed) == 1 and removed[0].reason == "expired"
    assert not state.units[U2].statuses


def test_burning_can_kill_at_turn_start_and_turn_passes() -> None:
    m = make_map("00000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ENEMY, (3, 0), "bandit"),
            spawn(Team.ENEMY, (4, 0), "bandit"),
        ],
    )
    state = give_turn(state, "unit_0001")
    s = state.clone()
    s.units[U2].hp = 1
    s = run_effects(s, [ApplyStatusEffect(target_id=U2, status_id="burning")]).state
    # 依先攻順序結束回合，直到 unit_0002 的回合開始時被燒死
    for _ in range(4):
        s, events = _end(s)
        if any(isinstance(e, UnitDowned) for e in events):
            break
    assert s.units[U2].downed and U2 not in s.turn_order
    assert s.active_unit is not None and s.active_unit != U2
    assert not s.ended


def test_with_rolls_helper_controls_damage() -> None:
    state = with_rolls(_pit_state(), [(6, 6)])
    result = run_effects(state, [DamageEffect(target_id=U1, dice="1d6")])  # type: ignore[arg-type]
    assert next(e for e in result.events if isinstance(e, DamageDealt)).amount == 6
