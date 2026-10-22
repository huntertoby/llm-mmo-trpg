"""Phase 3-25b：戰場變奏的 API 視圖（技能卡型態、技能列生效的型態、預覽的型態）。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.test_variants import FLAT7, SPARK, TIDAL, U1, _state
from trpg.api.presenter import preview_response
from trpg.api.variants import preview_variant, variant_states
from trpg.engine import UseSkill, legal_actions
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.shared.types import Pos

HEIGHTS = "0000000\n0000000\n0000000\n0001000\n0000000\n0000000\n0000000"


def test_the_skill_card_lists_every_form_with_condition_and_icon() -> None:
    lib = library()
    card = skill_card(lib, lib.skills[TIDAL])
    assert [v.id for v in card.variants] == ["tide_pierce", "high_tide"]
    water, high = card.variants
    assert water.name_zh == "水中貫穿" and "水" in water.condition
    assert water.condition_kind == "caster_surface" and not water.target_dependent
    assert "直線" in water.change and "雷" in water.change
    assert high.condition_kind == "caster_high_ground" and high.target_dependent
    assert "射程" in high.change
    assert water.icon != card.icon  # 型態自己的圖示（形狀不同）
    plain = skill_card(lib, lib.skills["skill_fire_bolt"])
    assert plain.variants == ()


def test_keywords_brought_only_by_a_variant_are_marked() -> None:
    lib = library()
    card = skill_card(lib, lib.skills[TIDAL])
    marked = {k.id for k in (*card.keywords.makes, *card.keywords.uses) if k.variant}
    assert "charged" in marked  # 水中型態的雷
    assert all(not k.variant for k in card.keywords.makes if k.id == "frozen")


def test_variant_states_report_the_active_and_reachable_forms() -> None:
    wet = _state([TIDAL], surfaces=[(3, 3, "water")])
    states = variant_states(wet, U1, tuple(legal_actions(wet)))
    assert len(states) == 1
    assert states[0].skill_id == TIDAL
    assert states[0].active == "tide_pierce"
    assert "tide_pierce" in states[0].available

    dry = _state([TIDAL])
    s = variant_states(dry, U1, tuple(legal_actions(dry)))[0]
    assert s.active is None and s.available == ()

    # 居高：不是施放者位置的條件，所以 active 為空；但對比自己低的目標點，合法動作會選到居高型態
    high = _state([TIDAL], heights=HEIGHTS)
    s = variant_states(high, U1, tuple(legal_actions(high)))[0]
    assert s.active is None and s.available == ("high_tide",)


def test_target_surface_forms_are_only_reachable_for_those_targets() -> None:
    state = _state([SPARK], foes=[(3, 0)], surfaces=[(3, 0, "oil")])
    s = variant_states(state, U1, tuple(legal_actions(state)))[0]
    assert s.active is None and s.available == ("oil_spark",)


def test_skills_without_variants_are_not_listed() -> None:
    state = _state(["skill_fire_bolt"])
    assert variant_states(state, U1, tuple(legal_actions(state))) == ()


def test_the_preview_names_the_form_for_the_chosen_target_point() -> None:
    state = _state([SPARK], foes=[(3, 0), (3, 1)], surfaces=[(3, 0, "oil")])
    oily = UseSkill(unit_id=U1, skill_id=SPARK, target_id="unit_0002")
    plain = UseSkill(unit_id=U1, skill_id=SPARK, target_id="unit_0003")
    out = preview_response(preview(state, oily), state)
    assert out.variant is not None and out.variant.id == "oil_spark"
    assert out.variant.name_zh == "油上火星"
    assert preview_response(preview(state, plain), state).variant is None
    assert preview_variant(state, UseSkill(unit_id=U1, skill_id=SPARK, target_pos=Pos(x=3, y=0)))


def test_the_flat_map_constant_is_what_the_helpers_use() -> None:
    assert FLAT7.count("\n") == 6
