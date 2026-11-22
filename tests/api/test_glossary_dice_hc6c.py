"""HC-6c（AR-X10 待決 5）：``/api/glossary`` 的規則句帶結構化的骰子欄位 ``rules_dice``。"""

from __future__ import annotations

import re

from trpg.api.glossary import build_glossary
from trpg.api.schemas import GlossaryEntry
from trpg.content.library import load_library
from trpg.shared.range_text import DiceNote, dice_note

_DICE_LINE = re.compile(r"^擲 \d+d\d+(，每點 ×\d+)?$")
"""舊的句型（AR-X10 前端用的正規式）：只拿來確認新欄位沒有漏標或多標。"""


def _entries() -> list[GlossaryEntry]:
    g = build_glossary(load_library())
    return [*g.terrain, *g.surfaces, *g.objects, *g.statuses, *g.stacks, *g.actions]


def test_dice_note_carries_dice() -> None:
    note = dice_note(2, 6, 10)
    assert isinstance(note, DiceNote)
    assert note == "擲 2d6，每點 ×10"
    assert (note.dice_count, note.dice_sides, note.dice_scale) == (2, 6, 10)


def test_rules_dice_marks_exactly_the_dice_lines() -> None:
    total = 0
    for entry in _entries():
        marked = {d.line for d in entry.rules_dice}
        by_text = {i for i, line in enumerate(entry.rules_zh) if _DICE_LINE.match(line)}
        assert marked == by_text, entry.id
        for d in entry.rules_dice:
            assert entry.rules_zh[d.line] == dice_note(d.count, d.sides, d.scale)
        total += len(marked)
    assert total > 0


def test_default_is_empty() -> None:
    entry = GlossaryEntry(id="x", name_zh="x")
    assert entry.rules_dice == ()
