"""魔劍士方案 A 的產生與驗證（Phase 3I-3，06 6.10 #46）。

- 組合器與 LLM 提議只在主角「第二高與最高屬性差 ≤ 4」時給第二屬性，機率 30%；第二屬性取主角
  最高的心智屬性（武器技）或最高的允許屬性（法術技）；稀有以上。
- 驗證器：武器技的第二屬性只能是心智屬性；身體類法術沒有第二屬性。
- 3H-7 留下：修正規則的 ``add_element``、命中後效果算主題訊號。
- 工坊第二屬性選單：武器技列心智屬性，會讓驗證器報錯的選項事前停用（3-48h 機制）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import STRIKE, walk_draft
from trpg.content.skill_scaling import ScalingFacts
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute
from trpg.skillgen import option_scaling
from trpg.skillgen.draft import DraftError, build_skill
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.scaling import (
    dual_eligible,
    grant_dual,
    hero_dual_ok,
    hero_secondary,
    retarget_scaling,
)
from trpg.skillgen.validate import validate_skill

A = Attribute
LIB = library()


def _hero(**over: int) -> dict[Attribute, int]:
    values = {a: 10 for a in A} | {Attribute(k): v for k, v in over.items()}
    return values


# ---------------------------------------------------------------------------
# 條件：第二高與最高差 ≤ 4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("attrs", "ok"),
    [
        (_hero(str=16, int=12), True),  # 差 4
        (_hero(str=17, int=12), False),  # 差 5
        (_hero(str=14, int=14), True),  # 並列
        (_hero(str=20), False),  # 其他都是 10
        (_hero(), True),  # 全部相同
    ],
)
def test_the_hero_gap_rule(attrs: dict[Attribute, int], ok: bool) -> None:
    assert hero_dual_ok(attrs, LIB) is ok


def _weapon_skill(**over: Any) -> SkillDef:
    base = LIB.skills["skill_cleave"]
    provenance = base.provenance.model_copy(update={"origin": "level_up"})
    update = {"id": "skill_t_dual", "provenance": provenance, "rarity": "rare", **over}
    return base.model_copy(update=update)


def test_the_hero_secondary_is_the_highest_mind_attribute() -> None:
    skill = _weapon_skill()
    assert hero_secondary(skill, _hero(str=16, int=12, wis=14), LIB) is A.WIS
    assert hero_secondary(skill, _hero(str=16, wil=15, wis=14), LIB) is A.WIL
    assert hero_secondary(skill, _hero(str=20, int=12), LIB) is None  # 差太多
    # 並列依六屬性順序（智力在感知之前）
    assert hero_secondary(skill, _hero(str=14, int=13, wis=13), LIB) is A.INT


def test_a_dual_skill_keeps_or_loses_its_second_attribute_by_the_hero_gap() -> None:
    skill = _weapon_skill(secondary_scaling_attr=A.INT)
    near = retarget_scaling(skill, _hero(str=16, wis=15), LIB)
    assert near.secondary_scaling_attr is A.WIS  # 換成主角最高的心智屬性
    far = retarget_scaling(skill, _hero(str=20, int=12), LIB)
    assert far.secondary_scaling_attr is None
    assert far.scaling_attr is A.STR  # 武器技的主屬性仍是武器大類的


def test_a_spell_dual_skill_follows_the_same_gap_rule() -> None:
    spell = LIB.skills["skill_fire_bolt"]
    provenance = spell.provenance.model_copy(update={"origin": "level_up"})
    dual = spell.model_copy(
        update={
            "id": "skill_t_dual_spell",
            "provenance": provenance,
            "rarity": "rare",
            "scaling_attr": A.INT,
            "secondary_scaling_attr": A.WIL,
        }
    )
    # 純火焰法術的範圍只有智力：沒有別的屬性可當第二屬性 → 拿掉
    assert retarget_scaling(dual, _hero(int=16, wil=15), LIB).secondary_scaling_attr is None


# ---------------------------------------------------------------------------
# 組合器與 LLM 提議
# ---------------------------------------------------------------------------


def test_the_composer_with_a_hero_gives_the_highest_mind_attribute_only_when_close() -> None:
    near = _hero(str=15, int=13, wil=14)
    far = _hero(str=24, int=13)
    seen_near = seen_far = 0
    for seed in range(300):
        for hero, near_case in ((near, True), (far, False)):
            skill = compose_random_skill(
                seed,
                tier=3,  # 雙屬性縮放要角色 3 階（3W-9）
                rarity="rare",
                skeleton="strike",
                category="weapon",
                library=LIB,
                hero_attributes=hero,
            )
            second = skill.secondary_scaling_attr
            if second is None:
                continue
            if near_case:
                seen_near += 1
                assert second is A.WIL  # 主角最高的心智屬性
            else:
                seen_far += 1
            assert validate_skill(skill, LIB) == []
    assert seen_near > 0
    assert seen_far == 0


def test_grant_dual_is_deterministic_and_roughly_thirty_percent() -> None:
    hero = _hero(str=15, int=14)
    hits = 0
    total = 600
    for i in range(total):
        skill = _weapon_skill(id=f"skill_t_dual_{i}")
        first = grant_dual(skill, hero, LIB)
        assert grant_dual(skill, hero, LIB) == first  # 同樣的技能 ID 必得同樣的結果
        if first.secondary_scaling_attr is not None:
            hits += 1
            assert first.secondary_scaling_attr is A.INT
    assert 0.2 * total < hits < 0.4 * total  # dual_permille ＝ 300


def test_grant_dual_respects_rarity_gap_and_existing_values() -> None:
    hero = _hero(str=15, int=14)
    for i in range(60):
        common = _weapon_skill(id=f"skill_t_c_{i}", rarity="common")
        assert grant_dual(common, hero, LIB).secondary_scaling_attr is None
        gap = _weapon_skill(id=f"skill_t_g_{i}")
        assert grant_dual(gap, _hero(str=30), LIB).secondary_scaling_attr is None
    dual = _weapon_skill(secondary_scaling_attr=A.WIS)
    assert grant_dual(dual, hero, LIB) is dual


def test_dual_eligibility_by_kind_and_rarity() -> None:
    assert dual_eligible(_weapon_skill(), LIB)
    assert not dual_eligible(_weapon_skill(rarity="common"), LIB)
    body = next(
        s for s in LIB.skills.values() if s.category == "spell" and LIB.secondary_range(s) == ()
    )
    assert not dual_eligible(body.model_copy(update={"rarity": "epic"}), LIB)


# ---------------------------------------------------------------------------
# 3H-7 留下：修正規則的 add_element、命中後效果算主題訊號
# ---------------------------------------------------------------------------


def test_modifier_add_element_counts_as_a_theme_signal() -> None:
    thunder = LIB.skills["skill_thunder_hand"]  # 修正規則 add_element: lightning
    assert not thunder.effects
    basis = LIB.scaling_basis(thunder)
    assert basis.source == "effect" and basis.themes == ("elemental",)
    assert LIB.scaling_range(thunder) == (A.INT,)


def test_modifier_on_hit_effects_count_as_theme_signals() -> None:
    def draft(change: dict[str, Any]) -> ScalingFacts:
        return ScalingFacts.of_draft(
            {
                "category": "spell",
                "weapon_req": "any",
                "effects": [],
                "modifiers": [{"applies_to": {"actions": ["attack"]}, "change": change}],
            }
        )

    burning = draft({"on_hit_effects": [{"type": "apply_status", "status": "burning"}]})
    assert LIB.scaling_range(burning) == (A.INT,)  # 點燃（燃燒狀態）→ 元素
    holy = draft({"add_element": "holy"})
    assert LIB.scaling_range(holy)[0] is A.WIS  # 神聖歸感知
    shadow = draft({"add_element": "shadow"})
    assert LIB.scaling_range(shadow)[0] is A.WIL
    nothing = draft({"damage_permille": 100})  # 沒有訊號：身體類
    assert LIB.scaling_basis(nothing).source == "body"


# ---------------------------------------------------------------------------
# 驗證器與工坊選單
# ---------------------------------------------------------------------------


def test_validator_messages_for_weapon_and_body_second_attributes() -> None:
    physical = _weapon_skill(secondary_scaling_attr=A.DEX, rarity="epic")
    found = [v.message for v in validate_skill(physical, LIB) if v.rule == "scaling.range"]
    assert len(found) == 1 and "心智屬性" in found[0] and "敏捷" in found[0]
    mind = _weapon_skill(secondary_scaling_attr=A.WIL, rarity="rare")
    assert [v for v in validate_skill(mind, LIB) if v.rule.startswith("scaling")] == []


def test_the_workshop_menu_lists_mind_attributes_and_marks_blocked_ones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = {**walk_draft(STRIKE), "rarity": "rare"}
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "rarity")
    field = next(f for f in step.fields if f.field == "secondary_scaling_attr")
    assert [c.value for c in field.choices] == ["int", "wis", "wil"]
    assert "心智屬性" in field.description_zh
    assert all("unavailable_zh" not in c.info for c in field.choices)

    real = build_skill

    def blocked(d: Any, overrides: Any) -> Any:
        if overrides.get("secondary_scaling_attr") == "wil":
            raise DraftError(["secondary_scaling_attr：測試用的不合規則原因"])
        return real(d, overrides)

    monkeypatch.setattr(option_scaling, "build_skill", blocked)
    step = next(s for s in draft_options(draft, LIB).steps if s.id == "rarity")
    field = next(f for f in step.fields if f.field == "secondary_scaling_attr")
    marks = {c.value: c.info.get("unavailable_zh") for c in field.choices}
    assert marks["int"] is None and marks["wis"] is None
    assert marks["wil"] is not None
