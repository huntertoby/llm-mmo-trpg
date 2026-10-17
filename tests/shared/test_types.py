"""trpg.shared.types、ids、errors 的測試。"""

from __future__ import annotations

from enum import StrEnum

import pytest
from pydantic import ValidationError

from trpg.shared.errors import ContentError, IllegalActionError, TrpgError
from trpg.shared.ids import IdAllocator, IdAllocatorState
from trpg.shared.types import Attribute, Element, Pos, Rarity, Surface, UnitId

# ---------------------------------------------------------------------------
# Pos
# ---------------------------------------------------------------------------


def test_pos_valid_and_frozen() -> None:
    p = Pos(x=3, y=4)
    assert (p.x, p.y) == (3, 4)
    with pytest.raises(ValidationError):
        p.x = 5  # type: ignore[misc]
    assert hash(p) == hash(Pos(x=3, y=4))
    assert p == Pos(x=3, y=4)
    assert len({p, Pos(x=3, y=4), Pos(x=4, y=3)}) == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"x": -1, "y": 0},
        {"x": 0, "y": -1},
        {"x": 1.5, "y": 0},
        {"x": "1", "y": 0},
        {"x": True, "y": 0},
        {"x": 0},
        {"x": 0, "y": 0, "z": 0},
    ],
)
def test_pos_invalid(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Pos.model_validate(kwargs)


def test_pos_neighbors4_order() -> None:
    assert Pos(x=2, y=2).neighbors4() == [
        Pos(x=2, y=1),  # 上
        Pos(x=3, y=2),  # 右
        Pos(x=2, y=3),  # 下
        Pos(x=1, y=2),  # 左
    ]


def test_pos_neighbors4_at_origin_omits_negative() -> None:
    assert Pos(x=0, y=0).neighbors4() == [Pos(x=1, y=0), Pos(x=0, y=1)]
    assert Pos(x=0, y=5).neighbors4() == [Pos(x=0, y=4), Pos(x=1, y=5), Pos(x=0, y=6)]


def test_pos_json_round_trip() -> None:
    p = Pos(x=7, y=1)
    assert Pos.model_validate_json(p.model_dump_json()) == p


# ---------------------------------------------------------------------------
# 列舉
# ---------------------------------------------------------------------------


def test_enum_values() -> None:
    assert [e.value for e in Element] == [
        "physical",
        "fire",
        "ice",
        "lightning",
        "poison",
        "holy",
        "shadow",
    ]
    assert [s.value for s in Surface] == ["none", "oil", "water", "fire", "ice", "poison", "holy"]
    assert [a.value for a in Attribute] == ["str", "dex", "con", "int", "wis", "wil"]
    assert [r.value for r in Rarity] == ["common", "uncommon", "rare", "epic", "legendary"]


@pytest.mark.parametrize("enum_cls", [Element, Surface, Attribute, Rarity])
def test_enum_display_names_complete(enum_cls: type[StrEnum]) -> None:
    names = [member.display_name for member in enum_cls]  # type: ignore[attr-defined]
    assert all(isinstance(n, str) and n for n in names)
    assert len(set(names)) == len(names)


def test_enum_is_str() -> None:
    assert isinstance(Element.FIRE, str)
    assert str(Element.FIRE) == "fire"
    assert Element("fire") is Element.FIRE
    assert Attribute.STR.display_name == "力量"
    assert Rarity.LEGENDARY.display_name == "傳說"


def test_id_newtypes_are_str() -> None:
    uid = UnitId("unit_0001")
    assert isinstance(uid, str)


# ---------------------------------------------------------------------------
# IdAllocator
# ---------------------------------------------------------------------------


def test_id_allocator_sequence() -> None:
    alloc = IdAllocator("unit")
    assert [alloc.next() for _ in range(3)] == ["unit_0001", "unit_0002", "unit_0003"]


def test_id_allocator_deterministic() -> None:
    a, b = IdAllocator("obj"), IdAllocator("obj")
    assert [a.next() for _ in range(10)] == [b.next() for _ in range(10)]


def test_id_allocator_state_round_trip() -> None:
    alloc = IdAllocator("battle")
    alloc.next()
    alloc.next()
    state = alloc.get_state()
    dumped = state.model_dump_json()
    restored = IdAllocator.from_state(IdAllocatorState.model_validate_json(dumped))
    assert restored.next() == alloc.next() == "battle_0003"


def test_id_allocator_width_grows() -> None:
    alloc = IdAllocator.from_state(IdAllocatorState(prefix="unit", issued=9999))
    assert alloc.next() == "unit_10000"


@pytest.mark.parametrize("prefix", ["", "Unit", "1unit", "unit-x", "單位"])
def test_id_allocator_rejects_bad_prefix(prefix: str) -> None:
    with pytest.raises(ValidationError):
        IdAllocator(prefix)


def test_id_allocator_state_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        IdAllocatorState(prefix="unit", issued=-1)


# ---------------------------------------------------------------------------
# 錯誤
# ---------------------------------------------------------------------------


def test_error_hierarchy() -> None:
    err = ContentError("content/elements.yaml", "缺少欄位")
    assert isinstance(err, TrpgError)
    assert issubclass(IllegalActionError, TrpgError)
    assert "elements.yaml" in str(err)
    assert "缺少欄位" in str(err)
    assert err.reason == "缺少欄位"
