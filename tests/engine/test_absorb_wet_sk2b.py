"""吸收表面「換元素」吸到水 → 帶潮濕（SK-2b，玩法交接 4.1.28 第 1 點）：這一招之後的傷害命中時在
目標格造水；傷害元素不變。油、煙霧不能換元素（驗證器擋）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill, with_rolls
from tests.engine.skill_helpers import SID, U2, battle, cast, of
from trpg.engine import state_to_json
from trpg.engine.events import DamageDealt, SurfaceAbsorbed
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary
from trpg.shared.types import Element, Surface

SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
FIRE = {"type": "damage", "dice": "1d4", "element": "fire"}


def _absorb(**params: Any) -> dict[str, Any]:
    return {"type": "absorb_surface", "affects": "self", "gain": "element", **params}


def test_water_keeps_the_element_and_soaks_the_hit_tile() -> None:
    skill = make_skill(SID, SINGLE5, [_absorb(), FIRE])
    state = with_rolls(battle(skill, [(5, 3)], surfaces=((3, 3, "water"),)), [(20, 19), (4, 2)])
    result = cast(state, target_id=U2)
    (absorbed,) = of(result, SurfaceAbsorbed)
    assert (absorbed.surface, absorbed.gain, absorbed.element) == (Surface.WATER, "element", None)
    (dmg,) = of(result, DamageDealt)
    assert dmg.element is Element.FIRE  # 元素不變
    assert result.state.tile(3, 3).surface is Surface.NONE  # 腳下的水吸走了
    assert result.state.tile(5, 3).surface is Surface.WATER  # 目標格造水
    text = describe_event(absorbed, result.state) or ""
    assert "潮濕" in text


def test_miss_does_not_soak() -> None:
    skill = make_skill(SID, SINGLE5, [_absorb(), FIRE])
    state = with_rolls(battle(skill, [(5, 3)], surfaces=((3, 3, "water"),)), [(20, 2)])
    result = cast(state, target_id=U2)
    assert not of(result, DamageDealt)
    assert result.state.tile(5, 3).surface is Surface.NONE


def test_elemental_surface_does_not_soak() -> None:
    skill = make_skill(SID, SINGLE5, [_absorb(), FIRE])
    state = with_rolls(battle(skill, [(5, 3)], surfaces=((3, 3, "ice"),)), [(20, 19), (4, 2)])
    result = cast(state, target_id=U2)
    (dmg,) = of(result, DamageDealt)
    assert dmg.element is Element.ICE
    assert result.state.tile(5, 3).surface is not Surface.WATER


def test_same_input_same_result() -> None:
    skill = make_skill(SID, SINGLE5, [_absorb(), FIRE])
    state = with_rolls(battle(skill, [(5, 3)], surfaces=((3, 3, "water"),)), [(20, 19), (4, 2)])
    first, second = cast(state, target_id=U2), cast(state, target_id=U2)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]


@pytest.mark.parametrize("name", ["oil", "smoke"])
def test_oil_and_smoke_cannot_be_absorbed_for_element(name: str) -> None:
    with pytest.raises(ValueError, match="油、煙霧"):
        make_skill(SID, SINGLE5, [_absorb(surface=name), FIRE])


@pytest.mark.parametrize("gain", ["heal", "shield"])
def test_oil_still_works_for_heal_and_shield(gain: str) -> None:
    make_skill(SID, {"type": "self"}, [_absorb(gain=gain, surface="oil", dice="1d4")])


def test_card_text_says_wet() -> None:
    lib = library()
    skill = make_skill(SID, SINGLE5, [_absorb(surface="water"), FIRE])
    assert "帶潮濕" in effect_summary(lib, skill, skill.effects[0])
    plain = make_skill(SID, SINGLE5, [_absorb(), FIRE])
    assert "帶潮濕" in effect_summary(lib, plain, plain.effects[0])
