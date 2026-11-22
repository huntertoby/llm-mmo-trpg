"""HC-7 a 裁定 4、10：傳承請求的 ``records`` 只擋格式，帶幾個照規則 ``max_carry``。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trpg.content.flash_templates import INHERIT_RECORDS_FORMAT_MAX, FlashRules
from trpg.content.library import ContentLibrary
from trpg.content.schemas import field_bounds
from trpg.roguelite.flashes import _carried_problem, max_carry
from trpg.roguelite.state import InheritChoice
from trpg.skillgen.flash_state import SkillFlash
from trpg.world.actions import InheritAction


def test_format_bound_follows_the_major_flash_schema() -> None:
    assert field_bounds(FlashRules, "major_flash")[1] - 1 == INHERIT_RECORDS_FORMAT_MAX


def test_requests_wider_than_the_rule_still_parse(library: ContentLibrary) -> None:
    """規則上限（現值 2）以上、格式上限以內的請求照樣讀得進來，由傳承檢查擋下並說明。"""
    wide = tuple(range(1, max_carry(library) + 2))
    assert len(wide) <= INHERIT_RECORDS_FORMAT_MAX
    InheritChoice(skill="a", source="b", records=wide)
    InheritAction(skill="a", source="b", records=wide)
    too_many = tuple(range(1, INHERIT_RECORDS_FORMAT_MAX + 2))
    with pytest.raises(ValidationError):
        InheritChoice(skill="a", source="b", records=too_many)
    with pytest.raises(ValidationError):
        InheritAction(skill="a", source="b", records=too_many)


def test_rule_still_caps_what_is_carried(library: ContentLibrary) -> None:

    picked = list(range(1, max_carry(library) + 2))
    problem = _carried_problem(library, SkillFlash(base_id="x"), picked)
    assert problem == f"最多帶走 {max_carry(library)} 個小變化"
