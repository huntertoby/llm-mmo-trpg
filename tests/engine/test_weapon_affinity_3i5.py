"""武器親和與招牌技（Phase 3I-5；`docs/phases/Phase3I計畫.md`；06 6.10，玩法決定 #50）。

- 條件 ``wielding_weapon``（手持某種武器時）：寫在效果上，主手武器或副手的 ID 相符才成立；
  沒拿那種武器時技能照常可用，只是少那個效果。
- ``weapon_only``（限定武器）：不符的武器不能裝備、不能施放。
- 卡片與實戰一致：卡片寫的「若手持…時」就是引擎成立的那一個效果。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, battle, hit_with, of
from trpg.content.battle import UnitTemplate
from trpg.content.equipment import loadout_held
from trpg.content.keyword_derive import skill_condition_specs
from trpg.content.library import gear_class_problem, gear_reference_problems, unit_skill_problems
from trpg.content.skills import (
    CASTER_CONDITIONS,
    ConditionSpec,
    SkillDef,
    held_gear,
    weapon_problem,
)
from trpg.engine import BattleSetupError, UseSkill, begin_battle, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, SkillUsed
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn
from trpg.engine.skills.conditions import Subject, condition_met, unit_held
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import state_to_json
from trpg.narrative.skills import condition_summary, skill_card
from trpg.shared.types import Team

LIB = library()


def _skills_with_affinity() -> list[SkillDef]:
    return sorted(
        (
            s
            for s in LIB.skills.values()
            if any(c.type == "wielding_weapon" for c in skill_condition_specs(s))
        ),
        key=lambda s: s.id,
    )


def _limited() -> list[SkillDef]:
    return sorted((s for s in LIB.skills.values() if s.weapon_only), key=lambda s: s.id)


def _equip(state: Any, weapon_id: str, offhand_id: str | None = None) -> None:
    unit = state.units[U1]
    unit.weapon = LIB.weapons[weapon_id]
    offhand = None if offhand_id is None else LIB.offhands[offhand_id]
    unit.gear = dataclasses.replace(unit.gear, offhand=offhand)


def _off_weapon(skill: SkillDef) -> str:
    """技能大類相容、但不是親和武器的另一把武器。"""
    return {"melee": "one_handed_sword", "ranged": "bow"}.get(skill.weapon_req, "fire_staff")


def _base(skill: SkillDef) -> str:
    """施放者的單位範本（依技能的武器需求；之後再換上指定的武器）。"""
    return {"melee": "hero_fighter", "ranged": "hero_archer"}.get(skill.weapon_req, "hero_mage")


def _built_battle(skill: SkillDef, weapon_id: str, offhand_id: str | None) -> Any:
    """施放者從開戰就拿著指定的主手武器與副手（限定武器的技能要這樣才裝得上）。"""
    equipment = {}
    if offhand_id is not None:
        equipment = {"off_hand": next(i for i, d in LIB.items.items() if d.offhand == offhand_id)}
    tmpl = caster_template([skill], base=_base(skill), weapon=weapon_id, equipment=equipment)
    caster = UnitSpawn(
        template=tmpl,
        weapon=LIB.weapons[weapon_id],
        team=Team.ALLY,
        position=(3, 3),
        equipment=LIB.loadout_of(tmpl),
    )
    foe = spawn(Team.ENEMY, (4, 3), no_reactions())
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    return give_turn(make_state(m, [caster, foe], skills=[skill]), U1)


def _aim(skill: SkillDef) -> dict[str, Any]:
    """依形狀給的選取：單體選 U2，錐形往東。"""
    return {"direction": "east"} if skill.shape.type == "cone" else {"target_id": U2}


# ---------------------------------------------------------------------------
# 條件本身：手持某種武器時
# ---------------------------------------------------------------------------

CONDITION_TABLE: list[tuple[str, str | None, str, bool]] = [
    # (主手, 副手, 條件指定的裝備, 是否成立)
    ("whip", None, "whip", True),
    ("one_handed_sword", None, "whip", False),
    ("dagger", None, "dual_dagger", False),  # 雙匕首不算匕首（成對武器是它自己那一種）
    ("dual_dagger", None, "dagger", False),
    ("dual_dagger", None, "dual_dagger", True),
    ("one_handed_sword", "round_shield", "round_shield", True),  # 副手也算「手持」
    ("one_handed_sword", "tower_shield", "round_shield", False),
    ("one_handed_sword", None, "round_shield", False),
    ("arcane_blade", "tome", "arcane_blade", True),
    ("arcane_blade", "tome", "tome", True),
    ("fire_staff", "orb", "tome", False),
]


@pytest.mark.parametrize(("weapon_id", "offhand_id", "wanted", "expected"), CONDITION_TABLE)
def test_wielding_weapon_matches_the_main_hand_or_the_offhand(
    weapon_id: str, offhand_id: str | None, wanted: str, expected: bool
) -> None:
    base = LIB.skills["skill_chain_lash"].model_copy(update={"id": SID})
    state = battle(base, [(4, 3)], caster=(3, 3), base="hero_fighter")
    _equip(state, weapon_id, offhand_id)
    caster = state.units[U1]
    spec = ConditionSpec(type="wielding_weapon", weapon=wanted)
    assert condition_met(state, caster, spec, Subject(state.units[U2], (4, 3))) is expected
    assert (wanted in unit_held(caster)) is expected


def test_the_condition_is_a_caster_condition_with_the_common_multiplier() -> None:
    assert "wielding_weapon" in CASTER_CONDITIONS
    definition = LIB.ruleset.conditions.by_id()["wielding_weapon"]
    assert (definition.harshness, definition.min_rarity) == ("common", "rare")
    assert definition.params["weapon"].type == "weapon"


# ---------------------------------------------------------------------------
# 親和技能：有拿才多一個效果，沒拿照常可用（實戰）
# ---------------------------------------------------------------------------


def _affinity_gear(skill: SkillDef) -> tuple[str, str | None]:
    """（主手, 副手）：讓技能的親和條件成立的最小裝備組合。"""
    wanted = next(
        c.weapon
        for c in skill_condition_specs(skill)
        if c.type == "wielding_weapon" and c.weapon is not None
    )
    if wanted in LIB.offhands:
        return _off_weapon(skill), wanted
    return wanted, None


def _damage_count(skill: SkillDef, weapon_id: str, offhand_id: str | None) -> int:
    probe = skill.model_copy(update={"id": SID})
    state = hit_with(battle(probe, [(4, 3)], caster=(3, 3), base=_base(skill)))
    _equip(state, weapon_id, offhand_id)
    unit = state.units[U1]
    unit.mana, unit.stamina, unit.ammo = 99, 99, 9
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, **_aim(skill)))
    return len([e for e in of(result, DamageDealt) if e.source_id == U1])


DAMAGE_COMBOS = [
    s
    for s in _skills_with_affinity()
    if sum(1 for e in s.effects if e.type == "damage") == 2
    and any(
        e.type == "damage" and e.condition is not None and e.condition.type == "wielding_weapon"
        for e in s.effects
    )
]


@pytest.mark.parametrize("skill", DAMAGE_COMBOS, ids=lambda s: s.id)
def test_the_bonus_damage_appears_only_while_wielding_the_weapon(skill: SkillDef) -> None:
    on_weapon, on_offhand = _affinity_gear(skill)
    with_it = _damage_count(skill, on_weapon, on_offhand)
    without = _damage_count(skill, _off_weapon(skill), None)
    assert with_it == without + 1  # 沒拿時照常可用（少一次傷害），拿了才多那一次
    assert without >= 1


def test_every_affinity_skill_is_castable_without_the_weapon() -> None:
    assert len(_skills_with_affinity()) >= 24
    for skill in _skills_with_affinity():
        if skill.weapon_only:
            continue
        probe = skill.model_copy(update={"id": SID})
        state = battle(probe, [(4, 3)], caster=(3, 3), base=_base(skill))
        _equip(state, _off_weapon(skill), None)
        unit = state.units[U1]
        unit.mana, unit.stamina, unit.ammo = 99, 99, 9
        problem = resource_problem(state, unit, probe)
        assert problem is None, (skill.id, problem)


def test_each_new_weapon_has_two_or_three_affinity_skills() -> None:
    wanted = ["fist", "scythe", "whip", "arcane_blade", "round_shield", "tower_shield"]
    wanted += ["tome", "orb", "dual_dagger", "shotgun", "pistol", "dual_pistol"]
    count = dict.fromkeys(wanted, 0)
    for skill in _skills_with_affinity():
        for cond in skill_condition_specs(skill):
            if cond.type == "wielding_weapon" and cond.weapon in count:
                count[cond.weapon] += 1
    assert all(2 <= n <= 3 for n in count.values()), count


# ---------------------------------------------------------------------------
# 限定武器：不符的武器不能裝備、不能施放
# ---------------------------------------------------------------------------

LIMITED_TABLE: list[tuple[str, str, str | None, bool]] = [
    # (技能, 主手, 副手, 可用)
    ("skill_whip_crack", "whip", None, True),
    ("skill_whip_crack", "one_handed_sword", None, False),
    ("skill_whip_crack", "dagger", None, False),
    ("skill_bastion_strike", "one_handed_sword", "round_shield", True),
    ("skill_bastion_strike", "one_handed_sword", "tower_shield", True),
    ("skill_bastion_strike", "one_handed_sword", None, False),
    ("skill_bastion_strike", "one_handed_sword", "tome", False),
    ("skill_crossing_slash", "dual_dagger", None, True),
    ("skill_crossing_slash", "dagger", None, False),
    ("skill_blazing_round", "pistol", None, True),
    ("skill_blazing_round", "shotgun", None, True),
    ("skill_blazing_round", "dual_pistol", None, True),
    ("skill_blazing_round", "longgun", None, True),
    ("skill_blazing_round", "bow", None, False),
    ("skill_blazing_round", "crossbow", None, False),
    ("skill_crossfire", "dual_pistol", None, True),
    ("skill_crossfire", "pistol", None, False),
]


@pytest.mark.parametrize(("skill_id", "weapon_id", "offhand_id", "usable"), LIMITED_TABLE)
def test_a_limited_skill_needs_the_listed_weapon_to_equip_and_to_cast(
    skill_id: str, weapon_id: str, offhand_id: str | None, usable: bool
) -> None:
    skill = LIB.skills[skill_id]
    weapon = LIB.weapons[weapon_id]
    offhand = None if offhand_id is None else LIB.offhands[offhand_id]
    held = held_gear(weapon, offhand)
    # 不能裝備：武器大類與限定武器都要符合
    equip_problem = weapon_problem(skill, weapon.weapon_class, held)
    assert (equip_problem is None) is usable, equip_problem
    # 不能施放：引擎在施放時也擋（防禦性檢查，例如暫時獲得的技能）
    probe = skill.model_copy(update={"id": SID})
    # 開戰時就裝不上：施放者的裝備與技能不相容，開戰檢查拒絕（不能裝）
    if not usable:
        with pytest.raises(BattleSetupError, match=r"需要|限定手持"):
            _built_battle(probe, weapon_id, offhand_id)
    # 施放時也擋：先拿著合法的裝備開戰，再把裝備換掉（防禦性檢查，例如暫時獲得的技能）
    legal_weapon, legal_off = {
        "skill_whip_crack": ("whip", None),
        "skill_bastion_strike": ("one_handed_sword", "round_shield"),
        "skill_crossing_slash": ("dual_dagger", None),
        "skill_crossfire": ("dual_pistol", None),
        "skill_blazing_round": ("pistol", None),
    }[skill_id]
    state = _built_battle(probe, legal_weapon, legal_off)
    unit = state.units[U1]
    unit.mana, unit.stamina, unit.ammo = 99, 99, 9
    assert resource_problem(state, unit, probe) is None
    _equip(state, weapon_id, offhand_id)
    cast_problem = resource_problem(state, unit, probe)
    if weapon.weapon_class != skill.weapon_req:
        assert cast_problem is not None
    else:
        assert (cast_problem is None) is usable, cast_problem
        if not usable:
            assert "限定手持" in str(cast_problem)
    legal = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    assert bool(legal) is (usable and cast_problem is None)


def _spawn_with(skill_id: str, weapon_id: str) -> BattleSetup:
    hero = LIB.unit("hero_fighter").model_copy(update={"skills": (skill_id,), "weapon": weapon_id})
    foe = LIB.unit("bandit")
    units = (
        UnitSpawn(template=hero, weapon=LIB.weapons[weapon_id], team=Team.ALLY, position=None),
        UnitSpawn(template=foe, weapon=LIB.weapon_of(foe), team=Team.ENEMY, position=None),
    )
    return BattleSetup(map=LIB.map("test_flat_6x6"), ruleset=LIB.ruleset, units=units)


def test_battle_setup_rejects_a_limited_skill_without_the_weapon() -> None:
    begin_battle(_spawn_with("skill_whip_crack", "whip"), 1)
    with pytest.raises(BattleSetupError, match="限定手持"):
        begin_battle(_spawn_with("skill_whip_crack", "one_handed_sword"), 1)


def test_unit_templates_check_limited_skills_against_the_offhand() -> None:
    hero: UnitTemplate = LIB.unit("hero_fighter").model_copy(
        update={"skills": ("skill_bastion_strike",)}
    )
    sword = LIB.weapons["one_handed_sword"]
    core = LIB.ruleset.core
    assert unit_skill_problems(hero, sword, LIB.skills, core, LIB.offhands["tower_shield"]) == []
    assert any("限定手持" in p for p in unit_skill_problems(hero, sword, LIB.skills, core))


def test_each_signature_skill_covers_its_gear_group() -> None:
    only = {s.id: set(s.weapon_only) for s in _limited()}
    assert only["skill_whip_crack"] == {"whip"}
    assert only["skill_bastion_strike"] == {"round_shield", "tower_shield"}
    assert only["skill_crossing_slash"] == {"dual_dagger"}
    assert only["skill_crossfire"] == {"dual_pistol"}
    assert only["skill_blazing_round"] == {"longgun", "shotgun", "pistol", "dual_pistol"}
    assert all(s.rarity == "rare" for s in _limited())


# ---------------------------------------------------------------------------
# schema 與驗證器
# ---------------------------------------------------------------------------


def test_the_condition_may_only_be_written_on_effects() -> None:
    data = LIB.skills["skill_chain_lash"].model_dump(mode="json")
    data["condition"] = {"type": "wielding_weapon", "weapon": "whip"}
    with pytest.raises(ValidationError, match="只能寫在效果上"):
        SkillDef.model_validate(data)


def test_weapon_only_must_not_repeat() -> None:
    data = LIB.skills["skill_whip_crack"].model_dump(mode="json")
    data["weapon_only"] = ["whip", "whip"]
    with pytest.raises(ValidationError, match="不可重複"):
        SkillDef.model_validate(data)


GEAR_TABLE: list[tuple[str, str, str | None]] = [
    ("melee", "whip", None),
    ("melee", "bow", "弓是遠程武器"),
    ("ranged", "whip", "鞭是近戰武器"),
    ("any", "bow", None),
    ("melee", "round_shield", None),  # 副手不分大類
    ("melee", "no_such_weapon", "未知的武器或副手"),
]


@pytest.mark.parametrize(("weapon_req", "gear", "expected"), GEAR_TABLE)
def test_gear_class_problem_table(weapon_req: str, gear: str, expected: str | None) -> None:
    found = gear_class_problem(weapon_req, gear, LIB.weapons, LIB.offhands)
    assert (found is None) if expected is None else (found is not None and expected in found)


def test_the_validator_reports_unknown_and_mismatched_gear() -> None:
    skill = LIB.skills["skill_whip_crack"]
    assert gear_reference_problems(skill, LIB.weapons, LIB.offhands) == []
    bad = skill.model_copy(update={"weapon_only": ("whip", "bow")})
    problems = gear_reference_problems(bad, LIB.weapons, LIB.offhands)
    assert len(problems) == 1 and "weapon_only" in problems[0] and "弓" in problems[0]
    first = skill.effects[0].model_copy(
        update={"condition": ConditionSpec(type="wielding_weapon", weapon="nope")}
    )
    unknown = skill.model_copy(update={"effects": (first, *skill.effects[1:])})
    assert any(
        "未知的武器或副手" in p for p in gear_reference_problems(unknown, LIB.weapons, LIB.offhands)
    )


# ---------------------------------------------------------------------------
# 卡片與實戰一致
# ---------------------------------------------------------------------------


def test_the_card_names_the_weapon_for_the_conditional_effect_and_the_limit() -> None:
    chain = skill_card(LIB, LIB.skills["skill_chain_lash"])
    assert chain.weapon_only is None
    assert len(chain.effects) == 2
    assert chain.effects[1].endswith("，若手持鞭時")
    assert "若手持" not in chain.effects[0]
    crack = skill_card(LIB, LIB.skills["skill_whip_crack"])
    assert crack.weapon_only == "限定手持：鞭"
    bastion = skill_card(LIB, LIB.skills["skill_bastion_strike"])
    assert bastion.weapon_only == "限定手持：圓盾、塔盾"
    spec = ConditionSpec(type="wielding_weapon", weapon="dual_pistol")
    assert condition_summary(LIB, spec) == "手持雙手槍時"


def test_every_conditional_effect_on_the_card_is_the_one_the_engine_gates() -> None:
    """卡片上標「若手持…」的效果，就是引擎依武器判斷的那一個（逐技能比對）。"""
    for skill in _skills_with_affinity():
        card = skill_card(LIB, skill)
        gated = [
            i
            for i, e in enumerate(skill.effects)
            if e.condition is not None and e.condition.type == "wielding_weapon"
        ]
        marked = [i for i, line in enumerate(card.effects) if "，若手持" in line]
        assert gated == marked, skill.id


def test_a_battle_with_signature_and_affinity_skills_replays_identically() -> None:
    """一場含招牌技與親和技能的 AI 對戰：初始狀態＋動作列表重播得到相同的最終狀態。"""

    def hero(weapon: str, skills: tuple[str, ...], base: str) -> UnitSpawn:
        tmpl = LIB.unit(base).model_copy(
            update={"weapon": weapon, "skills": skills, "max_mana": 40}
        )
        return UnitSpawn(template=tmpl, weapon=LIB.weapons[weapon], team=Team.ALLY, position=None)

    bandit = LIB.unit("bandit")
    foes = [
        UnitSpawn(template=bandit, weapon=LIB.weapon_of(bandit), team=Team.ENEMY, position=None)
        for _ in range(3)
    ]
    allies = [
        hero(
            "whip", ("skill_whip_crack", "skill_chain_lash", "skill_hamstring_lash"), "hero_fighter"
        ),
        hero(
            "dual_pistol",
            ("skill_crossfire", "skill_akimbo_burst", "skill_blazing_round"),
            "hero_archer",
        ),
        hero(
            "dual_dagger",
            ("skill_crossing_slash", "skill_twin_fang", "skill_blade_dance"),
            "hero_fighter",
        ),
    ]
    setup = BattleSetup(
        map=LIB.map("test_flat_6x6"), ruleset=LIB.ruleset, units=(*allies, *foes), max_rounds=30
    )
    run = run_battle(setup, 3, UtilityAI(LIB.ai_profiles))
    again = replay(setup, 3, run.actions)
    assert state_to_json(run.state) == state_to_json(again.state)
    assert len(run.events) == len(again.events)
    used = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
    assert {"skill_whip_crack", "skill_crossfire"} & used  # 戰鬥中真的施放了招牌技


def test_held_gear_helpers_agree() -> None:
    sword, shield = LIB.weapons["one_handed_sword"], LIB.offhands["round_shield"]
    assert held_gear(sword, shield) == {"one_handed_sword": sword.name_zh, "round_shield": "圓盾"}
    assert loadout_held(sword, None) == {"one_handed_sword": sword.name_zh}
