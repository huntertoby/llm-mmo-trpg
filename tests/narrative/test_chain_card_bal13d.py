"""BAL-13d（06 6.5「BAL-13c 定」）：技能卡的連鎖形狀行加寫「每跳 −25%」（讀 core.yaml）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.narrative.skills import skill_shape_text


def test_chain_shape_line_mentions_the_falloff() -> None:
    lib = library()
    falloff = lib.ruleset.core.chain_falloff_permille
    text = skill_shape_text(lib, lib.skills["skill_chain_lightning"])
    assert text.startswith("連鎖（")
    assert f"每跳 −{falloff // 10}%" in text


def test_other_shapes_do_not_mention_the_falloff() -> None:
    lib = library()
    assert "每跳" not in skill_shape_text(lib, lib.skills["skill_fire_bolt"])
