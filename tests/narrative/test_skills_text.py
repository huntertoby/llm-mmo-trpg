"""``trpg.narrative.skills`` 的測試（Phase 3-1 3.4）：技能卡片。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.narrative.skills import SkillCard, effect_summary, mark_repeats, skill_card
from trpg.skillgen.flash_offer import FlashRequest, try_variation
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage


def test_every_skill_has_a_card_with_one_line_per_effect() -> None:
    lib = library()
    for skill in lib.skills.values():
        card = skill_card(lib, skill)
        assert card.id == skill.id and card.name_zh == skill.name_zh
        assert len(card.effects) == len(skill.effects)
        texts = [effect_summary(lib, skill, e) for e in skill.effects]
        assert card.effects == mark_repeats([e.type for e in skill.effects], texts)
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


def test_repeated_hits_are_not_listed_twice() -> None:
    """4-L11：連打把一段傷害拆成相同的兩段時，卡片不再把同一句完整列兩次（行數仍和效果一一對應）。"""
    lib = library()
    base = lib.skills["skill_air_burst"]
    first = base.effects[0]
    half = first
    skill = base.model_copy(update={"effects": (half, half, *base.effects[1:])})
    card = skill_card(lib, skill)
    assert len(card.effects) == len(skill.effects) == len(card.effect_ids)
    assert card.effects[0].startswith("第 1 擊：1d8") and card.effects[1] == "第 2 擊：同上"
    assert len(set(card.effects)) == len(card.effects)


def test_multi_hit_flash_card_has_no_duplicate_lines() -> None:
    """4-L9 樣本「氣爆 → 濕風環撞」：連打（小變化）後的卡片不重複列風傷害。"""
    lib = library()
    state = acquire("skill_air_burst").model_copy(update={"used": True})
    request = FlashRequest(lib.skills["skill_air_burst"], state, SkillUsage(), 7)
    variation = Variation(source="minor", template="multi_hit", category="combo")
    option = try_variation(lib, request, variation)
    assert option is not None
    damages = [e for e in option.skill.effects if e.type == "damage"]
    assert len(damages) == 2 and damages[0] == damages[1]  # 兩段相同的傷害
    card = skill_card(lib, option.skill)
    assert len(set(card.effects)) == len(card.effects)
    assert "第 2 擊：同上" in card.effects
