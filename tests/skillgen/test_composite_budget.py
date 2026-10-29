"""Phase 3F-3a：複合技能的預算（``docs/phases/Phase3F計畫.md`` 3.3）。

複合技能點數 ＝（位移段點數 ＋ 動作段點數）×（1000 ＋ ``composite_tax_permille``）÷ 1000；兩段各自依
自己的骨架與形狀倍率計算；``trpg skills budget`` 與工坊檢查都列出兩段明細與加成。
"""

from __future__ import annotations

import io
from fractions import Fraction

from tests.engine.helpers import library
from tests.engine.test_composite_skills import CONE, CROSS, combo, combo_data
from trpg.cli.budget import print_skill_budget
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.draft_check import check_draft

DEMO = "skill_shadow_whirl"


def test_the_tax_is_150_permille_in_the_content() -> None:
    assert library().budget.composite_tax_permille == 150


def test_the_total_is_both_segments_plus_15_percent() -> None:
    lib = library()
    for skill in (combo("teleport", CONE), combo("leap", CROSS), combo("dash", CONE)):
        report = skill_budget(skill, lib)
        move = skill_budget(skill.move_segment(), lib)
        follow_skill = skill.followup_skill()
        assert follow_skill is not None
        follow = skill_budget(follow_skill, lib)
        assert report.total == (move.total + follow.total) * Fraction(115, 100)
        first, second = report.segments
        assert (first.label, second.label) == ("位移段", "動作段")
        assert first.total == move.total and second.total == follow.total
        assert report.composite_tax_permille == 150
        # 可用預算照技能本身的 AP 與代價
        assert report.usable == move.usable


def test_each_segment_uses_its_own_shape_multiplier() -> None:
    lib = library()
    cone = skill_budget(combo("teleport", CONE), lib)
    cross = skill_budget(combo("teleport", CROSS), lib)
    assert cone.segments[1].effects[0].shape == Fraction(13, 10)  # 錐形 2
    assert cross.segments[1].effects[0].shape == Fraction(18, 10)  # 十字
    assert cone.segments[0].effects[0].type == "teleport"
    assert [e.index for e in cone.effects] == [0, 1]


def test_the_cli_budget_shows_both_segments_and_the_tax() -> None:
    lib = library()
    out = io.StringIO()
    assert print_skill_budget(lib, lib.skills[DEMO], out) == 0
    text = out.getvalue()
    assert "【位移段】骨架 displace  形狀 ground_tile" in text
    assert "【動作段】骨架 area  形狀 cone" in text
    assert "複合加成 +150‰" in text and "→ 合格" in text


def test_the_workshop_check_lists_both_segments() -> None:
    lib = library()
    data = lib.skills[DEMO].model_dump(mode="json", exclude_none=True)
    result = check_draft(data, lib)
    assert result.legal, result.problems
    assert result.budget is not None
    assert [s.label for s in result.budget.segments] == ["位移段", "動作段"]
    assert result.budget.composite_tax_permille == 150
    assert result.minimum_rarity == "rare"


def test_a_common_composite_is_only_marked_by_the_workshop_check() -> None:
    # 3W-9：稀有度只是標記，普通的複合技能不再被擋；最低稀有度仍照結構算
    result = check_draft({**combo_data(), "kind": "active", "rarity": "common"}, library())
    assert result.complete, result.missing_steps
    assert "rarity.composite" not in [p.rule for p in result.problems]
    assert result.minimum_rarity == "rare"
