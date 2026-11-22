"""E4（#175，08 8.29 E4 第 4～6 點）：觸發篩選的結算。

- 元素看實際造成傷害的元素（轉換以後）；多段、多下對同一個目標只觸發 1 次。
- 持續傷害、表面傷害也算「受到該元素傷害」。
- 近戰的定義和格擋相同：近戰普攻、近戰武器技、近戰反應攻擊都算。
- 來源（普攻、技能、反應）與反應 ID；裝備的觸發詞條同一套；重播的確定性。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from tests.engine.test_gear_g3a import THORNS, always, scene
from trpg.content.equipment import TriggerAffix
from trpg.content.skills import SkillDef
from trpg.engine import Attack, Move, UseSkill, resolve
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import DamageDealt, EventBase, GearTriggered, SkillTriggered
from trpg.engine.events.base import DamageCause
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Element, Pos, Team, UnitId

PASSIVE = "skill_t_e4_filter"
SKILL = "skill_t_e4_strike"


def weapon_strike() -> SkillDef:
    """近戰單體武器技（射程 1）。"""
    damage = [{"type": "damage", "multiplier_permille": 1000}]
    return make_skill(SKILL, {"type": "single", "range": 1}, damage, category="weapon")


def spell_strike() -> SkillDef:
    """單體火焰法術技（射程 4）。"""
    damage = [{"type": "damage", "dice": "1d4", "element": "fire"}]
    return make_skill(SKILL, {"type": "single", "range": 4}, damage, weapon_req="any")


def passive(event: str, max_per_round: int = 1, **filters: Any) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": PASSIVE,
            "name_zh": "測試篩選",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "wis",
            "shape": {"type": "self"},
            "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            "trigger": {
                "event": event,
                "target": "self",
                "max_per_round": max_per_round,
                **filters,
            },
            "cost": {"mana": 0},
        }
    )


def fired(events: list[EventBase]) -> int:
    return sum(1 for e in events if isinstance(e, SkillTriggered) and e.skill_id == PASSIVE)


def attacker_scene(
    p: SkillDef, *, weapon: str | None = None, extra: tuple[SkillDef, ...] = ()
) -> BattleState:
    """U1（帶被動的戰士，(3, 3)）打 U2（(4, 3) 的木樁）。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    hero = caster_template([p, *extra], base="hero_fighter")
    spawns = [
        spawn(Team.ALLY, (3, 3), hero, weapon, skills=None),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999)),
    ]
    return give_turn(make_state(m, spawns, skills=[p, *extra]), U1)


def target_scene(
    p: SkillDef,
    *,
    weapon: str | None = None,
    foe: tuple[int, int] = (4, 3),
    skill: SkillDef | None = None,
) -> BattleState:
    """U1（戰士）打 U2（帶被動的木樁，``foe``）。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe])
    extra = [] if skill is None else [skill]
    hero = caster_template(extra, base="hero_fighter")
    spawns = [
        spawn(Team.ALLY, (3, 3), hero, weapon, skills=None),
        spawn(Team.ENEMY, foe, template("bandit", reactions=[], max_hp=999, skills=[p.id])),
    ]
    return give_turn(make_state(m, spawns, skills=[p, *extra]), U1)


def flame(state: BattleState, unit: UnitId = U1) -> BattleState:
    """焰刃姿態：普攻的物理傷害改成火焰（元素轉換）。"""
    s = state.clone()
    s.units[unit].statuses.append(StatusInstance("stance_flame", remaining=99))
    return s


# ---------------------------------------------------------------------------
# 元素（第 4、5 點）
# ---------------------------------------------------------------------------


def test_element_filter_looks_at_the_converted_element(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = attacker_scene(passive("on_hit", element="fire"))
    plain = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    assert {e.element for e in plain if isinstance(e, DamageDealt)} == {Element.PHYSICAL}
    assert fired(plain) == 0
    burning = resolve(flame(state), Attack(unit_id=U1, target_id=U2)).events
    assert {e.element for e in burning if isinstance(e, DamageDealt)} == {Element.FIRE}
    assert fired(burning) == 1


def test_unfiltered_hit_trigger_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = attacker_scene(passive("on_hit"))
    assert fired(resolve(state, Attack(unit_id=U1, target_id=U2)).events) == 1


def test_several_strikes_on_one_target_fire_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """雙匕首一次普攻打兩下：不篩時每一下命中各記一次，篩元素時對同一個目標只算 1 次。"""
    always(monkeypatch)
    loose = flame(attacker_scene(passive("on_hit", max_per_round=3), weapon="dual_dagger"))
    assert fired(resolve(loose, Attack(unit_id=U1, target_id=U2)).events) == 2
    strict = flame(
        attacker_scene(passive("on_hit", max_per_round=3, element="fire"), weapon="dual_dagger")
    )
    events = resolve(strict, Attack(unit_id=U1, target_id=U2)).events
    assert sum(1 for e in events if isinstance(e, DamageDealt) and e.source_id == U1) == 2
    assert fired(events) == 1


def test_any_segment_of_a_mixed_skill_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """一招有冰與物理兩段：篩冰就算（任一段符合）。"""
    always(monkeypatch)
    skill = make_skill(
        SKILL,
        {"type": "single", "range": 1},
        [
            {"type": "damage", "multiplier_permille": 500},
            {"type": "damage", "multiplier_permille": 500, "element": "ice"},
        ],
        category="weapon",
    )
    for element, expected in (("ice", 1), ("fire", 0)):
        state = attacker_scene(passive("on_hit", element=element), extra=(skill,))
        events = resolve(state, UseSkill(unit_id=U1, skill_id=SKILL, target_id=U2)).events
        got = {e.element for e in events if isinstance(e, DamageDealt) and e.source_id == U1}
        assert got == {Element.PHYSICAL, Element.ICE}
        assert fired(events) == expected, element


def _damage(state: BattleState, element: Element, cause: DamageCause) -> list[EventBase]:
    ctx = Ctx(state.clone())
    execute(
        ctx,
        [
            DamageEffect(
                target_id=U2,
                source_id=None,
                cause=cause,
                element=element,
                flat=3,
            )
        ],
    )
    return ctx.events


@pytest.mark.parametrize(
    ("element", "cause", "want", "expected"),
    [
        (Element.FIRE, "status", "fire", 1),  # 燃燒每回合的傷害
        (Element.POISON, "surface", "poison", 1),  # 毒表面
        (Element.POISON, "surface", "fire", 0),
    ],
)
def test_damage_over_time_and_surfaces_count(
    element: Element, cause: DamageCause, want: str, expected: int
) -> None:
    state = target_scene(passive("on_damaged", element=want))
    assert fired(_damage(state, element, cause)) == expected


# ---------------------------------------------------------------------------
# 近戰（第 6 點）與來源
# ---------------------------------------------------------------------------


def test_melee_basic_attack_counts_as_melee(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = target_scene(passive("on_damaged", attack_kind="melee"))
    assert fired(resolve(state, Attack(unit_id=U1, target_id=U2)).events) == 1


def test_ranged_basic_attack_is_not_melee(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    melee = target_scene(passive("on_damaged", attack_kind="melee"), weapon="bow", foe=(3, 6))
    assert fired(resolve(melee, Attack(unit_id=U1, target_id=U2)).events) == 0
    ranged = target_scene(passive("on_damaged", attack_kind="ranged"), weapon="bow", foe=(3, 6))
    assert fired(resolve(ranged, Attack(unit_id=U1, target_id=U2)).events) == 1


def test_melee_weapon_skill_counts_as_melee_like_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """近戰武器技也算近戰（同格擋：技能看技能自己的近戰判定）。"""
    always(monkeypatch)
    skill = weapon_strike()
    for kind, expected in (("melee", 1), ("ranged", 0), ("spell", 0)):
        state = target_scene(passive("on_damaged", attack_kind=kind), skill=skill)
        events = resolve(state, UseSkill(unit_id=U1, skill_id=SKILL, target_id=U2)).events
        assert fired(events) == expected, kind


def test_spell_skill_is_spell(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = spell_strike()
    for kind, expected in (("spell", 1), ("melee", 0), ("ranged", 0)):
        state = target_scene(passive("on_damaged", attack_kind=kind), skill=skill)
        events = resolve(state, UseSkill(unit_id=U1, skill_id=SKILL, target_id=U2)).events
        assert fired(events) == expected, kind


def test_source_filter_separates_attack_and_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = weapon_strike()
    for source, by_attack, by_skill in (("attack", 1, 0), ("skill", 0, 1), ("reaction", 0, 0)):
        state = attacker_scene(passive("on_hit", source=source), extra=(skill,))
        assert fired(resolve(state, Attack(unit_id=U1, target_id=U2)).events) == by_attack
        cast = resolve(state, UseSkill(unit_id=U1, skill_id=SKILL, target_id=U2)).events
        assert fired(cast) == by_skill, source


def _oa_scene(p: SkillDef) -> BattleState:
    """U1（帶被動、有預設反應的戰士，(1, 0)）；U2（盜賊，(2, 0)）拿到回合。"""
    m = make_map("000000\n000000", ally=[(1, 0)], enemy=[(2, 0)])
    hero = template("hero_fighter", skills=[p.id])
    spawns = [
        spawn(Team.ALLY, (1, 0), hero),
        spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=999, reactions=[])),
    ]
    return give_turn(make_state(m, spawns, skills=[p]), U2)


def _walk_away(state: BattleState) -> list[EventBase]:
    path = (Pos(x=2, y=0), Pos(x=3, y=0), Pos(x=4, y=0))
    return resolve(state, Move(unit_id=U2, path=path)).events


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"source": "reaction"}, 1),
        ({"source": "reaction", "reaction": "opportunity_attack"}, 1),
        ({"source": "reaction", "reaction": "counter_attack"}, 0),
        ({"source": "attack"}, 0),
        ({"attack_kind": "melee"}, 1),  # 近戰反應攻擊也算近戰
    ],
)
def test_reaction_attacks(
    monkeypatch: pytest.MonkeyPatch, filters: dict[str, str], expected: int
) -> None:
    always(monkeypatch)
    events = _walk_away(_oa_scene(passive("on_hit", 1, **filters)))
    assert any(e.type == "reaction_triggered" for e in events)  # type: ignore[attr-defined]
    assert fired(events) == expected


# ---------------------------------------------------------------------------
# 裝備的觸發詞條（同一套篩選）
# ---------------------------------------------------------------------------


def _gear(state: BattleState, unit: UnitId, **changes: Any) -> BattleState:
    """把 ``unit`` 身上的「荊棘燃燒」換成測試用的篩選版本（同 ID，不改其他詞條）。"""
    s = state.clone()
    owner = s.units[unit]
    swapped = []
    for gear in owner.gear.affixes:
        affix = gear.affix
        if isinstance(affix, TriggerAffix) and affix.id == THORNS[0]:
            swapped.append(replace(gear, affix=affix.model_copy(update=changes)))
        else:
            swapped.append(gear)
    owner.gear = replace(owner.gear, affixes=tuple(swapped))
    return s


def _gear_fired(events: list[EventBase]) -> int:
    return sum(1 for e in events if isinstance(e, GearTriggered) and e.affix_id == THORNS[0])


def test_gear_on_hit_element_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    base = scene({"body": [THORNS]})
    state = _gear(base, U1, trigger="on_hit", melee_only=False, element=Element.FIRE,
                  effect_target="target")  # fmt: skip
    assert _gear_fired(resolve(state, Attack(unit_id=U1, target_id=U2)).events) == 0
    assert _gear_fired(resolve(flame(state), Attack(unit_id=U1, target_id=U2)).events) == 1


def test_gear_on_damaged_kind_filter_differs_from_melee_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """舊的 ``melee_only`` 不改（攻擊傷害、距離在近戰範圍內就算，貼身的法術也算）；新的
    ``attack_kind: melee`` 照格擋的定義，法術技不算近戰。"""
    always(monkeypatch)
    skill = spell_strike()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    foe = spawn(Team.ENEMY, (4, 3), caster_template([skill], base="bandit"))
    hero = spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter"))
    state = give_turn(make_state(m, [hero, foe], skills=[skill]), U2)
    state.units[U1].gear = scene({"body": [THORNS]}).units[U1].gear
    old = resolve(state, UseSkill(unit_id=U2, skill_id=SKILL, target_id=U1)).events
    assert _gear_fired(old) == 1  # melee_only：貼身的法術傷害也算（現有結果不變）
    for kind, expected in (("melee", 0), ("spell", 1)):
        new = _gear(state, U1, melee_only=False, attack_kind=kind)
        events = resolve(new, UseSkill(unit_id=U2, skill_id=SKILL, target_id=U1)).events
        assert _gear_fired(events) == expected, kind


# ---------------------------------------------------------------------------
# 確定性
# ---------------------------------------------------------------------------


def test_replay_is_deterministic() -> None:
    state = flame(attacker_scene(passive("on_hit", element="fire", source="attack")))
    first = resolve(state, Attack(unit_id=U1, target_id=U2))
    second = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
