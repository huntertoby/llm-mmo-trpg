"""技能測試共用的小工具：建立有施放者的戰場、施放、挑事件。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from trpg.content.battle import UnitTemplate
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, ResolveResult, UseSkill, resolve
from trpg.engine.events import EventBase
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId

U1, U2, U3, U4, U5 = (UnitId(f"unit_000{i}") for i in range(1, 6))
FLAT7 = "\n".join(["0000000"] * 7)
SID = "skill_t_prim"


def battle(
    skill: SkillDef,
    foes: Sequence[tuple[int, int] | tuple[int, int, UnitTemplate]] = (),
    *,
    allies: Sequence[tuple[int, int]] = (),
    caster: tuple[int, int] = (3, 3),
    heights: str = FLAT7,
    objects: tuple[tuple[int, int, str], ...] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
    base: str = "hero_mage",
) -> BattleState:
    """施放者是 U1，之後依序是 ``allies``、``foes``；施放者拿到回合與滿 AP。"""
    foe_xy = [(f[0], f[1]) for f in foes] or [(6, 6)]
    m = make_map(heights, ally=[caster, *allies], enemy=foe_xy, objects=objects, surfaces=surfaces)
    spawns = [spawn(Team.ALLY, caster, caster_template([skill], base=base))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    for f in foes or [(6, 6)]:
        tmpl = f[2] if len(f) == 3 else no_reactions()
        spawns.append(spawn(Team.ENEMY, (f[0], f[1]), tmpl))
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def cast(state: BattleState, **fields: Any) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, **fields))


def of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


def hit_with(state: BattleState, extra: Sequence[tuple[int, int]] = ()) -> BattleState:
    """第一顆 d20 為 19（命中、不暴擊），之後依序是 ``extra`` 的骰值。"""
    return with_rolls(state, [(20, 19), *extra])


def script_rolls(monkeypatch: pytest.MonkeyPatch, values: Sequence[int]) -> list[int]:
    """讓接下來的 ``Rng.roll`` 依序回傳 ``values``（用完再擲會讓測試失敗）。

    ``with_rolls`` 以搜尋種子的方式固定骰值，只適合 3 顆左右；多目標的範圍技能用這個。
    """
    queue = list(values)

    def roll(self: Rng, sides: int) -> int:
        assert queue, "骰值用完了"
        value = queue.pop(0)
        assert 1 <= value <= sides, f"{value} 不是 d{sides} 的合法結果"
        return value

    monkeypatch.setattr(Rng, "roll", roll)
    return queue
