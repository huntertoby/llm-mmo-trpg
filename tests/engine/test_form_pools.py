"""Phase 3J-4／3J-4b：形態內容與形態池（Phase3J計畫.md 4.11、06-技能.md 6.30）。

- 10 招「化身為〇」的階級與類別、卡片＝實戰（維持費、進入）；
- 3 招主動利用者（化形撲擊、野性怒吼、化形回春）：在形態中／不在形態中，卡片數字＝實戰；
- 定向蓄力（龍的吐息）中，AI 不選別的形態的進入；
- 形態池名單：1 階主動起始技能與主動利用者。
"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.content.form_text import form_sentence
from trpg.content.rules import SkillSlots
from trpg.engine import Attack, BattleState, EndStance, EndTurn, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    DamageDealt,
    FormEntered,
    FormUpkeepPaid,
    Healed,
    StatusApplied,
)
from trpg.engine.rules.statuses import effective_attribute
from trpg.narrative.skills import skill_card
from trpg.shared.types import Attribute, Team
from trpg.skillgen.keywords import is_starter_skill, keyword_pools

POUNCE, ROAR, RENEWAL = "skill_form_pounce", "skill_wild_roar", "skill_form_renewal"
BEAR = "skill_form_bear"
DRAGON = "skill_form_dragon"
SLOTS = SkillSlots(active=12, passive=2, reaction=1, stance=2)

# 06 6.30「形態池名單」：1 階 熊、貓、巨鵰、狼人；2 階 惡魔、巨人、元素化身、暗影形態、樹人、龍
TIERS = {
    "bear": 1,
    "cat": 1,
    "roc": 1,
    "werewolf": 1,
    "demon": 2,
    "giant": 2,
    "elemental": 2,
    "shadow": 2,
    "treant": 2,
    "dragon": 2,
}
NAMES = {
    "bear": "化身為熊",
    "cat": "化身為貓",
    "roc": "化身為巨鵰",
    "werewolf": "化身為狼人",
    "demon": "化身為惡魔",
    "giant": "化身為巨人",
    "elemental": "化身為元素化身",
    "shadow": "化身為暗影形態",
    "treant": "化身為樹人",
    "dragon": "化身為龍",
}


def arena(
    skills: list[str],
    *,
    foes: tuple[tuple[int, int], ...] = ((4, 3),),
    hp: int = 999,
) -> BattleState:
    """U1（戰士）在 (3, 3) 手上有回合，資源充足；敵人們各 999 HP、沒有反應。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    owner = caster_template(skills, base="hero_fighter", max_hp=hp, stamina=40)
    spawns = [spawn(Team.ALLY, (3, 3), owner)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=999)) for xy in foes]
    state = give_turn(make_state(m, spawns, skill_slots=SLOTS), U1)  # type: ignore[arg-type]
    unit = state.units[U1]
    unit.stamina = 40
    unit.mana = 40
    unit.stamina_regen = 0
    unit.ap = 8
    return state


def use(state: BattleState, skill_id: str, **extra: object) -> object:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **extra))  # type: ignore[arg-type]


def into_bear(state: BattleState) -> BattleState:
    state = use(state, BEAR).state  # type: ignore[attr-defined]
    state.units[U1].ap = 8
    return state


# ---------------------------------------------------------------------------
# 10 招「化身為〇」
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("form_id", "tier"), sorted(TIERS.items()))
def test_each_form_skill_is_the_named_spell_with_the_pool_tier(form_id: str, tier: int) -> None:
    skill = library().ruleset.skill_def(f"skill_form_{form_id}")
    assert skill.name_zh == NAMES[form_id] and skill.tier == tier
    assert skill.kind == "stance" and skill.category == "spell" and skill.weapon_req == "any"
    assert skill.cost.model_dump(exclude_none=True, exclude_defaults=True) == {}  # 只有姿態的 1 AP
    assert skill.form_id == form_id


@pytest.mark.parametrize("form_id", sorted(TIERS))
def test_entering_and_upkeep_match_the_card(form_id: str) -> None:
    lib = library()
    skill_id = f"skill_form_{form_id}"
    card = skill_card(lib, lib.ruleset.skill_def(skill_id))
    form = lib.ruleset.form_def(form_id)
    assert card.effects == (form_sentence(lib.ruleset.forms, form, lib.ruleset.core),)
    match = re.search(r"每回合開始 −(\d+) (耐力|法力)", card.effects[0])
    assert match is not None
    state = arena([skill_id])
    entered = use(state, skill_id)
    assert [e.form_id for e in of(entered, FormEntered)] == [form_id]  # type: ignore[arg-type]
    state = entered.state  # type: ignore[attr-defined]
    resource = "mana" if match.group(2) == "法力" else "stamina"
    before = getattr(state.units[U1], resource)
    paid: list[FormUpkeepPaid] = []
    result = resolve(state, EndTurn(unit_id=U1))
    while True:
        paid += of(result, FormUpkeepPaid)
        if result.state.active_unit == U1:
            break
        result = resolve(result.state, EndTurn(unit_id=result.state.active_unit))  # type: ignore[arg-type]
    assert [(p.resource, p.amount) for p in paid] == [(resource, int(match.group(1)))]
    assert getattr(result.state.units[U1], resource) == before - int(match.group(1))


# ---------------------------------------------------------------------------
# 3 招主動利用者：卡片數字＝實戰（在形態中／不在形態中）
# ---------------------------------------------------------------------------


def _card_lines(skill_id: str) -> tuple[str, ...]:
    lib = library()
    return skill_card(lib, lib.ruleset.skill_def(skill_id)).effects


def _exact(rolls_sum: int, scaled_permille: int, multiplier: int) -> int:
    """傷害或治療的精確值：（骰值＋屬性加成）整體乘倍率，一次無條件捨去（屬性加成只算一次）。"""
    return (rolls_sum * 1000 + scaled_permille) * multiplier // 1_000_000


def test_the_pounce_dashes_and_the_form_adds_exactly_thirty_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    (line,) = [x for x in _card_lines(POUNCE) if "3d4" in x]
    assert "若你在形態中，整體 +30%" in line and len(_card_lines(POUNCE)) == 2  # 衝鋒＋一筆傷害
    bonus = effective_attribute(library().ruleset, arena([POUNCE]).units[U1], Attribute.STR)
    foes = ((6, 3),)
    plain = use(arena([POUNCE, BEAR], foes=foes), POUNCE, target_id=U2)
    (dealt,) = of(plain, DamageDealt)  # type: ignore[arg-type]
    assert dealt.rolls == (1, 1, 1) and dealt.scaled_permille == bonus * 500
    assert dealt.multiplier_permille == 1000 and dealt.amount == _exact(3, bonus * 500, 1000)
    assert plain.state.units[U1].xy == (5, 3)  # type: ignore[attr-defined]  # 衝鋒到目標身旁
    inside = use(into_bear(arena([POUNCE, BEAR], foes=foes)), POUNCE, target_id=U2)
    (hit,) = of(inside, DamageDealt)  # type: ignore[arg-type]
    assert hit.rolls == (1, 1, 1) and hit.scaled_permille == bonus * 500  # 屬性加成只算一次
    assert hit.multiplier_permille == 1300 and hit.amount == _exact(3, bonus * 500, 1300)
    assert inside.state.units[U1].xy == (5, 3)  # type: ignore[attr-defined]


def test_the_roar_hits_adjacent_enemies_only_and_the_form_adds_exactly_thirty_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    assert any("若你在形態中，整體 +30%" in x for x in _card_lines(ROAR))
    bonus = effective_attribute(library().ruleset, arena([ROAR]).units[U1], Attribute.CON)
    foes = ((4, 3), (6, 3))  # 第二個不在自己周圍 1 格
    plain = use(arena([ROAR, BEAR], foes=foes), ROAR)
    (hit,) = of(plain, DamageDealt)  # type: ignore[arg-type]
    assert (hit.target_id, hit.rolls) == (U2, (1, 1))
    assert hit.amount == _exact(2, bonus * 500, 1000)
    weak = [e for e in of(plain, StatusApplied) if e.status_id == "weaken"]  # type: ignore[arg-type]
    assert [(e.target_id, e.duration) for e in weak] == [(U2, 1)]
    inside = use(into_bear(arena([ROAR, BEAR], foes=foes)), ROAR)
    (hit,) = of(inside, DamageDealt)  # type: ignore[arg-type]
    assert (hit.target_id, hit.rolls) == (U2, (1, 1)) and hit.multiplier_permille == 1300
    assert hit.amount == _exact(2, bonus * 500, 1300)
    assert U3 not in {h.target_id for h in of(inside, DamageDealt)}  # type: ignore[arg-type]


def test_the_form_renewal_heals_exactly_thirty_percent_more_inside_a_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    assert any("若你在形態中，整體 +30%" in x for x in _card_lines(RENEWAL))
    state = arena([RENEWAL, BEAR], hp=200)
    state.units[U1].hp = 50
    plain = use(state, RENEWAL)
    (healed,) = of(plain, Healed)  # type: ignore[arg-type]
    assert healed.rolls == (1, 1) and healed.target_id == U1
    wis = effective_attribute(library().ruleset, state.units[U1], Attribute.WIS)
    assert healed.amount == _exact(2, wis * 500, 1000)
    inside_state = into_bear(state)
    inside_state.units[U1].hp = 50
    inside = use(inside_state, RENEWAL)
    (healed,) = of(inside, Healed)  # type: ignore[arg-type]
    assert healed.rolls == (1, 1) and healed.amount == _exact(2, wis * 500, 1300)


def test_the_exploiters_belong_to_the_form_pool() -> None:
    lib = library()
    exclusive = keyword_pools(lib, starter_only=True, exclusive_only=True)["form"]
    makers = tuple(f"skill_form_{f}" for f in ("bear", "cat", "roc", "werewolf"))
    assert set(exclusive) == {*makers, POUNCE, RENEWAL, ROAR}  # 3J-4b：1 階化身也當起始技能
    assert all(is_starter_skill(lib.skills[i]) and lib.skills[i].tier == 1 for i in exclusive)
    everyone = keyword_pools(lib, exclusive_only=True)["form"]
    for form_id in TIERS:  # 十招進入技能是製造者（姿態不算起始技能）
        assert f"skill_form_{form_id}" in everyone


# ---------------------------------------------------------------------------
# AI：定向蓄力中不換形態
# ---------------------------------------------------------------------------


def _rank_skills(state: BattleState) -> set[str]:
    ranked = UtilityAI(library().ai_profiles).rank(state)
    assert not any(isinstance(s.action, EndStance) for s in ranked)  # AI 從不取消形態
    return {s.action.skill_id for s in ranked if isinstance(s.action, UseSkill)}


def test_the_ai_does_not_switch_forms_while_the_dragon_is_charging() -> None:
    skills = [DRAGON, BEAR, "skill_form_cat"]
    foe = ((6, 3),)
    in_dragon = use(arena(skills, foes=foe), DRAGON).state  # type: ignore[attr-defined]
    in_dragon.units[U1].ap = 8
    in_dragon.units[U1].move_points = 0
    # 對照：龍形態、還沒蓄力時，其他形態是輪替候選
    assert _rank_skills(in_dragon) & {BEAR, "skill_form_cat"}
    charging = resolve(in_dragon, Attack(unit_id=U1, direction="east")).state
    assert charging.units[U1].ap > 0 and charging.units[U1].form is not None
    assert _rank_skills(charging) & {BEAR, "skill_form_cat"} == set()
    # 蓄力結束（下一個自己的回合）後恢復輪替
    released = give_turn(charging, U1)
    released.units[U1].statuses = [s for s in released.units[U1].statuses if s.direction is None]
    released.units[U1].ap = 8
    released.units[U1].move_points = 0
    assert _rank_skills(released) & {BEAR, "skill_form_cat"}
