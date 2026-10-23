"""Phase 3-48f：工坊提示——刻印 + 給友方增益 + 沒有讀取符文的條件（玩法決定 #51）。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from trpg.skillgen.options import draft_options

LIB = library()
_INSCRIBE = {"type": "inscribe", "element": "lightning", "duration": 2}
_SHIELD_ALLIES = {"type": "shield", "dice": "1d6", "affects": "allies"}
_HINT = "符文本身沒有效果"


def _effects_notes(effects: list[dict[str, Any]], **over: Any) -> tuple[str, ...]:
    base = LIB.skills["skill_thunder_sigil"].model_dump(mode="json", exclude_none=True)
    keys = ("skeleton", "kind", "category", "weapon_req", "scaling_attr", "tier", "ap_cost")
    draft: dict[str, Any] = {k: base[k] for k in (*keys, "name_zh", "shape", "cost", "rarity")}
    draft.update(effects=effects, **over)
    step = next(s for s in draft_options(draft, LIB).steps if s.id == "effects")
    return step.notes_zh


def test_rune_hint_shows_for_inscribe_plus_ally_buff_without_a_reader() -> None:
    notes = _effects_notes([_INSCRIBE, _SHIELD_ALLIES])
    assert any(_HINT in n and "持續區域" in n for n in notes)


def test_rune_hint_hidden_without_ally_buff() -> None:
    assert not any(_HINT in n for n in _effects_notes([_INSCRIBE]))


def test_rune_hint_hidden_when_a_rune_reader_exists() -> None:
    reader = {**_SHIELD_ALLIES, "condition": {"type": "on_own_rune"}}
    assert not any(_HINT in n for n in _effects_notes([_INSCRIBE, reader]))
    top = _effects_notes([_INSCRIBE, _SHIELD_ALLIES], condition={"type": "on_own_rune"})
    assert not any(_HINT in n for n in top)
