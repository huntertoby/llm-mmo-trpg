"""E4（#175，08 8.29 E4 第 1、2 點）：新時機 ``on_displace``「你讓別人位移時」。

持有者是推的人、另一方是被推的人；推、拉、擊退、傳送別人、互換都算，隊友也算；實際移動至少 1 格；
一次位移只觸發 1 次；移動 0 格只算撞擊；冰上滑行不另外算；讓另外兩人互換時兩人各 1 次；「換位」
動作也算，裝備觸發每回合最多 1 次（8.21.5.3）。
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
)
from tests.engine.test_gear_g3a import THORNS, always, scene
from trpg.content.equipment import TriggerAffix
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, Swap, UseSkill, resolve
from trpg.engine.events import Collided, EventBase, GearTriggered, SkillTriggered, UnitMoved
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT = "\n".join(["0000000"] * 7)
PASSIVE = "skill_t_e4_displace"
SKILL = "skill_t_e4_move"


def passive(max_per_round: int = 1) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": PASSIVE,
            "name_zh": "測試位移",
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
            "trigger": {"event": "on_displace", "target": "self", "max_per_round": max_per_round},
            "cost": {"mana": 0},
        }
    )


def fired(events: list[EventBase]) -> list[SkillTriggered]:
    return [e for e in events if isinstance(e, SkillTriggered) and e.skill_id == PASSIVE]


def arena(
    skill: SkillDef,
    *,
    allies: tuple[tuple[int, int], ...] = ((3, 3),),
    heights: str = FLAT,
    max_per_round: int = 1,
    surfaces: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """U1（帶被動與 ``skill`` 的法師，(2, 3)）；之後是 ``allies``（不反應的我方）。"""
    p = passive(max_per_round)
    m = make_map(heights, ally=[(2, 3), *allies], enemy=[(6, 6)], surfaces=surfaces)
    spawns = [spawn(Team.ALLY, (2, 3), caster_template([skill, p]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_mage")) for xy in allies]
    spawns.append(spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=999)))
    return give_turn(make_state(m, spawns, skills=[skill, p]), U1)


def push_skill(distance: int = 2, kind: str = "push") -> SkillDef:
    effect = {"type": kind, "distance": distance, "affects": "allies"}
    return make_skill(SKILL, {"type": "single", "range": 3}, [effect])


def use(state: BattleState, **fields: Any) -> list[EventBase]:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SKILL, **fields)).events


def test_push_two_tiles_fires_once_with_the_pushed_unit_as_other() -> None:
    events = use(arena(push_skill(2)), target_id=U2)
    moved = [e for e in events if isinstance(e, UnitMoved) and e.unit_id == U2]
    assert len(moved) == 2  # 推 2 格（隊友也算）
    got = fired(events)
    assert [(e.unit_id, e.other_id) for e in got] == [(U1, U2)]


def test_pull_counts() -> None:
    events = use(arena(push_skill(1, "pull"), allies=((5, 3),)), target_id=U2)
    assert any(isinstance(e, UnitMoved) and e.unit_id == U2 for e in events)
    assert len(fired(events)) == 1


def test_push_blocked_on_the_first_tile_is_only_a_collision() -> None:
    """推了但第一格就被牆擋住（移動 0 格）：只算撞擊，不算位移。"""
    walls = "\n".join(["0000000"] * 3 + ["0000300"] + ["0000000"] * 3)  # (4, 3) 是高牆
    events = use(arena(push_skill(2), heights=walls), target_id=U2)
    assert any(isinstance(e, Collided) and e.unit_id == U2 for e in events)
    assert not any(isinstance(e, UnitMoved) and e.unit_id == U2 for e in events)
    assert fired(events) == []


def test_push_one_tile_then_blocked_still_counts_once() -> None:
    walls = "\n".join(["0000000"] * 3 + ["0000030"] + ["0000000"] * 3)  # (5, 3) 是高牆
    events = use(arena(push_skill(2), heights=walls), target_id=U2)
    assert any(isinstance(e, Collided) and e.unit_id == U2 for e in events)
    assert len(fired(events)) == 1


def test_teleporting_someone_else_counts() -> None:
    skill = make_skill(SKILL, {"type": "unit_then_tile", "range": 5}, [{"type": "teleport_target"}],
                       ap_cost=2)  # fmt: skip
    events = use(arena(skill), target_id=U2, target_pos=Pos(x=3, y=0))
    assert any(isinstance(e, UnitMoved) and e.mode == "teleported" for e in events)
    assert [(e.unit_id, e.other_id) for e in fired(events)] == [(U1, U2)]


def test_swapping_with_the_caster_counts_the_other_only() -> None:
    skill = make_skill(
        SKILL, {"type": "single", "range": 3}, [{"type": "swap", "affects": "allies"}]
    )
    events = use(arena(skill), target_id=U2)
    assert [(e.unit_id, e.other_id) for e in fired(events)] == [(U1, U2)]


def test_swapping_two_others_fires_once_for_each() -> None:
    skill = make_skill(SKILL, {"type": "unit_pair", "range": 5}, [{"type": "swap_any"}], ap_cost=2)
    state = arena(skill, allies=((3, 3), (3, 5)), max_per_round=2)
    events = use(state, target_id=U2, second_target_id=U3)
    assert sorted(str(e.other_id) for e in fired(events)) == [U2, U3]


def test_pushed_onto_ice_counts_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """被推上冰面：只算推的那 1 次（被推進冰面照舊不滑，滑行本來就不會另外算位移）。"""
    always(monkeypatch, d20=1)  # 冰面檢定一律失敗
    state = arena(push_skill(2), surfaces=((4, 3, "ice"), (5, 3, "ice")))
    events = use(state, target_id=U2)
    assert not any(isinstance(e, UnitMoved) and e.mode == "slide" for e in events)
    assert len(fired(events)) == 1


# ---------------------------------------------------------------------------
# 「換位」動作與每回合上限
# ---------------------------------------------------------------------------


def _swap_scene(*, gear: bool, max_per_round: int = 1) -> BattleState:
    """U1（帶被動的法師，(2, 3)）旁邊是隊友 U2（(3, 3)）；``gear`` 時 U1 身上的「荊棘燃燒」改成
    ``on_displace`` 的測試版本（同 ID）。"""
    m = make_map(FLAT, ally=[(2, 3), (3, 3)], enemy=[(6, 6)])
    p = passive(max_per_round)
    hero = spawn(Team.ALLY, (2, 3), caster_template([p]))
    friend = spawn(Team.ALLY, (3, 3), no_reactions("hero_mage"))
    foe = spawn(Team.ENEMY, (6, 6), no_reactions())
    state = give_turn(make_state(m, [hero, friend, foe], skills=[p]), U1)
    if gear:
        owner = state.units[U1]
        loadout = scene({"body": [THORNS]}).units[U1].gear
        change = {"trigger": "on_displace", "melee_only": False}
        swapped = [
            replace(g, affix=g.affix.model_copy(update=change))
            if isinstance(g.affix, TriggerAffix) and g.affix.id == THORNS[0]
            else g
            for g in loadout.affixes
        ]
        owner.gear = replace(loadout, affixes=tuple(swapped))
    return state


def test_swap_action_counts_and_gear_fires_once_per_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """「換位」1 AP 就能觸發；同一回合換位兩次，裝備的觸發只算 1 次（8.21.5.3），被動照每輪次數。"""
    always(monkeypatch)
    state = _swap_scene(gear=True)
    first = resolve(state, Swap(unit_id=U1, target_id=U2))
    second = resolve(first.state, Swap(unit_id=U1, target_id=U2))
    events = [*first.events, *second.events]
    gear = [e for e in events if isinstance(e, GearTriggered) and e.affix_id == THORNS[0]]
    assert len(gear) == 1
    assert len(fired(first.events)) == 1
    assert fired(second.events) == []  # 被動 max_per_round 1：這一輪用完了


def test_passive_with_two_per_round_fires_on_each_swap() -> None:
    """被動照現有的每輪次數：``max_per_round: 2`` 時同一回合換位兩次觸發兩次。"""
    state = _swap_scene(gear=False, max_per_round=2)
    first = resolve(state, Swap(unit_id=U1, target_id=U2))
    second = resolve(first.state, Swap(unit_id=U1, target_id=U2))
    assert len(fired(first.events)) == 1 and len(fired(second.events)) == 1


def test_replay_is_deterministic() -> None:
    state = arena(push_skill(2))
    first = use(state, target_id=U2)
    second = use(state, target_id=U2)
    assert [e.model_dump() for e in first] == [e.model_dump() for e in second]
