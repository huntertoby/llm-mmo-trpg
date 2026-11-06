"""Phase 3J-1b：天生武器特性、其餘 5 種形態資料、「下一次攻擊」作用在所有命中擲骰、沉默、AI 輪替
的行為一致測試（``docs/phases/Phase3J計畫.md`` 第 3、4.2、4.4 節）。
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.form_text import form_sentence
from trpg.content.rules import SkillSlots
from trpg.engine import (
    Attack,
    BattleState,
    EndStance,
    Move,
    UseSkill,
    legal_actions,
    resolve,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.events import (
    AttackRolled,
    Collided,
    DamageDealt,
    FormEntered,
    Healed,
    ReactionTriggered,
    ShieldGained,
    StatusApplied,
)
from trpg.engine.rules.combat import positional_bonus, weapon_profile
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.forms import form_collision_permille
from trpg.engine.rules.statuses import damage_taken_permille, move_points_for_turn
from trpg.engine.runner import replay
from trpg.engine.state import StatusInstance, state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Pos, Team

DEMON, GIANT, SHADOW, TREANT, DRAGON = (
    "skill_form_demon",
    "skill_form_giant",
    "skill_form_shadow",
    "skill_form_treant",
    "skill_form_dragon",
)
BEAR, CAT, ROC, WEREWOLF = (
    "skill_form_bear",
    "skill_form_cat",
    "skill_form_roc",
    "skill_form_werewolf",
)
ALL = (BEAR, CAT, ROC, WEREWOLF, DEMON, GIANT, SHADOW, TREANT, DRAGON)
SLOTS = SkillSlots(active=12, passive=2, reaction=1, stance=2)


def scene(
    *,
    caster_at: tuple[int, int] = (3, 3),
    foe_at: tuple[int, int] = (4, 3),
    extra_foe: tuple[int, int] | None = None,
    ally_at: tuple[int, int] | None = None,
    hp: int = 999,
    foe_hp: int = 999,
    extra_skills: tuple[object, ...] = (),
) -> BattleState:
    """U1（戰士，帶 9 個形態技能）在 (3, 3) 手上有回合；U2 是敵人（友方加入時 U2 是友方）。"""
    foes = [foe_at] + ([extra_foe] if extra_foe else [])
    allies = [caster_at] + ([ally_at] if ally_at else [])
    m = make_map(FLAT7, ally=allies, enemy=foes)
    owner = caster_template([*ALL, *extra_skills], base="hero_fighter", max_hp=hp, stamina=40)  # type: ignore[list-item]
    spawns = [spawn(Team.ALLY, caster_at, owner)]
    if ally_at:
        spawns.append(spawn(Team.ALLY, ally_at, no_reactions("hero_fighter", max_hp=100)))
    spawns.append(spawn(Team.ENEMY, foe_at, no_reactions(max_hp=foe_hp)))
    if extra_foe:
        spawns.append(spawn(Team.ENEMY, extra_foe, no_reactions(max_hp=foe_hp)))
    state = make_state(
        m,
        spawns,
        skill_slots=SLOTS,  # type: ignore[arg-type]
        skills=[s for s in extra_skills if not isinstance(s, str)],  # type: ignore[misc]
    )
    state = give_turn(state, U1)
    state.units[U1].stamina = 40
    state.units[U1].mana = 40
    state.units[U1].stamina_regen = 0
    return state


def enter(state: BattleState, skill_id: str, **extra: object) -> BattleState:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **extra)).state  # type: ignore[arg-type]


def test_all_ten_forms_are_defined() -> None:
    forms = library().ruleset.forms.by_id()
    assert set(forms) == {
        "bear",
        "cat",
        "roc",
        "elemental",
        "werewolf",
        "demon",
        "giant",
        "shadow",
        "treant",
        "dragon",
    }
    kinds = {fid: f.category for fid, f in forms.items()}
    assert {k for k, v in kinds.items() if v == "physical"} == {
        "bear",
        "cat",
        "werewolf",
        "demon",
        "giant",
    }


# ---------------------------------------------------------------------------
# 其餘 5 種形態的資料（形態效果＋進入獎勵）
# ---------------------------------------------------------------------------


def test_demon_data_and_entry_move_applies_this_turn() -> None:
    state = scene()
    base = state.units[U1]
    result = resolve(state, UseSkill(unit_id=U1, skill_id=DEMON))
    unit = result.state.units[U1]
    weapon = unit.weapon
    assert (weapon.dice.count, weapon.dice.sides, weapon.element) == (1, 6, Element.SHADOW)
    assert weapon.strikes == 2 and weapon.is_melee
    assert unit.move_points == base.move_points + 2  # 進入獎勵：本回合移動 +2，當回合生效
    rules = result.state.ruleset
    # 形態效果「移動 +1」照現狀從下回合起算
    assert move_points_for_turn(rules, unit) == move_points_for_turn(rules, base) + 1


def test_giant_data() -> None:
    entered = enter(scene(), GIANT)
    weapon = entered.units[U1].weapon
    assert (weapon.dice.sides, weapon.knockback, weapon.element) == (10, 1, Element.PHYSICAL)
    rules = entered.ruleset
    assert move_points_for_turn(rules, entered.units[U1]) == (
        move_points_for_turn(rules, scene().units[U1]) - 1
    )


def test_shadow_data_taken_modifiers_and_conceal(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene()
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SHADOW))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    plain = state.units[U1]
    assert damage_taken_permille(rules, unit, Element.PHYSICAL) == (
        damage_taken_permille(rules, plain, Element.PHYSICAL) * 800 // 1000
    )
    assert damage_taken_permille(rules, unit, Element.HOLY) == (
        damage_taken_permille(rules, plain, Element.HOLY) * 1500 // 1000
    )
    assert damage_taken_permille(rules, unit, Element.FIRE) == damage_taken_permille(
        rules, plain, Element.FIRE
    )
    assert (unit.weapon.weapon_class, unit.weapon.range) == ("ranged", 3)
    assert unit.has_status("concealed")
    applied = [e for e in of(result, StatusApplied) if e.status_id == "concealed"]
    assert applied and applied[0].duration == 1


def test_treant_data_heal_bonus_and_heals_adjacent_allies(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=4)
    state = scene(ally_at=(2, 3))
    state.units[U2].hp = 999  # U2 是友方（第二個友方）；先把它打殘
    ally = state.units[U2]
    ally.hp = 10
    base = state.units[U1]
    result = resolve(state, UseSkill(unit_id=U1, skill_id=TREANT))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    assert (unit.weapon.range, unit.weapon.reach, unit.weapon.is_melee) == (2, 2, True)
    assert move_points_for_turn(rules, unit) == move_points_for_turn(rules, base) - 2
    assert damage_taken_permille(rules, unit, Element.FIRE) == (
        damage_taken_permille(rules, base, Element.FIRE) * 1500 // 1000
    )
    healed = [e for e in of(result, Healed) if e.target_id == ally.id]
    assert len(healed) == 1
    # 1d8（骰面 4）＋感知 × 0.5，再乘上形態的治療加成 +20%
    assert healed[0].amount >= 4 * 1200 // 1000


def test_dragon_data_hp_move_and_shield() -> None:
    state = scene()
    base = state.units[U1]
    result = resolve(state, UseSkill(unit_id=U1, skill_id=DRAGON))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    assert unit.max_hp == base.max_hp + base.max_hp * 100 // 1000
    assert move_points_for_turn(rules, unit) == move_points_for_turn(rules, base) - 1
    (shield,) = of(result, ShieldGained)
    assert shield.amount == unit.max_hp * 50 // 1000
    assert unit.form is not None and unit.form.element is Element.FIRE
    assert unit.weapon.element is Element.FIRE


# ---------------------------------------------------------------------------
# 天生武器特性
# ---------------------------------------------------------------------------


def test_demon_strikes_twice_and_each_strike_rolls_to_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=1)
    entered = enter(scene(), DEMON)
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    rolls = of(result, AttackRolled)
    assert len(rolls) == 2 and all(r.hit for r in rolls)
    assert len([e for e in of(result, DamageDealt) if e.target_id == U2]) == 2


def test_demon_strikes_roll_independently(monkeypatch: pytest.MonkeyPatch) -> None:
    entered = enter(scene(), DEMON)
    seq = iter([19, 2])  # 第一下命中、第二下失手

    def fake(self: object, sides: int) -> int:
        return next(seq) if sides == 20 else 1

    monkeypatch.setattr(Rng, "roll", fake)
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    assert [r.hit for r in of(result, AttackRolled)] == [True, False]


def test_giant_punch_pushes_one_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=1)
    entered = enter(scene(), GIANT)
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (5, 3)  # 從 (4, 3) 沿攻擊方向推 1 格


def _collision_damage(state: BattleState) -> int:
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert of(result, Collided)
    return sum(e.amount for e in of(result, DamageDealt) if e.cause == "collision")


def test_giant_entry_boosts_collision_damage_this_turn_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=4)
    state = scene(caster_at=(5, 3), foe_at=(6, 3))  # 推 1 格會撞地圖邊
    entered = enter(state, GIANT)
    with_bonus = _collision_damage(give_turn(entered, U1))
    unit = entered.units[U1]
    assert unit.form is not None
    stale = entered.clone()
    stale.units[U1].form = replace(unit.form, entered_round=unit.form.entered_round - 1)
    without = _collision_damage(give_turn(stale, U1))
    assert without > 0
    assert with_bonus == without * 3 // 2  # 撞擊傷害 +50%


def test_collision_bonus_ignores_other_forms_and_other_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=4)
    state = scene(caster_at=(5, 3), foe_at=(6, 3))
    entered = give_turn(enter(state, GIANT), U2)  # 輪到別人行動：加成不算在別人的回合
    assert form_collision_permille(entered, entered.units[U1]) == 1000
    assert form_collision_permille(give_turn(entered, U1), entered.units[U1]) == 1500
    bear = enter(state, BEAR)
    assert form_collision_permille(bear, bear.units[U1]) == 1000


def test_werewolf_hit_causes_one_round_of_bleed(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=1)
    entered = enter(scene(), WEREWOLF)
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    bleed = [e for e in of(result, StatusApplied) if e.status_id == "bleed"]
    assert len(bleed) == 1 and bleed[0].target_id == U2 and bleed[0].duration == 1
    plain = resolve(enter(scene(), BEAR), Attack(unit_id=U1, target_id=U2))
    assert not [e for e in of(plain, StatusApplied) if e.status_id == "bleed"]


def test_werewolf_miss_does_not_bleed(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=1, die=1)
    entered = enter(scene(), WEREWOLF)
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    assert not of(result, StatusApplied)


def test_treant_attacks_at_range_two_and_provokes_at_reach_two() -> None:
    state = scene(foe_at=(5, 3))
    entered = enter(state, TREANT)
    assert any(
        isinstance(a, Attack) and a.target_id == U2 for a in legal_actions(give_turn(entered, U1))
    )
    bear = enter(state, BEAR)
    assert not any(
        isinstance(a, Attack) and a.target_id == U2 for a in legal_actions(give_turn(bear, U1))
    )


def _oa_scene(skill_id: str) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(5, 3)])
    guard = template("hero_fighter", skills=[BEAR, TREANT], max_hp=999, stamina=40)
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), guard),
            spawn(Team.ENEMY, (5, 3), template("bandit", max_hp=300, reactions=[])),
        ],
        skill_slots=SLOTS,  # type: ignore[arg-type]
    )
    state = give_turn(state, U1)
    state.units[U1].mana = 40
    entered = resolve(state, UseSkill(unit_id=U1, skill_id=skill_id)).state
    return give_turn(entered, U2)


def test_treant_gets_opportunity_attack_when_a_foe_leaves_reach_two() -> None:
    state = _oa_scene(TREANT)
    result = resolve(state, Move(unit_id=U2, path=(Pos(x=5, y=3), Pos(x=6, y=3))))
    triggered = [e for e in of(result, ReactionTriggered) if e.unit_id == U1]
    assert triggered and triggered[0].reaction == "opportunity_attack"


def test_bear_gets_no_opportunity_attack_at_distance_two() -> None:
    state = _oa_scene(BEAR)
    result = resolve(state, Move(unit_id=U2, path=(Pos(x=5, y=3), Pos(x=6, y=3))))
    assert not [e for e in of(result, ReactionTriggered) if e.unit_id == U1]


def test_cat_backstab_crit_range_is_one_wider_than_other_forms() -> None:
    state = scene(foe_at=(4, 3))
    target = state.units[U2]
    target.facing = "east"  # 朝東：攻擊者在西邊 → 背刺
    assert is_behind(state.units[U1].xy, target)

    def crit_range(skill_id: str) -> int:
        s = enter(state, skill_id)
        s.units[U2].facing = "east"
        profile = weapon_profile(s, s.units[U1])
        return positional_bonus(s, s.units[U1], s.units[U2], profile).crit_range

    bear = crit_range(BEAR)
    assert bear < 20  # 核心規則的背刺加成
    assert crit_range(CAT) == bear - 1  # 貓：再 +1
    assert crit_range(WEREWOLF) == bear


def test_cat_backstab_trait_does_not_apply_without_a_backstab() -> None:
    state = scene(foe_at=(4, 3))
    state.units[U2].facing = "west"  # 朝向攻擊者：不是背刺
    entered = enter(state, CAT)
    profile = weapon_profile(entered, entered.units[U1])
    assert positional_bonus(entered, entered.units[U1], entered.units[U2], profile).crit_range == 20


# ---------------------------------------------------------------------------
# 「下一次攻擊」的進入獎勵作用在所有命中擲骰
# ---------------------------------------------------------------------------


def _totals(result: object) -> list[int]:
    return [r.total for r in of(result, AttackRolled)]  # type: ignore[arg-type]


def test_next_attack_bonus_applies_to_both_demon_strikes_and_is_then_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=10, die=1)
    entered = enter(scene(), DEMON)
    plain = _totals(resolve(entered, Attack(unit_id=U1, target_id=U2)))
    entered.units[U1].next_attack_hit = 2
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    assert len(plain) == 2
    assert _totals(result) == [t + 2 for t in plain]  # 兩下都吃到
    assert result.state.units[U1].next_attack_hit == 0
    again = resolve(give_turn(result.state, U1), Attack(unit_id=U1, target_id=U2))
    assert _totals(again) == plain  # 用掉了


CONE = make_skill(
    "skill_t_cone_form",
    {"type": "cone", "size": 3},
    [{"type": "damage", "dice": "1d6", "element": "fire", "affects": "enemies"}],
    weapon_req="any",
)


def test_next_attack_bonus_applies_to_every_target_of_an_area_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=10, die=1)
    state = scene(foe_at=(4, 3), extra_foe=(5, 3), extra_skills=(CONE,))
    entered = give_turn(enter(state, ROC), U1)  # 巨鵰：下一次攻擊命中 +2
    assert entered.units[U1].next_attack_hit == 2
    cast = UseSkill(unit_id=U1, skill_id=CONE.id, direction="east")
    result = resolve(entered, cast)
    spent = entered.clone()
    spent.units[U1].next_attack_hit = 0
    plain = resolve(spent, cast)
    rolls = _totals(result)
    assert len(rolls) == 2 and rolls == [t + 2 for t in _totals(plain)]
    assert result.state.units[U1].next_attack_hit == 0


def test_next_attack_bonus_is_lost_when_leaving_the_form() -> None:
    entered = enter(scene(), CAT)
    assert entered.units[U1].next_attack_crit == 2
    switched = enter(give_turn(entered, U1), BEAR)
    assert switched.units[U1].next_attack_crit == 0


# ---------------------------------------------------------------------------
# 沉默：心智形態的進入技能算法術，物理形態不算
# ---------------------------------------------------------------------------


def _silenced(state: BattleState) -> BattleState:
    s = state.clone()
    s.units[U1].statuses = list(s.units[U1].statuses)
    s.units[U1].statuses.append(StatusInstance(status_id="silenced", remaining=2))
    return s


@pytest.mark.parametrize("skill_id", [ROC, SHADOW, TREANT, DRAGON])
def test_silence_blocks_mental_form_skills(skill_id: str) -> None:
    state = _silenced(scene())
    with pytest.raises(IllegalActionError, match="沉默"):
        resolve(state, UseSkill(unit_id=U1, skill_id=skill_id))
    ids = {a.skill_id for a in legal_actions(state) if isinstance(a, UseSkill)}
    assert skill_id not in ids


@pytest.mark.parametrize("skill_id", [BEAR, CAT, WEREWOLF, DEMON, GIANT])
def test_silence_does_not_block_physical_form_skills(skill_id: str) -> None:
    state = _silenced(scene())
    ids = {a.skill_id for a in legal_actions(state) if isinstance(a, UseSkill)}
    assert skill_id in ids
    assert enter(state, skill_id).units[U1].form is not None


# ---------------------------------------------------------------------------
# 卡片句與 AI 輪替
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("form_id", "phrase"),
    [
        ("demon", "普攻打 2 下（各自擲命中）"),
        ("giant", "命中推擊 1 格"),
        ("giant", "本回合你造成的撞擊傷害 +50%"),
        ("werewolf", "命中流血 1 回合"),
        ("cat", "背刺暴擊範圍再 +1"),
        ("treant", "觸及 2"),
        ("shadow", "受物理傷害 −20%"),
        ("shadow", "受神聖傷害 +50%"),
    ],
)
def test_card_sentence_describes_the_traits(form_id: str, phrase: str) -> None:
    rules = library().ruleset
    text = form_sentence(rules.forms, rules.form_def(form_id), rules.core)
    assert phrase in text


def test_the_ai_may_rotate_to_another_form_but_never_cancels_or_repeats() -> None:
    state = scene(foe_at=(6, 6))
    state.units[U1].move_points = 0
    ai = UtilityAI(library().ai_profiles)
    entered = give_turn(enter(state, BEAR), U1)
    entered.units[U1].move_points = 0
    ranked = ai.rank(entered)
    skills = {s.action.skill_id for s in ranked if isinstance(s.action, UseSkill)}
    assert not any(isinstance(s.action, EndStance) for s in ranked)
    assert BEAR not in skills  # 已在這個形態中、冷卻也不是重點：不重複進入
    assert skills & set(ALL) - {BEAR}  # 其他形態是輪替候選


def test_the_ai_does_not_use_a_form_skill_while_in_a_plain_stance_or_on_cooldown() -> None:
    state = scene(foe_at=(6, 6))
    left = enter(give_turn(enter(state, BEAR), U1), CAT)  # 熊離開、冷卻 2
    ranked = UtilityAI(library().ai_profiles).rank(give_turn(left, U1))
    skills = {s.action.skill_id for s in ranked if isinstance(s.action, UseSkill)}
    assert BEAR not in skills


def test_a_rotation_battle_with_the_new_forms_replays_identically() -> None:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([DEMON, GIANT, SHADOW, TREANT, DRAGON], base="hero_fighter", stamina=40)
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
        if not steps and unit.id == U1:
            action: object = UseSkill(unit_id=U1, skill_id=DEMON)
        else:
            action = ai(state)
        steps.append(action)
        state = resolve(state, action).state  # type: ignore[arg-type]
    run = replay(setup, 5, steps)  # type: ignore[arg-type]
    assert state_to_json(run.state) == state_to_json(state)
    assert any(isinstance(e, FormEntered) for e in run.events)
