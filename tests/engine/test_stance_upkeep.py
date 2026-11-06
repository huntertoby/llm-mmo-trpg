"""Phase 3W-2b：姿態每招維持費（``SkillDef.stance_upkeep``）與元素姿態的結算。

維持費 ±1 實際扣費（法術技扣法力、武器技扣耐力）、付不起解除姿態、
元素傷害加成與狀態持續加成真的生效。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from trpg.content.rules import SkillSlots
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, resolve
from trpg.engine.events import DamageDealt, StanceUpkeepPaid, StatusApplied, StatusRemoved
from trpg.engine.rules.statuses import (
    damage_dealt_permille,
    damage_taken_permille,
    status_duration_bonus,
)
from trpg.engine.state import StatusInstance
from trpg.narrative.skills import cost_parts
from trpg.shared.types import Element, Team


def _stance(
    skill_id: str, status: str, upkeep: int, *, category: str = "spell", mana: int = 0
) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"測試姿態 {skill_id[-4:]}",
            "tier": 2,
            "rarity": "rare",
            "kind": "stance",
            "skeleton": "stance",
            "category": category,
            "weapon_req": "any" if category == "spell" else "melee",
            "ap_cost": None,
            "scaling_attr": "int" if category == "spell" else "str",
            "shape": {"type": "self"},
            "effects": [{"type": "apply_status", "status": status, "affects": "self"}],
            "cost": {"mana": mana} if mana else {},
            "stance_upkeep": upkeep,
        }
    )


def _scene(stance: SkillDef, *extra: SkillDef, base: str = "hero_mage") -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([stance, *extra], base=base, max_hp=999)
    foe = no_reactions(max_hp=999)
    state = make_state(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), foe)],
        skills=[stance, *extra],
        skill_slots=SkillSlots(active=6, passive=3, reaction=1, stance=1),  # type: ignore[arg-type]
    )
    return give_turn(state, U1)


def _next_own_turn(state: BattleState):  # type: ignore[no-untyped-def]
    """U1 結束回合、敵人結束回合，回到 U1 的回合開始（回傳這一段的事件）。"""
    first = resolve(state, EndTurn(unit_id=U1))
    second = answered(resolve(first.state, EndTurn(unit_id=U2)))
    return second


@pytest.mark.parametrize("upkeep", [0, 1, 2])
def test_spell_stance_pays_mana_per_upkeep_point_each_own_turn(upkeep: int) -> None:
    stance = _stance("skill_t_stance_a", "stance_fire_2", upkeep)
    state = resolve(_scene(stance), UseSkill(unit_id=U1, skill_id=stance.id)).state
    result = _next_own_turn(state)
    paid = of(result, StanceUpkeepPaid)
    per_point = library().ruleset.forms.stance_upkeep_mana
    if upkeep == 0:
        assert paid == []
    else:
        assert len(paid) == 1
        assert paid[0].resource == "mana" and paid[0].amount == upkeep * per_point
        assert paid[0].skill_id == stance.id and paid[0].status_id == "stance_fire_2"
        assert paid[0].remaining == result.state.units[U1].mana
    # 法力每回合會回復，所以只比「事件」與「姿態還在」
    assert any(s.status_id == "stance_fire_2" for s in result.state.units[U1].statuses)


def test_weapon_stance_pays_stamina_not_mana() -> None:
    stance = _stance("skill_t_stance_b", "stance_physical_2", 2, category="weapon")
    state = resolve(
        _scene(stance, base="hero_fighter"), UseSkill(unit_id=U1, skill_id=stance.id)
    ).state
    result = _next_own_turn(state)
    (paid,) = of(result, StanceUpkeepPaid)
    assert paid.resource == "stamina"
    assert paid.amount == 2 * library().ruleset.forms.stance_upkeep_stamina


def test_upkeep_plus_one_costs_exactly_one_more_point() -> None:
    """維持費 ±1：差一點，扣的量就差一個單位（法術技 1 點 ＝ ``stance_upkeep_mana``）。"""
    amounts = {}
    for upkeep in (1, 2):
        stance = _stance(f"skill_t_stance_c{upkeep}", "stance_fire_2", upkeep)
        state = resolve(_scene(stance), UseSkill(unit_id=U1, skill_id=stance.id)).state
        (paid,) = of(_next_own_turn(state), StanceUpkeepPaid)
        amounts[upkeep] = paid.amount
    assert amounts[2] - amounts[1] == library().ruleset.forms.stance_upkeep_mana


def test_stance_is_removed_when_the_upkeep_cannot_be_paid() -> None:
    stance = _stance("skill_t_stance_d", "stance_fire_2", 2)
    state = resolve(_scene(stance), UseSkill(unit_id=U1, skill_id=stance.id)).state
    state = state.clone()
    state.units[U1].mana = 0
    state.units[U1].max_mana = 0  # 回合開始不回法力
    result = _next_own_turn(state)
    assert of(result, StanceUpkeepPaid) == []
    removed = [e for e in of(result, StatusRemoved) if e.status_id == "stance_fire_2"]
    assert [e.reason for e in removed] == ["upkeep"]
    assert not any(s.status_id == "stance_fire_2" for s in result.state.units[U1].statuses)


def test_stance_without_upkeep_never_pays() -> None:
    """舊姿態（維持費 0）與沒有 skill_id 的姿態狀態不付維持費。"""
    state = _scene(_stance("skill_t_stance_e", "stance_fire_2", 0))
    state = state.clone()
    state.units[U1].statuses.append(StatusInstance(status_id="stance_fury"))
    assert of(_next_own_turn(state), StanceUpkeepPaid) == []


def test_upkeep_is_budget_allowance_in_the_card() -> None:
    lib = library()
    text = "".join(cost_parts(lib, _stance("skill_t_stance_f", "stance_fire_2", 2)))
    assert "維持費" in text and "法力" in text


# ---------------------------------------------------------------------------
# 元素姿態的效果
# ---------------------------------------------------------------------------


def test_element_dealt_only_boosts_its_own_element() -> None:
    lib = library().ruleset
    state = _scene(_stance("skill_t_stance_g", "stance_fire_2", 1))
    unit = state.units[U1]
    assert damage_dealt_permille(lib, unit, Element.FIRE) == 1000
    unit.statuses.append(StatusInstance(status_id="stance_fire_2"))
    fire = damage_dealt_permille(lib, unit, Element.FIRE)
    assert fire == lib.status_def("stance_fire_2").element_dealt_permille > 1000
    assert damage_dealt_permille(lib, unit, Element.ICE) == 1000
    assert damage_dealt_permille(lib, unit) == 1000


def test_element_stance_raises_real_fire_damage() -> None:
    bolt = make_skill(
        "skill_t_bolt_a",
        {"type": "single", "range": 3},
        [{"type": "damage", "element": "fire", "dice": "2d6"}],
    )
    higher = 0
    for seed in range(8):
        plain = _bolt_damage(bolt, seed, stance=None)
        boosted = _bolt_damage(bolt, seed, stance="stance_fire_5")
        assert boosted >= plain
        higher += boosted > plain
    assert higher >= 1


def _bolt_damage(bolt: SkillDef, seed: int, *, stance: str | None) -> int:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([bolt], max_hp=999)
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))],
            seed=seed,
            skills=[bolt],
        ),
        U1,
    )
    if stance is not None:
        state.units[U1].statuses.append(StatusInstance(status_id=stance))
    result = answered(resolve(state, UseSkill(unit_id=U1, skill_id=bolt.id, target_id=U2)))
    return sum(e.amount for e in of(result, DamageDealt) if e.target_id == U2)


def test_fire_stance_makes_burning_last_one_turn_longer() -> None:
    ignite = make_skill(
        "skill_t_ignite",
        {"type": "single", "range": 3},
        [{"type": "apply_status", "status": "burning", "affects": "enemies"}],
    )
    lib = library().ruleset

    def burning_turns(stance: str | None) -> int | None:
        m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
        owner = caster_template([ignite], max_hp=999)
        state = give_turn(
            make_state(
                m,
                [
                    spawn(Team.ALLY, (3, 3), owner),
                    spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999)),
                ],
                skills=[ignite],
            ),
            U1,
        )
        if stance is not None:
            state.units[U1].statuses.append(StatusInstance(status_id=stance))
        result = answered(resolve(state, UseSkill(unit_id=U1, skill_id=ignite.id, target_id=U2)))
        applied = [e for e in of(result, StatusApplied) if e.status_id == "burning"]
        return applied[0].duration if applied else None

    base = burning_turns(None)
    assert base is not None
    assert burning_turns("stance_fire_2") == base + 1
    assert burning_turns("stance_ice_2") == base  # 別的元素姿態不加
    assert (
        status_duration_bonus(
            lib, _scene(_stance("skill_t_stance_h", "stance_fire_2", 1)).units[U1], "burning"
        )
        == 0
    )


def test_earth_stance_lowers_physical_damage_taken() -> None:
    rules = library().ruleset
    state = _scene(_stance("skill_t_stance_i", "stance_earth_4", 1))
    unit = state.units[U1]
    unit.statuses.append(StatusInstance(status_id="stance_earth_4"))
    assert (
        damage_taken_permille(rules, unit, Element.PHYSICAL) == 900
    )  # 大地架勢（3 階）：物理 −10%
    assert damage_taken_permille(rules, unit, Element.FIRE) == 1000


def _lightning_bolt_damage(bolt: SkillDef, seed: int, *, stance: str | None, water: bool) -> int:
    m = make_map(
        FLAT7,
        ally=[(3, 3)],
        enemy=[(4, 3)],
        surfaces=[(4, 3, "water")] if water else [],
    )
    owner = caster_template([bolt], max_hp=999)
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))],
            seed=seed,
            skills=[bolt],
        ),
        U1,
    )
    if stance is not None:
        state.units[U1].statuses.append(StatusInstance(status_id=stance))
    result = answered(resolve(state, UseSkill(unit_id=U1, skill_id=bolt.id, target_id=U2)))
    return sum(e.amount for e in of(result, DamageDealt) if e.target_id == U2)


def test_thunder_stance_has_no_blind_bonus_and_boosts_wet_targets() -> None:
    lib = library().ruleset
    for level in range(1, 6):
        defn = lib.status_def(f"stance_lightning_{level}")
        assert "blinded" not in defn.status_duration_bonus
        assert defn.element_dealt_wet_permille > 1000
    unit = _scene(_stance("skill_t_stance_t", "stance_lightning_3", 1)).units[U1]
    unit.statuses.append(StatusInstance(status_id="stance_lightning_3"))
    dry = damage_dealt_permille(lib, unit, Element.LIGHTNING)
    wet = damage_dealt_permille(lib, unit, Element.LIGHTNING, on_water=True)
    assert wet > dry > 1000
    assert damage_dealt_permille(lib, unit, Element.FIRE, on_water=True) == 1000


def test_thunder_stance_real_damage_is_higher_on_water() -> None:
    bolt = make_skill(
        "skill_t_bolt_l",
        {"type": "single", "range": 3},
        [{"type": "damage", "element": "lightning", "dice": "2d6"}],
    )
    stance = "stance_lightning_5"
    more = 0
    for seed in range(8):
        dry_plain = _lightning_bolt_damage(bolt, seed, stance=None, water=False)
        dry = _lightning_bolt_damage(bolt, seed, stance=stance, water=False)
        wet = _lightning_bolt_damage(bolt, seed, stance=stance, water=True)
        assert dry >= dry_plain
        assert wet >= dry
        more += wet > dry
    assert more >= 1
