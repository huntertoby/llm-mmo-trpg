"""「目前加成」文字（Phase 3H-5）：主文捨去成整數，帶小數時另附說明標記。"""

from __future__ import annotations

from trpg.shared.bonus_text import BONUS_MARK, bonus_text, plain_text


def test_whole_values_have_no_mark() -> None:
    assert bonus_text(10, 500) == "目前 +5"
    assert bonus_text(0, 300) == "目前 +0"


def test_fractional_values_show_the_floor_and_explain_the_actual() -> None:
    text = bonus_text(14, 300)  # 實際 4.2
    assert text == "⟦目前 +4｜實際 4.2，和其他加成合計後才捨去⟧"
    assert plain_text(f"普攻（{text}）") == "普攻（目前 +4）"
    match = BONUS_MARK.search(text)
    assert match is not None and match.group(1) == "目前 +4"
    assert plain_text(bonus_text(13, 500)) == "目前 +6"  # 6.5 → 6
