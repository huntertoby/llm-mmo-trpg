"""閃現轉型：複合技整招（含接續段）當作轉型的基底（玩法 PM 決定；06 6.34.5 #70、#73）。

玩法 PM：「要帶走。複合技轉型時，整招（含接續段）一起當作轉型的基底，預算照新結構重算；否則蓄力斬
這類技能轉完會沒有傷害。」新種類都沒有接續段，接續段的效果併入新結構的效果清單。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import answered, give_turn, library
from tests.skillgen.test_flash_major import _battle, _dice_count
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import Attack
from trpg.engine.events import DamageDealt, ReactionTriggered, SkillTriggered
from trpg.narrative.skills import skill_card
from trpg.shared.types import Element, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_offer import FlashRequest, UsageSource, choose, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

FOLLOWUP_ONLY = ("skill_charged_cleave", "skill_parry_riposte", "skill_shadow_whirl")
"""主段沒有敵對效果、傷害只在接續段的複合技。"""
TIER1 = ("to_passive_on_hit", "to_reaction_melee")
DAMAGING = (*TIER1, "to_trap")
ALL = (*DAMAGING, "to_summon", "to_stance", "to_modifier")
SEED = 11


def _transform(template: str) -> Variation:
    return Variation(source="transform", template=template, category="transform")


def _derived(base_id: str, template: str, tier: int) -> SkillDef:
    lib = library()
    record = FlashRecord(nth=3, variation=_transform(template))
    state = SkillFlash(base_id=base_id, records=(record,), used=True)
    return derive_skill(lib, lib.skills[base_id], state, SEED, tier)


@pytest.mark.parametrize("base_id", FOLLOWUP_ONLY)
def test_followup_only_skills_have_no_hostile_main_segment(base_id: str) -> None:
    skill = library().skills[base_id]
    assert skill.followup is not None
    assert not any(e.type == "damage" for e in skill.effects)
    assert any(e.type == "damage" for e in skill.followup.effects)


@pytest.mark.parametrize("base_id", FOLLOWUP_ONLY)
@pytest.mark.parametrize("template", ALL)
def test_followup_skill_transforms_into_a_legal_skill(base_id: str, template: str) -> None:
    lib = library()
    skill = _derived(base_id, template, 3)
    assert skill.id != base_id  # 真的轉型了（不是退回原招）
    assert skill.followup is None
    assert validate_skill(skill, lib) == []
    report = skill_budget(skill, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio  # 預算比例在窗內


@pytest.mark.parametrize("base_id", FOLLOWUP_ONLY)
@pytest.mark.parametrize("template", DAMAGING)
def test_followup_damage_becomes_the_transformed_damage(base_id: str, template: str) -> None:
    lib = library()
    tier = 2 if template == "to_trap" else 1
    skill = _derived(base_id, template, tier)
    damage = [e for e in skill.effects if e.type == "damage"]
    assert damage and all(e.element == Element.PHYSICAL for e in damage)
    card = skill_card(lib, skill)  # 卡片上的骰子＝技能資料的骰子
    for effect in damage:
        assert effect.dice is not None
        assert str(effect.dice) in " ".join(card.effects)


def test_charged_cleave_stance_uses_the_offense_ladder() -> None:
    """整招有傷害（在接續段），姿態轉型走攻擊姿態，不是防守姿態。"""
    lib = library()
    skill = _derived("skill_charged_cleave", "to_stance", 2)
    status = skill.effects[0].status
    assert status is not None
    assert status in lib.flash.stance_ladders["physical"] or status in (
        lib.flash.transform_template("to_stance").stances.get("offense", ())  # type: ignore[union-attr]
    )


def test_charged_cleave_passive_hits_with_the_card_dice() -> None:
    skill = _derived("skill_charged_cleave", "to_passive_on_hit", 1)
    result = answered(
        resolve(_battle(skill), Attack(unit_id=UnitId("unit_0001"), target_id=UnitId("unit_0002")))
    )
    triggered = next(e for e in result.events if isinstance(e, SkillTriggered))
    assert triggered.skill_id == skill.id
    after = result.events[result.events.index(triggered) + 1 :]
    damage = next(e for e in after if isinstance(e, DamageDealt))
    assert len(damage.rolls) == _dice_count(skill)  # 卡片的骰數＝實際擲出的骰數
    assert damage.element == Element.PHYSICAL


def test_charged_cleave_reaction_answers_a_melee_hit_with_the_card_dice() -> None:
    skill = _derived("skill_charged_cleave", "to_reaction_melee", 1)
    dealt: list[DamageDealt] = []
    for seed in range(40):  # 反擊要擲命中：找一個命中的種子
        state = give_turn(_battle(skill, seed=seed), "unit_0002")
        result = answered(
            resolve(state, Attack(unit_id=UnitId("unit_0002"), target_id=UnitId("unit_0001")))
        )
        dealt = [
            e for e in result.events if isinstance(e, DamageDealt) and e.target_id == "unit_0002"
        ]
        if dealt:
            break
    assert any(isinstance(e, ReactionTriggered) for e in result.events)
    assert dealt and len(dealt[0].rolls) == _dice_count(skill)


@pytest.mark.parametrize("base_id", ("skill_charged_cleave", "skill_parry_riposte"))
def test_tier1_major_offer_of_a_followup_skill_has_a_passive_or_reaction(base_id: str) -> None:
    """1 階保底（#70）：傷害只在接續段的複合技，第 3 次大變化也一定有轉型選項。（影旋斬 1 階的
    小變化不夠先閃兩次，與本修正無關，見報告。）"""
    lib = library()
    base = lib.skills[base_id]
    state = acquire(base_id).model_copy(update={"used": True})
    for _ in range(2):
        offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, tier=1))
        state, _skill = choose(state, offer, 0)
        state = state.model_copy(update={"used": True})
    offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, tier=1), UsageSource())
    assert offer.major
    found = [o for o in offer.options if o.variation.source == "transform"]
    assert len(found) == 1
    assert found[0].variation.template in TIER1
    assert any(e.type == "damage" for e in found[0].skill.effects)
