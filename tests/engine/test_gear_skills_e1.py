"""裝備授予技能一般化（Phase E1，08 8.28，#174）。

用測試內容：把 ``affix_act_grapple`` 複製成授予別的技能的詞條（content 裡沒有這樣的詞條）。
涵蓋：四類技能都能授予、不佔欄、普攻精通的空格不算它們、反應共用每輪 1 次、同一個技能從兩處
拿到（主動技兩招冷卻分開、反應兩條都列）、修正技的數字遞減與全身上限的先後、非數字效果各自發動、
重播。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7
from trpg.content.equipment import (
    ActionAffix,
    EquippedAffix,
    EquippedItem,
    ItemDef,
    Loadout,
)
from trpg.content.library import ContentLibrary, _affix_reference_problems
from trpg.content.skill_rules import budget_rule_problems
from trpg.content.skills import SkillDef
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import Attack, BattleState, Move, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, ReactionTriggered
from trpg.engine.modifiers import (
    ATTACK,
    damage_permille,
    empty_active_slots,
    heal_permille,
    skill_use,
)
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import UnitState, state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.library_check import gear_grant_violations

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")

REACTION = "skill_parting_slash"  # 反應技（近戰，敵人離開相鄰格）
MODIFIER = "skill_attack_mastery"  # 修正技（普攻精通：主動欄每空 1 格普攻 +5%）
PASSIVE = "skill_bloodlust"  # 被動（擊倒時治療）
ACTIVE = "skill_gear_grapple"  # 主動（鉤爪）


def grant(skill_id: str, affix_id: str = "affix_t_grant") -> EquippedAffix:
    """測試用詞條：授予 ``skill_id``。"""
    base = library().affixes["affix_act_grapple"]
    assert isinstance(base, ActionAffix)
    every = tuple(dict.fromkeys(SLOT_TYPE_OF.values()))
    update = {"id": affix_id, "skill": skill_id, "slots": every, "item_tags": {}}
    return EquippedAffix(affix=base.model_copy(update=update))


def loadout(slots: Mapping[str, Sequence[str]], *, same_id: bool = False) -> Loadout:
    """``slots``：欄位 → 這件物品授予的技能。``same_id``：每件的詞條 ID 一樣（同一條詞條出現在兩件
    裝備上）。"""
    order = list(SLOT_TYPE_OF)
    items: list[EquippedItem] = []
    for slot in sorted(slots, key=order.index):
        slot_type = SLOT_TYPE_OF[slot]
        affixes = tuple(
            grant(s, f"affix_t_{i}" if same_id else f"affix_t_{slot}_{i}")
            for i, s in enumerate(slots[slot])
        )
        item = ItemDef.model_validate(
            {
                "id": f"item_t_{slot}",
                "name_zh": f"測試{slot}",
                "slot_type": slot_type,
                "weapon": "one_handed_sword" if slot_type == "weapon" else None,
                "affixes": [{"affix": a.affix.id, "value": None} for a in affixes],
            }
        )
        items.append(EquippedItem(slot=slot, item=item, affixes=affixes))  # type: ignore[arg-type]
    return Loadout(items=tuple(items))


def hero(
    slots: Mapping[str, Sequence[str]],
    skills: Sequence[str] | None = None,
    *,
    react: bool = False,
    same_id: bool = False,
    xy: tuple[int, int] = (0, 0),
) -> UnitSpawn:
    base = no_reactions("hero_fighter")
    if react:
        base = base.model_copy(update={"reactions": None})
    if skills is not None:
        base = base.model_copy(update={"skills": tuple(skills)})
    gear = loadout(slots, same_id=same_id)
    return spawn(Team.ALLY, xy, base).model_copy(update={"equipment": gear})


def scene(
    slots: Mapping[str, Sequence[str]],
    skills: Sequence[str] | None = None,
    *,
    react: bool = False,
    foe: tuple[int, int] = (3, 0),
    seed: int = 0,
    same_id: bool = False,
    xy: tuple[int, int] = (0, 0),
    extra: Sequence[SkillDef] = (),
) -> BattleState:
    m = make_map(FLAT7, ally=[xy], enemy=[foe])
    enemy = spawn(Team.ENEMY, foe, no_reactions("bandit", max_hp=999))
    me_ = hero(slots, skills, react=react, same_id=same_id, xy=xy)
    return give_turn(make_state(m, [me_, enemy], seed=seed, skills=extra), U1)


def me(state: BattleState) -> UnitState:
    return state.units[U1]


# ---------------------------------------------------------------------------
# 第 2 項：四類都能授予、不佔欄
# ---------------------------------------------------------------------------


def test_all_four_kinds_can_be_granted_but_not_stances() -> None:
    lib = library()
    keyword_ids = frozenset(lib.ruleset.keywords.ids())

    def problems(skill_id: str) -> list[str]:
        affix = grant(skill_id).affix
        return _affix_reference_problems(affix, lib.ruleset, lib.weapons, keyword_ids)

    for skill_id in (ACTIVE, REACTION, MODIFIER, PASSIVE):
        assert problems(skill_id) == [], skill_id
    stance = next(s.id for s in lib.ruleset.skills.skills if s.kind == "stance")
    assert any("必須是主動、反應、修正、被動技" in p for p in problems(stance))


def test_granted_skills_take_no_slot_even_when_every_slot_is_full() -> None:
    lib = library()
    slots = lib.ruleset.core.skill_slots
    actives = [
        s.id
        for s in lib.ruleset.skills.skills
        if s.kind == "active" and s.slot_kind == "active" and s.weapon_req in {"any", "melee"}
    ][: slots.active]
    full = [*actives, "skill_reflex_ward", MODIFIER, PASSIVE, "skill_eagle_eye"]
    state = scene({"main_hand": [ACTIVE], "off_hand": [REACTION, "skill_ember_brand"]}, full)
    unit = me(state)
    assert unit.gear_skills == (ACTIVE, REACTION, "skill_ember_brand")
    assert unit.skills == (*full, ACTIVE, REACTION, "skill_ember_brand")


def test_granted_active_is_usable_and_listed() -> None:
    state = scene({"main_hand": [ACTIVE]})
    assert ACTIVE in me(state).all_skills
    assert any(isinstance(a, UseSkill) and a.skill_id == ACTIVE for a in legal_actions(state))


def test_empty_active_slots_ignore_gear_granted_actives() -> None:
    """改前：裝備給的主動技被算成佔欄（空格少 1）；改後不算。"""
    plain = scene({}, [MODIFIER])
    geared = scene({"main_hand": [ACTIVE]}, [MODIFIER])
    total = library().ruleset.core.skill_slots.active
    assert empty_active_slots(plain, me(plain)) == total
    assert empty_active_slots(geared, me(geared)) == total


def test_granted_modifier_and_passive_take_effect() -> None:
    state = scene({"neck": [MODIFIER, PASSIVE]}, [])
    unit = me(state)
    assert {MODIFIER, PASSIVE} <= set(unit.all_skills)
    assert empty_active_slots(state, unit) == library().ruleset.core.skill_slots.active


# ---------------------------------------------------------------------------
# 第 3 項：同一個技能從兩處拿到
# ---------------------------------------------------------------------------

COPY = f"{ACTIVE}~2"


def always(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 1) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def grapples(state: BattleState) -> list[UseSkill]:
    return [
        a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id.startswith(ACTIVE)
    ]


@pytest.mark.parametrize("same_id", [False, True])
def test_one_active_from_two_items_is_two_moves(same_id: bool) -> None:
    """兩件裝備都給同一招（詞條 ID 相同也一樣，8.28 第 4 點是 8.21.5.3 的例外）。"""
    state = scene({"main_hand": [ACTIVE], "off_hand": [ACTIVE]}, [], same_id=same_id)
    unit = me(state)
    assert unit.gear_skills == (ACTIVE, COPY)
    assert state.ruleset.skill_def(COPY).id == COPY
    assert state.ruleset.skill_def(COPY).name_zh == state.ruleset.skill_def(ACTIVE).name_zh
    assert {a.skill_id for a in grapples(state)} == {ACTIVE, COPY}


def test_a_granted_copy_of_a_learned_move_has_its_own_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [ACTIVE]}, [ACTIVE], foe=(3, 0))
    assert me(state).skills == (ACTIVE, COPY) and me(state).gear_skills == (COPY,)
    first = next(a for a in grapples(state) if a.skill_id == ACTIVE)
    after = resolve(state, first).state
    cooldown = state.ruleset.skill_def(ACTIVE).cost.cooldown
    assert after.units[U1].cooldowns.get(ACTIVE) == cooldown
    assert COPY not in after.units[U1].cooldowns
    assert {a.skill_id for a in grapples(after)} == {COPY}
    second = resolve(after, grapples(after)[0]).state
    assert second.units[U1].cooldowns.get(COPY) == cooldown


def test_copies_round_trip_through_json() -> None:
    state = scene({"main_hand": [ACTIVE], "off_hand": [ACTIVE]}, [ACTIVE])
    back = state_from_json(state_to_json(state))
    assert back.units[U1].skills == state.units[U1].skills
    assert back.units[U1].gear_skills == (COPY, f"{ACTIVE}~3")


def test_plain_units_do_not_serialize_gear_skills() -> None:
    state = scene({}, [ACTIVE])
    assert "gear_skills" not in state_to_json(state)


def test_two_copies_of_a_reaction_are_both_listed_but_fire_once_per_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(
        {"main_hand": [REACTION], "off_hand": [REACTION]}, [], react=True, xy=(3, 3), foe=(4, 3)
    )
    keys = [r.reaction for r in me(state).reactions]
    assert REACTION in keys and f"{REACTION}~2" in keys
    foe = give_turn(state, U2)
    path = (Pos(x=4, y=3), Pos(x=5, y=3), Pos(x=6, y=3))
    result = resolve(foe, Move(unit_id=U2, path=path))
    fired = [e for e in result.events if isinstance(e, ReactionTriggered) and e.unit_id == U1]
    assert len(fired) == 1  # 每輪 1 次，和藉機攻擊等其他反應共用
    assert result.state.units[U1].reactions_used == 1


# ---------------------------------------------------------------------------
# 第 6 項：顯示
# ---------------------------------------------------------------------------


def test_views_name_the_item_for_skills_and_reactions() -> None:
    state = scene({"main_hand": [ACTIVE, REACTION], "off_hand": [ACTIVE]}, [], react=True)
    view = next(u for u in project_for(state, Team.ALLY).units if u.id == U1)
    by_key = {g.skill_id: g for g in view.gear_skills}
    assert set(by_key) == {ACTIVE, COPY, REACTION}
    assert set(by_key) <= set(view.skills)
    assert by_key[COPY].copy_of == ACTIVE and by_key[ACTIVE].copy_of is None
    assert (by_key[REACTION].kind, by_key[ACTIVE].kind) == ("reaction", "active")
    assert by_key[COPY].slot_zh and by_key[COPY].item_name_zh == "測試off_hand"
    rule = next(r for r in view.reaction_rules if r.reaction == REACTION)
    assert rule.gear_source_zh == f"{by_key[REACTION].slot_zh}：測試main_hand"
    assert all(r.gear_source_zh == "" for r in view.reaction_rules if r.reaction != REACTION)


# ---------------------------------------------------------------------------
# 第 5 項：修正技重複——數字遞減後再套全身上限，非數字各自發動
# ---------------------------------------------------------------------------


def modifier(skill_id: str, change: Mapping[str, object]) -> SkillDef:
    """測試專用修正技（普攻的改變 ``change``）。"""
    base = library().skills[MODIFIER].model_dump(mode="json")
    rule = {"applies_to": {"actions": ["attack"]}, "change": dict(change)}
    data = {**base, "id": skill_id, "modifiers": [rule], "exclusive_group": None}
    return SkillDef.model_validate(data)


HEAVY = modifier("skill_t_heavy", {"damage_permille": 300})
MENDING = SkillDef.model_validate(
    {
        **library().skills[MODIFIER].model_dump(mode="json"),
        "id": "skill_t_mending",
        "exclusive_group": None,
        "modifiers": [{"applies_to": {"all_skills": True}, "change": {"heal_permille": 150}}],
    }
)
SEARING = modifier(
    "skill_t_searing",
    {
        "on_hit_effects": [
            {"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"}
        ]
    },
)


def attack_permille(state: BattleState) -> int:
    foe = state.units[U2]
    return damage_permille(state, me(state), ATTACK, Subject(foe, foe.xy))


@pytest.mark.parametrize(
    ("gear", "expected"),
    [
        ({}, 1300),  # 只有自己學的 1 份
        ({"neck": [HEAVY.id]}, 1450),  # 300 ＋ 300×50%
        ({"neck": [HEAVY.id], "ring_1": [HEAVY.id]}, 1500),  # 300＋150＋75＝525 → 上限 +50%
    ],
)
def test_repeated_modifier_numbers_diminish_then_hit_the_cap(
    gear: Mapping[str, Sequence[str]], expected: int
) -> None:
    state = scene(gear, [HEAVY.id], extra=[HEAVY])
    assert attack_permille(state) == expected


def test_diminishing_happens_before_the_cap() -> None:
    """兩份 +300 遞減後 +450，沒到上限；如果先截上限（各 300）再加，會變成 +500。"""
    state = scene({"neck": [HEAVY.id]}, [HEAVY.id], extra=[HEAVY])
    assert (
        attack_permille(state)
        == 1450
        < 1000 + library().ruleset.equipment.caps.damage_bonus_permille
    )


def test_three_copies_of_a_heal_modifier_add_one_and_three_quarters() -> None:
    state = scene({"neck": [MENDING.id], "ring_1": [MENDING.id]}, [MENDING.id], extra=[MENDING])
    any_skill = skill_use(state.ruleset.skill_def(ACTIVE))
    assert heal_permille(state, me(state), any_skill) == 1000 + 150 + 75 + 37  # 37.5 捨去


def test_non_numeric_parts_fire_once_per_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)

    def fire_hits(gear: Mapping[str, Sequence[str]]) -> int:
        state = scene(gear, [SEARING.id], foe=(1, 0), extra=[SEARING])
        result = resolve(state, Attack(unit_id=U1, target_id=U2))
        return sum(1 for e in result.events if isinstance(e, DamageDealt) and e.element == "fire")

    assert fire_hits({}) == 1
    assert fire_hits({"neck": [SEARING.id]}) == 2


# ---------------------------------------------------------------------------
# 第 7 項：AI 與重播
# ---------------------------------------------------------------------------


def test_ai_ranks_both_copies_and_falls_back_to_the_second_one() -> None:
    state = scene({"main_hand": [ACTIVE], "off_hand": [ACTIVE]}, [], foe=(4, 0))
    ai = UtilityAI(library().ai_profiles, override="brute")
    ranked = {s.action.skill_id for s in ai.rank(state) if isinstance(s.action, UseSkill)}
    assert {ACTIVE, COPY} <= ranked
    state.units[U1].cooldowns[ACTIVE] = 2  # 第一份冷卻中：第二份照樣在候選裡
    ranked = {s.action.skill_id for s in ai.rank(state) if isinstance(s.action, UseSkill)}
    assert COPY in ranked and ACTIVE not in ranked


def _geared_setup() -> BattleSetup:
    lib = library()
    setup = build_setup(lib, "test_flat_6x6", ["hero_fighter"], ["bandit", "bandit"])
    gear = loadout(
        {"main_hand": [ACTIVE, REACTION], "off_hand": [ACTIVE], "neck": [HEAVY.id, PASSIVE]}
    )
    hero = setup.units[0].model_copy(update={"equipment": gear})
    ruleset = setup.ruleset.with_skills([HEAVY])
    return setup.model_copy(update={"units": (hero, *setup.units[1:]), "ruleset": ruleset})


def test_battles_with_granted_skills_replay_identically() -> None:
    setup = _geared_setup()
    first = run_battle(setup, 11)
    second = run_battle(setup, 11)
    dump = [e.model_dump() for e in first.events]
    assert dump == [e.model_dump() for e in second.events]
    again = replay(setup, 11, first.actions)
    assert [e.model_dump() for e in again.events] == dump
    assert state_to_json(again.state) == state_to_json(first.state)
    hero = first.state.units[U1]
    assert sorted(hero.gear_skills) == sorted([ACTIVE, COPY, REACTION, HEAVY.id, PASSIVE])


# ---------------------------------------------------------------------------
# 第 4 項：授予技能的預算窗（一律照 gear_skill_tier 那一階）
# ---------------------------------------------------------------------------


def _granting_library(skill_id: str, tier: int | None = None) -> ContentLibrary:
    lib = library()
    affixes = dict(lib.affixes)
    affixes["affix_t_grant"] = grant(skill_id).affix
    budget = lib.budget if tier is None else lib.budget.model_copy(update={"gear_skill_tier": tier})
    return replace(lib, affixes=affixes, budget=budget)


def test_the_gear_tier_defaults_to_one_and_is_bounded_by_the_tier_count() -> None:
    lib = library()
    assert lib.budget.gear_skill_tier == 1
    tiers = lib.ruleset.core.skill_limits.tiers
    too_high = lib.budget.model_copy(update={"gear_skill_tier": tiers + 1})
    assert any("gear_skill_tier" in p for p in budget_rule_problems(too_high, lib.ruleset.core))
    assert budget_rule_problems(lib.budget, lib.ruleset.core) == []


def test_current_content_has_no_gear_tier_violations() -> None:
    assert gear_grant_violations(library()) == []


def test_a_higher_tier_skill_granted_by_gear_is_checked_in_the_tier_one_window() -> None:
    skill = library().skills["skill_arcane_blade"]  # 2 階
    assert skill.tier == 2 and skill_budget(skill, library()).ok
    found = gear_grant_violations(_granting_library(skill.id))
    assert [(v.skill_id, v.rule) for v in found] == [(skill.id, "budget.gear_tier")]
    assert "1 階" in found[0].message
    assert gear_grant_violations(_granting_library(skill.id, tier=2)) == []
