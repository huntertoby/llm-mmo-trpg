"""Phase 3-52b：專注自動消耗（下一個造成傷害的主動技能吃掉全部專注）與氣只加成治療自己。"""

from __future__ import annotations

from tests.engine.helpers import library, with_rolls
from tests.engine.skill_helpers import U1, U2, of
from tests.engine.test_stack_expansion import FIGHTER, HIT, JAB, MEND, SHOT, scene
from trpg.content.skills import SkillDef
from trpg.content.stacks import auto_consumed
from trpg.engine import UseSkill, resolve
from trpg.engine.events import DamageDealt, Healed, StacksChanged
from trpg.shared.types import Team

BREATH = "skill_qi_breath"


def _jab(focus: int) -> tuple[int, dict[str, int]]:
    state = scene([JAB], base=FIGHTER)
    state.units[U1].stacks = {"focus": focus} if focus else {}
    result = resolve(with_rolls(state, [HIT]), UseSkill(unit_id=U1, skill_id=JAB, target_id=U2))
    (dealt,) = of(result, DamageDealt)
    return dealt.multiplier_permille, dict(result.state.units[U1].stacks)


def test_the_next_damaging_skill_eats_all_the_focus() -> None:
    plain, _ = _jab(0)
    boosted, left = _jab(3)
    assert boosted == plain * (1000 + 3 * 150) // 1000
    assert "focus" not in left  # 吃完歸零


def test_each_stack_adds_fifteen_percent() -> None:
    plain, _ = _jab(0)
    for n in (1, 2):
        boosted, _ = _jab(n)
        assert boosted == plain * (1000 + n * 150) // 1000


def test_a_skill_that_deals_no_damage_leaves_the_focus_alone() -> None:
    state = scene([MEND])
    state.units[U2].team = Team.ALLY
    state.units[U1].stacks = {"focus": 2}
    result = resolve(with_rolls(state, [HIT]), UseSkill(unit_id=U1, skill_id=MEND, target_id=U2))
    assert result.state.units[U1].stacks.get("focus") == 2
    assert not [e for e in of(result, StacksChanged) if e.stack_id == "focus"]


def test_the_demo_consumer_keeps_its_own_setting_and_is_not_boosted_twice() -> None:
    state = scene([SHOT], base="hero_archer")
    state.units[U1].stacks = {"focus": 2}
    result = resolve(with_rolls(state, [HIT]), UseSkill(unit_id=U1, skill_id=SHOT, target_id=U2))
    (dealt,) = of(result, DamageDealt)
    assert dealt.multiplier_permille == 1500 * (1000 + 2 * 150) // 1000
    assert len([e for e in of(result, StacksChanged) if e.stack_id == "focus"]) == 1


def test_the_focus_survives_a_non_damaging_skill() -> None:
    state = scene([MEND])
    state.units[U2].team = Team.ALLY
    state.units[U1].stacks = {"focus": 1}
    healed = resolve(with_rolls(state, [HIT]), UseSkill(unit_id=U1, skill_id=MEND, target_id=U2))
    assert healed.state.units[U1].stacks.get("focus") == 1


def test_only_active_damaging_skills_without_their_own_consume_auto_consume() -> None:
    lib = library()
    stacks = lib.ruleset.stacks.stacks
    assert [s.id for s in auto_consumed(lib.skills[JAB], stacks)] == ["focus"]
    assert auto_consumed(lib.skills[MEND], stacks) == ()
    assert auto_consumed(lib.skills[SHOT], stacks) == ()  # 自己有 consume_stack 專注
    passive: SkillDef = lib.skills[JAB].model_copy(update={"kind": "passive"})
    assert auto_consumed(passive, stacks) == ()


def test_ki_only_boosts_effects_that_heal_yourself() -> None:
    ki = library().ruleset.stack_def("ki")
    assert ki.consumer is not None and ki.consumer.heal_self_only
    heal = next(e for e in library().skills[BREATH].effects if e.type == "heal")
    assert heal.affects == "self" and ki.consumer.boosts_effect(heal)
    assert not ki.consumer.boosts_effect(heal.model_copy(update={"affects": "allies"}))
    assert not ki.consumer.boosts_effect(heal.model_copy(update={"affects": None}))
    damage = next(e for e in library().skills[JAB].effects if e.type == "damage")
    assert ki.consumer.boosts_effect(damage)
    holy = library().ruleset.stack_def("holy_power").consumer
    assert holy is not None and holy.boosts_effect(heal.model_copy(update={"affects": "allies"}))


def test_ki_boosts_the_self_heal_in_play() -> None:
    def healed(ki: int) -> int:
        state = scene([BREATH], base=FIGHTER)
        unit = state.units[U1]
        unit.hp = 1
        unit.stacks = {"ki": ki} if ki else {}
        result = resolve(
            with_rolls(state, [(6, 4), (6, 4), (6, 4)]), UseSkill(unit_id=U1, skill_id=BREATH)
        )
        (event,) = of(result, Healed)
        assert event.target_id == U1
        return event.amount

    assert healed(3) > healed(0)
