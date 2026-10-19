"""Phase 3C-2：修正規則（修正型被動與改造型技能）的引擎套用點、預覽一致與確定性。"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.cli.battle import cmd_replay
from trpg.content.library import unit_skill_problems
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, Shove, UseSkill, legal_actions, resolve
from trpg.engine import modifiers as mods
from trpg.engine.ai.simple import choose_action
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    SkillCooldownChanged,
    SkillTriggered,
    StatusApplied,
    TriggerLimitReached,
    UnitMoved,
)
from trpg.engine.preview import preview
from trpg.engine.rules.combat import is_hit
from trpg.engine.runner import run_battle
from trpg.engine.skill_triggers import MODIFIER_ON_HIT
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import StatusInstance
from trpg.shared.types import Element, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
FLAT = "\n".join(["00000000"] * 5)
HERO = (1, 2)
FOE = (2, 2)


def mod(skill_id: str, *rules: Mapping[str, Any], weapon_req: str = "any") -> SkillDef:
    """測試用修正技能（不放在 ``content/``）。"""
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"測試修正 {skill_id[-5:]}",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": weapon_req,
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": list(rules),
        }
    )


def arena(
    equipped: Sequence[str],
    *,
    test_skills: Sequence[SkillDef] = (),
    hero: str = "hero_fighter",
    weapon: str | None = None,
    foes: Sequence[tuple[int, int]] = (FOE,),
    surfaces: Sequence[tuple[int, int, str]] = (),
    burning: bool = False,
    max_trigger_depth: int = 3,
) -> BattleState:
    """主角 U1（沒有反應、法力 99、裝備 ``equipped``）對上不反應的盜賊（HP 200）。"""
    hero_t = template(hero, reactions=[], max_mana=99, skills=list(equipped))
    spawns = [spawn(Team.ALLY, HERO, hero_t, weapon)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    m = make_map(FLAT, ally=[HERO], enemy=list(foes), surfaces=surfaces)
    state = make_state(m, spawns, skills=test_skills, max_trigger_depth=max_trigger_depth)
    if burning:
        state.units[U2].statuses.append(StatusInstance("burning", 2))
    return give_turn(state, U1)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def attack_damage(state: BattleState) -> DamageDealt:
    result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    return next(e for e in of(result.events, DamageDealt) if e.cause == "attack")


# ---------------------------------------------------------------------------
# damage_permille（修正型被動：灼傷之痕）
# ---------------------------------------------------------------------------


def test_searing_scar_adds_ten_percent_damage_only_against_burning_targets() -> None:
    plain = attack_damage(arena(["skill_searing_scar"]))
    burning = attack_damage(arena(["skill_searing_scar"], burning=True))
    without = attack_damage(arena([], burning=True))
    assert plain.multiplier_permille == 1000
    assert without.multiplier_permille == 1000
    assert burning.multiplier_permille == 1100
    assert burning.amount >= without.amount


def test_searing_scar_also_modifies_attack_skills() -> None:
    state = arena(
        ["skill_searing_scar", "skill_fire_bolt"], hero="hero_mage", foes=[(4, 2)], burning=True
    )
    result = resolve(
        with_rolls(state, [(20, 15), (8, 4)]),
        UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U2),
    )
    damage = next(e for e in of(result.events, DamageDealt) if e.cause == "attack")
    assert damage.multiplier_permille == 1100


def test_modifiers_do_not_change_triggered_passive_effects() -> None:
    """被動觸發不是持有者的動作：灼傷之痕不加成「命中時」被動的傷害。"""
    passive = SkillDef.model_validate(
        {
            "id": "skill_t_onhit",
            "name_zh": "測試被動",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [{"type": "damage", "dice": "1d4", "element": "fire"}],
            "trigger": {"event": "on_hit", "target": "other"},
        }
    )
    state = arena(["skill_searing_scar", passive.id], test_skills=[passive], burning=True)
    result = resolve(
        with_rolls(state, [(20, 15), (8, 4), (4, 2)]), Attack(unit_id=U1, target_id=U2)
    )
    triggered = [e for e in of(result.events, DamageDealt) if e.element is Element.FIRE]
    assert triggered and all(e.multiplier_permille == 1000 for e in triggered)


# ---------------------------------------------------------------------------
# hit_bonus
# ---------------------------------------------------------------------------

STEADY = mod("skill_t_steady", {"applies_to": {"actions": ["attack"]}, "change": {"hit_bonus": 2}})


def test_hit_bonus_is_added_to_the_attack_total_and_recorded() -> None:
    state = arena([STEADY.id], test_skills=[STEADY])
    result = resolve(with_rolls(state, [(20, 9), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    roll = of(result.events, AttackRolled)[0]
    assert roll.modifier_bonus == 2
    assert roll.total == (
        roll.natural + roll.hit_modifier + roll.proficiency + roll.situational + roll.cover + 2
    )


# ---------------------------------------------------------------------------
# cooldown_delta（餘燼循環）
# ---------------------------------------------------------------------------

BOLT = make_skill(
    "skill_t_cd_bolt",
    {"type": "single", "range": 5},
    [{"type": "damage", "dice": "1d6", "element": "fire"}],
    cost={"mana": 0, "cooldown": 3},
)


@pytest.mark.parametrize(("burning", "remaining"), [(True, 2), (False, 3)])
def test_ember_cycle_shortens_the_cooldown_after_hitting_a_burning_target(
    burning: bool, remaining: int
) -> None:
    state = arena(
        ["skill_ember_cycle", BOLT.id],
        test_skills=[BOLT],
        hero="hero_mage",
        foes=[(4, 2)],
        burning=burning,
    )
    result = resolve(
        with_rolls(state, [(20, 15), (6, 3)]), UseSkill(unit_id=U1, skill_id=BOLT.id, target_id=U2)
    )
    assert result.state.units[U1].cooldowns[BOLT.id] == remaining
    changes = [e.remaining for e in of(result.events, SkillCooldownChanged)]
    assert changes == ([3, 2] if burning else [3])


def test_ember_cycle_needs_a_hit() -> None:
    state = arena(
        ["skill_ember_cycle", BOLT.id], test_skills=[BOLT], hero="hero_mage", foes=[(4, 2)]
    )
    state.units[U2].statuses.append(StatusInstance("burning", 2))
    result = resolve(
        with_rolls(state, [(20, 1)]), UseSkill(unit_id=U1, skill_id=BOLT.id, target_id=U2)
    )
    assert result.state.units[U1].cooldowns[BOLT.id] == 3


# ---------------------------------------------------------------------------
# push_distance_delta 與 ap_delta（重踏）
# ---------------------------------------------------------------------------


def test_heavy_stomp_shoves_two_tiles_for_two_ap() -> None:
    state = arena(["skill_heavy_stomp"])
    result = resolve(with_rolls(state, [(20, 20)]), Shove(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (4, 2)
    assert result.state.units[U1].ap == state.units[U1].ap - 2
    plain = resolve(with_rolls(arena([]), [(20, 20)]), Shove(unit_id=U1, target_id=U2))
    assert plain.state.units[U2].xy == (3, 2)


def test_heavy_stomp_push_distance_is_capped_at_two_tiles() -> None:
    """颶風踢本來就推 2 格（上限），重踏不會推更遠（多出的 1 格在 3C-3a 起改為一次撞擊傷害，見
    ``test_collision.py``），AP 仍 +1。"""
    state = arena(["skill_heavy_stomp", "skill_gale_kick"])
    result = resolve(
        with_rolls(state, [(20, 15), (8, 4)]),
        UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2),
    )
    assert result.state.units[U2].xy == (4, 2)
    assert result.state.units[U1].ap == state.units[U1].ap - 2
    hero = state.units[U1]
    use = mods.skill_use(library().skills["skill_gale_kick"])
    assert mods.displace_distance(state, hero, use, Subject(None, FOE), 2) == 2
    assert mods.displace_distance(state, hero, use, Subject(None, FOE), 1) == 2


def test_ap_delta_makes_an_action_illegal_without_enough_ap() -> None:
    state = arena(["skill_heavy_stomp"])
    state.units[U1].ap = 1
    actions = legal_actions(state)
    assert not any(isinstance(a, Shove) for a in actions)
    assert any(isinstance(a, Attack) for a in actions)


def test_ap_delta_never_goes_below_one() -> None:
    cheap = mod(
        "skill_t_cheap",
        {"applies_to": {"actions": ["attack", "shove"]}, "change": {"ap_delta": -1}},
    )
    state = arena([cheap.id], test_skills=[cheap])
    result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U1].ap == state.units[U1].ap - 1


# ---------------------------------------------------------------------------
# range_delta
# ---------------------------------------------------------------------------

LONG = mod("skill_t_long", {"applies_to": {"all_attacks": True}, "change": {"range_delta": 1}})


def test_range_delta_extends_basic_attack_and_skill_range() -> None:
    far = [(3, 2)]  # 距離 2
    assert not any(isinstance(a, Attack) for a in legal_actions(arena([], foes=far)))
    state = arena([LONG.id], test_skills=[LONG], foes=far)
    assert Attack(unit_id=U1, target_id=U2) in legal_actions(state)
    mage = arena([LONG.id, "skill_fire_bolt"], test_skills=[LONG], hero="hero_mage", foes=[(7, 2)])
    assert UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U2) in legal_actions(mage)


# ---------------------------------------------------------------------------
# add_element（雷之手）
# ---------------------------------------------------------------------------


def test_thunder_hand_basic_attack_becomes_lightning_and_conducts_through_water() -> None:
    water = [(2, 2, "water"), (3, 2, "water"), (4, 2, "water")]
    state = arena(["skill_thunder_hand"], foes=[FOE, (4, 2)], surfaces=water)
    result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    damage = of(result.events, DamageDealt)
    direct = next(e for e in damage if e.cause == "attack")
    assert direct.element is Element.LIGHTNING
    assert [e.target_id for e in damage if e.cause == "conduct"] == [U3]
    plain = resolve(
        with_rolls(arena([], foes=[FOE, (4, 2)], surfaces=water), [(20, 15), (8, 4)]),
        Attack(unit_id=U1, target_id=U2),
    )
    assert not [e for e in of(plain.events, DamageDealt) if e.cause == "conduct"]


def test_add_element_does_not_override_an_existing_element() -> None:
    state = arena(["skill_thunder_hand"], hero="hero_mage", weapon="fire_staff", foes=[(4, 2)])
    hero = state.units[U1]
    assert mods.damage_element(state, hero, mods.ATTACK, Element.FIRE) is Element.FIRE
    assert mods.damage_element(state, hero, mods.ATTACK, Element.PHYSICAL) is Element.LIGHTNING


# ---------------------------------------------------------------------------
# add_tags（標籤改寫接上另一條修正）
# ---------------------------------------------------------------------------

KINDLE = mod(
    "skill_t_kindle", {"applies_to": {"skill_tags": ["push"]}, "change": {"add_tags": ["fire"]}}
)
FIRE_BOOST = mod(
    "skill_t_zboost", {"applies_to": {"skill_tags": ["fire"]}, "change": {"damage_permille": 200}}
)


def test_add_tags_lets_another_modifier_match_the_skill() -> None:
    state = arena([KINDLE.id, FIRE_BOOST.id, "skill_gale_kick"], test_skills=[KINDLE, FIRE_BOOST])
    gale = library().skills["skill_gale_kick"]
    assert mods.effective_tags(state, state.units[U1], gale) == (*gale.tags, "fire")
    result = resolve(
        with_rolls(state, [(20, 15), (8, 4)]),
        UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2),
    )
    damage = next(e for e in of(result.events, DamageDealt) if e.cause == "attack")
    assert damage.multiplier_permille == 400 * 1200 // 1000
    alone = arena([FIRE_BOOST.id, "skill_gale_kick"], test_skills=[FIRE_BOOST])
    assert mods.effective_tags(alone, alone.units[U1], gale) == gale.tags


# ---------------------------------------------------------------------------
# on_hit_effects 與觸發深度
# ---------------------------------------------------------------------------

SCORCH = mod(
    "skill_t_scorch",
    {
        "applies_to": {"actions": ["attack"]},
        "change": {"on_hit_effects": [{"type": "apply_status", "status": "vulnerable"}]},
    },
)


def test_on_hit_effects_apply_after_a_hit_as_a_depth_one_trigger() -> None:
    state = arena([SCORCH.id], test_skills=[SCORCH])
    result = resolve(
        with_rolls(state, [(20, 15), (8, 4), (20, 20)]), Attack(unit_id=U1, target_id=U2)
    )
    fired = of(result.events, SkillTriggered)
    assert [(e.skill_id, e.trigger, e.other_id, e.trigger_depth) for e in fired] == [
        (SCORCH.id, MODIFIER_ON_HIT, U2, 1)
    ]
    applied = of(result.events, StatusApplied)
    assert [(e.target_id, e.status_id) for e in applied] == [(U2, "vulnerable")]


def test_on_hit_effects_do_nothing_on_a_miss() -> None:
    state = arena([SCORCH.id], test_skills=[SCORCH])
    result = resolve(with_rolls(state, [(20, 1)]), Attack(unit_id=U1, target_id=U2))
    assert not of(result.events, SkillTriggered)


def test_on_hit_effects_respect_max_trigger_depth() -> None:
    state = arena([SCORCH.id], test_skills=[SCORCH], max_trigger_depth=0)
    result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
    assert not of(result.events, SkillTriggered)
    assert [e.skill_id for e in of(result.events, TriggerLimitReached)] == [SCORCH.id]


# ---------------------------------------------------------------------------
# 預覽與實際結算一致
# ---------------------------------------------------------------------------


def _chance(bonus: int, target: int) -> Fraction:
    return Fraction(sum(is_hit(n, n + bonus, target) for n in range(1, 21)), 20)


def test_preview_matches_resolution_for_modified_attacks() -> None:
    state = arena(["skill_searing_scar", STEADY.id], test_skills=[STEADY], burning=True)
    action = Attack(unit_id=U1, target_id=U2)
    shown = preview(state, action)
    actual = resolve(with_rolls(state, [(20, 9), (8, 4)]), action)
    roll = of(actual.events, AttackRolled)[0]
    assert roll.modifier_bonus == 2
    assert shown.hit_chance == _chance(roll.total - roll.natural, roll.target_number)
    low = next(e for e in shown.min_events if isinstance(e, DamageDealt))
    real = next(e for e in of(actual.events, DamageDealt) if e.cause == "attack")
    assert low.multiplier_permille == real.multiplier_permille == 1100
    assert shown.damage is not None
    assert shown.damage.minimum <= real.amount <= shown.damage.maximum
    assert shown.ap_cost == state.units[U1].ap - actual.state.units[U1].ap == 1
    assert shown.reach == 1


def test_preview_matches_resolution_for_modified_skills_and_maneuvers() -> None:
    state = arena(
        ["skill_heavy_stomp", "skill_gale_kick", LONG.id], test_skills=[LONG], foes=[(3, 2)]
    )
    kick = UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2)
    shown = preview(state, kick)
    actual = resolve(with_rolls(state, [(20, 15), (8, 4)]), kick)
    assert shown.ap_cost == state.units[U1].ap - actual.state.units[U1].ap == 2
    assert shown.reach == 2  # 武器射程 1 ＋ range_delta 1
    moved = [e for e in of(list(shown.min_events), UnitMoved) if e.unit_id == U2]
    real = [e for e in of(actual.events, UnitMoved) if e.unit_id == U2]
    assert moved[-1].to_pos == real[-1].to_pos
    adjacent = arena(["skill_heavy_stomp"])
    shove = Shove(unit_id=U1, target_id=U2)
    after = resolve(with_rolls(adjacent, [(20, 20)]), shove)
    assert preview(adjacent, shove).ap_cost == adjacent.units[U1].ap - after.state.units[U1].ap


def test_preview_hit_chance_includes_the_skill_hit_bonus() -> None:
    aim = mod("skill_t_aim", {"applies_to": {"all_skills": True}, "change": {"hit_bonus": 3}})
    state = arena([aim.id, "skill_fire_bolt"], test_skills=[aim], hero="hero_mage", foes=[(4, 2)])
    action = UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U2)
    target = preview(state, action).targets[0]
    roll = of(resolve(with_rolls(state, [(20, 9), (8, 4)]), action).events, AttackRolled)[0]
    assert roll.modifier_bonus == 3
    assert target.hit_chance == _chance(roll.total - roll.natural, roll.target_number)


# ---------------------------------------------------------------------------
# 被動欄位 3
# ---------------------------------------------------------------------------


def test_three_passive_slot_skills_are_allowed_and_four_are_rejected() -> None:
    lib = library()
    assert lib.ruleset.core.skill_slots.passive == 3
    weapon = lib.weapons["one_handed_sword"]
    three = ["skill_bloodlust", "skill_crippling_crit", "skill_searing_scar"]
    ok = template("hero_fighter", skills=three)
    assert unit_skill_problems(ok, weapon, lib.skills, lib.ruleset.core) == []
    four = template("hero_fighter", skills=[*three, "skill_ember_cycle"])
    problems = unit_skill_problems(four, weapon, lib.skills, lib.ruleset.core)
    assert problems == ["skills：被動（含修正）技能超過欄位上限：4 個（上限 3）"]


# ---------------------------------------------------------------------------
# 確定性：疊加順序與重播
# ---------------------------------------------------------------------------


def test_stacking_order_is_by_skill_id_then_rule_index_regardless_of_equip_order() -> None:
    first = mod(
        "skill_t_ord_a",
        {"applies_to": {"actions": ["attack"]}, "change": {"add_element": "fire"}},
        {"applies_to": {"actions": ["attack"]}, "change": {"damage_permille": 100}},
    )
    second = mod(
        "skill_t_ord_b",
        {"applies_to": {"actions": ["attack"]}, "change": {"add_element": "ice"}},
        {"applies_to": {"actions": ["attack"]}, "change": {"damage_permille": 250}},
    )
    for order in ([first.id, second.id], [second.id, first.id]):
        state = arena(order, test_skills=[first, second])
        hero = state.units[U1]
        assert [(a.skill.id, a.index) for a in mods.unit_rules(state, hero)] == [
            (first.id, 0),
            (first.id, 1),
            (second.id, 0),
            (second.id, 1),
        ]
        damage = attack_damage(state)
        assert damage.element is Element.FIRE
        assert damage.multiplier_permille == 1350


def test_battles_with_modifiers_are_deterministic_and_replay(tmp_path: Path) -> None:
    water = [(3, 2, "water"), (4, 2, "water"), (5, 2, "water")]
    hero_t = template(
        "hero_fighter",
        skills=["skill_thunder_hand", "skill_heavy_stomp", "skill_searing_scar", "skill_gale_kick"],
    )
    setup = make_setup(
        make_map(FLAT, ally=[HERO], enemy=[(5, 2), (6, 3)], surfaces=water),
        [
            spawn(Team.ALLY, HERO, hero_t),
            spawn(Team.ENEMY, (5, 2)),
            spawn(Team.ENEMY, (6, 3)),
        ],
        max_rounds=6,
    )
    first = run_battle(setup, 11, choose_action)
    again = run_battle(setup, 11, choose_action)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in again.events]
    lightning = [
        e for e in first.events if isinstance(e, DamageDealt) and e.element is Element.LIGHTNING
    ]
    assert lightning  # 雷之手的普攻確實出現在這場戰鬥
    path = tmp_path / "log.json"
    path.write_text(first.to_log().model_dump_json(), encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()
