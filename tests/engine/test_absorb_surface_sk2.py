"""吸收表面（SK-2，#166，06 6.38 第 4 點）：移除施放者腳下或目標格的一種表面，換成層數、治療、
護盾，或讓這一招改成該表面的元素。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, preview, state_to_json
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    Healed,
    ShieldGained,
    SurfaceAbsorbed,
    SurfaceChanged,
)
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary
from trpg.shared.types import Element, Pos, Surface
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

SELF: dict[str, Any] = {"type": "self"}
SINGLE5: dict[str, Any] = {"type": "single", "range": 5}


def absorb(gain: str, **params: Any) -> dict[str, Any]:
    return {"type": "absorb_surface", "affects": "self", "gain": gain, **params}


def skill_of(shape: dict[str, Any], *effects: dict[str, Any]) -> SkillDef:
    return make_skill(SID, shape, list(effects))


def surface_at(state: BattleState, x: int, y: int) -> Surface:
    return state.tile(x, y).surface


def test_stack_gain_removes_the_surface_under_the_caster() -> None:
    skill = skill_of(SELF, absorb("stack", stack="fury", amount=2))
    state = battle(skill, surfaces=((3, 3, "fire"),))
    result = cast(state)
    (absorbed,) = of(result, SurfaceAbsorbed)
    assert (absorbed.unit_id, absorbed.surface, absorbed.gain, absorbed.element) == (
        U1,
        Surface.FIRE,
        "stack",
        None,
    )
    assert absorbed.pos == Pos(x=3, y=3)
    (changed,) = of(result, SurfaceChanged)
    assert (changed.before, changed.after, changed.cause) == (Surface.FIRE, Surface.NONE, "absorb")
    assert surface_at(result.state, 3, 3) is Surface.NONE
    assert result.state.units[U1].stacks.get("fury") == 2


def test_heal_gain_heals_the_caster() -> None:
    skill = skill_of(SELF, absorb("heal", dice="1d6"))
    state = battle(skill, surfaces=((3, 3, "water"),))
    state.units[U1].hp = 5
    result = cast(state)
    (healed,) = of(result, Healed)
    assert healed.target_id == U1 and healed.amount > 0
    assert result.state.units[U1].hp == 5 + healed.amount
    assert surface_at(result.state, 3, 3) is Surface.NONE


def test_shield_gain_shields_the_caster() -> None:
    skill = skill_of(SELF, absorb("shield", dice="1d6"))
    result = cast(battle(skill, surfaces=((3, 3, "oil"),)))
    (gained,) = of(result, ShieldGained)
    assert gained.unit_id == U1 and gained.amount > 0
    assert result.state.units[U1].has_status("shielded")


def test_element_gain_turns_this_casts_damage_into_the_surface_element() -> None:
    fire = {"type": "damage", "dice": "1d4", "element": "fire"}
    skill = skill_of(SINGLE5, absorb("element"), fire)
    state = hit_with(battle(skill, [(5, 3)], surfaces=((3, 3, "ice"),)), [(4, 2)])
    result = cast(state, target_id=U2)
    (absorbed,) = of(result, SurfaceAbsorbed)
    assert (absorbed.gain, absorbed.element) == ("element", Element.ICE)
    (dmg,) = of(result, DamageDealt)
    assert dmg.element is Element.ICE
    assert surface_at(result.state, 3, 3) is Surface.NONE


def test_target_tile_is_the_selected_tile() -> None:
    skill = skill_of(
        {"type": "ground_tile", "range": 4},
        {
            "type": "absorb_surface",
            "affects": "tiles",
            "gain": "stack",
            "stack": "fury",
            "amount": 1,
        },
    )
    state = battle(skill, surfaces=((5, 3, "poison"), (3, 3, "fire")))
    result = cast(state, target_pos=Pos(x=5, y=3))
    assert surface_at(result.state, 5, 3) is Surface.NONE
    assert surface_at(result.state, 3, 3) is Surface.FIRE  # 腳下不動
    assert result.state.units[U1].stacks.get("fury") == 1


@pytest.mark.parametrize(
    ("surfaces", "params"),
    [
        ((), {}),  # 沒有表面
        (((3, 3, "fire"),), {"surface": "water"}),  # 只吸水，腳下是火
    ],
)
def test_nothing_to_absorb_fizzles_and_keeps_the_rest(
    surfaces: tuple[tuple[int, int, str], ...], params: dict[str, Any]
) -> None:
    fire = {"type": "damage", "dice": "1d4", "element": "fire"}
    skill = skill_of(SINGLE5, absorb("element", **params), fire)
    state = hit_with(battle(skill, [(5, 3)], surfaces=surfaces), [(4, 2)])
    result = cast(state, target_id=U2)
    (fizzled,) = of(result, EffectFizzled)
    assert (fizzled.effect_kind, fizzled.reason) == ("absorb_surface", "no_surface")
    assert not of(result, SurfaceAbsorbed)
    (dmg,) = of(result, DamageDealt)
    assert dmg.element is Element.FIRE  # 照原本的元素
    for x, y, name in surfaces:
        assert surface_at(result.state, x, y) is Surface(name)


@pytest.mark.parametrize("name", ["oil", "smoke"])
def test_element_gain_does_not_take_oil_or_smoke(name: str) -> None:
    """油、煙霧沒有元素：換元素時不吸（水改成潮濕，見 test_absorb_wet_sk2b；SK-2b）。"""
    fire = {"type": "damage", "dice": "1d4", "element": "fire"}
    skill = skill_of(SINGLE5, absorb("element"), fire)
    state = hit_with(battle(skill, [(5, 3)], surfaces=((3, 3, name),)), [(4, 2)])
    result = cast(state, target_id=U2)
    assert [e.reason for e in of(result, EffectFizzled)] == ["no_surface"]
    assert surface_at(result.state, 3, 3) is Surface(name)


@pytest.mark.parametrize(
    ("effects", "message"),
    [
        ([{"type": "absorb_surface", "affects": "self"}], "必須填 gain"),
        ([absorb("stack", stack="fury")], "必須填 amount"),
        ([absorb("heal")], "必須填 dice"),
        ([absorb("element", dice="1d4")], "不能填 dice"),
        ([{"type": "heal", "dice": "1d4", "gain": "heal"}], "只有 absorb_surface 使用 gain"),
        (
            [{"type": "heal", "dice": "1d4", "affects": "self"}, absorb("heal", dice="1d4")],
            "absorb_surface",
        ),
    ],
)
def test_validation(effects: list[dict[str, Any]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        skill_of(SELF, *effects)


def test_preview_has_no_side_effects_and_shows_the_gain() -> None:
    skill = skill_of(SELF, absorb("stack", stack="fury", amount=2))
    state = battle(skill, surfaces=((3, 3, "fire"),))
    before = state_to_json(state)
    shown = preview(state, UseSkill(unit_id=U1, skill_id=SID))
    assert state_to_json(state) == before
    assert shown is not None


def test_same_input_same_result_and_log_text() -> None:
    skill = skill_of(SELF, absorb("heal", dice="2d6"))
    state = battle(skill, surfaces=((3, 3, "holy"),))
    state.units[U1].hp = 3
    first, second = cast(state), cast(state)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    (absorbed,) = of(first, SurfaceAbsorbed)
    text = describe_event(absorbed, first.state) or ""
    assert "吸走" in text and "聖光" in text


@pytest.mark.parametrize(
    ("effect", "words"),
    [
        (absorb("stack", stack="fury", amount=2), ("你腳下", "怒氣")),
        (absorb("heal", dice="1d6"), ("治療自己",)),
        (absorb("shield", dice="1d6", surface="water"), ("水", "護盾")),
        (absorb("element"), ("元素",)),
    ],
)
def test_card_text_and_budget(effect: dict[str, Any], words: tuple[str, ...]) -> None:
    lib = library()
    skill = skill_of(SELF, effect)
    text = effect_summary(lib, skill, skill.effects[0])
    for word in words:
        assert word in text
    report = skill_budget(skill, lib)
    assert report.effects[0].base > 0


def test_stack_gain_must_be_a_self_owned_stack() -> None:
    lib = library()
    bad = skill_of(SELF, absorb("stack", stack="hoarfrost", amount=1))
    messages = [v.message for v in validate_skill(bad, lib)]
    assert any("owner: self" in m for m in messages)
    good = skill_of(SELF, absorb("stack", stack="fury", amount=1))
    assert not any("owner: self" in v.message for v in validate_skill(good, lib))
