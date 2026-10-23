"""縮放範圍補齊（Phase 3H-7，06 6.10）：驗證器 ``scaling.range``、工坊選單只列允許屬性、隨機組合器
與工坊「隨機」只在範圍內抽、第二屬性限在範圍內、候選的武器技看手上武器。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute
from trpg.skillgen.candidates import follows_attr
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_models import FieldSpec
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.scaling import fit_draft_scaling, fit_scaling, retarget_scaling
from trpg.skillgen.validate import validate_skill

A = Attribute
LIB = library()


def _generated(skill_id: str, **update: Any) -> SkillDef:
    """內建技能改成「產生的」技能（不同 ID、不是內建）再改欄位。"""
    base = LIB.skills[skill_id]
    provenance = base.provenance.model_copy(update={"origin": "workshop"})
    return base.model_copy(update={"id": "skill_t_range", "provenance": provenance, **update})


def _range_violations(skill: SkillDef) -> list[str]:
    return [v.message for v in validate_skill(skill, LIB) if v.rule == "scaling.range"]


def test_a_fire_spell_with_strength_is_rejected_with_a_chinese_reason() -> None:
    """盤點 #1：火焰法術縮放改力量 → 擋下，原因寫出主要效果與主題。"""
    assert _range_violations(_generated("skill_fire_bolt")) == []
    found = _range_violations(_generated("skill_fire_bolt", scaling_attr=A.STR))
    assert len(found) == 1
    assert "縮放屬性 力量" in found[0]
    assert "元素傷害與互動" in found[0]
    assert "只能看 智力" in found[0]


def test_a_second_attribute_outside_the_range_is_rejected() -> None:
    """盤點 #4：史詩火焰法術第二屬性設體質 → 擋下；組合主題內的第二屬性合法。"""
    epic = {"rarity": "epic"}
    bad = _generated("skill_fire_bolt", secondary_scaling_attr=A.CON, **epic)
    found = _range_violations(bad)
    assert len(found) == 1 and "第二縮放屬性 體質" in found[0]
    combo = _generated("skill_soul_burst", secondary_scaling_attr=A.INT, **epic)
    assert _range_violations(combo) == []


def test_a_weapon_skill_never_carries_a_second_attribute() -> None:
    """武器技不帶第二屬性（魔劍士方案 A 決定前）：進化而來的武器技也擋。"""
    sword = LIB.skills["skill_cleave"]
    provenance = sword.provenance.model_copy(update={"origin": "level_up", "parents": (sword.id,)})
    evolved = sword.model_copy(
        update={
            "id": "skill_cleave_evo_x",
            "provenance": provenance,
            "rarity": "epic",
            "secondary_scaling_attr": A.INT,
        }
    )
    assert any("第二縮放屬性" in m for m in _range_violations(evolved))


def test_the_arcane_blade_exception_keeps_strength_and_intelligence() -> None:
    blade = LIB.skills["skill_arcane_blade"]
    assert blade.category == "spell"
    assert LIB.scaling_range(blade) == (A.STR, A.INT)
    assert validate_skill(blade, LIB) == []


def _scaling_field(draft: dict[str, Any]) -> FieldSpec:
    options = draft_options(draft, LIB)
    basics = next(s for s in options.steps if s.id == "basics")
    return next(f for f in basics.fields if f.field == "scaling_attr")


def _draft(skill_id: str, **update: Any) -> dict[str, Any]:
    data = LIB.skills[skill_id].model_dump(mode="json", exclude_none=True)
    for key in ("id", "provenance", "tags", "narrative"):
        data.pop(key, None)
    return {**data, **update}


@pytest.mark.parametrize(
    ("skill_id", "allowed"),
    [
        ("skill_fire_bolt", ["int"]),
        ("skill_renewal", ["wis"]),
        ("skill_raise_skeleton", ["wil"]),
        ("skill_soul_burst", ["wil", "int"]),
        ("skill_gear_grapple", ["str", "dex", "con"]),
    ],
)
def test_the_workshop_lists_only_the_allowed_attributes(skill_id: str, allowed: list[str]) -> None:
    """工坊草稿沒有標籤，主題由效果推導（盤點 #3）；選單只列允許的，預設範圍裡第一個。"""
    field = _scaling_field(_draft(skill_id))
    assert [c.value for c in field.choices] == allowed
    assert field.default == allowed[0]
    assert "只能看" in (field.description_zh or "")


def test_the_workshop_check_explains_a_wrong_attribute() -> None:
    result = check_draft(_draft("skill_fire_bolt", scaling_attr="str"), LIB)
    assert not result.legal
    rules = {p.rule for p in result.problems}
    assert "scaling.range" in rules
    message = next(p.message_zh for p in result.problems if p.rule == "scaling.range")
    assert "火焰" in message and "智力" in message


@pytest.mark.parametrize("seed", range(150))
def test_random_skills_are_always_in_range(seed: int) -> None:
    """工坊「隨機」與組合器（沒有主角屬性）：只在允許範圍內抽（盤點 #5），全部合法。"""
    skill = compose_random_skill(seed, library=LIB)
    allowed = LIB.scaling_range(skill)
    assert skill.scaling_attr in allowed, (seed, skill.scaling_attr, allowed)
    if skill.secondary_scaling_attr is not None:
        assert skill.category == "spell"
        assert skill.secondary_scaling_attr in allowed
    assert validate_skill(skill, LIB) == []


@pytest.mark.parametrize("seed", range(40))
def test_random_skills_follow_the_hero_inside_the_range(seed: int) -> None:
    hero = {a: 10 for a in A} | {A.CON: 18}
    skill = compose_random_skill(seed, tier=2, library=LIB, hero_attributes=hero)
    assert skill.scaling_attr in LIB.scaling_range(skill)
    assert validate_skill(skill, LIB) == []


def test_fit_scaling_keeps_an_allowed_attribute_and_falls_back_to_the_first() -> None:
    soul = _generated("skill_soul_burst", scaling_attr=A.INT)
    assert fit_scaling(soul, LIB).scaling_attr is A.INT  # 範圍內不動
    moved = fit_scaling(_generated("skill_soul_burst", scaling_attr=A.DEX), LIB)
    assert moved.scaling_attr is A.WIL  # 範圍裡第一個（主題的屬性）
    dual = _generated(
        "skill_fire_bolt", rarity="epic", scaling_attr=A.INT, secondary_scaling_attr=A.WIL
    )
    assert fit_scaling(dual, LIB).secondary_scaling_attr is None  # 純元素沒有別的屬性
    data = fit_draft_scaling(_draft("skill_fire_bolt", scaling_attr="wil"), LIB)
    assert data["scaling_attr"] == "int"


def test_retarget_draws_the_second_attribute_from_the_range() -> None:
    """3H-3 的 retarget：第二屬性也在範圍內（主屬性以外主角最高的）。"""
    dual = _generated(
        "skill_soul_burst", rarity="epic", scaling_attr=A.WIL, secondary_scaling_attr=A.DEX
    )
    hero = {a: 10 for a in A} | {A.INT: 16, A.WIL: 12}
    moved = retarget_scaling(dual, hero, LIB)
    assert (moved.scaling_attr, moved.secondary_scaling_attr) == (A.INT, A.WIL)


def test_candidates_compare_weapon_skills_by_the_weapon_in_hand() -> None:
    """3H-6 待決 #2：加深／橋接／新方向的屬性比對，武器技看主角手上武器的屬性。"""
    cleave = LIB.skills["skill_cleave"]
    fire = LIB.skills["skill_fire_bolt"]
    dagger = (A.DEX, A.STR)
    assert follows_attr(cleave, A.DEX, dagger)
    assert not follows_attr(cleave, A.INT, dagger)
    assert follows_attr(fire, A.INT, dagger)  # 法術照技能自己的
    assert follows_attr(cleave, cleave.scaling_attr)  # 沒有武器時退回技能的提示
