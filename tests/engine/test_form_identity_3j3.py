"""Phase 3J-3：形態身分的行為一致測試（``docs/phases/Phase3J計畫.md`` 4.8 節，06 6.30）。

- 條件 ``in_form``（任何／物理／心智）：引擎、驗證器、卡片句；
- 化形專精（``skill_form_mastery``）：維持費減半、進入獎勵 ×1.5（各自無條件捨去）、手上武器的武器技
  傷害 −20%（普攻不受影響）、與其他專精互斥；
- 10 招測試形態技能的法術類別／`weapon_req`／沉默規則與形態類別一致。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, of
from tests.engine.test_combo_resources import BURN, SINGLE5, _problems
from tests.engine.test_forms import _next_own_turn
from tests.engine.test_forms_3j1b import (
    ALL,
    BEAR,
    CAT,
    DEMON,
    DRAGON,
    GIANT,
    ROC,
    SHADOW,
    TREANT,
    WEREWOLF,
    enter,
    scene,
)
from tests.engine.test_passive_triggers import always
from trpg.content.skills import ConditionSpec, SkillDef, condition_text, skill_slot_problems
from trpg.engine import Attack, BattleState, EndStance, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.events import (
    DamageDealt,
    FormEntered,
    FormLeft,
    FormUpkeepPaid,
    Healed,
    ShieldGained,
    StatusApplied,
)
from trpg.engine.rules.forms import form_collision_permille, is_spell_for_silence
from trpg.engine.runner import replay
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import state_to_json
from trpg.roguelite.offers import equip_problems
from trpg.shared.types import Team
from trpg.skillgen.keywords import derive_keywords

MASTERY = "skill_form_mastery"
ELEMENTAL = "skill_form_elemental"
PHYSICAL = {BEAR, CAT, WEREWOLF, DEMON, GIANT}
MENTAL = {ROC, ELEMENTAL, SHADOW, TREANT, DRAGON}


def real(skill_id: str) -> SkillDef:
    return library().skills[skill_id]


def _met(state: BattleState, category: str | None) -> bool:
    caster = state.units[U1]
    condition = ConditionSpec(type="in_form", form_category=category)  # type: ignore[arg-type]
    return condition_met(state, caster, condition, Subject(caster, caster.xy))


# ---------------------------------------------------------------------------
# 條件「在形態中」
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("form_skill", "any_form", "physical", "mental"),
    [
        (None, False, False, False),  # 不在形態中：全部不成立
        (BEAR, True, True, False),
        (WEREWOLF, True, True, False),
        (ROC, True, False, True),
        (DRAGON, True, False, True),
    ],
)
def test_in_form_condition_table(
    form_skill: str | None, any_form: bool, physical: bool, mental: bool
) -> None:
    state = scene() if form_skill is None else enter(scene(), form_skill)
    assert (_met(state, None), _met(state, "physical"), _met(state, "mental")) == (
        any_form,
        physical,
        mental,
    )


def test_in_form_ends_with_the_form() -> None:
    state = enter(scene(), BEAR)
    assert _met(state, None)
    assert not _met(resolve(state, EndStance(unit_id=U1)).state, None)


def _form_skill(condition: dict[str, Any], *, top: bool = False) -> SkillDef:
    effects = [BURN if top else {**BURN, "condition": condition}]
    skill = make_skill(SID, SINGLE5, effects, weapon_req="any")
    return skill.model_copy(update={"condition": ConditionSpec(**condition)}) if top else skill


def test_skill_level_in_form_makes_the_skill_usable_only_in_a_form() -> None:
    skill = _form_skill({"type": "in_form"}, top=True)
    state = scene(extra_skills=(skill,))

    def usable(s: BattleState) -> bool:
        return any(isinstance(a, UseSkill) and a.skill_id == SID for a in legal_actions(s))

    assert not usable(state)
    assert usable(enter(state, BEAR))


@pytest.mark.parametrize(
    ("category", "form_skill", "expect"),
    [
        (None, BEAR, True),
        (None, ROC, True),
        ("physical", BEAR, True),
        ("physical", ROC, False),
        ("mental", ROC, True),
        ("mental", BEAR, False),
    ],
)
def test_effect_level_in_form_applies_the_effect_only_when_it_holds(
    category: str | None, form_skill: str, expect: bool
) -> None:
    condition: dict[str, Any] = {"type": "in_form"}
    if category is not None:
        condition["form_category"] = category
    skill = _form_skill(condition)
    state = enter(scene(extra_skills=(skill,)), form_skill)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    burned = [e for e in of(result, StatusApplied) if e.status_id == "burning"]
    assert bool(burned) is expect


def test_in_form_without_a_form_does_not_apply_the_effect() -> None:
    skill = _form_skill({"type": "in_form"})
    result = resolve(scene(extra_skills=(skill,)), UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert not [e for e in of(result, StatusApplied) if e.status_id == "burning"]


def test_in_form_validator_accepts_valid_and_rejects_bad_parameters() -> None:
    for condition in ({"type": "in_form"}, {"type": "in_form", "form_category": "mental"}):
        assert _problems(make_skill(SID, SINGLE5, [{**BURN, "condition": condition}])) == []
    bad = make_skill(SID, SINGLE5, [{**BURN, "condition": {"type": "in_form", "status": "x"}}])
    assert any("不接受參數 status" in p for p in _problems(bad))
    with pytest.raises(ValueError, match="form_category"):
        make_skill(
            SID, SINGLE5, [{**BURN, "condition": {"type": "in_form", "form_category": "water"}}]
        )


def test_in_form_condition_text_has_no_english() -> None:
    assert condition_text(ConditionSpec(type="in_form")) == "你在形態中"
    assert condition_text(ConditionSpec(type="in_form", form_category="physical")) == (
        "你在物理形態中"
    )
    assert condition_text(ConditionSpec(type="in_form", form_category="mental")) == (
        "你在心智形態中"
    )


def test_in_form_is_a_form_keyword_exploiter_and_enter_form_a_maker() -> None:
    lib = library()
    uses = _form_skill({"type": "in_form"})
    assert "form" in derive_keywords(uses, lib.keywords).uses
    assert "form" in derive_keywords(real(BEAR), lib.keywords).makes
    mastery = derive_keywords(real(MASTERY), lib.keywords)
    assert "form" in mastery.uses and not mastery.makes


# ---------------------------------------------------------------------------
# 10 招測試形態技能（06 6.30 實作細節：法術類別、weapon_req 不限、沉默看形態類別）
# ---------------------------------------------------------------------------


def test_the_ten_form_skills_are_spells_with_any_weapon_and_silence_follows_the_form() -> None:
    lib = library()
    form_skills = {s.id: s for s in lib.skills.values() if s.id.startswith("skill_form_")}
    entering = {k: v for k, v in form_skills.items() if v.form_id is not None}
    assert len(entering) == 10 and MASTERY in form_skills
    for skill_id, skill in entering.items():
        assert skill.category == "spell" and skill.weapon_req == "any", skill_id
        assert skill.kind == "stance" and skill.ap_cost is None, skill_id
        assert skill.form_id is not None
        category = lib.ruleset.form_def(skill.form_id).category
        assert is_spell_for_silence(lib.ruleset, skill) is (category == "mental"), skill_id
    physical = {
        k
        for k, v in entering.items()
        if v.form_id is not None and lib.ruleset.form_def(v.form_id).category == "physical"
    }
    assert physical == PHYSICAL
    assert set(entering) == PHYSICAL | MENTAL


# ---------------------------------------------------------------------------
# 化形專精
# ---------------------------------------------------------------------------


def with_mastery(**kwargs: Any) -> BattleState:
    return scene(extra_skills=(MASTERY,), **kwargs)


def test_mastery_is_an_epic_modifier_in_the_mastery_group() -> None:
    skill = real(MASTERY)
    assert (skill.kind, skill.rarity, skill.exclusive_group) == ("modifier", "epic", "mastery")
    kinds = sorted(rule.change.kind for rule in skill.modifiers)
    assert kinds == ["damage_permille", "form_entry_permille", "form_upkeep_permille"]


def test_mastery_is_mutually_exclusive_with_the_other_masteries() -> None:
    slots = library().ruleset.core.skill_slots
    for other in ("skill_attack_mastery", "skill_summon_swarm", "skill_summon_elite"):
        problems = skill_slot_problems([real(MASTERY), real(other)], slots)
        assert any("只能擇一" in p for p in problems), other
    problems = equip_problems(library(), [real(MASTERY), real("skill_summon_elite")])
    assert problems and "化形專精" in problems[0]
    assert skill_slot_problems([real(MASTERY)], slots) == []


@pytest.mark.parametrize(
    ("skill_id", "resource", "plain", "halved"),
    [
        (BEAR, "stamina", 8, 4),
        (WEREWOLF, "stamina", 8, 4),
        (ROC, "mana", 3, 1),
        (DRAGON, "mana", 3, 1),
    ],
)
def test_mastery_halves_the_upkeep_rounding_down(
    skill_id: str, resource: str, plain: int, halved: int
) -> None:
    for build, expected in ((scene(), plain), (with_mastery(), halved)):
        state = enter(build, skill_id)
        before = getattr(state.units[U1], resource)
        state, events = _next_own_turn(state)
        paid = [e for e in events if isinstance(e, FormUpkeepPaid)]
        assert [(e.resource, e.amount) for e in paid] == [(resource, expected)]
        assert getattr(state.units[U1], resource) == before - expected


def test_mastery_upkeep_that_rounds_to_zero_is_not_paid() -> None:
    """3 法力減半 → 1；再減半的情況不存在，但付得起的判斷用減半後的值（法力 1 就夠）。"""
    state = enter(with_mastery(), ROC)
    state.units[U1].mana = 1
    state, events = _next_own_turn(state)
    assert state.units[U1].form is not None and not [e for e in events if isinstance(e, FormLeft)]


def _shield(state: BattleState, skill_id: str) -> int:
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill_id))
    return sum(e.amount for e in of(result, ShieldGained))


@pytest.mark.parametrize(("skill_id", "permille"), [(BEAR, 100), (DRAGON, 50)])
def test_mastery_scales_the_entry_shield_by_one_and_a_half(skill_id: str, permille: int) -> None:
    plain, boosted = _shield(scene(), skill_id), _shield(with_mastery(), skill_id)
    max_hp = scene().units[U1].max_hp
    # 龍進入時最大 HP +10%（先加最大 HP 再算護盾）
    base = enter(scene(), skill_id).units[U1].max_hp * permille // 1000
    assert plain == base and boosted == base * 3 // 2
    assert max_hp > 0


def test_mastery_scales_numeric_entry_bonuses() -> None:
    plain, boosted = scene(), with_mastery()
    # 貓：下一次攻擊暴擊範圍 +2 → +3；巨鵰：命中 +2 → +3；惡魔：本回合移動 +2 → +3
    assert enter(plain, CAT).units[U1].next_attack_crit == 2
    assert enter(boosted, CAT).units[U1].next_attack_crit == 3
    assert enter(plain, ROC).units[U1].next_attack_hit == 2
    assert enter(boosted, ROC).units[U1].next_attack_hit == 3
    base_move = plain.units[U1].move_points
    assert enter(plain, DEMON).units[U1].move_points == base_move + 2
    assert enter(boosted, DEMON).units[U1].move_points == base_move + 3


def test_mastery_scales_the_giant_collision_bonus_for_this_turn_only() -> None:
    for build, expected in ((scene(), 1500), (with_mastery(), 1750)):  # +50% → +75%
        entered = give_turn(enter(build, GIANT), U1)
        assert form_collision_permille(entered, entered.units[U1]) == expected
        other = give_turn(entered, U2)
        assert form_collision_permille(other, other.units[U1]) == 1000


def with_mastery_elemental() -> BattleState:
    return scene(foe_at=(4, 3), extra_skills=(MASTERY, ELEMENTAL))


def test_mastery_scales_the_treant_adjacent_heal_and_the_elemental_burst(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=4)
    heals = []
    for build in (scene(ally_at=(2, 3)), with_mastery(ally_at=(2, 3))):
        build.units[U2].hp = 10  # 友方（第二個友方）先打殘才吃得到治療
        result = resolve(build, UseSkill(unit_id=U1, skill_id=TREANT))
        heals.append(sum(e.amount for e in of(result, Healed)))
    # 倍率在最後一步才乘（無條件捨去），所以比「先捨去再 ×1.5」最多多 1
    assert heals[0] > 0 and heals[0] * 3 // 2 <= heals[1] <= heals[0] * 3 // 2 + 1

    bursts = []
    for build in (scene(foe_at=(4, 3), extra_skills=(ELEMENTAL,)), with_mastery_elemental()):
        result = resolve(build, UseSkill(unit_id=U1, skill_id=ELEMENTAL))
        bursts.append(sum(e.amount for e in of(result, DamageDealt)))
    assert bursts[0] > 0 and bursts[0] * 3 // 2 <= bursts[1] <= bursts[0] * 3 // 2 + 1


def test_mastery_does_not_change_anything_without_a_form() -> None:
    """專精只改形態：不進形態時，普攻與狀態和沒有專精完全一樣。"""
    a, b = scene(), with_mastery()
    assert a.units[U1].stamina == b.units[U1].stamina
    assert a.units[U1].move_points == b.units[U1].move_points


def _weapon_skill() -> SkillDef:
    return make_skill(
        SID,
        {"type": "single", "range": 1},
        [{"type": "damage", "multiplier_permille": 1000}],
        category="weapon",
        weapon_req="melee",
    )


def _hit(state: BattleState, skill: bool) -> int:
    action: Any = (
        UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
        if skill
        else Attack(unit_id=U1, target_id=U2)
    )
    return sum(e.amount for e in of(resolve(state, action), DamageDealt))


def test_mastery_cuts_weapon_skill_damage_by_twenty_percent_but_not_basic_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=5)
    extra = (_weapon_skill(),)
    plain, boosted = scene(extra_skills=extra), scene(extra_skills=(*extra, MASTERY))
    base_skill, cut_skill = _hit(plain, True), _hit(boosted, True)
    assert base_skill > 0 and cut_skill < base_skill
    assert abs(cut_skill - base_skill * 8 // 10) <= 1  # −20%（各步無條件捨去，容許 1 點）
    assert _hit(plain, False) == _hit(boosted, False)  # 普攻不受影響
    # 形態中的普攻（天生武器）也不受影響
    assert _hit(enter(plain, BEAR), False) == _hit(enter(boosted, BEAR), False)


def test_mastery_does_not_touch_spells() -> None:
    spell = make_skill(
        SID, SINGLE5, [{"type": "damage", "dice": "2d6", "element": "fire"}], weapon_req="any"
    )
    plain, boosted = scene(extra_skills=(spell,)), scene(extra_skills=(spell, MASTERY))
    assert _hit_spell(plain) == _hit_spell(boosted)


def _hit_spell(state: BattleState) -> int:
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    return sum(e.amount for e in of(result, DamageDealt))


def test_a_battle_with_the_mastery_and_form_rotation_replays_identically() -> None:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([MASTERY, BEAR, ROC, DRAGON], base="hero_fighter", stamina=40)
    setup = make_setup(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=90))],
    )
    state = start_battle(setup, 5)
    steps: list[object] = []
    ai = UtilityAI(library().ai_profiles)
    for _ in range(60):
        if state.ended:
            break
        unit = state.active
        assert unit is not None
        action: object = (
            UseSkill(unit_id=U1, skill_id=BEAR) if not steps and unit.id == U1 else ai(state)
        )
        steps.append(action)
        state = resolve(state, action).state  # type: ignore[arg-type]
    run = replay(setup, 5, steps)  # type: ignore[arg-type]
    assert state_to_json(run.state) == state_to_json(state)
    assert any(isinstance(e, FormEntered) for e in run.events)


def test_all_form_skills_still_enter_with_the_mastery_equipped() -> None:
    state = with_mastery()
    for skill_id in ALL:
        assert enter(state, skill_id).units[U1].form is not None
