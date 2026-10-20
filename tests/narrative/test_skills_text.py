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
        if skill.is_activatable and skill.ap_cost is None:  # 修正型傳說：啟動 AP（3D-6）
            assert card.cost[0] == f"AP {lib.ruleset.core.legendary_activation_ap}"
        elif skill.ap_cost is None:  # 被動／反應技沒有 AP 代價（3-4b：不再出現「AP None」）
            assert not any(part.startswith("AP") for part in card.cost)
        else:
            assert card.cost[0] == f"AP {skill.ap_cost}"
        assert (card.mastery is None) == (skill.mastery is None)
        assert (card.followup is None) == (skill.followup is None)  # 複合技能（3F-3a）
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
