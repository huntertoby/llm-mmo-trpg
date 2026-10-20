"""Phase 3C-6a：被近戰攻擊後（不論命中與否）轉身面向攻擊者（``docs/design/05-戰鬥.md`` 5.1）。

近戰命中與未命中都轉身、遠程不轉、強制位移不轉、背刺以擲骰當下的朝向為準所以第二下不再背刺。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, with_rolls
from tests.engine.skill_helpers import U1, U2, U3
from tests.engine.test_facing_backstab import BACKSTAB, duel, rolled
from trpg.engine import Attack, Shove, UseSkill, resolve
from trpg.shared.types import Team


def test_a_melee_hit_turns_the_target_toward_the_attacker() -> None:
    state = duel((4, 3), foe_facing="west", weapon="one_handed_sword")
    result = resolve(with_rolls(state, [(20, 20)]), Attack(unit_id=U1, target_id=U2))
    assert rolled(result)[0].hit and rolled(result)[0].backstab == 2  # 擲骰當下仍在背後
    assert result.state.units[U2].facing == "east"  # 結算後轉身面向 (4, 3)


def test_a_melee_miss_also_turns_the_target() -> None:
    state = duel((3, 4), foe_facing="west", weapon="one_handed_sword")
    result = resolve(with_rolls(state, [(20, 1)]), Attack(unit_id=U1, target_id=U2))
    assert not rolled(result)[0].hit
    assert result.state.units[U2].facing == "south"


def test_a_melee_skill_turns_the_target_hit_or_miss() -> None:
    for natural in (1, 20):
        state = duel((3, 4), (3, 3), skills=("skill_pincer_strike",))
        action = UseSkill(unit_id=U1, skill_id="skill_pincer_strike", target_id=U2)
        result = resolve(with_rolls(state, [(20, natural)]), action)
        assert rolled(result)[0].hit is (natural == 20)
        assert result.state.units[U2].facing == "south"


def test_ranged_attacks_do_not_turn_the_target() -> None:
    state = duel((5, 3), foe_facing="north", weapon="bow", base="hero_archer", skills=())
    for natural in (1, 20):
        result = resolve(with_rolls(state, [(20, natural)]), Attack(unit_id=U1, target_id=U2))
        assert result.state.units[U2].facing == "north"


def test_forced_displacement_does_not_turn_the_target() -> None:
    state = duel((2, 3), (3, 3))
    state.units[U2].facing = "north"
    shoved = resolve(with_rolls(state, [(20, 20)]), Shove(unit_id=U1, target_id=U2)).state
    assert shoved.units[U2].xy == (4, 3) and shoved.units[U2].facing == "north"


def test_the_second_melee_attack_is_no_longer_a_backstab() -> None:
    state = duel((4, 3), foe_facing="west", weapon="one_handed_sword")
    first = resolve(with_rolls(state, [(20, 10), (20, 10)]), Attack(unit_id=U1, target_id=U2))
    second = resolve(first.state, Attack(unit_id=U1, target_id=U2))
    assert rolled(first)[0].backstab == 2
    assert rolled(second)[0].backstab == 0


def test_the_tank_turns_the_enemy_and_the_teammate_backstabs() -> None:
    # U2 面向北；U1（坦克）從西邊砍，U2 轉向西，東邊的 U3（盜賊）就站在他背後
    state = duel((2, 3), foe_facing="north", extra=((Team.ALLY, (4, 3)),))
    assert state.units[U3].weapon.is_melee
    before = resolve(give_turn(with_rolls(state, [(20, 10)]), U3), Attack(unit_id=U3, target_id=U2))
    assert rolled(before, U3)[0].backstab == 0  # 沒有先轉向：側面
    tank = resolve(with_rolls(state, [(20, 10), (20, 10)]), Attack(unit_id=U1, target_id=U2))
    assert tank.state.units[U2].facing == "west"
    rogue = resolve(give_turn(tank.state, U3), Attack(unit_id=U3, target_id=U2))
    assert rolled(rogue, U3)[0].backstab == 2


def test_a_backstab_cast_keeps_its_bonus_damage_then_the_target_turns() -> None:
    # 瞬步背刺的第二段傷害（條件 from_behind）在同一次施放內仍成立，施放完才轉身
    state = duel((1, 3), foe_facing="west", skills=(BACKSTAB,))
    action = UseSkill(unit_id=U1, skill_id=BACKSTAB, target_id=U2)
    result = resolve(with_rolls(state, [(20, 20)] * 4), action)
    assert [r.backstab for r in rolled(result)] == [2]
    assert result.state.units[U1].xy == (4, 3) and result.state.units[U2].facing == "east"
