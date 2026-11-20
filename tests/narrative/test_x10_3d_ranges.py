"""X10-3d：卡片以外的骰子寫法也只寫範圍（同 X10-3b 卡片；連接號「–」），長說明多一行
「擲 NdM，每點 ×10」。

範圍：狀態說明、地形（表面、物件）說明、主角面板的普攻、閃現變化列表。"""

from __future__ import annotations

import re

from tests.engine.helpers import card_dice, library
from trpg.api.flash_changes import flash_changes
from trpg.content.battle import Dice
from trpg.narrative.status_info import stack_rules, status_rules
from trpg.narrative.tile_info import object_rules, surface_rules

_DICE = re.compile(r"\d+d\d+")
_NOTE = re.compile(r"^擲 \d+d\d+，每點 ×10$")


def _no_dice_outside_notes(lines: tuple[str, ...]) -> None:
    for line in lines:
        if _NOTE.match(line):
            continue
        assert not _DICE.search(line), line


def test_status_and_stack_rules_write_ranges() -> None:
    lib = library()
    for status in lib.ruleset.statuses.statuses:
        _no_dice_outside_notes(status_rules(status, lib))
    for stack in lib.ruleset.stacks.stacks:
        _no_dice_outside_notes(stack_rules(stack, lib))
    heal = status_rules(lib.ruleset.status_def("regenerating"), lib)
    assert "回合開始時恢復 10–40 HP" in heal
    assert heal[heal.index("回合開始時恢復 10–40 HP") + 1] == "擲 1d4，每點 ×10"


def test_surface_and_object_rules_write_ranges() -> None:
    lib = library()
    for surface in lib.ruleset.surfaces.surfaces:
        _no_dice_outside_notes(surface_rules(surface, lib))
    for obj in lib.ruleset.objects.objects:
        lines = object_rules(obj, lib)
        _no_dice_outside_notes(lines)
        if obj.explosion is not None:
            amount = card_dice(obj.explosion.dice, obj.explosion.flat)
            assert any(f"，{amount} " in line for line in lines), lines


def test_basic_attack_line_writes_a_range_and_a_dice_note() -> None:
    lib = library()
    core = lib.ruleset.core
    for weapon in lib.weapons.values():
        lines = weapon.rule_lines_zh(core, lambda _a: 100)
        assert lines[0].startswith(f"普攻：{card_dice(weapon.dice, weapon.flat)}＋"), lines[0]
        assert not _DICE.search(lines[0]), lines[0]
        assert lines[1] == f"擲 {weapon.dice}，每點 ×10"


def test_flash_dice_row_shows_ranges() -> None:
    lib = library()
    before = next(
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.effects and s.effects[0].type == "damage" and s.effects[0].dice is not None
    )
    first = before.effects[0]
    assert first.dice is not None
    bigger = Dice(count=first.dice.count + 1, sides=first.dice.sides)
    after = before.model_copy(
        update={"effects": (first.model_copy(update={"dice": bigger}), *before.effects[1:])}
    )
    rows = [r for r in flash_changes(lib, before, after) if r.field == "effects[0].dice"]
    assert len(rows) == 1
    row = rows[0]
    assert row.before == str(first.dice)  # 資料欄位照舊是骰子
    assert row.before_zh == card_dice(first.dice, first.flat_bonus or 0)
    assert row.after_zh == card_dice(bigger, first.flat_bonus or 0)
    assert "–" in (row.after_zh or "")
