"""環形只打「恰好半徑」那一圈（Phase 6F-3；12B 對照 #8「暗影環打不到相鄰的敵人」）。

``content/skill_shapes.yaml`` 的環形：影響與施放者切比雪夫距離**恰為** ``radius`` 的格子。引擎照這條
規則結算（相鄰的敵人在半徑 2 的環內圈，不會被打到），不是 bug；卡片的形狀說明補上「不含相鄰」。
表格測試實際跑引擎：同一場上相鄰與距離 2 的敵人，只有距離 2 的受傷；卡片文字與實際一致。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import U1, of
from tests.engine.test_passive_triggers import always
from trpg.engine import UseSkill, resolve
from trpg.engine.events import DamageDealt
from trpg.engine.skills.shapes import ring_tiles
from trpg.narrative.skills import skill_shape_text
from trpg.shared.types import Team, UnitId
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
NINE = "\n".join(["0" * 9] * 9)
CENTER = (4, 4)


def _ring(radius: int):
    skill = compose_whiteboard(
        7, kind="active", recipe_id="shadow_ring", library=LIB, weapon_class="melee"
    )
    shape = skill.shape.model_copy(update={"radius": radius})
    return skill.model_copy(update={"shape": shape})


@pytest.mark.parametrize(
    ("radius", "foe", "hit"),
    [
        (2, (5, 4), False),  # 相鄰（距離 1）：不在半徑 2 的環上
        (2, (5, 5), False),  # 斜角相鄰
        (2, (6, 4), True),  # 距離 2
        (2, (6, 6), True),  # 斜角距離 2（切比雪夫）
        (2, (7, 4), False),  # 距離 3：環外
        (1, (5, 4), True),  # 半徑 1＝相鄰的 8 格
        (1, (6, 4), False),
    ],
)
def test_ring_hits_exactly_radius(
    monkeypatch: pytest.MonkeyPatch, radius: int, foe: tuple[int, int], hit: bool
) -> None:
    always(monkeypatch)
    skill = _ring(radius)
    m = make_map(NINE, ally=[CENTER], enemy=[foe])
    hero = caster_template([skill], base="hero_fighter", weapon="dagger")
    foe_unit = no_reactions("bandit", max_hp=999)
    spawns = [spawn(Team.ALLY, CENTER, hero), spawn(Team.ENEMY, foe, foe_unit)]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    action = UseSkill(unit_id=U1, skill_id=skill.id)
    tiles = ring_tiles(state, CENTER, radius)
    assert (foe in tiles) is hit
    assert len(tiles) == (16 if radius == 2 else 8)
    result = answered(resolve(state, action))
    damaged = {d.target_id for d in of(result, DamageDealt)}
    assert (UnitId("unit_0002") in damaged) is hit


def test_card_says_ring_skips_adjacent() -> None:
    assert "不含相鄰" in skill_shape_text(LIB, _ring(2))
    assert "不含相鄰" not in skill_shape_text(LIB, _ring(1))
