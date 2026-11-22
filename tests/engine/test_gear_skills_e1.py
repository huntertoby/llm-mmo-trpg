"""裝備授予技能一般化（Phase E1，08 8.28，#174）。

用測試內容：把 ``affix_act_grapple`` 複製成授予別的技能的詞條（content 裡沒有這樣的詞條）。
涵蓋：四類技能都能授予、不佔欄、普攻精通的空格不算它們、反應共用每輪 1 次、同一個技能從兩處
拿到（主動技兩招冷卻分開、反應兩條都列）、修正技的數字遞減與全身上限的先後、非數字效果各自發動、
重播。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

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
    SLOT_TYPE_OF,
    ActionAffix,
    EquippedAffix,
    EquippedItem,
    ItemDef,
    Loadout,
)
from trpg.content.library import _affix_reference_problems
from trpg.engine import BattleState, Move, UseSkill, legal_actions, resolve
from trpg.engine.events import ReactionTriggered
from trpg.engine.modifiers import empty_active_slots
from trpg.engine.setup import UnitSpawn
from trpg.engine.state import UnitState, state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

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
) -> BattleState:
    m = make_map(FLAT7, ally=[xy], enemy=[foe])
    enemy = spawn(Team.ENEMY, foe, no_reactions("bandit", max_hp=999))
    me_ = hero(slots, skills, react=react, same_id=same_id, xy=xy)
    return give_turn(make_state(m, [me_, enemy], seed=seed), U1)


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
