"""E6-b1 第 2 項：招牌同時 3 個（08 8.27、8.30 第 4、5、10 點，8.29 E2 第 1 點，#180）。

用測試內容：現有詞條都沒有標招牌，這裡把詞條複製一份、標上 ``signature`` 再穿上。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import TypeAdapter

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_attack_shape_e5 import LINE_SKILL, line_skill
from tests.engine.test_unit_rules_e2 import loadout as e2_loadout
from tests.engine.test_unit_rules_e2 import terrain
from trpg.content.equipment import AffixDef, EquippedAffix, Loadout, chosen_key
from trpg.content.library import Ruleset
from trpg.engine.gear.core import build_gear
from trpg.engine.gear.limits import limit_gear, whole_no_effect
from trpg.engine.gear.state import GearState
from trpg.engine.reshape_gate import gate_key
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

U1 = UnitId("unit_0001")
_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)

SWORD = "one_handed_sword"
BOW = "bow"


def sig(affix_id: str, kind: str = "action") -> EquippedAffix:
    """內容裡的詞條 ``affix_id`` 標上招牌 ``kind``。"""
    affix = library().affixes[affix_id].model_copy(update={"signature": kind})
    return EquippedAffix(affix=affix)


def sig_terrain(affix_id: str, **params: Any) -> EquippedAffix:
    """測試用地形規則招牌。"""
    plain = terrain(affix_id, "測試地形", **params)
    return EquippedAffix(affix=plain.affix.model_copy(update={"signature": "terrain"}))


def grant(skill: str, affix_id: str, kind: str = "behavior") -> EquippedAffix:
    data = {
        "id": affix_id,
        "name_zh": "測試授予",
        "category": "action",
        "skill": skill,
        "slots": ["weapon", "offhand", "head", "body", "hands", "feet", "neck", "ring"],
        "signature": kind,
    }
    return EquippedAffix(affix=_ADAPTER.validate_python(data))


GRAPPLE = "affix_act_grapple"
SMOKE = "affix_act_smoke"
WALL = "affix_act_shield_wall"
GUARD = "affix_react_guard_ally"
RANGED_BLOCK = "affix_react_ranged_block"


def limited(
    slots: Mapping[str, Sequence[EquippedAffix]],
    *,
    chosen: tuple[str, ...] = (),
    race: str | None = None,
    weapon: str = SWORD,
    ruleset: Ruleset | None = None,
) -> GearState:
    rules = ruleset or library().ruleset
    wear: Loadout = e2_loadout(slots).model_copy(update={"chosen": chosen})
    gear = build_gear(wear, rules.equipment)
    return limit_gear(gear, wear, rules, race=race, weapon=library().weapons[weapon])


def states(gear: GearState) -> list[tuple[str, str, bool, str | None]]:
    """標了招牌的詞條：（欄位, 詞條 id, 生效, 標灰原因），依欄位順序。"""
    return [
        (a.slot, a.affix.id, a.active, a.limited_by)
        for a in sorted(gear.affixes, key=lambda a: (a.slot, a.affix.id))
        if a.affix.signature is not None
    ]


def active_ids(gear: GearState) -> list[tuple[str, str]]:
    return sorted((a.slot, a.affix.id) for a in gear.affixes if a.active)


FOUR = {
    "main_hand": [sig(GRAPPLE)],
    "off_hand": [sig(SMOKE)],
    "body": [sig(GUARD, "reaction")],
    "neck": [sig(RANGED_BLOCK, "reaction")],
}


# ---------------------------------------------------------------------------
# 超過 3 個：照部位順序／玩家的勾選
# ---------------------------------------------------------------------------


def test_four_signatures_grey_the_last_by_slot_order() -> None:
    gear = limited(FOUR)
    greyed = [(s, i) for s, i, active, _ in states(gear) if not active]
    assert greyed == [("neck", RANGED_BLOCK)]
    assert [a.limited_by for a in gear.affixes if not a.active] == ["signature"]


def test_three_signatures_are_all_active() -> None:
    three = {k: v for k, v in FOUR.items() if k != "neck"}
    assert all(active for _, _, active, _ in states(limited(three)))


def test_unsigned_affixes_do_not_use_slots() -> None:
    plain = {**FOUR, "neck": [EquippedAffix(affix=library().affixes[RANGED_BLOCK])]}
    gear = limited(plain)
    assert all(a.active for a in gear.affixes)


def test_the_players_choice_is_kept() -> None:
    chosen = (chosen_key("neck", RANGED_BLOCK),)
    gear = limited(FOUR, chosen=chosen)
    greyed = [(s, i) for s, i, active, _ in states(gear) if not active]
    assert greyed == [("body", GUARD)]  # 勾了項鍊，沒勾的裡面排最後的是身體


def test_choosing_three_keeps_exactly_those() -> None:
    chosen = tuple(chosen_key(s, i) for s, i in (("neck", RANGED_BLOCK), ("body", GUARD)))
    chosen += (chosen_key("off_hand", SMOKE),)
    gear = limited(FOUR, chosen=chosen)
    greyed = [(s, i) for s, i, active, _ in states(gear) if not active]
    assert greyed == [("main_hand", GRAPPLE)]


def test_greyed_signature_grants_nothing_in_battle() -> None:
    """建立單位時套用：標灰的新動作不會出現在技能列；非玩家（敵人）一樣照部位順序。"""
    five = {
        "main_hand": [grant("skill_gear_grapple", "affix_t_a", "action")],
        "off_hand": [grant("skill_gear_smoke_bomb", "affix_t_b", "action")],
        "body": [grant("skill_gear_shield_wall", "affix_t_c", "action")],
        "neck": [grant("skill_gear_grapple", "affix_t_d", "action")],
        "ring_1": [grant("skill_gear_smoke_bomb", "affix_t_e", "action")],
    }
    for team in (Team.ALLY, Team.ENEMY):
        unit = _battle(five, team=team).units[U1]
        assert set(unit.gear_skills) == {
            "skill_gear_grapple",
            "skill_gear_smoke_bomb",
            "skill_gear_shield_wall",
        }
        greyed = sorted(a.slot for a in unit.gear.affixes if a.limited_by == "signature")
        assert greyed == ["neck", "ring_1"]
    chosen = (chosen_key("ring_1", "affix_t_e"),)
    wear = e2_loadout(five).model_copy(update={"chosen": chosen})
    unit = _battle(five, team=Team.ALLY, wear=wear).units[U1]
    greyed = sorted(a.slot for a in unit.gear.affixes if a.limited_by == "signature")
    assert greyed == ["body", "neck"]
    assert "skill_gear_shield_wall" not in unit.skills


def _battle(
    slots: Mapping[str, Sequence[EquippedAffix]], *, team: Team, wear: Loadout | None = None
) -> BattleState:
    m = make_map(FLAT7, None, ally=[(3, 3)], enemy=[(6, 6)])
    me = spawn(team, (3, 3), no_reactions("hero_fighter", max_hp=200))
    me = me.model_copy(update={"equipment": wear or e2_loadout(slots)})
    other = Team.ENEMY if team is Team.ALLY else Team.ALLY
    return give_turn(make_state(m, [me, spawn(other, (6, 6), no_reactions(max_hp=200))]), U1)


# ---------------------------------------------------------------------------
# 怎麼算名額
# ---------------------------------------------------------------------------


def test_same_granted_skill_stacks_and_each_copy_uses_a_slot() -> None:
    same = {
        "main_hand": [sig(GRAPPLE)],
        "off_hand": [sig(GRAPPLE)],
        "hands": [sig(GRAPPLE)],
        "neck": [sig(SMOKE)],
    }
    gear = limited(same)
    assert [(s, a) for s, _, a, _ in states(gear)] == [
        ("hands", True),
        ("main_hand", True),
        ("neck", False),
        ("off_hand", True),
    ]
    state = _battle(same, team=Team.ALLY)
    unit = state.units[U1]
    assert {"skill_gear_grapple", "skill_gear_grapple~2", "skill_gear_grapple~3"} <= set(
        unit.skills
    )
    assert "skill_gear_smoke_bomb" not in unit.skills


def test_same_terrain_rule_counts_once() -> None:
    ice = {"rule": "slip_immunity", "surfaces": ["ice"]}
    same = {
        "main_hand": [sig(GRAPPLE)],
        "off_hand": [sig(SMOKE)],
        "feet": [sig_terrain("affix_t_ice", **ice)],
        "neck": [sig_terrain("affix_t_ice", **ice)],
    }
    gear = limited(same)
    assert not any(a.limited_by for a in gear.affixes)
    assert [a.active for a in gear.affixes if a.affix.id == "affix_t_ice"] == [True, False]


def test_terrain_fully_covered_by_race_uses_no_slot() -> None:
    """矮人（冰上不滑）穿「冰上不滑」的招牌：整條沒效果，不佔名額（8.29 E2 第 1 點）。"""
    slots = {**FOUR, "feet": [sig_terrain("affix_t_ice", rule="slip_immunity", surfaces=["ice"])]}
    slots.pop("neck")
    gear = limited(slots, race="dwarf")
    assert not any(a.limited_by for a in gear.affixes)
    # 沒有種族時它有效果，就佔名額：排在最後的腳被標灰
    gear = limited(slots)
    assert [(a.slot, a.limited_by) for a in gear.affixes if a.limited_by] == [("feet", "signature")]


def test_terrain_partly_covered_by_race_still_uses_a_slot() -> None:
    both = sig_terrain("affix_t_both", rule="slip_immunity", surfaces=["ice", "water"])
    slots = {
        "main_hand": [sig(GRAPPLE)],
        "off_hand": [sig(SMOKE)],
        "body": [sig(GUARD, "reaction")],
    }
    gear = limited({**slots, "feet": [both]}, race="dwarf")
    assert [(a.slot, a.limited_by) for a in gear.affixes if a.limited_by] == [("feet", "signature")]


def test_freed_terrain_is_recounted_after_its_cover_is_greyed() -> None:
    """腳的地形規則完全蓋過項鍊那條（項鍊不佔名額）；腳因為超過名額被標灰後，項鍊那條就有效果、
    要佔名額，也被標灰。"""
    cover = sig_terrain("affix_t_both", rule="slip_immunity", surfaces=["ice", "water"])
    covered = sig_terrain("affix_t_ice", rule="slip_immunity", surfaces=["ice"])
    slots = {
        "main_hand": [sig(GRAPPLE)],
        "off_hand": [sig(SMOKE)],
        "body": [sig(GUARD, "reaction")],
        "feet": [cover],
        "neck": [covered],
    }
    gear = limited(slots)
    assert [(a.slot, a.limited_by) for a in gear.affixes if a.limited_by] == [
        ("feet", "signature"),
        ("neck", "signature"),
    ]


def test_attack_shape_that_cannot_apply_uses_no_slot() -> None:
    """普攻變形拿著弓、或過不了預算閘門：整條沒效果，不佔名額；拿劍而且過閘門時照佔（8.29 E5
    第 3 點、8.30 第 10 點）。"""
    blocked = make_setup(
        make_map(FLAT7, None, ally=[(3, 3)], enemy=[(6, 6)]),
        [
            spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (6, 6), no_reactions()),
        ],
        skills=[line_skill()],
    ).ruleset
    rules = blocked.model_copy(update={"reshape_gates": {gate_key(LINE_SKILL, "attack"): 800}})
    slots = {
        "main_hand": [grant(LINE_SKILL, "affix_t_line")],
        "off_hand": [sig(SMOKE)],
        "body": [sig(GUARD, "reaction")],
        "neck": [sig(RANGED_BLOCK, "reaction")],
    }
    wear = e2_loadout(slots)
    gear = build_gear(wear, rules.equipment)
    line = next(i for i, a in enumerate(gear.affixes) if a.affix.id == "affix_t_line")
    assert line in whole_no_effect(rules, gear, None, library().weapons[BOW])
    assert line not in whole_no_effect(rules, gear, None, library().weapons[SWORD])
    assert line in whole_no_effect(blocked, gear, None, library().weapons[SWORD])
    with_bow = limited(slots, weapon=BOW, ruleset=rules)
    assert not any(a.limited_by for a in with_bow.affixes)
    with_sword = limited(slots, weapon=SWORD, ruleset=rules)
    assert [(a.slot, a.limited_by) for a in with_sword.affixes if a.limited_by] == [
        ("neck", "signature")
    ]


def test_rule_greyed_by_the_rule_cap_uses_no_slot() -> None:
    rules_four = {
        "main_hand": [sig(GRAPPLE)],
        "off_hand": [sig(SMOKE)],
        "neck": [sig("affix_rule_fire_mends", "rule")],
        "ring_1": [sig("affix_rule_bleeding_wake", "rule")],
    }
    gear = limited(rules_four)
    assert [(a.slot, a.limited_by) for a in gear.affixes if a.limited_by] == [("ring_1", "rule")]


def test_limits_are_deterministic() -> None:
    assert limited(FOUR) == limited(FOUR)
