"""HC-2：量類寫死值跟著 ``quantity_scale`` 走（``docs/phases/PhaseHC-2計畫.md``）。

把 ``core.quantity_scale`` 換成 1（內容本身不動），這些位置算出來的量要剛好是 10 時的 1/10：
生成器寫死的候選法力、互動與資源回復的後備量。另外確認 schema 的量類上限是「換算前 × 最大倍率」。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from pydantic import BaseModel

from trpg.content.battle import StatusDef, SummonDetonate, SummonPulse
from trpg.content.environment import InteractionOutcome, ReactionDef
from trpg.content.flash_templates import FlashRules, TransformTemplate
from trpg.content.forms import FormTable
from trpg.content.library import ContentLibrary
from trpg.content.quantity import MAX_QUANTITY_SCALE, quantity_cap
from trpg.content.rules import CoreRules, SummonGrowth, SummonTrait
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen import composer_recipes as recipes
from trpg.skillgen import flash_major
from trpg.skillgen.budget import _restore_resource_points
from trpg.skillgen.composer_parts import Retry

_QUANTITY_COSTS = ("mana", "stamina")


def scaled_library(library: ContentLibrary, scale: int) -> ContentLibrary:
    """只把 ``core.quantity_scale`` 換掉的內容庫（內容本身不動）。"""
    core = library.ruleset.core.model_copy(update={"quantity_scale": scale})
    ruleset = library.ruleset.model_copy(update={"core": core})
    return dataclasses.replace(library, ruleset=ruleset)


def _assert_tenth(costs_one: list[dict[str, Any]], costs_ten: list[dict[str, Any]]) -> None:
    """倍率 1 的代價：法力、耐力剛好是倍率 10 的 1/10；冷卻等其他欄位相同。"""
    assert len(costs_one) == len(costs_ten) > 0
    for one, ten in zip(costs_one, costs_ten, strict=True):
        assert set(one) == set(ten)
        for key, value in ten.items():
            expected = one[key] * 10 if key in _QUANTITY_COSTS else one[key]
            assert value == expected, (key, one, ten)
    assert any(c.get("mana") for c in costs_ten)  # 真的有寫死的法力


# ---------------------------------------------------------------------------
# 生成器寫死的候選法力（flash_major、composer_recipes；X10-2b 經 core.scaled_cost）

_TRANSFORMS = [
    *(("hostile", to) for to in ("passive", "reaction", "summon", "trap")),
    *flash_major._SOURCE_BUILDERS,
]


def _builder(source: str, to: str) -> flash_major._Builder:
    if source == "hostile":
        return flash_major._BUILDERS[to]
    return flash_major._SOURCE_BUILDERS[(source, to)]


def _transform_case(
    library: ContentLibrary, source: str, to: str
) -> tuple[SkillDef, TransformTemplate]:
    """第一個做得出草稿的（技能, 轉型模板）。"""
    build = _builder(source, to)
    for template in library.flash.transforms:
        if (template.source, template.to) != (source, to):
            continue
        for skill in library.skills.values():
            if skill.kind != "active" or not flash_major._fits(template, skill, library):
                continue
            if build(skill, template, library):
                return skill, template
    pytest.fail(f"找不到 {source} → {to} 的轉型草稿")


@pytest.mark.parametrize(("source", "to"), _TRANSFORMS)
def test_transform_costs_follow_scale(library: ContentLibrary, source: str, to: str) -> None:
    skill, template = _transform_case(library, source, to)
    build = _builder(source, to)
    costs_ten = [base["cost"] for base, _ in build(skill, template, library)]
    costs_one = [base["cost"] for base, _ in build(skill, template, scaled_library(library, 1))]
    _assert_tenth(costs_one, costs_ten)


def _recipe_costs(library: ContentLibrary, name: str) -> list[dict[str, Any]]:
    recipe = recipes.Recipe(name=name, param=None, keywords=())
    for tier in (1, 2, 3):
        try:
            if name == recipes._COMPANION:
                _, drafts = recipes.passive_drafts(
                    Rng(7), library, 7, tier=tier, rarity="rare", recipe=recipe, keyword=None
                )
            else:
                _, drafts = recipes.reaction_drafts(
                    Rng(7),
                    library,
                    7,
                    tier=tier,
                    rarity="rare",
                    category="spell",
                    recipe=recipe,
                    keyword=None,
                )
        except Retry:
            continue
        return [base["cost"] for base, _ in drafts]
    pytest.fail(f"{name} 做不出草稿")


@pytest.mark.parametrize("name", [recipes._COMPANION, recipes._GUARDIAN])
def test_recipe_costs_follow_scale(library: ContentLibrary, name: str) -> None:
    _assert_tenth(_recipe_costs(scaled_library(library, 1), name), _recipe_costs(library, name))


# ---------------------------------------------------------------------------
# 後備量：沒寫時 1 × quantity_scale


def test_interaction_min_damage_default_follows_scale(library: ContentLibrary) -> None:
    outcome = InteractionOutcome(op="conduct")
    assert outcome.min_damage is None
    assert outcome.min_damage_for(10) == 10 * outcome.min_damage_for(1) == 10
    conduct = [o for r in library.ruleset.interactions.rules for o in r.then if o.op == "conduct"]
    assert conduct and all(o.min_damage == 10 for o in conduct)  # 內容照舊寫明 10


def _restore(library: ContentLibrary) -> tuple[SkillDef, Any]:
    for skill in library.skills.values():
        for effect in skill.effects:
            if effect.type == "restore_resource" and effect.resource == "mana":
                return skill, effect.model_copy(update={"amount": None})
    pytest.fail("內容沒有回復法力的技能")


def test_restore_mana_fallback_follows_scale(library: ContentLibrary) -> None:
    """``amount`` 是必填參數；後備量是 1 × scale，所以預算點數在兩種倍率下相同（量 ÷ scale）。"""
    skill, effect = _restore(library)
    one, _ = _restore_resource_points(skill, effect, scaled_library(library, 1))
    ten, note = _restore_resource_points(skill, effect, library)
    assert one == ten
    assert note.startswith("法力 10 ÷ 10")


# ---------------------------------------------------------------------------
# schema 的量類上限：換算前的上限 × 最大倍率（載入時拿不到內容的倍率）


@pytest.mark.parametrize(
    ("model", "name", "old"),
    [
        (StatusDef, "attack_bonus", 10),
        (StatusDef, "shield_reflect", 5),
        (SummonDetonate, "flat", 20),
        (SummonPulse, "heal_flat", 10),
        (ReactionDef, "shield_flat", 20),
        (FlashRules, "trigger_flat_bonus", 10),
        (FormTable, "upkeep_stamina", 20),
        (FormTable, "stance_upkeep_mana", 10),
        (SummonGrowth, "hp_per_level", 20),
        (SummonTrait, "armor_bonus", 3),
    ],
)
def test_quantity_caps_are_old_cap_times_max_scale(
    model: type[BaseModel], name: str, old: int
) -> None:
    caps = [m.le for m in model.model_fields[name].metadata if hasattr(m, "le")]
    assert caps == [old * MAX_QUANTITY_SCALE] == [quantity_cap(old)]


def test_max_scale_is_the_largest_allowed_scale() -> None:
    assert MAX_QUANTITY_SCALE == 10
    assert CoreRules.model_fields["quantity_scale"].default == 1
