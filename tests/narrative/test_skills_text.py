"""``trpg.narrative.skills`` 的測試（Phase 3-1 3.4）：技能卡片。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.narrative.skills import SkillCard, effect_summary, skill_card


def test_every_skill_has_a_card_with_one_line_per_effect() -> None:
    lib = library()
    for skill in lib.skills.values():
        card = skill_card(lib, skill)
        assert card.id == skill.id and card.name_zh == skill.name_zh
        assert len(card.effects) == len(skill.effects)
        assert card.effects == tuple(effect_summary(lib, skill, e) for e in skill.effects)
        assert card.cost[0] == f"AP {skill.ap_cost}"
        assert (card.mastery is None) == (skill.mastery is None)
        # 卡片是 pydantic：JSON 往返
        assert SkillCard.model_validate_json(card.model_dump_json()) == card


def test_trap_skill_card_describes_the_hidden_trap() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_bear_trap"])
    assert any("放置隱藏陷阱" in line for line in card.effects)


def test_mastery_note_follows_the_active_flag() -> None:
    lib = library()
    skill = next(s for s in lib.skills.values() if s.mastery is not None)
    assert "生效中" in (skill_card(lib, skill, mastery_active=True).mastery or "")
    assert "未生效" in (skill_card(lib, skill, mastery_active=False).mastery or "")
