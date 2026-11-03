"""Boss 階段的新觸發種類與護陣 ×0（Phase 5F-3；``docs/phases/Phase5計畫.md`` 36.3）。

都實際跑引擎：``tag_down``（同陣營帶標籤的單位倒下 N 名）、``round_at``（第 N 輪起）、護陣倍率 0
（持有者在場時同門不受骰值傷害）。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_setup, spawn, template
from trpg.content.battle import BossPhase, check_phases
from trpg.engine import BattleState, resolve
from trpg.engine.actions import EndTurn
from trpg.engine.battle import start_battle
from trpg.engine.events import BossPhaseChanged
from trpg.engine.formation import ward_permille
from trpg.engine.setup import with_phase_assets
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId

HERO = UnitId("unit_0001")
BOSS = UnitId("unit_0002")
PILLAR_A = UnitId("unit_0003")
PILLAR_B = UnitId("unit_0004")

PHASES = (
    {"id": "pillars", "name_zh": "柱"},
    {
        "id": "open",
        "name_zh": "開",
        "trigger": {"kind": "tag_down", "tag": "pillar", "count": 2, "tag_name_zh": "柱子"},
    },
    {"id": "late", "name_zh": "晚", "trigger": {"kind": "round_at", "round": 3}},
)


def _state() -> BattleState:
    lib = library()
    hero = template("hero_fighter", reactions=())
    boss = template(
        "bandit",
        max_hp=100,
        tags=("boss", "core"),
        phases=PHASES,
        reactions=(),
    )
    pillar = template("bandit", max_hp=20, tags=("pillar",), reactions=())
    setup = make_setup(
        lib.map("test_flat_6x6"),
        [
            spawn(Team.ALLY, (0, 5), hero),
            spawn(Team.ENEMY, (4, 0), boss),
            spawn(Team.ENEMY, (5, 0), pillar),
            spawn(Team.ENEMY, (5, 1), pillar),
        ],
        max_rounds=30,
    )
    return start_battle(with_phase_assets(lib, setup), 0)


def _end_turn(state: BattleState) -> list[BossPhaseChanged]:
    s = give_turn(state, HERO)
    result = resolve(s, EndTurn(unit_id=HERO))
    return [e for e in result.events if isinstance(e, BossPhaseChanged)]


def _down(state: BattleState, unit: UnitId) -> None:
    state.units[unit].hp = 0
    state.units[unit].downed = True


def test_tag_down_needs_count() -> None:
    state = _state()
    _down(state, PILLAR_A)
    assert _end_turn(state) == []


def test_tag_down_fires_when_enough_are_down() -> None:
    state = _state()
    _down(state, PILLAR_A)
    _down(state, PILLAR_B)
    fired = _end_turn(state)
    assert [e.phase_id for e in fired] == ["open"]
    event = fired[0]
    assert event.trigger == "tag_down"
    assert event.permille is None
    assert event.condition_zh == "「柱子」倒下 2 名"
    assert "倒下 2 名" in (describe_event(event, state) or "")


def test_round_at_waits_for_previous_phase() -> None:
    state = _state()
    state.round = 5
    assert _end_turn(state) == []  # 階段依序：還沒到第 2 階段，第 3 階段不會先觸發
    _down(state, PILLAR_A)
    _down(state, PILLAR_B)
    fired = _end_turn(state)
    assert [(e.phase_id, e.trigger) for e in fired] == [("open", "tag_down"), ("late", "round_at")]


def test_check_phases_only_orders_hp_triggers() -> None:
    phases = tuple(
        BossPhase.model_validate(p)
        for p in (
            {"id": "a", "name_zh": "甲"},
            {"id": "b", "name_zh": "乙", "trigger": {"kind": "round_at", "round": 10}},
            {"id": "c", "name_zh": "丙", "trigger": {"kind": "hp_below", "permille": 500}},
            {"id": "d", "name_zh": "丁", "trigger": {"kind": "hp_below", "permille": 600}},
        )
    )
    assert check_phases(phases) == ["階段 d 的 HP 門檻必須比前一個階段低"]


def test_trigger_schema_bounds() -> None:
    with pytest.raises(ValidationError):
        BossPhase.model_validate(
            {"id": "x", "name_zh": "x", "trigger": {"kind": "tag_down", "tag": "p", "count": 0}}
        )
    with pytest.raises(ValidationError):
        BossPhase.model_validate(
            {"id": "x", "name_zh": "x", "trigger": {"kind": "round_at", "round": 1}}
        )


def test_zero_ward_blocks_all_dice_damage() -> None:
    lib = library()
    state = start_battle(
        with_phase_assets(
            lib,
            make_setup(
                lib.map("test_flat_6x6"),
                [
                    spawn(Team.ALLY, (0, 5), template("hero_fighter", reactions=())),
                    spawn(
                        Team.ENEMY,
                        (4, 0),
                        template("rift_shard_lord", reactions=(), phases=()),
                    ),
                    spawn(Team.ENEMY, (5, 0), template("rift_pillar_fire", reactions=())),
                ],
                max_rounds=30,
            ),
        ),
        0,
    )
    assert ward_permille(state, state.units[BOSS]) == 0
    state.units[PILLAR_A].hp = 0
    state.units[PILLAR_A].downed = True
    assert ward_permille(state, state.units[BOSS]) == 1000
