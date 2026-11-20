"""X10-3b：量類骰子的範圍文字（卡片、技能列、預覽同一種連接號）。"""

from __future__ import annotations

from pathlib import Path

from trpg.shared.range_text import RANGE_DASH, dice_note, range_text, span

ROOT = Path(__file__).resolve().parents[2]


def test_span_scales_faces_and_adds_extra() -> None:
    assert span(2, 8, 10) == (20, 160)
    assert span(2, 8, 10, 15) == (35, 175)
    assert span(1, 1, 10) == (10, 10)


def test_range_text_uses_the_en_dash() -> None:
    assert RANGE_DASH == "–"
    assert range_text(20, 160) == "20–160"
    assert range_text(130, 1060) == "130–1060"
    assert range_text(10, 10) == "10"


def test_dice_note() -> None:
    assert dice_note(2, 8, 10) == "擲 2d8，每點 ×10"
    assert dice_note(2, 8, 1) == "擲 2d8"


def test_battle_preview_uses_the_same_dash() -> None:
    """戰鬥預覽 ``damageText`` 的範圍和卡片同一個連接號。"""
    text = (ROOT / "client" / "src" / "battle" / "previewText.ts").read_text(encoding="utf-8")
    assert f"`${{d.minimum}}{RANGE_DASH}${{d.maximum}}`" in text
