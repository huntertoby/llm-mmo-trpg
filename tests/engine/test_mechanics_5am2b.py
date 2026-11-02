"""Phase 5A-M2b：陣眼石靈「護陣」（狀態 ``ward``，``docs/design/18-雲嶺內容.md`` 18.2）。"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_map, make_state, spawn, template
from trpg.content.battle import StatusDef, UnitTemplate
from trpg.engine import BattleState
from trpg.engine.ai.priority import priority_points
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import DamageDealt, EventBase, UnitDowned
from trpg.engine.formation import ward_permille
from trpg.narrative.events import describe_event
from trpg.narrative.unit_traits import unit_trait_lines
from trpg.shared.types import Pos, Team, UnitId

FLAT = "\n".join(["0000000"] * 7)
U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))


def _state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
) -> BattleState:
    m = make_map(FLAT, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns)


def _stone() -> UnitTemplate:
    return library().unit("sect_array_stone")


def _monk() -> UnitTemplate:
    return template("bandit", tags=("humanoid", "sect"), max_hp=100)


def _hit(state: BattleState, target: UnitId, flat: int = 10) -> list[EventBase]:
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=target, source_id=U1, flat=flat, cause="attack")])
    return list(ctx.events)


def _dealt(events: Sequence[EventBase], target: UnitId) -> DamageDealt:
    return next(e for e in events if isinstance(e, DamageDealt) and e.target_id == target)


def _scene() -> BattleState:
    # U1 玩家；U2 陣眼石靈 (3,3)；U3 同門 (3,5)；U4 同門 (0,6)（超出 3 格）
    return _state(
        [((3, 0), template("hero_fighter", reactions=[], skills=[], max_hp=200))],
        [((3, 3), _stone()), ((3, 5), _monk()), ((0, 6), _monk())],
    )


def test_ward_reduces_kin_damage_in_range_only() -> None:
    state = _scene()
    assert state.units[U2].has_status("array_ward")
    assert ward_permille(state, state.units[U3]) == 800
    assert ward_permille(state, state.units[U4]) == 1000  # 距離 6 格
    assert ward_permille(state, state.units[U2]) == 1000  # 石靈自己不算
    near = _dealt(_hit(state, U3, 10), U3)
    far = _dealt(_hit(state, U4, 10), U4)
    assert near.ward_permille == 800 and near.amount == 8
    assert far.ward_permille == 1000 and far.amount == 10
    assert "護陣 ×0.8" in (describe_event(near, state) or "")


def test_ward_ends_when_stone_is_broken() -> None:
    state = _scene()
    events = _hit(state, U2, 500)  # 打碎石靈
    assert any(isinstance(e, UnitDowned) and e.unit_id == U2 for e in events)
    assert ward_permille(state, state.units[U3]) == 1000
    assert _dealt(_hit(state, U3, 10), U3).amount == 10


def test_ward_ignores_other_team_and_non_kin() -> None:
    state = _scene()
    state.units[U3].team = Team.ALLY  # 不同陣營
    assert ward_permille(state, state.units[U3]) == 1000
    state = _scene()
    state.units[U3].pos = Pos(x=3, y=4)
    state.units[U3].tags = ("humanoid",)  # 沒有 sect 標籤
    assert ward_permille(state, state.units[U3]) == 1000


def test_ward_schema_and_traits() -> None:
    base = {
        "id": "x_ward",
        "name_zh": "測",
        "description_zh": "測",
        "polarity": "neutral",
        "expires": "never",
        "ward": {"range": 3, "taken_permille": 800},
    }
    assert StatusDef.model_validate(base).ward is not None
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "polarity": "buff", "beneficial": True})
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "ward": {"range": 3, "taken_permille": 1000}})
    lines = unit_trait_lines(library(), "sect_array_stone")
    assert any(line.startswith("護陣「護陣」") and "×80%" in line for line in lines)


def test_ai_values_breaking_the_ward_stone() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _scene()
    down = UnitDowned(unit_id=U2, seq=0, round=1)
    plain = UnitDowned(unit_id=U3, seq=0, round=1)
    hero = state.units[U1]
    ev_stone = priority_points(state, hero, (down,), (down,), Fraction(1), rules)
    ev_plain = priority_points(state, hero, (plain,), (plain,), Fraction(1), rules)
    assert ev_stone - ev_plain == rules.ward_kill_points
