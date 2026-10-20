"""Phase 3E-1 #2：``damage``、``hurl_object``、``charge_through`` 共用同一個攻擊傷害組裝。

投擲與直線衝撞的傷害也吃修正規則（``add_element``、``damage_permille``）與賭注倍率。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.events import DamageDealt
from trpg.shared.rng import Rng
from trpg.shared.types import ObjectId, Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FLAT = "\n".join(["0000000"] * 7)
HERO = (0, 3)
FOE = (3, 3)
HURL = make_skill(
    "skill_t_hurl",
    {"type": "object_then_tile", "range": 4},
    [{"type": "hurl_object", "range": 3, "dice": "2d6"}],
)
CHARGE = make_skill(
    "skill_t_charge",
    {"type": "ground_tile", "range": 6},
    [{"type": "charge_through", "dice": "2d6", "on_hit": "knock_prone"}],
    category="weapon",
    ap_cost=2,
)
DOUBLE: dict[str, Any] = {"type": "damage_multiplier", "damage_multiplier_permille": 2000}


def modifier(skill_id: str, change: Mapping[str, Any]) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": "測試修正",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": [{"applies_to": {"all_skills": True}, "change": dict(change)}],
        }
    )


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4, gamble_roll: int = 1) -> None:
    """d20 一律 19、賭注 d1000 一律 ``gamble_roll``（1 ＝ 一定成功）、其他骰子一律 ``die``。"""

    def fake(_self: Rng, sides: int) -> int:
        if sides == 20:
            return 19
        return min(gamble_roll, sides) if sides == 1000 else min(die, sides)

    monkeypatch.setattr(Rng, "roll", fake)


def arena(
    kind: str, skills: Sequence[SkillDef], main: SkillDef | None = None
) -> tuple[BattleState, UseSkill]:
    """U1 施放 ``kind``（``hurl``／``charge``）技能，裝備 ``skills``（含修正技能）；U2 是敵人。"""
    main = main or (HURL if kind == "hurl" else CHARGE)
    extra = [s for s in skills if s.id != main.id]
    equipped = [main, *extra]
    objects = [(1, 3, "crate")] if kind == "hurl" else []
    m = make_map(FLAT, ally=[HERO], enemy=[FOE], objects=objects)
    base = "hero_mage" if kind == "hurl" else "hero_fighter"
    spawns = [
        spawn(Team.ALLY, HERO, caster_template(equipped, base=base)),
        spawn(Team.ENEMY, FOE, no_reactions(max_hp=300)),
    ]
    state = give_turn(make_state(m, spawns, skills=equipped), U1)
    if kind == "hurl":
        action = UseSkill(
            unit_id=U1,
            skill_id=main.id,
            target_object_id=ObjectId("obj_0001"),
            target_pos=Pos(x=FOE[0], y=FOE[1]),
        )
    else:
        action = UseSkill(unit_id=U1, skill_id=main.id, target_pos=Pos(x=5, y=3))
    return state, action


def hit_on_foe(state: BattleState, action: UseSkill) -> DamageDealt:
    result = resolve(state, action)
    (dealt,) = [e for e in result.events if isinstance(e, DamageDealt) and e.target_id == U2]
    return dealt


@pytest.mark.parametrize("kind", ["hurl", "charge"])
def test_add_element_applies_to_thrown_and_charge_damage(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    always(monkeypatch)
    plain = hit_on_foe(*arena(kind, []))
    assert plain.element.value == "physical"
    fire = hit_on_foe(*arena(kind, [modifier("skill_t_mod_fire", {"add_element": "fire"})]))
    assert fire.element.value == "fire"


@pytest.mark.parametrize("kind", ["hurl", "charge"])
def test_damage_permille_modifier_applies_to_thrown_and_charge_damage(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    always(monkeypatch)
    plain = hit_on_foe(*arena(kind, []))
    boosted = hit_on_foe(*arena(kind, [modifier("skill_t_mod_dmg", {"damage_permille": 500})]))
    assert boosted.multiplier_permille == plain.multiplier_permille * 3 // 2
    assert boosted.amount > plain.amount


def test_gamble_multiplier_applies_to_thrown_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    """投擲技搭配賭注（成功分支 ``damage_multiplier``）：投擲傷害同樣乘上賭注倍率。
    （直線衝撞的非衝撞效果一律只能作用在自己，無法搭配賭注——schema 擋住，沒有可測的組合。）"""
    always(monkeypatch)
    plain = hit_on_foe(*arena("hurl", []))
    extra: list[dict[str, Any]] = [
        {"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"},
        {"type": "gamble", "chance_permille": 900, "win": [DOUBLE]},
    ]
    effects = [*HURL.model_dump(mode="json")["effects"], *extra]
    gambler = SkillDef.model_validate({**HURL.model_dump(mode="json"), "effects": effects})
    state, action = arena("hurl", [], gambler)
    result = resolve(state, action)
    thrown = [
        e
        for e in result.events
        if isinstance(e, DamageDealt) and e.target_id == U2 and e.element.value == "physical"
    ]
    assert [e.multiplier_permille for e in thrown] == [plain.multiplier_permille * 2]
