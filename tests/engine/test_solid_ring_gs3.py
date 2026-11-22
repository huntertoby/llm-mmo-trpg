"""GS-3（#173，06 6.3 形狀清單）：環形的「實心」選項＝「周圍 N 格」（切比雪夫距離 1～N，不含自己）。

- 引擎幾何：實心 1、2 涵蓋貼身的敵人、不含自己；不填照舊只打剛好距離 N 的一圈。
- 預算：形狀倍率查 ``shape_budget.ring.solid_by_value``（照涵蓋格數）；格數查 ``cell_count``。
- 驗證：只有環形、只能填 true、只有內建內容、不能和持續區域一起用。
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, U3, battle, cast, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import ShapeSpec
from trpg.engine.events import DamageDealt
from trpg.engine.skills.shapes import ring_tiles
from trpg.skillgen.budget import skill_budget, zone_cell_count
from trpg.skillgen.validate import validate_skill


def _ring(radius: int, *, solid: bool | None) -> dict[str, object]:
    shape: dict[str, object] = {"type": "ring", "radius": radius}
    if solid is not None:
        shape["solid"] = solid
    return shape


def _skill(radius: int, *, solid: bool | None = True):  # type: ignore[no-untyped-def]
    return make_skill(
        SID,
        _ring(radius, solid=solid),
        [{"type": "damage", "dice": "1d4", "element": "physical"}],
        weapon_req="any",
    )


@pytest.mark.parametrize(("radius", "count"), [(1, 8), (2, 24)])
def test_a_solid_ring_covers_distance_one_to_radius_without_the_caster(
    radius: int, count: int
) -> None:
    state = battle(_skill(radius))
    tiles = ring_tiles(state, (3, 3), radius, solid=True)
    assert len(tiles) == count and (3, 3) not in tiles
    assert all(1 <= max(abs(x - 3), abs(y - 3)) <= radius for x, y in tiles)
    plain = ring_tiles(state, (3, 3), radius)
    assert set(plain) < set(tiles) or radius == 1
    assert all(max(abs(x - 3), abs(y - 3)) == radius for x, y in plain)


@pytest.mark.parametrize("radius", [1, 2])
def test_a_solid_ring_hits_an_adjacent_foe_and_never_the_caster(
    radius: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    always(monkeypatch, d20=15, die=1)
    foes = ((4, 3), (5, 5))  # 貼身 1 格、斜角 2 格
    result = cast(battle(_skill(radius), foes=foes))
    hit = {h.target_id for h in of(result, DamageDealt)}
    assert U2 in hit and U1 not in hit
    assert (U3 in hit) == (radius == 2)


def test_a_plain_ring_two_still_misses_the_adjacent_foe(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    result = cast(battle(_skill(2, solid=None), foes=((4, 3), (5, 5))))
    assert {h.target_id for h in of(result, DamageDealt)} == {U3}


def test_the_solid_ring_prices_its_cells_from_the_budget_table() -> None:
    lib = library()
    price = lib.budget.shape_budget["ring"]
    assert price.solid_by_value is not None and set(price.solid_by_value) == {1, 2}
    shape = lib.ruleset.shape_def("ring")
    for radius in (1, 2):
        solid = skill_budget(_skill(radius), lib).effects[0]
        plain = skill_budget(_skill(radius, solid=None), lib).effects[0]
        assert solid.shape == Fraction(price.solid_by_value[radius], 1000)
        assert plain.shape == Fraction(price.by_value[radius], 1000)  # type: ignore[index]
        assert shape.cell_count is not None
        assert shape.cell_count.count_for({"radius": radius}, solid=True) == (8, 24)[radius - 1]
        assert zone_cell_count(_skill(radius), lib) == (8, 24)[radius - 1]
    assert price.solid_by_value[2] >= price.by_value[2]  # type: ignore[index]  # 格數多不會更便宜


def test_solid_must_be_true_and_only_rings_offer_it() -> None:
    with pytest.raises(ValidationError, match="只能填 true"):
        ShapeSpec.model_validate({"type": "ring", "radius": 2, "solid": False})
    lib = library()
    cone = make_skill(
        SID,
        {"type": "cone", "size": 2, "solid": True},
        [{"type": "damage", "dice": "1d4", "element": "physical"}],
        weapon_req="any",
    )
    assert any("沒有實心選項" in v.message for v in validate_skill(cone, lib))


def test_only_builtin_content_can_write_a_solid_ring() -> None:
    lib = library()
    builtin = _skill(2).model_copy(
        update={"provenance": _skill(2).provenance.model_copy(update={"origin": "builtin"})}
    )
    assert not any("實心" in v.message for v in validate_skill(builtin, lib))
    generated = builtin.model_copy(
        update={"provenance": builtin.provenance.model_copy(update={"origin": "generated"})}
    )
    assert any("只有內建內容能寫" in v.message for v in validate_skill(generated, lib))


def test_omitting_solid_keeps_the_serialized_shape_unchanged() -> None:
    assert "solid" not in ShapeSpec(type="ring", radius=2).model_dump()
    assert ShapeSpec(type="ring", radius=2, solid=True).model_dump()["solid"] is True
