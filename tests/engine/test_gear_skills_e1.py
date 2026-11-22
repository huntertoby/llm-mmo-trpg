"""裝備授予技能一般化（Phase E1，08 8.28，#174）。

用測試內容：把 ``affix_act_grapple`` 複製成授予別的技能的詞條（content 裡沒有這樣的詞條）。
涵蓋：四類技能都能授予、不佔欄、普攻精通的空格不算它們、反應共用每輪 1 次、同一個技能從兩處
拿到（主動技兩招冷卻分開、反應兩條都列）、修正技的數字遞減與全身上限的先後、非數字效果各自發動、
重播。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

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
from trpg.engine import BattleState, UseSkill, legal_actions
from trpg.engine.modifiers import empty_active_slots
from trpg.engine.setup import UnitSpawn
from trpg.engine.state import UnitState
from trpg.shared.types import Team, UnitId

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


def loadout(slots: Mapping[str, Sequence[str]]) -> Loadout:
    """``slots``：欄位 → 這件物品授予的技能。"""
    order = list(SLOT_TYPE_OF)
    items: list[EquippedItem] = []
    for slot in sorted(slots, key=order.index):
        slot_type = SLOT_TYPE_OF[slot]
        affixes = tuple(grant(s, f"affix_t_{slot}_{i}") for i, s in enumerate(slots[slot]))
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
    slots: Mapping[str, Sequence[str]], skills: Sequence[str] | None = None, *, react: bool = False
) -> UnitSpawn:
    base = no_reactions("hero_fighter")
    if react:
        base = base.model_copy(update={"reactions": None})
    if skills is not None:
        base = base.model_copy(update={"skills": tuple(skills)})
    return spawn(Team.ALLY, (0, 0), base).model_copy(update={"equipment": loadout(slots)})


def scene(
    slots: Mapping[str, Sequence[str]],
    skills: Sequence[str] | None = None,
    *,
    react: bool = False,
    foe: tuple[int, int] = (3, 0),
    seed: int = 0,
) -> BattleState:
    m = make_map(FLAT7, ally=[(0, 0)], enemy=[foe])
    enemy = spawn(Team.ENEMY, foe, no_reactions("bandit", max_hp=999))
    return give_turn(make_state(m, [hero(slots, skills, react=react), enemy], seed=seed), U1)


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
