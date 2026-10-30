"""閃現轉型：物理武器技也能轉成被動、反應、陷阱（閃現轉型查修；06 6.34.5 #73、#70）。

原因：轉型後的新技能一律是法術類（``_new_base``），法術技的傷害一定要有元素；``_hostile_core``
以前把物理元素丟掉，所以沒有元素的武器技轉被動、反應、陷阱全部被驗證器擋下，1 階（只開被動、
反應）幾乎沒有轉型可出。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import answered, library
from tests.skillgen.test_flash_major import _battle, _dice_count
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import Attack
from trpg.engine.events import DamageDealt, SkillTriggered
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Element, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_derive import apply_variation, at_role_tier, derive_skill
from trpg.skillgen.flash_major import transform_drafts
from trpg.skillgen.flash_offer import FlashRequest, UsageSource, choose, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

PHYSICAL = ("skill_wild_blade", "skill_whirlwind", "skill_sniper_shot")
TIER1 = ("to_passive_on_hit", "to_reaction_melee")
CARRY = (*TIER1, "to_trap")
BONUS = 120  # 第 3 次閃現：+120‰
SEED = 11


def _transform(template: str) -> Variation:
    return Variation(source="transform", template=template, category="transform")


def _derived(base_id: str, template: str, tier: int) -> SkillDef:
    lib = library()
    record = FlashRecord(nth=3, variation=_transform(template))
    state = SkillFlash(base_id=base_id, records=(record,), used=True)
    return derive_skill(lib, lib.skills[base_id], state, SEED, tier)


def _is_physical_weapon(skill: SkillDef) -> bool:
    damage = [e for e in skill.effects if e.type == "damage"]
    return (
        skill.category == "weapon"
        and bool(damage)
        and all(e.element in (None, Element.PHYSICAL) for e in damage)
    )


@pytest.mark.parametrize("base_id", PHYSICAL)
@pytest.mark.parametrize("template", CARRY)
def test_physical_weapon_skill_transforms_with_physical_damage(base_id: str, template: str) -> None:
    lib = library()
    assert _is_physical_weapon(lib.skills[base_id])
    tier = 2 if template == "to_trap" else 1
    skill = _derived(base_id, template, tier)
    assert validate_skill(skill, lib) == []
    report = skill_budget(skill, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio  # 預算比例在窗內
    damage = [e for e in skill.effects if e.type == "damage"]
    assert damage and all(e.element == Element.PHYSICAL for e in damage)
    card = skill_card(lib, skill)  # 卡片上的骰子＝技能資料的骰子
    for effect in damage:
        assert str(effect.dice) in " ".join(card.effects)


def test_physical_passive_transform_hits_with_the_card_dice() -> None:
    skill = _derived("skill_wild_blade", "to_passive_on_hit", 1)
    state = _battle(skill)
    result = answered(
        resolve(state, Attack(unit_id=UnitId("unit_0001"), target_id=UnitId("unit_0002")))
    )
    triggered = next(e for e in result.events if isinstance(e, SkillTriggered))
    assert triggered.skill_id == skill.id
    after = result.events[result.events.index(triggered) + 1 :]
    damage = next(e for e in after if isinstance(e, DamageDealt))
    assert len(damage.rolls) == _dice_count(skill)  # 卡片的骰數＝實際擲出的骰數
    assert damage.element == Element.PHYSICAL


@pytest.mark.parametrize("base_id", PHYSICAL)
def test_tier1_major_offer_of_a_physical_skill_has_a_passive_or_reaction(base_id: str) -> None:
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
    assert len(found) == 1  # #70 保底
    assert found[0].variation.template in TIER1
    assert found[0].skill.kind in ("passive", "reaction")


def test_most_tier1_skills_with_a_carryable_effect_can_become_passive_or_reaction() -> None:
    """1 階主動技：有可帶走的敵對效果（傷害、狀態）的，絕大多數能轉被動或反應。"""
    lib = library()
    carried = 0
    legal = 0
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        if skill.kind != "active" or skill.tier > 1:
            continue
        base = at_role_tier(lib, skill, 1)
        variations = [_transform(t) for t in TIER1]
        if not any(transform_drafts(base, v, lib) for v in variations):
            continue
        carried += 1
        legal += any(
            apply_variation(lib, base, v, bonus=BONUS, rng=Rng(1)) is not None for v in variations
        )
    assert carried >= 100
    assert legal * 10 >= carried * 9, (legal, carried)  # 修正前約 1／3（只有帶元素的法術技）
