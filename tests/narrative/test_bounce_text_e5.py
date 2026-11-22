"""彈射的卡片文字（E5，08 8.29 E5 第 1 點：彈射就是現有的「單體→連鎖」）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import ModifierSpec
from trpg.narrative.skills import modifier_summary


def _summary(change: dict[str, object]) -> str:
    lib = library()
    rule = ModifierSpec.model_validate({"applies_to": {"all_skills": True}, "change": change})
    return modifier_summary(lib, lib.skills["skill_attack_mastery"], rule)


def test_chain_conversion_is_described_as_bounce() -> None:
    core = library().ruleset.core
    text = _summary({"shape_to": "chain"})
    assert "彈射" in text
    assert "沒打中也會跳" in text
    assert "2 格內" in text  # 轉換表的 jump_range
    assert f"−{core.chain_falloff_permille / 10:g}%" in text


def test_other_conversions_do_not_mention_bounce() -> None:
    assert "彈射" not in _summary({"shape_to": "line"})
    assert "彈射" not in _summary({"shape_to": "cone"})
