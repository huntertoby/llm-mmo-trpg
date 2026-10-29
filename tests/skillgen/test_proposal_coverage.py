"""提議格式的結構往返盤點（Phase 4-L8）：覆蓋率下限（不得下降）、分類、每個開放的結構至少一招
手寫技能往返成功。不需要網路與模型。"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.skillgen.proposal_coverage import CATEGORIES, Inventory, round_trip_inventory

MIN_ROUND_TRIP = 248
"""往返成功的手寫技能數下限（4-L8 開工時 241／301；開放結構後只能往上調，不得下降）。"""

NEVER_OPEN = ("modifier", "form")
"""規格明定不開放的結構（修正規則的 change 欄位、形態／種族）。"""


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _inventory() -> Inventory:
    return round_trip_inventory(_lib())


def test_round_trip_coverage_floor() -> None:
    inventory = _inventory()
    assert inventory.total == len(_lib().skills)
    assert inventory.passed >= MIN_ROUND_TRIP, inventory.by_category()


def test_every_failure_is_categorized() -> None:
    for row in _inventory().rows:
        if not row.ok:
            assert row.category in CATEGORIES, row
            assert row.detail, row


def test_modifier_skills_stay_closed() -> None:
    """修正規則（modifiers）不開放：用到的手寫技能全部歸在不開放的分類。"""
    groups = _inventory().by_category()
    for skill in _lib().skills.values():
        if skill.modifiers:
            assert any(skill.id in groups.get(c, ()) for c in NEVER_OPEN), skill.id
