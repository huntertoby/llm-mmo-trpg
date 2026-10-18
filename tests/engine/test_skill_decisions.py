"""Phase 2A-2 6.0 的 PM 決定：武器技暴擊（#3）、敵我不分不打自己（#4，見 test_skill_scenarios）、
預覽的擊倒成功率（#5），以及條件技能的預覽與實際結算一致。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, battle, of, script_rolls
from trpg.engine import BattleState, UseSkill, preview, resolve
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.engine.rules.combat import is_hit
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team

STRIKE = {"type": "single", "range": "weapon"}


def _crit_of(base: str, natural: int, category: str = "weapon") -> bool:
    if category == "weapon":
        skill = make_skill(
            SID, STRIKE, [{"type": "damage"}], category="weapon", weapon_req="melee", attr="str"
        )
    else:
        skill = make_skill(
            SID,
            {"type": "single", "range": 1},
            [{"type": "damage", "dice": "1d6", "element": "fire"}],
        )
    state = battle(skill, [(4, 3)], base=base)
    caster = state.units[U1]
    assert (category == "spell") or caster.weapon.is_melee
    state = with_rolls(state, [(20, natural)] + [(6, 3)] * 4)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    (roll,) = of(result, AttackRolled)
    return roll.hit and roll.crit


def test_weapon_skill_crits_on_the_weapons_crit_range() -> None:
    """決定 #3：匕首（crit_range 19）的武器技在自然 19 暴擊，單手劍（20）不會。"""
    assert library().weapons["dagger"].crit_range == 19
    assert library().weapons["one_handed_sword"].crit_range == 20
    assert _crit_of("bandit", 19)  # 匕首
    assert not _crit_of("hero_fighter", 19)  # 單手劍
    assert _crit_of("hero_fighter", 20)


def test_spell_skill_crits_only_on_a_natural_20() -> None:
    """法術技維持只有自然 20，即使法器的暴擊範圍更低。"""
    assert not _crit_of("hero_mage", 19, "spell")
    assert _crit_of("hero_mage", 20, "spell")


def test_preview_uses_the_weapon_crit_range_for_weapon_skills() -> None:
    skill = make_skill(SID, STRIKE, [{"type": "damage"}], category="weapon", weapon_req="melee")
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    (dagger,) = preview(battle(skill, [(4, 3)], base="bandit"), action).targets
    (sword,) = preview(battle(skill, [(4, 3)], base="hero_fighter"), action).targets
    # 自然 19 與 20 都命中時，匕首的暴擊率是單手劍的兩倍
    assert dagger.crit_chance == Fraction(2, 20) and sword.crit_chance == Fraction(1, 20)


# ---------------------------------------------------------------------------
# 決定 #5：預覽顯示擊倒的對抗成功率
# ---------------------------------------------------------------------------


def _expected_knock(state: object, attr: str) -> Fraction:
    rules = library().ruleset
    caster, target = state.units[U1], state.units[U2]  # type: ignore[attr-defined]
    modifier = rules.hit_table.modifier(caster.attributes[attr], max(1, target.attributes[attr]))
    total = modifier + rules.core.proficiency
    wins = sum(1 for n in range(1, 21) if is_hit(n, n + total, rules.core.hit_target))
    return Fraction(wins, 20)


def test_preview_reports_the_knock_prone_contest_chance() -> None:
    skill = make_skill(
        SID, STRIKE, [{"type": "damage"}, {"type": "knock_prone"}], category="weapon"
    )
    state = battle(skill, [(4, 3)], base="hero_fighter")
    (target,) = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets
    assert target.knock_chance == _expected_knock(state, "str")
    assert target.knock_chance is not None and 0 < target.knock_chance < 1


def test_the_knock_chance_follows_the_attribute_matchup() -> None:
    skill = make_skill(
        SID, STRIKE, [{"type": "damage"}, {"type": "knock_prone"}], category="weapon"
    )
    weak = battle(skill, [(4, 3)], base="hero_fighter")
    strong = battle(skill, [(4, 3)], base="hero_fighter")
    strong.units[U2].attributes = {**strong.units[U2].attributes, "str": 30}  # type: ignore[dict-item]
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    strong_chance = preview(strong, action).targets[0].knock_chance
    weak_chance = preview(weak, action).targets[0].knock_chance
    assert strong_chance is not None and weak_chance is not None
    assert strong_chance < weak_chance


def test_no_knock_chance_without_a_knock_prone_effect() -> None:
    skill = make_skill(SID, STRIKE, [{"type": "damage"}], category="weapon")
    state = battle(skill, [(4, 3)], base="hero_fighter")
    (target,) = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets
    assert target.knock_chance is None


# ---------------------------------------------------------------------------
# 條件技能：預覽與實際結算一致
# ---------------------------------------------------------------------------


def _real_battle(skill_id: str, base: str = "hero_mage") -> BattleState:
    """施放者（U1）裝備 ``content/`` 裡真正的技能；敵人 U2 在 (4, 3)。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    caster = template(base, reactions=[], max_mana=99, skills=[skill_id])
    spawns = [spawn(Team.ALLY, (3, 3), caster), spawn(Team.ENEMY, (4, 3), no_reactions())]
    return give_turn(make_state(m, spawns), U1)


@pytest.mark.parametrize("burning", [False, True])
def test_preview_of_a_conditional_damage_skill_matches_the_resolution(
    burning: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    lib = library()
    skill = lib.skills["skill_cinder_burst"]
    state = _real_battle(skill.id)
    if burning:
        state.units[U2].statuses.append(StatusInstance("burning", 2))
    action = UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2)
    (target,) = preview(state, action).targets
    assert target.damage is not None
    # 最小骰值：d20 = 19（命中、不暴擊），所有傷害骰 = 1
    script_rolls(monkeypatch, [19, *([1] * 6)])
    result = resolve(state, action)
    dealt = sum(d.amount for d in of(result, DamageDealt) if d.cause == "attack")
    assert dealt == target.damage.minimum
    assert result.state.units[U2].team is Team.ENEMY


def test_the_burning_bonus_raises_the_expected_damage_but_not_the_plain_hit() -> None:
    lib = library()
    skill = lib.skills["skill_cinder_burst"]
    action = UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2)

    def expected(burning: bool) -> Fraction:
        state = _real_battle(skill.id)
        if burning:
            state.units[U2].statuses.append(StatusInstance("burning", 2))
        (target,) = preview(state, action).targets
        assert target.damage is not None
        return target.damage.expected_if_hit

    assert expected(True) > expected(False) + 5  # 3d6 平均 10.5（再乘元素與護甲，至少多 5 點）
