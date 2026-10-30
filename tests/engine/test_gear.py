"""裝備詞條的結算（Phase 3G-G1）：第 1、2、8 類、遞減疊加、硬上限、舊資料相容、預覽與檢視。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
)
from trpg.cli.main import main as cli_main
from trpg.content.equipment import (
    EquippedAffix,
    EquippedItem,
    ItemDef,
    Loadout,
    StatAffix,
    resolve_loadout,
)
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import Attack, BattleState, preview, start_battle
from trpg.engine import modifiers as mods
from trpg.engine.context import Ctx
from trpg.engine.events import GearHpLost
from trpg.engine.gear.core import (
    build_gear,
    cap_ap_gain,
    cap_cooldown,
    cap_crit_range,
    gear_cooldown,
    gear_damage_permille,
    gear_damage_taken_permille,
    gear_defense_permille,
    gear_hit_bonus,
)
from trpg.engine.rules.combat import defense_value_permille, element_modifier_ppm
from trpg.engine.rules.statuses import damage_taken_permille
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetupError, UnitSpawn, build_setup
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.targeting import pay_skill_cost
from trpg.engine.state import UnitState, state_from_json, state_to_json
from trpg.engine.turns import start_turn
from trpg.engine.view import project_for
from trpg.shared.types import Attribute, Element, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")

type Rolls = Sequence[tuple[str, int | None]]


def _item(slot: str, rolls: Rolls, *, weapon: str | None = None) -> EquippedItem:
    """測試用物品（不檢查欄位與數值範圍；合法性另外測）。"""
    lib = library()
    slot_type = SLOT_TYPE_OF[slot]
    item = ItemDef.model_validate(
        {
            "id": f"item_t_{slot}",
            "name_zh": f"測試{slot}",
            "slot_type": slot_type,
            "weapon": weapon or ("one_handed_sword" if slot_type == "weapon" else None),
            "affixes": [{"affix": a, "value": v} for a, v in rolls],
        }
    )
    return EquippedItem(
        slot=slot,  # type: ignore[arg-type]
        item=item,
        affixes=tuple(EquippedAffix(affix=lib.affixes[a], value=v) for a, v in rolls),
    )


def _loadout(slots: Mapping[str, Rolls]) -> Loadout:
    order = list(SLOT_TYPE_OF)
    return Loadout(items=tuple(_item(s, slots[s]) for s in sorted(slots, key=order.index)))


def _geared(slots: Mapping[str, Rolls], base: str = "hero_fighter") -> UnitSpawn:
    s = spawn(Team.ALLY, (0, 0), no_reactions(base))
    return s.model_copy(update={"equipment": _loadout(slots)})


def _state(
    hero: UnitSpawn, heights: str = "000\n000", enemy: str = "bandit", seed: int = 0
) -> BattleState:
    rows = heights.strip().split("\n")
    m = make_map(heights, ally=[(0, 0)], enemy=[(len(rows[0]) - 1, 0)])
    foe = spawn(Team.ENEMY, (len(rows[0]) - 1, 0), no_reactions(enemy))
    return start_battle(make_setup(m, [hero, foe]), seed)


def _unit(slots: Mapping[str, Rolls], base: str = "hero_fighter") -> UnitState:
    return _state(_geared(slots, base)).units[U1]


# ---------------------------------------------------------------------------
# 第 1 類 數值
# ---------------------------------------------------------------------------


def test_stat_affixes_merge_into_unit_totals() -> None:
    plain = _state(spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter"))).units[U1]
    unit = _unit(
        {
            "main_hand": [("affix_attr_str", 2)],
            "body": [("affix_max_hp", 12), ("affix_resist_fire", 100)],
        }
    )
    assert unit.attributes[Attribute.STR] == plain.attributes[Attribute.STR] + 2
    assert unit.max_hp == plain.max_hp + 12 and unit.hp == unit.max_hp
    assert unit.element_mods.get(Element.FIRE, 0) == plain.element_mods.get(Element.FIRE, 0) - 100
    assert dict(unit.gear.merged) == {"attr:str": 2, "max_hp": 12, "resist:fire": 100}


@pytest.mark.parametrize("attr", list(Attribute))
def test_all_six_attribute_affixes_exist_and_raise_their_attribute(attr: Attribute) -> None:
    """3H-1（08 8.24）：六種屬性詞條都有，部位同力量，範圍 1～4，合併進總屬性。"""
    lib = library()
    affix = lib.affixes[f"affix_attr_{attr.value}"]
    assert isinstance(affix, StatAffix)
    assert affix.attribute is attr
    assert affix.slots == lib.affixes["affix_attr_str"].slots
    assert (affix.value.min, affix.value.max) == (1, 4)  # type: ignore[union-attr]
    assert affix.name_zh == f"{attr.display_name} +{{n}}"
    plain = _unit({})
    unit = _unit({"ring_1": [(affix.id, 3)], "neck": [(affix.id, 3)]})
    # 同 id 遞減疊加：100%＋50%（rules/equipment.yaml）
    assert unit.attributes[attr] > plain.attributes[attr] + 3


def test_constitution_from_gear_also_raises_hp() -> None:
    lib = library()
    con = lib.affixes["affix_attr_con"]
    item = _item("ring_1", [])
    item = item.model_copy(update={"affixes": (EquippedAffix(affix=con, value=2),)})
    hero = spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter"))
    plain = _state(hero).units[U1]
    geared = _state(hero.model_copy(update={"equipment": Loadout(items=(item,))})).units[U1]
    per_con = lib.ruleset.core.hp_per_con_point
    assert geared.max_hp == plain.max_hp + 2 * per_con


def test_strength_from_gear_changes_attack_value() -> None:
    plain = give_turn(_state(spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")), "00"), U1)
    geared = give_turn(_state(_geared({"main_hand": [("affix_attr_str", 4)]}), "00"), U1)
    low = preview(plain, Attack(unit_id=U1, target_id=U2))
    high = preview(geared, Attack(unit_id=U1, target_id=U2))
    assert high.damage is not None and low.damage is not None
    assert high.damage.maximum > low.damage.maximum
    assert high.hit_chance is not None and low.hit_chance is not None
    assert high.hit_chance >= low.hit_chance


def test_fire_resist_reduces_fire_damage_modifier() -> None:

    rules = library().ruleset
    plain = _unit({})
    geared = _unit({"body": [("affix_resist_fire", 150)]})
    assert element_modifier_ppm(geared, Element.FIRE, rules) < element_modifier_ppm(
        plain, Element.FIRE, rules
    )


# ---------------------------------------------------------------------------
# 第 2 類 條件數值
# ---------------------------------------------------------------------------


def test_height_hit_only_from_high_ground() -> None:
    hero = _geared({"main_hand": [("affix_cond_height_hit", 1)]})
    high = _state(hero, "100\n000")
    flat = _state(hero)
    for state, expected in ((high, 1), (flat, 0)):
        unit, target = state.units[U1], state.units[U2]
        subject = Subject(target, target.xy)
        assert gear_hit_bonus(state, unit, subject) == expected
        assert mods.hit_bonus(state, unit, mods.ATTACK, subject) == expected


def test_still_defense_only_when_not_moved() -> None:
    unit = _unit({"body": [("affix_cond_still_defense", 200)]})
    rules = library().ruleset
    unit.moved_this_turn = False
    still = defense_value_permille(unit, rules)
    assert gear_defense_permille(unit) == 200
    unit.moved_this_turn = True
    assert gear_defense_permille(unit) == 0
    moved = defense_value_permille(unit, rules)
    assert still * 1000 == moved * 1200


def test_low_hp_damage_only_below_half() -> None:
    state = _state(_geared({"neck": [("affix_cond_low_hp_damage", 150)]}))
    unit, target = state.units[U1], state.units[U2]
    subject = Subject(target, target.xy)
    unit.hp = unit.max_hp // 2  # 剛好一半：不算低於
    assert gear_damage_permille(state, unit, subject) == 0
    assert mods.damage_permille(state, unit, mods.ATTACK, subject) == 1000
    unit.hp = unit.max_hp // 2 - 1
    assert gear_damage_permille(state, unit, subject) == 150
    assert mods.damage_permille(state, unit, mods.ATTACK, subject) == 1150


# ---------------------------------------------------------------------------
# 第 8 類 代價型
# ---------------------------------------------------------------------------


def test_glass_raises_damage_dealt_and_taken() -> None:
    state = _state(_geared({"neck": [("affix_cost_glass", None)]}))
    unit, target = state.units[U1], state.units[U2]
    subject = Subject(target, target.xy)
    assert mods.damage_permille(state, unit, mods.ATTACK, subject) == 1200
    assert gear_damage_taken_permille(unit) == 1100
    assert damage_taken_permille(state.ruleset, unit) == 1100
    assert damage_taken_permille(state.ruleset, target) == 1000


def _turn_start_events(state: BattleState, uid: UnitId) -> list[GearHpLost]:
    ctx = Ctx(state.clone())
    start_turn(ctx, uid)
    return [e for e in ctx.events if isinstance(e, GearHpLost)]


def test_blood_loses_hp_at_turn_start_but_never_kills() -> None:
    state = _state(_geared({"neck": [("affix_cost_blood", None)]}))
    lost = _turn_start_events(state, U1)
    assert [(e.amount, e.hp_after) for e in lost] == [(2, state.units[U1].hp - 2)]
    assert lost[0].affix_id == "affix_cost_blood"
    low = state.clone()
    low.units[U1].hp = 2
    assert [(e.amount, e.hp_after) for e in _turn_start_events(low, U1)] == [(1, 1)]
    low.units[U1].hp = 1
    assert _turn_start_events(low, U1) == []
    assert _turn_start_events(state, U2) == []  # 沒有裝備的單位不受影響


def test_blood_reduces_cooldown_with_floor_of_one() -> None:
    unit = _unit({"neck": [("affix_cost_blood", None)]})
    assert [gear_cooldown(unit, cd) for cd in (None, 0, 1, 2, 3)] == [None, 0, 1, 1, 2]
    plain = _unit({})
    assert gear_cooldown(plain, 3) == 3
    skill = library().skills["skill_whirlwind"]
    base = skill.cost.cooldown
    assert base is not None and base >= 2
    paid = pay_skill_cost(library().ruleset.core, unit, skill)
    assert paid.cooldown == base - 1 and unit.cooldowns[skill.id] == base - 1


def test_swift_adds_move_and_lowers_defense() -> None:
    plain = _unit({})
    unit = _unit({"feet": [("affix_cost_swift", None)]})
    assert unit.speed == plain.speed + 2
    unit.moved_this_turn = plain.moved_this_turn = False
    rules = library().ruleset
    assert gear_defense_permille(unit) == -150
    assert defense_value_permille(unit, rules) * 1000 == defense_value_permille(plain, rules) * 850


# ---------------------------------------------------------------------------
# 遞減疊加（8.21.5.3）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((16,), 16),
        ((16, 16), 24),  # 100 ＋ 50
        ((16, 16, 16), 28),  # 100 ＋ 50 ＋ 25
        ((16, 16, 16, 16), 28),  # 第 4 條起 0
        ((8, 16), 20),  # 大到小：16 ＋ 8 × 50%
        ((5, 5, 5), 8),  # 加總後才捨去：5 ＋ 2.5 ＋ 1.25 ＝ 8.75 → 8
    ],
)
def test_numeric_affixes_diminish(values: tuple[int, ...], expected: int) -> None:
    slots = ("head", "body", "hands", "feet")
    unit = _unit({slot: [("affix_max_hp", v)] for slot, v in zip(slots, values, strict=False)})
    assert dict(unit.gear.merged)["max_hp"] == expected


def test_ties_follow_slot_order() -> None:
    loadout = _loadout({"ring_2": [("affix_max_hp", 8)], "head": [("affix_max_hp", 8)]})
    gear = build_gear(loadout, library().ruleset.equipment)
    assert [(a.slot, a.weight_permille, a.rank) for a in gear.affixes] == [
        ("head", 1000, 0),
        ("ring_2", 500, 1),
    ]


def test_conditional_affixes_diminish_before_condition() -> None:
    state = _state(
        _geared(
            {
                "main_hand": [("affix_cond_height_hit", 1)],
                "ring_1": [("affix_cond_height_hit", 1)],
                "head": [("affix_cond_height_hit", 1)],
            }
        ),
        "100\n000",
    )
    unit, target = state.units[U1], state.units[U2]
    assert gear_hit_bonus(state, unit, Subject(target, target.xy)) == 1  # 1 ＋ 0.5 ＋ 0.25 → 1


def test_non_numeric_same_id_counts_once() -> None:
    loadout = _loadout(
        {"main_hand": [("affix_trig_kill_ap", None)], "neck": [("affix_trig_kill_ap", None)]}
    )
    gear = build_gear(loadout, library().ruleset.equipment)
    assert [a.weight_permille for a in gear.affixes] == [1000, 0]
    assert len(gear.active_affixes("trigger")) == 1
    assert gear.active_affixes("trigger")[0].slot == "main_hand"


def test_numeric_fourth_copy_is_inactive() -> None:
    slots = ("head", "body", "hands", "feet")
    gear = build_gear(
        _loadout({s: [("affix_max_hp", 4)] for s in slots}), library().ruleset.equipment
    )
    assert [a.weight_permille for a in gear.affixes] == [1000, 500, 250, 0]
    assert [a.active for a in gear.affixes] == [True, True, True, False]


# ---------------------------------------------------------------------------
# 硬上限
# ---------------------------------------------------------------------------


def test_damage_bonus_capped_at_50_percent_after_diminishing() -> None:
    state = _state(
        _geared(
            {
                "main_hand": [("affix_cost_glass", None), ("affix_cond_low_hp_damage", 150)],
                "neck": [("affix_cond_low_hp_damage", 150)],
                "ring_1": [("affix_cost_glass", None)],
            }
        )
    )
    unit, target = state.units[U1], state.units[U2]
    subject = Subject(target, target.xy)
    unit.hp = 1
    # 玻璃 200 ＋ 100、低血 150 ＋ 75 ＝ 525 → 截斷為 500
    assert gear_damage_permille(state, unit, subject) == 500
    assert mods.damage_permille(state, unit, mods.ATTACK, subject) == 1500
    unit.hp = unit.max_hp
    assert gear_damage_permille(state, unit, subject) == 300


def test_move_bonus_capped_at_two() -> None:
    plain = _unit({})
    unit = _unit({"feet": [("affix_cost_swift", None)], "body": [("affix_cost_swift", None)]})
    assert dict(unit.gear.uncapped)["move"] == 3
    assert dict(unit.gear.merged)["move"] == 2
    assert unit.speed == plain.speed + 2


def test_element_resist_capped_at_50_percent() -> None:
    hero = no_reactions("hero_fighter")
    near = hero.model_copy(update={"element_mods": {Element.FIRE: -400}})
    high = hero.model_copy(update={"element_mods": {Element.FIRE: -600}})
    ring = {"ring_1": [("affix_resist_fire", 150)]}
    for template, expected in ((near, -500), (high, -600)):
        s = spawn(Team.ALLY, (0, 0), template).model_copy(update={"equipment": _loadout(ring)})
        assert _state(s).units[U1].element_mods[Element.FIRE] == expected


def test_total_damage_reduction_still_floored_at_75_percent() -> None:

    rules = library().ruleset
    hero = no_reactions("hero_fighter").model_copy(
        update={"resist": dict.fromkeys(no_reactions().resist, 900)}
    )
    s = spawn(Team.ALLY, (0, 0), hero).model_copy(
        update={"equipment": _loadout({"ring_1": [("affix_resist_fire", 150)]})}
    )
    unit = _state(s).units[U1]
    assert element_modifier_ppm(unit, Element.FIRE, rules) == 250_000


def test_cap_helpers_for_later_segments() -> None:
    rules = library().ruleset
    assert cap_crit_range(rules, 16) == 18 and cap_crit_range(rules, 19) == 19
    assert [cap_ap_gain(rules, gained, 1) for gained in (0, 1, 2)] == [1, 0, 0]
    assert cap_ap_gain(rules, 0, 2) == 1
    assert [cap_cooldown(1, base, -2) for base in (0, 1, 2, 4)] == [0, 1, 1, 2]


def test_setup_rejects_illegal_loadout() -> None:

    lib = library()
    loadout = resolve_loadout(
        {
            "main_hand": "item_test_hammer",
            "neck": "item_test_amulet",
            "ring_1": "item_test_ring_fire",
        },
        lib.items,
        lib.affixes,
    )
    hero = spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter"), weapon="hammer")
    hero = hero.model_copy(update={"equipment": loadout})
    with pytest.raises(BattleSetupError, match="代價型"):
        _state(hero)


# ---------------------------------------------------------------------------
# 舊資料相容、序列化、預覽與檢視
# ---------------------------------------------------------------------------


def test_units_without_equipment_have_empty_gear() -> None:
    lib = library()
    setup = build_setup(lib, "test_flat_6x6", ["hero_fighter"], ["bandit"])
    assert all(s.equipment == Loadout() for s in setup.units)
    state = start_battle(setup, 1)
    for unit in state.units.values():
        assert unit.gear.items == () and unit.gear.bonuses == () and unit.gear.merged == ()


def test_old_build_with_only_weapon_behaves_the_same() -> None:
    """主手放一件沒有詞條的同一把武器 ＝ 舊資料只有 ``weapon``：整場事件完全相同。"""
    lib = library()
    setup = build_setup(lib, "test_flat_6x6", ["hero_fighter"], ["bandit", "bandit"])
    bare = run_battle(setup, 5)
    hero = setup.units[0]
    item = ItemDef(id="item_bare_sword", name_zh="長劍", slot_type="weapon", weapon=hero.weapon.id)
    loadout = Loadout(items=(EquippedItem(slot="main_hand", item=item),))
    units = (hero.model_copy(update={"equipment": loadout}), *setup.units[1:])
    equipped = run_battle(setup.model_copy(update={"units": units}), 5)
    assert [e.model_dump() for e in equipped.events] == [e.model_dump() for e in bare.events]


def test_gear_state_round_trips_through_json() -> None:
    state = _state(
        _geared({"neck": [("affix_cost_blood", None)], "head": [("affix_cond_still_defense", 150)]})
    )
    again = state_from_json(state_to_json(state))
    assert again.units[U1].gear == state.units[U1].gear
    assert state_to_json(again) == state_to_json(state)


def test_preview_includes_gear_hit_and_damage() -> None:
    plain = give_turn(
        _state(spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")), "100\n000"), U1
    )
    geared_hero = _geared(
        {"main_hand": [("affix_cond_height_hit", 1)], "neck": [("affix_cost_glass", None)]}
    )
    geared = give_turn(_state(geared_hero, "100\n000"), U1)
    for state in (plain, geared):  # 讓目標站到相鄰的低處
        state.units[U2].pos = state.units[U2].pos.model_copy(update={"x": 1})
    low = preview(plain, Attack(unit_id=U1, target_id=U2))
    high = preview(geared, Attack(unit_id=U1, target_id=U2))
    assert low.hit_chance is not None and high.hit_chance is not None
    assert high.hit_chance > low.hit_chance
    assert low.damage is not None and high.damage is not None
    assert high.damage.maximum > low.damage.maximum


def test_unit_view_lists_equipment() -> None:
    lib = library()
    setup = build_setup(lib, "test_flat_6x6", ["gear_tester"], ["bandit"])
    state = start_battle(setup, 1)
    hero = next(u for u in project_for(state, Team.ENEMY).units if u.template_id == "gear_tester")
    slots = [e.slot for e in hero.equipment]
    assert slots[0] == "main_hand" and len(slots) == 9
    sword = hero.equipment[0]
    assert sword.name_zh == "試煉長劍" and sword.slot_zh == "主手"
    texts = {a.text_zh for a in sword.affixes}
    assert texts == {"力量 +2", "站在高處時命中 +1"}
    helm = next(e for e in hero.equipment if e.slot == "head")
    assert "火焰抗性 +10%" in {a.text_zh for a in helm.affixes}
    foe = next(u for u in project_for(state, Team.ENEMY).units if u.template_id == "bandit")
    assert foe.equipment == ()


def test_gear_battle_log_json_and_replay(tmp_path: Path) -> None:
    log = tmp_path / "gear.json"
    args = ["battle", "--map", "test_flat_6x6", "--allies", "gear_tester"]
    args += ["--enemies", "bandit,bandit", "--seed", "7", "--log-json", str(log)]
    assert cli_main(args) == 0
    text = log.read_text(encoding="utf-8")
    assert '"gear_hp_lost"' in text and '"item_test_sword"' in text
    assert cli_main(["battle", "replay", str(log)]) == 0
