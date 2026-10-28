"""Phase 3J-1a：形態核心規則的行為一致測試（``docs/phases/Phase3J計畫.md`` 第 3 節，限本段範圍）。

5 種形態（熊、貓、巨鵰、元素化身、狼人）實際跑引擎：進入花 1 AP、和姿態互斥、自己回合取消免費、
倒下與戰鬥結束解除、維持費每回合扣與不夠自動解除、離開後該形態冷卻 2 回合（別的形態不受影響）、
進入獎勵的數值、形態效果、天生武器的 ``damage_dealt`` 等於卡片「目前 +N」、重播一致。
"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.rules import SkillSlots
from trpg.content.skills import skill_slot_problems
from trpg.engine import (
    Attack,
    BattleState,
    EndStance,
    EndTurn,
    UseSkill,
    legal_actions,
    resolve,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    FormEntered,
    FormLeft,
    FormUpkeepPaid,
    Healed,
    ShieldGained,
    StatusRemoved,
)
from trpg.engine.rules.combat import defense_value_permille
from trpg.engine.rules.forms import held_weapon
from trpg.engine.rules.movement import unit_step_cost
from trpg.engine.rules.statuses import (
    damage_taken_permille,
    effective_attribute,
    move_points_for_turn,
)
from trpg.engine.runner import replay
from trpg.engine.state import state_from_json, state_to_json
from trpg.narrative.skills import CardOwner, skill_card
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Team

BEAR, CAT, ROC, ELEMENTAL, WEREWOLF = (
    "skill_form_bear",
    "skill_form_cat",
    "skill_form_roc",
    "skill_form_elemental",
    "skill_form_werewolf",
)
FORM_SKILLS = (BEAR, CAT, ROC, ELEMENTAL, WEREWOLF)
FURY = "skill_fury_stance"
SLOTS = SkillSlots(active=8, passive=2, reaction=1, stance=2)


def scene(*, hp: int = 999, foe_hp: int = 999, foe_at: tuple[int, int] = (4, 3)) -> BattleState:
    """U1（戰士，帶 5 個形態技能與狂怒姿態，耐力與法力充足）在 (3, 3) 手上有回合；U2（敵人）。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe_at])
    owner = caster_template([*FORM_SKILLS, FURY], base="hero_fighter", max_hp=hp, stamina=40)
    state = make_state(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, foe_at, no_reactions(max_hp=foe_hp))],
        skill_slots=SLOTS,  # type: ignore[arg-type]
    )
    state = give_turn(state, U1)
    state.units[U1].stamina = 40
    state.units[U1].mana = 40
    state.units[U1].stamina_regen = 0
    return state


def enter(state: BattleState, skill_id: str, **extra: object) -> BattleState:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **extra)).state  # type: ignore[arg-type]


def form_of(state: BattleState) -> str | None:
    form = state.units[U1].form
    return None if form is None else form.form_id


# ---------------------------------------------------------------------------
# 進入、互斥、取消、倒下、戰鬥結束
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", FORM_SKILLS)
def test_entering_a_form_costs_one_ap_and_swaps_the_basic_attack(skill_id: str) -> None:
    state = scene()
    lib = library()
    form_id = lib.ruleset.skill_def(skill_id).form_id
    assert form_id is not None
    hand = state.units[U1].weapon
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill_id))
    unit = result.state.units[U1]
    assert unit.ap == state.units[U1].ap - state.ruleset.core.stance_ap_cost == unit.ap
    assert form_of(result.state) == form_id
    assert unit.weapon.id == f"form_{form_id}"
    natural = lib.ruleset.form_def(form_id).natural_weapon
    assert unit.weapon.dice == natural.dice and unit.weapon.range == natural.range
    assert held_weapon(unit) == hand  # 武器技仍看手上武器
    (entered,) = of(result, FormEntered)
    assert entered.form_id == form_id and entered.skill_id == skill_id


def test_entering_a_form_replaces_a_stance_and_a_stance_ends_the_form() -> None:
    state = enter(scene(), FURY)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BEAR))
    assert ("stance_fury", "replaced") in [
        (e.status_id, e.reason) for e in of(result, StatusRemoved)
    ]
    assert not result.state.units[U1].has_status("stance_fury")
    back = resolve(give_turn(result.state, U1), UseSkill(unit_id=U1, skill_id=FURY))
    (left,) = of(back, FormLeft)
    assert (left.form_id, left.reason) == ("bear", "stance")
    assert form_of(back.state) is None and back.state.units[U1].has_status("stance_fury")


def test_switching_forms_leaves_the_old_one_and_cools_only_it() -> None:
    state = enter(scene(), BEAR)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=CAT))
    (left,) = of(result, FormLeft)
    assert (left.form_id, left.reason, left.cooldown) == ("bear", "switched", 2)
    unit = result.state.units[U1]
    assert form_of(result.state) == "cat"
    assert unit.form_cooldowns == {"bear": 2}
    ids = [
        a.skill_id for a in legal_actions(give_turn(result.state, U1)) if isinstance(a, UseSkill)
    ]
    assert BEAR not in ids and CAT not in ids  # 熊冷卻中、已在貓形態中
    assert ROC in ids and WEREWOLF in ids  # 別的形態不受影響


def test_end_stance_cancels_a_form_for_free_and_restores_the_hand_weapon() -> None:
    state = scene()
    hand = state.units[U1].weapon
    entered = enter(state, BEAR)
    assert [a for a in legal_actions(entered) if isinstance(a, EndStance)]
    result = resolve(entered, EndStance(unit_id=U1))
    unit = result.state.units[U1]
    assert unit.ap == entered.units[U1].ap  # 免費
    assert unit.form is None and unit.weapon == hand
    assert unit.max_hp == state.units[U1].max_hp
    (left,) = of(result, FormLeft)
    assert left.reason == "cancelled" and unit.form_cooldowns == {"bear": 2}


def test_form_cooldown_ticks_on_own_turn_starts() -> None:
    state = resolve(enter(scene(), BEAR), EndStance(unit_id=U1)).state
    assert state.units[U1].form_cooldowns == {"bear": 2}
    with pytest.raises(IllegalActionError, match="形態冷卻中"):
        resolve(state, UseSkill(unit_id=U1, skill_id=BEAR))
    seen: list[dict[str, int]] = []
    for _ in range(2):
        state = resolve(state, EndTurn(unit_id=U1)).state
        while state.active_unit != U1:
            state = resolve(state, EndTurn(unit_id=state.active_unit)).state  # type: ignore[arg-type]
        seen.append(dict(state.units[U1].form_cooldowns))
    assert seen == [{"bear": 1}, {}]
    assert form_of(enter(give_turn(state, U1), BEAR)) == "bear"


def test_a_form_ends_when_the_unit_goes_down(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=8)
    state = enter(scene(hp=5), CAT)
    result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U1))
    assert result.state.units[U1].downed and form_of(result.state) is None
    assert [(e.form_id, e.reason) for e in of(result, FormLeft)] == [("cat", "downed")]


def test_a_form_ends_when_the_battle_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=8)
    state = enter(scene(foe_hp=1), BEAR)
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert result.state.ended
    assert [(e.form_id, e.reason) for e in of(result, FormLeft)] == [("bear", "battle_end")]
    unit = result.state.units[U1]
    assert unit.form is None and unit.max_hp == state.units[U1].max_hp - 149  # 999 × 15%


# ---------------------------------------------------------------------------
# 維持費與自動解除
# ---------------------------------------------------------------------------


def _next_own_turn(state: BattleState) -> tuple[BattleState, list[object]]:
    events: list[object] = []
    result = resolve(state, EndTurn(unit_id=U1))
    events += result.events
    state = result.state
    while state.active_unit != U1:
        result = resolve(state, EndTurn(unit_id=state.active_unit))  # type: ignore[arg-type]
        events += result.events
        state = result.state
    return state, events


@pytest.mark.parametrize(
    ("skill_id", "resource", "amount"),
    [(BEAR, "stamina", 5), (WEREWOLF, "stamina", 5), (ROC, "mana", 3), (ELEMENTAL, "mana", 3)],
)
def test_upkeep_is_paid_at_each_turn_start(skill_id: str, resource: str, amount: int) -> None:
    state = enter(scene(), skill_id)
    before = getattr(state.units[U1], resource)
    state, events = _next_own_turn(state)
    paid = [e for e in events if isinstance(e, FormUpkeepPaid)]
    assert [(e.resource, e.amount) for e in paid] == [(resource, amount)]
    assert getattr(state.units[U1], resource) == before - amount
    assert form_of(state) is not None


def test_upkeep_that_cannot_be_paid_ends_the_form_and_its_move_bonus() -> None:
    state = enter(scene(), CAT)
    state.units[U1].stamina = 4
    state, events = _next_own_turn(state)
    left = [e for e in events if isinstance(e, FormLeft)]
    assert [(e.form_id, e.reason) for e in left] == [("cat", "upkeep")]
    unit = state.units[U1]
    assert unit.form is None and unit.stamina == 4
    assert unit.move_points == unit.speed  # 貓的移動 +1 不再算
    assert unit.form_cooldowns == {"cat": 2}


# ---------------------------------------------------------------------------
# 形態效果（表格）
# ---------------------------------------------------------------------------


def test_bear_effects_and_entry_shield() -> None:
    state = scene()
    base = state.units[U1]
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BEAR))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    assert unit.max_hp == base.max_hp + base.max_hp * 150 // 1000
    assert unit.hp == base.hp  # 目前 HP 不變
    plain = defense_value_permille(base, rules)
    assert defense_value_permille(unit, rules) == plain * 1100 // 1000
    assert move_points_for_turn(rules, unit) == move_points_for_turn(rules, base) - 1
    (shield,) = of(result, ShieldGained)
    assert shield.amount == unit.max_hp * 100 // 1000


def test_cat_effects_and_next_attack_crit_range(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene()
    base = state.units[U1]
    entered = enter(state, CAT)
    unit = entered.units[U1]
    assert (
        move_points_for_turn(entered.ruleset, unit) == move_points_for_turn(state.ruleset, base) + 1
    )
    assert unit.next_attack_crit == 2
    always(monkeypatch, d20=18, die=1)  # 18 平常不暴擊；暴擊範圍 +2 後 18 暴擊
    result = resolve(entered, Attack(unit_id=U1, target_id=U2))
    (rolled,) = of(result, AttackRolled)
    assert rolled.crit
    assert result.state.units[U1].next_attack_crit == 0  # 用掉
    again = resolve(give_turn(result.state, U1), Attack(unit_id=U1, target_id=U2))
    assert not of(again, AttackRolled)[0].crit


def test_roc_effects_and_next_attack_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=10, die=1)
    state = scene()
    base = state.units[U1]
    plain = of(resolve(state, Attack(unit_id=U1, target_id=U2)), AttackRolled)[0]
    entered = enter(state, ROC)
    unit = entered.units[U1]
    assert unit.max_hp == base.max_hp - base.max_hp * 100 // 1000
    assert unit.weapon.range == 4 and unit.weapon.weapon_class == "ranged"
    rolled = of(resolve(entered, Attack(unit_id=U1, target_id=U2)), AttackRolled)[0]
    # 鳥喙看感知（10）、劍看力量（16）：命中修正不同，只比「下一次攻擊 +2」那一段
    assert rolled.total - rolled.hit_modifier == plain.total - plain.hit_modifier + 2


def test_roc_walks_height_one_as_flat() -> None:
    m = make_map("\n".join(["0100000"] + ["0000000"] * 6), ally=[(0, 0)], enemy=[(6, 6)])
    owner = caster_template([ROC], base="hero_fighter")
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), owner), spawn(Team.ENEMY, (6, 6), no_reactions())]),
        U1,
    )
    climb = unit_step_cost(state, state.units[U1], (0, 0), (1, 0))
    assert climb is not None and climb > 1
    entered = enter(state, ROC)
    assert unit_step_cost(entered, entered.units[U1], (0, 0), (1, 0)) == 1


def test_elemental_chooses_an_element_and_bursts_adjacent_enemies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=4)
    state = scene()
    result = resolve(state, UseSkill(unit_id=U1, skill_id=ELEMENTAL, form_element=Element.ICE))
    unit = result.state.units[U1]
    assert unit.form is not None and unit.form.element is Element.ICE
    assert unit.weapon.element is Element.ICE
    (burst,) = [e for e in of(result, DamageDealt) if e.target_id == U2]
    assert burst.element is Element.ICE and burst.rolls == (4,)
    rules = result.state.ruleset
    assert damage_taken_permille(rules, unit, Element.ICE) == (
        damage_taken_permille(rules, state.units[U1], Element.ICE) * 500 // 1000
    )
    assert damage_taken_permille(rules, unit, Element.FIRE) == damage_taken_permille(
        rules, state.units[U1], Element.FIRE
    )


def test_elemental_defaults_to_the_first_element_and_rejects_others() -> None:
    state = scene()
    assert enter(state, ELEMENTAL).units[U1].form.element is Element.FIRE  # type: ignore[union-attr]
    with pytest.raises(IllegalActionError, match="只能選"):
        resolve(state, UseSkill(unit_id=U1, skill_id=ELEMENTAL, form_element=Element.HOLY))
    with pytest.raises(IllegalActionError, match="form_element"):
        resolve(state, UseSkill(unit_id=U1, skill_id=BEAR, form_element=Element.FIRE))


def test_werewolf_effects_and_entry_heal() -> None:
    state = scene()
    base = state.units[U1]
    base.hp = 500
    result = resolve(state, UseSkill(unit_id=U1, skill_id=WEREWOLF))
    unit = result.state.units[U1]
    rules = result.state.ruleset
    assert move_points_for_turn(rules, unit) == move_points_for_turn(rules, base) + 1
    plain = defense_value_permille(base, rules)
    assert defense_value_permille(unit, rules) == plain * 900 // 1000
    (healed,) = of(result, Healed)
    assert healed.amount == unit.max_hp * 100 // 1000 and unit.hp == 500 + healed.amount


# ---------------------------------------------------------------------------
# 天生武器：damage_dealt ＝ 卡片「目前 +N」；武器技仍看手上武器
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", [BEAR, CAT, WEREWOLF, ROC])
def test_natural_weapon_damage_matches_the_card_bonus(
    monkeypatch: pytest.MonkeyPatch, skill_id: str
) -> None:
    always(monkeypatch, d20=15, die=1)
    state = enter(scene(foe_at=(4, 3)), skill_id)
    unit = state.units[U1]
    lib = library()
    owner = CardOwner(
        weapon=held_weapon(unit),
        attr_get=lambda attr: effective_attribute(state.ruleset, unit, attr),
    )
    card = skill_card(lib, lib.ruleset.skill_def(skill_id), owner=owner)
    (line,) = [x for x in card.formula_lines if x.startswith("天生武器")]
    match = re.search(r"目前 \+(\d+)", line)
    assert match is not None
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (dealt,) = of(result, DamageDealt)
    assert dealt.rolls == (1,)
    assert dealt.scaled_permille // 1000 == int(match.group(1))
    assert dealt.amount == 1 + int(match.group(1))


def test_weapon_skills_still_use_the_hand_weapon_in_a_form() -> None:
    lib = library()
    weapon_skill = next(
        s
        for s in lib.ruleset.skills.skills
        if s.category == "weapon"
        and s.weapon_req == "melee"
        and s.kind == "active"
        and s.shape.type == "single"
        and not s.weapon_only
        and s.followup is None
    )
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([ROC, weapon_skill.id], base="hero_fighter", stamina=40)
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))],
        ),
        U1,
    )
    entered = enter(state, ROC)
    assert entered.units[U1].weapon.weapon_class == "ranged"  # 鳥喙
    ids = {a.skill_id for a in legal_actions(entered) if isinstance(a, UseSkill)}
    assert weapon_skill.id in ids  # 近戰武器技：看手上的劍


# ---------------------------------------------------------------------------
# 欄位、存檔、重播、AI
# ---------------------------------------------------------------------------


def test_form_skills_take_an_active_slot() -> None:
    lib = library()
    defs = [lib.ruleset.skill_def(s) for s in (BEAR, CAT)]
    slots = SkillSlots(active=1, passive=2, reaction=1, stance=2)
    assert any("主動" in p for p in skill_slot_problems(defs, slots))
    assert not skill_slot_problems(defs, SkillSlots(active=2, passive=2, reaction=1, stance=0))


def test_state_in_a_form_round_trips_through_json() -> None:
    state = enter(scene(), ELEMENTAL, form_element=Element.LIGHTNING)
    state = enter(give_turn(resolve(state, EndStance(unit_id=U1)).state, U1), BEAR)
    restored = state_from_json(state_to_json(state))
    assert restored == state
    assert restored.units[U1].form == state.units[U1].form
    assert restored.units[U1].form_cooldowns == {"elemental": 2}


def test_a_battle_with_forms_replays_identically() -> None:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([BEAR, CAT], base="hero_fighter", stamina=40)
    setup = make_setup(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=60))],
    )
    state = start_battle(setup, 7)
    steps: list[object] = []
    ai = UtilityAI(library().ai_profiles)
    for _ in range(40):
        if state.ended:
            break
        unit = state.active
        assert unit is not None
        if unit.id == U1 and unit.form is None and not unit.form_cooldowns and unit.ap >= 1:
            action: object = UseSkill(unit_id=U1, skill_id=CAT if steps else BEAR)
        else:
            action = ai(state)
        steps.append(action)
        state = resolve(state, action).state  # type: ignore[arg-type]
    run = replay(setup, 7, steps)  # type: ignore[arg-type]
    assert state_to_json(run.state) == state_to_json(state)
    assert any(isinstance(e, FormEntered) for e in run.events)


def test_the_ai_enters_a_form_when_it_has_nothing_better_and_never_cancels() -> None:
    state = scene(foe_at=(6, 6))
    state.units[U1].move_points = 0
    ai = UtilityAI(library().ai_profiles)
    scores = ai.rank(state)
    assert any(isinstance(s.action, UseSkill) and s.action.skill_id in FORM_SKILLS for s in scores)
    entered = enter(state, BEAR)
    ranked = ai.rank(give_turn(entered, U1))
    assert not any(isinstance(s.action, EndStance) for s in ranked)
    assert not any(
        isinstance(s.action, UseSkill) and s.action.skill_id in (*FORM_SKILLS, FURY) for s in ranked
    )
