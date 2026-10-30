"""閃現 note_zh 一致性：護盾橋接（水幕、帶電、烙印）的附帶效果寫在狀態定義上，敘事提到它們也算有
對應（閃現轉型查修；06 6.34.5 護盾類橋接、4-L11 一致性檢查）。

原因：``skill_facts`` 只看技能資料，護盾橋接的技能只寫 ``status: shielded_wet``，「破盾造水」
（``shield_break_surface: water``）、「破盾雷擊」（``shield_break_lightning``）在狀態定義裡，
所以 note_zh 照模板說明寫「一灘水」「雷電」都被判 ``note_zh.effect_mismatch``，``shield_wet``
在量測裡 46 次全被退回。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.llm.consistency import skill_facts
from trpg.llm.flash_propose import note_checker
from trpg.skillgen.flash_major import meets_floor
from trpg.skillgen.flash_offer import (
    FlashRequest,
    UsageSource,
    choose,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage

SHIELD = "skill_rune_ward"
SEED = 3

CASES = [
    ("shield_wet", "wet", "surface:water", "護盾被打破時在腳下留下一灘水"),
    ("shield_charged", "charged", "element:lightning", "護盾被打破時以雷電反擊攻擊者"),
    ("shield_marking", "marked", "status:marked", "護盾被打破時在攻擊者身上留下標記"),
]


def _third(tier: int) -> FlashRequest:
    lib = library()
    base = lib.skills[SHIELD]
    state: SkillFlash = acquire(SHIELD).model_copy(update={"used": True})
    for _ in range(2):
        offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, tier=tier))
        state, _skill = choose(state, offer, 0)
        state = state.model_copy(update={"used": True})
    request = FlashRequest(base, state, SkillUsage(), SEED, tier=tier)
    assert make_offer(lib, request, UsageSource()).major
    return request


@pytest.mark.parametrize(("template", "keyword", "fact", "note"), CASES)
def test_shield_bridge_rider_counts_as_an_effect(
    template: str, keyword: str, fact: str, note: str
) -> None:
    lib = library()
    request = _third(1)
    before = skill_before(lib, request)
    variation = Variation(source="major", template=template, category="bridge", keyword=keyword)
    option = try_variation(lib, request, variation)
    assert option is not None
    assert meets_floor(before, option.skill, lib)  # 強度下限
    assert fact in skill_facts(lib, option.skill)
    assert fact not in skill_facts(lib, before)
    check = note_checker(lib, request, before)
    assert check(variation, note) == []  # 照模板說明寫的 note 合格


def test_shield_wet_note_must_still_mention_the_water() -> None:
    lib = library()
    request = _third(1)
    before = skill_before(lib, request)
    variation = Variation(source="major", template="shield_wet", category="bridge", keyword="wet")
    codes = [p.code for p in note_checker(lib, request, before)(variation, "護盾更加堅固")]
    assert codes == ["note_zh.missing_added"]  # 加上的「水」沒被提到


def test_mentioning_lightning_without_the_charged_rider_is_still_a_mismatch() -> None:
    lib = library()
    request = _third(1)
    before = skill_before(lib, request)
    variation = Variation(source="major", template="shield_wet", category="bridge", keyword="wet")
    check = note_checker(lib, request, before)
    codes = [p.code for p in check(variation, "破盾時留下一灘水與雷電")]
    assert codes == ["note_zh.effect_mismatch"]
