"""Phase 3-50c：代價狀態（技能代價自己付的狀態）淨化與驅散都移除不了（玩法決定 #62）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.engine import EndTurn, resolve
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, CleanseEffect
from trpg.engine.events import StatusRemoved
from trpg.engine.resources import dispelled_buffs, pick_stolen_buff
from trpg.engine.state import BattleState, StatusInstance
from trpg.engine.view import project_for
from trpg.shared.types import Team, UnitId

COST_STATUSES = ["stun", "silenced", "bleed", "vulnerable", "slow", "overdrawn"]


def _state() -> BattleState:
    skill = make_skill(SID, {"type": "self"}, [{"type": "cleanse", "affects": "self"}], ap_cost=1)
    return battle(skill, [(6, 6)])


def _apply(state: BattleState, status_id: str, *, source: UnitId, paid: bool) -> None:
    execute(
        Ctx(state),
        [
            ApplyStatusEffect(
                source_id=source,
                target_id=U1,
                status_id=status_id,
                duration=3,
                self_paid=paid,
            )
        ],
    )


def _cleanse(state: BattleState) -> list[str]:
    ctx = Ctx(state)
    execute(ctx, [CleanseEffect(target_id=U1, source_id=U1)])
    return [e.status_id for e in ctx.events if isinstance(e, StatusRemoved)]


@pytest.mark.parametrize("status_id", COST_STATUSES)
def test_self_paid_status_is_marked_and_survives_cleanse(status_id: str) -> None:
    state = _state()
    _apply(state, status_id, source=U1, paid=True)
    instance = state.units[U1].get_status(status_id)
    assert instance is not None and instance.cost_status
    assert _cleanse(state) == []
    assert state.units[U1].get_status(status_id) is not None


@pytest.mark.parametrize("status_id", COST_STATUSES)
def test_the_same_status_from_an_enemy_is_cleansed_as_usual(status_id: str) -> None:
    state = _state()
    _apply(state, status_id, source=U2, paid=False)
    instance = state.units[U1].get_status(status_id)
    assert instance is not None and not instance.cost_status
    assert _cleanse(state) == [status_id]
    assert state.units[U1].get_status(status_id) is None


def test_a_mix_only_removes_the_non_cost_debuffs() -> None:
    state = _state()
    _apply(state, "stun", source=U1, paid=True)
    _apply(state, "bleed", source=U2, paid=False)
    _apply(state, "silenced", source=U1, paid=True)
    _apply(state, "slow", source=U2, paid=False)
    assert _cleanse(state) == ["bleed", "slow"]
    assert {s.status_id for s in state.units[U1].statuses} == {"stun", "silenced"}


def test_a_cleanse_skill_cast_leaves_the_cost_status_alone() -> None:
    state = _state()
    _apply(state, "vulnerable", source=U1, paid=True)
    _apply(state, "slow", source=U2, paid=False)
    result = cast(state)
    assert [e.status_id for e in of(result, StatusRemoved)] == ["slow"]
    assert result.state.units[U1].get_status("vulnerable") is not None


def test_a_shorter_enemy_status_keeps_the_cost_mark_of_the_existing_one() -> None:
    state = _state()
    _apply(state, "slow", source=U1, paid=True)  # 持續 3
    execute(
        Ctx(state),
        [ApplyStatusEffect(source_id=U2, target_id=U1, status_id="slow", duration=1)],
    )
    instance = state.units[U1].get_status("slow")
    assert instance is not None and instance.cost_status and instance.remaining == 3


def test_a_longer_enemy_status_replaces_the_cost_one_and_can_be_cleansed() -> None:
    state = _state()
    _apply(state, "slow", source=U1, paid=True)
    execute(
        Ctx(state),
        [ApplyStatusEffect(source_id=U2, target_id=U1, status_id="slow", duration=5)],
    )
    instance = state.units[U1].get_status("slow")
    assert instance is not None and not instance.cost_status
    assert _cleanse(state) == ["slow"]


def test_dispel_and_steal_skip_cost_status() -> None:
    state = _state()
    unit = state.units[U1]
    unit.statuses = [
        StatusInstance("hasted", 3, U1, cost_status=True),
        StatusInstance("shielded", 2, U2, 5),
    ]
    ctx = Ctx(state)
    assert [s.status_id for s in dispelled_buffs(ctx, unit, "all")] == ["shielded"]
    picked = pick_stolen_buff(ctx, unit)
    assert picked is not None and picked.status_id == "shielded"
    unit.statuses = [StatusInstance("hasted", 3, U1, cost_status=True)]
    assert dispelled_buffs(ctx, unit, 1) == [] and pick_stolen_buff(ctx, unit) is None


def test_the_cost_mark_survives_the_end_of_turn_countdown_and_reaches_the_view() -> None:
    state = _state()
    _apply(state, "overdrawn", source=U1, paid=True)
    after = resolve(state, EndTurn(unit_id=U1)).state
    instance = after.units[U1].get_status("overdrawn")
    assert instance is not None and instance.cost_status
    view = project_for(after, Team.ALLY)
    unit_view = next(u for u in view.units if u.id == U1)
    assert next(s for s in unit_view.statuses if s.status_id == "overdrawn").cost_status


def test_the_ai_does_not_count_cleanse_as_support_for_a_cost_only_target() -> None:
    from trpg.engine.ai.utility import _supports  # noqa: PLC0415
    from trpg.engine.skills.targeting import resolve_effects  # noqa: PLC0415

    state = _state()
    skill = state.ruleset.skill_def(SID)
    effects = resolve_effects(state, skill)
    caster = state.units[U1]
    _apply(state, "stun", source=U1, paid=True)
    assert not _supports(state, caster, skill, effects, caster)  # 只有代價狀態：淨化沒有用
    _apply(state, "slow", source=U2, paid=False)
    assert _supports(state, caster, skill, effects, caster)  # 有敵人施加的減益：有用
