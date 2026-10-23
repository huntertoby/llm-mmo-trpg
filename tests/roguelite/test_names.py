"""一輪裡的技能名稱：組合技能撞名時加「（二）」（2026-10-23 使用者決定）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.roguelite.names import unique_skill_name
from trpg.skillgen.random_composer import compose_random_skill


def test_no_clash_keeps_the_skill_unchanged() -> None:
    skill = compose_random_skill(0, library=library())
    assert unique_skill_name(skill, ["別的技能"]) is skill
    assert "#" not in skill.name_zh


def test_clash_appends_chinese_numerals_and_keeps_the_id() -> None:
    skill = compose_random_skill(0, library=library())
    base = skill.name_zh
    second = unique_skill_name(skill, [base])
    assert second.name_zh == f"{base}（二）" and second.id == skill.id
    third = unique_skill_name(skill, [base, f"{base}（二）"])
    assert third.name_zh == f"{base}（三）"


def test_after_ten_numerals_it_falls_back_to_digits() -> None:
    skill = compose_random_skill(0, library=library())
    base = skill.name_zh
    marks = ["二", "三", "四", "五", "六", "七", "八", "九", "十"]
    taken = [base, *(f"{base}（{m}）" for m in marks)]
    assert unique_skill_name(skill, taken).name_zh == f"{base}（11）"
