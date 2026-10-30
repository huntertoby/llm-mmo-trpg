"""BAL-4c：傷害預覽與實際結算用同一套敵方傷害倍率（敵人／Boss／護衛）。"""

from __future__ import annotations

from fractions import Fraction

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
from tests.engine.skill_helpers import FLAT7
from trpg.engine import Attack, UseSkill, preview, resolve
from trpg.engine.events import DamageDealt
from trpg.engine.ids import BOSS_ESCORT_TAG, BOSS_TAG
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
ATTACK = Attack(unit_id=U1, target_id=U2)
FIRE_BOLT = "skill_fire_bolt"
TAG_CASES = [([], "enemy"), ([BOSS_TAG], "boss"), ([BOSS_ESCORT_TAG], "escort")]


def _state(tags: list[str], *, enemy: int, boss: int, escort: int) -> BattleState:
    """敵方（``tags``）在 (0, 0) 攻擊相鄰的我方。"""
    state = make_state(
        make_map("000"),
        [
            spawn(Team.ENEMY, (0, 0), no_reactions("bandit", tags=tags)),
            spawn(Team.ALLY, (1, 0), no_reactions("bandit", max_hp=99)),
        ],
        enemy_damage_permille=enemy,
        boss_damage_permille=boss,
        boss_escort_damage_permille=escort,
    )
    return give_turn(state, U1)


def _scaled(tags: list[str]) -> BattleState:
    # 三個倍率各不相同，才分辨得出套用了哪一個
    return _state(tags, enemy=1500, boss=2000, escort=2500)


def _actual(state: BattleState, face: int) -> int:
    """命中、不暴擊、傷害骰擲出 ``face`` 時的實際扣血。"""
    sides = state.units[U1].weapon.dice.sides
    result = resolve(with_rolls(state, [(20, 15), (sides, face)]), ATTACK)
    damage = next(e for e in result.events if isinstance(e, DamageDealt) and e.target_id == U2)
    return damage.amount - damage.absorbed


@pytest.mark.parametrize(("tags", "kind"), TAG_CASES)
def test_preview_matches_actual_damage_under_the_enemy_multiplier(
    tags: list[str], kind: str
) -> None:
    state = _scaled(tags)
    p = preview(state, ATTACK)
    assert p.damage is not None, kind
    sides = state.units[U1].weapon.dice.sides
    amounts = [_actual(state, face) for face in range(1, sides + 1)]
    assert p.damage.minimum == amounts[0]
    # 不暴擊時的期望傷害 ＝ 每個骰面實際結算的平均（暴擊另計，故只比對下界）
    normal_mean = Fraction(sum(amounts), sides)
    if p.crit_chance == 0:
        assert p.damage.expected_if_hit == normal_mean
    else:
        assert p.damage.expected_if_hit >= normal_mean


@pytest.mark.parametrize(("tags", "kind"), TAG_CASES)
def test_preview_numbers_grow_with_the_matching_multiplier(tags: list[str], kind: str) -> None:
    neutral = preview(_state(tags, enemy=1000, boss=1000, escort=1000), ATTACK)
    scaled = preview(_scaled(tags), ATTACK)
    assert neutral.damage is not None and scaled.damage is not None, kind
    assert scaled.damage.maximum > neutral.damage.maximum
    assert scaled.damage.expected > neutral.damage.expected
    # 其他兩種倍率不影響這一類敵人
    other = {
        "enemy": _state(tags, enemy=1500, boss=1000, escort=1000),
        "boss": _state(tags, enemy=1000, boss=2000, escort=1000),
        "escort": _state(tags, enemy=1000, boss=1000, escort=2500),
    }[kind]
    only = preview(other, ATTACK)
    assert only.damage == scaled.damage


@pytest.mark.parametrize(("tags", "kind"), TAG_CASES)
def test_enemy_skill_preview_brackets_actual_damage_under_the_multiplier(
    tags: list[str], kind: str
) -> None:
    """敵方施放單體火焰箭：預告的最少／最多與實際結算（同樣的骰值）一致，且大於不乘倍率時。"""

    def build(enemy: int, boss: int, escort: int) -> BattleState:
        m = make_map(FLAT7, ally=[(4, 3)], enemy=[(1, 3)])
        caster = caster_template([FIRE_BOLT]).model_copy(update={"tags": tags})
        spawns = [
            spawn(Team.ENEMY, (1, 3), caster),
            spawn(Team.ALLY, (4, 3), no_reactions(max_hp=99)),
        ]
        state = make_state(
            m,
            spawns,
            enemy_damage_permille=enemy,
            boss_damage_permille=boss,
            boss_escort_damage_permille=escort,
        )
        return give_turn(state, U1)

    state = build(1500, 2000, 2500)
    action = UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2)
    (target,) = preview(state, action).targets
    assert target.damage is not None, kind
    low = resolve(with_rolls(state, [(20, 19), (8, 1), (8, 1)]), action)
    high = resolve(with_rolls(state, [(20, 20), (8, 8), (8, 8), (8, 8), (8, 8)]), action)
    (low_dmg,) = [e for e in low.events if isinstance(e, DamageDealt) and e.cause == "attack"]
    (high_dmg,) = [e for e in high.events if isinstance(e, DamageDealt) and e.cause == "attack"]
    assert low_dmg.amount == target.damage.minimum
    assert high_dmg.amount == target.damage.maximum
    (neutral,) = preview(build(1000, 1000, 1000), action).targets
    assert neutral.damage is not None
    assert target.damage.expected > neutral.damage.expected
