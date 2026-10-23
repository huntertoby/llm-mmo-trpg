"""陷阱的觸發範圍是形狀 ID 字串，不是 ``{"type": ...}`` 物件。

使用者：「觸發範圍不能選 選了就會稀有度不見」。
"""

from __future__ import annotations

from trpg.content.library import load_library
from trpg.skillgen.options import draft_options

_DRAFT = {
    "kind": "active",
    "ap_cost": 1,
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "tier": 1,
    "skeleton": "trap",
    "shape": {"type": "ground_tile", "range": 6},
    "effects": [
        {"type": "place_trap"},
        {"type": "apply_status", "affects": "enemies", "status": "burning"},
        {"type": "damage", "affects": "enemies", "element": "physical"},
    ],
}


def _trap_shape_spec() -> object:
    lib = load_library()
    opts = draft_options({**_DRAFT, "trap": {"trigger": "enter"}}, lib)
    trap = next(f for s in opts.steps for f in s.fields if f.field == "trap")
    return next(f for f in trap.fields if f.field == "shape")


def test_trap_shape_is_a_plain_choice_not_an_object() -> None:
    spec = _trap_shape_spec()
    assert spec.type == "choice"  # type: ignore[attr-defined]
    assert spec.object_choice is False  # type: ignore[attr-defined]


def test_every_trap_shape_choice_keeps_rarity_available() -> None:
    lib = load_library()
    for choice in _trap_shape_spec().choices:  # type: ignore[attr-defined]
        trap = {"trigger": "enter", "rounds": 3, "shape": choice.value}
        opts = draft_options({**_DRAFT, "trap": trap}, lib)
        rarity = next(s for s in opts.steps if s.id == "rarity")
        assert any(f.field == "rarity" and f.choices for f in rarity.fields), choice.value
