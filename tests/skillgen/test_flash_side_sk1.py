"""SK-1（06 6.38 第 3 點，#166）：閃現側變與補模板。

- 側變（``side: true``）：換形狀可換骨架、換元素、推 ↔ 拉、換觸發時機、以血支付；每次閃現最多 1 張。
- 新小變化：收回射程、蓄勢、利用地面、距離加碼、擊殺重置、每場一次、附淨化／附加速。
- 不做：打帶跑、濺射、拋射、分打（沒有這些模板）。
行為一致：預算比例在窗內、分數不低於變化前、驗證通過。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import apply_variation, at_role_tier
from trpg.skillgen.flash_offer import FlashRequest, flash_slots, is_side, make_offer
from trpg.skillgen.flash_state import SkillFlash, Variation, acquire
from trpg.skillgen.flash_trade import MINOR_OPS
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

SIDES = ("reshape_skeleton", "element_swap", "push_pull_swap", "trigger_swap", "cost_blood")
NEW = (
    "range_reclaim",
    "momentum_buff",
    "surface_exploit",
    "distance_bonus",
    "kill_reset",
    "cost_once",
    "support_cleanse",
    "support_haste",
)


def _variation(template_id: str, **params: object) -> Variation:
    template = library().flash.minor_template(template_id)
    assert template is not None
    return Variation.model_validate(
        {"source": "minor", "template": template_id, "category": template.category, **params}
    )


def _at(skill_id: str, tier: int = 1) -> SkillDef:
    return at_role_tier(library(), library().skills[skill_id], tier)


def _apply(skill: SkillDef, variation: Variation) -> SkillDef:
    lib = library()
    after = apply_variation(lib, skill, variation, bonus=40, rng=Rng(3))
    assert after is not None, variation.template
    assert validate_skill(after, lib) == []
    report = skill_budget(after, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio
    assert budget_power(after, lib) >= budget_power(skill, lib)
    return after


def test_templates_exist_with_ops_and_side_flags() -> None:
    table = library().flash
    for template_id in (*SIDES, *NEW):
        template = table.minor_template(template_id)
        assert template is not None, template_id
        assert template.op in MINOR_OPS, template_id
        assert template.side is (template_id in SIDES), template_id
    assert table.rules.max_side_per_offer == 1
    ops = {t.op for t in table.minor}
    assert not ops & {"hit_and_run", "splash", "lob", "split_hit"}  # 6.38 第 3 點：先不做


@pytest.mark.parametrize("shape", [{"type": "line", "size": 3}, {"type": "cone", "size": 2}])
def test_single_strike_reshapes_into_an_area_skeleton(shape: dict[str, object]) -> None:
    bolt = _at("skill_fire_bolt")
    after = _apply(bolt, _variation("reshape_skeleton", shape=shape))
    assert after.skeleton != bolt.skeleton
    assert after.shape.type == shape["type"]


def test_reshape_skeleton_skips_shapes_the_own_skeleton_allows() -> None:
    cleave = _at("skill_cleave")  # 範圍骨架本來就能換形狀：交給「換形狀」
    lib = library()
    variation = _variation("reshape_skeleton", shape={"type": "line", "size": 3})
    assert apply_variation(lib, cleave, variation, bonus=40, rng=Rng(3)) is None


def test_element_swap_changes_every_damage_element() -> None:
    bolt = _at("skill_fire_bolt")
    after = _apply(bolt, _variation("element_swap", element="ice"))
    damages = [e for e in after.effects if e.type == "damage"]
    assert damages and all(e.element is not None and e.element.value == "ice" for e in damages)


def test_range_reclaim_trades_two_tiles_of_range_for_power() -> None:
    bolt = _at("skill_fire_bolt")
    after = _apply(bolt, _variation("range_reclaim"))
    assert after.shape.range == 3


def test_momentum_adds_a_self_buff_on_hit() -> None:
    after = _apply(_at("skill_air_burst"), _variation("momentum_buff"))
    last = after.effects[-1]
    assert last.type == "apply_status" and last.status == "empowered" and last.affects == "self"


@pytest.mark.parametrize(
    ("template_id", "param", "condition"),
    [
        ("surface_exploit", "oil", "target_on_surface"),
        ("distance_bonus", "long_range", "long_range"),
        ("distance_bonus", "point_blank", "point_blank"),
    ],
)
def test_conditional_bonus_damage(template_id: str, param: str, condition: str) -> None:
    after = _apply(_at("skill_fire_bolt", 2), _variation(template_id, keyword=param))
    extra = after.effects[-1]
    assert extra.type == "damage" and extra.condition is not None
    assert extra.condition.type == condition


def test_cost_once_and_blood_price() -> None:
    once = _apply(_at("skill_air_burst"), _variation("cost_once"))
    assert once.cost.uses_per_battle == 1 and once.cost.cooldown is None
    blood = _apply(_at("skill_fire_bolt"), _variation("cost_blood"))
    assert blood.cost.mana == 10 and blood.cost.stamina == 0  # 主動技至少花 1 × 倍率（驗證器）
    assert blood.cost.hp_percent is not None and blood.cost.hp_percent > 0


def test_kill_reset_needs_a_cooldown() -> None:
    after = _apply(_at("skill_air_burst"), _variation("kill_reset"))
    first = next(e for e in after.effects if e.type == "damage")
    assert first.on_kill is not None and first.on_kill[0].type == "refund_cooldown"
    lib = library()
    bolt = _at("skill_fire_bolt")  # 沒有冷卻
    assert apply_variation(lib, bolt, _variation("kill_reset"), bonus=40, rng=Rng(3)) is None


@pytest.mark.parametrize(
    ("template_id", "kind"), [("support_cleanse", "cleanse"), ("support_haste", "apply_status")]
)
def test_support_riders_follow_the_heal(template_id: str, kind: str) -> None:
    mend = _at("skill_breathing_qi")
    after = _apply(mend, _variation(template_id))
    assert after.effects[-1].type == kind


def test_push_pull_swap() -> None:
    kick = _at("skill_gale_kick")
    after = _apply(kick, _variation("push_pull_swap"))
    assert any(e.type == "pull" for e in after.effects)
    assert not any(e.type == "push" for e in after.effects)


def _request(skill_id: str, seed: int, category: str | None = None) -> FlashRequest:
    lib = library()
    state: SkillFlash = acquire(skill_id)
    return FlashRequest(
        base=lib.skills[skill_id],
        state=state,
        usage=SkillUsage(),
        seed=seed,
        tier=1,
        category=category,
    )


@pytest.mark.parametrize("skill_id", ["skill_fire_bolt", "skill_cleave", "skill_radiant_mend"])
def test_at_most_one_side_per_offer(skill_id: str) -> None:
    lib = library()
    for seed in range(12):
        request = _request(skill_id, seed)
        offer = make_offer(lib, request)
        assert sum(is_side(lib, o.variation) for o in offer.options) <= 1
        slots = flash_slots(lib, request)
        sides = sum(is_side(lib, c.variation) for s in slots for c in s.candidates)
        assert sides <= 1
