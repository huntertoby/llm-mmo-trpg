"""刻印的對象只有影響的格子（Phase 3-48e；玩法 PM 2026-10-24）。

工坊技能 ``skill_ws_c61379c350``（``affects: self`` 的刻印）曾在實戰沒有刻出符文：驗證器現在擋下，
引擎遇到讀入的舊技能也不能靜默失敗（``effect_fizzled``：``inscribe_needs_tiles``）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, of
from trpg.engine.events import EffectFizzled, RuneInscribed
from trpg.narrative.events import describe_event
from trpg.shared.types import Pos
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.skill_yaml import skill_from_yaml
from trpg.skillgen.validate import validate_skill

_SHAPE = {"type": "square3", "range": 5}
_RALLY = {"type": "apply_status", "affects": "allies", "status": "rallied", "duration": 3}


def _skill(affects: str | None):  # type: ignore[no-untyped-def]
    inscribe: dict[str, object] = {"type": "inscribe", "element": "physical", "duration": 4}
    if affects is not None:
        inscribe["affects"] = affects
    return make_skill(SID, _SHAPE, [inscribe, _RALLY])


@pytest.mark.parametrize("affects", ["self", "allies", "enemies", "all"])
def test_inscribe_on_units_never_fails_silently(affects: str) -> None:
    result = cast(battle(_skill(affects), foes=[(6, 3)]), target_pos=Pos(x=5, y=3))
    assert not result.state.runes
    assert not of(result, RuneInscribed)
    (fizzled,) = of(result, EffectFizzled)
    assert (fizzled.effect_kind, fizzled.reason) == ("inscribe", "inscribe_needs_tiles")
    assert "符文只能刻在影響的格子" in (describe_event(fizzled, result.state) or "")


@pytest.mark.parametrize("affects", [None, "tiles"])
def test_inscribe_on_tiles_inscribes_every_shape_tile(affects: str | None) -> None:
    result = cast(battle(_skill(affects), foes=[(6, 3)]), target_pos=Pos(x=5, y=3))
    assert not of(result, EffectFizzled)
    assert len(of(result, RuneInscribed)) >= 1
    assert {r.remaining for r in result.state.runes} == {4}


def _draft(affects: str) -> dict[str, object]:
    return {
        "id": "skill_ws_c61379c350",
        "name_zh": "測試",
        "rarity": "epic",
        "skeleton": "rune",
        "kind": "active",
        "tier": 1,
        "category": "weapon",
        "weapon_req": "melee",
        "ap_cost": 1,
        "scaling_attr": "str",
        "shape": _SHAPE,
        "effects": [
            {"type": "inscribe", "affects": affects, "element": "physical", "duration": 4},
            _RALLY,
        ],
        "cost": {"mana": 1, "stamina": 0, "cooldown": 1},
    }


def test_validator_rejects_inscribe_on_units_with_a_chinese_reason() -> None:
    lib = library()
    bad = check_draft(_draft("self"), lib)
    assert not bad.legal
    assert any("刻印只能刻在影響的格子" in p.message_zh for p in bad.problems)
    good = check_draft(_draft("tiles"), lib)
    assert not any("刻印只能刻在" in p.message_zh for p in good.problems)


def test_legacy_yaml_is_loaded_but_flagged_by_the_validator() -> None:
    """匯入舊 YAML 仍讀得進來（schema 通過），驗證器標示違規讓玩家修。"""
    skill = skill_from_yaml(
        "id: skill_ws_c61379c350\nname_zh: 舊\nrarity: epic\nkind: active\ntier: 1\n"
        "skeleton: rune\ncategory: weapon\nweapon_req: melee\nap_cost: 1\nscaling_attr: str\n"
        "shape: {type: square3, range: 5}\n"
        "effects:\n- {type: inscribe, affects: self, element: physical, duration: 4}\n"
        "cost: {mana: 1, stamina: 0, cooldown: 1}\n"
    )
    assert any("刻印只能刻在影響的格子" in v.message for v in validate_skill(skill, library()))
