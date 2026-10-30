"""BAL-2c 用途 a：變身姿態套用姿態的修正類閃現模板，以形態幅度當旋鈕。

- 修正類（``stance_potency``）：維持費不變（照形態種類，#67）、形態幅度提高、預算分數嚴格變大、
  預算比例在窗內、1～3 階都合法。
- 費用類（蓄力、輕巧）不出：維持費不能動，形態上沒有其他可動的代價。
- 行為一致：閃現後卡片的數字＝引擎（同一個 ``scaled_form_def``）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import apply_variation, at_role_tier
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.validate import validate_skill

LIGHT = Variation(source="minor", template="stance_cost_light", category="cost")
HEAVY = Variation(source="minor", template="stance_cost_heavy", category="cost")
POTENCY = Variation(source="minor", template="stance_potency", category="modifier")


def _form_skills() -> list[str]:
    return sorted(s.id for s in library().skills.values() if s.form_id is not None)


def test_there_are_ten_form_stances() -> None:
    assert len(_form_skills()) == 10


def _at(skill_id: str, tier: int) -> SkillDef:
    return at_role_tier(library(), library().skills[skill_id], tier)


@pytest.mark.parametrize("tier", [1, 2, 3])
@pytest.mark.parametrize("skill_id", _form_skills())
def test_potency_raises_the_form_magnitude_at_every_tier(skill_id: str, tier: int) -> None:
    lib = library()
    stance = _at(skill_id, tier)
    got = apply_variation(lib, stance, POTENCY, bonus=40, rng=Rng(3))
    assert got is not None
    assert got.form_id == stance.form_id and len(got.effects) == 1  # 進入形態仍是唯一效果
    assert got.stance_upkeep == 0  # 形態沒有每招維持費
    assert got.form_magnitude > stance.form_magnitude
    assert budget_power(got, lib) > budget_power(stance, lib)  # 嚴格變強
    assert validate_skill(got, lib) == []
    report = skill_budget(got, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio


@pytest.mark.parametrize("skill_id", _form_skills())
def test_cost_templates_are_not_offered_for_forms(skill_id: str) -> None:
    lib = library()
    for tier in (1, 3):
        stance = _at(skill_id, tier)
        for variation in (LIGHT, HEAVY):
            assert apply_variation(lib, stance, variation, bonus=40, rng=Rng(3)) is None


def test_the_flashed_form_card_shows_the_engine_numbers() -> None:
    lib = library()
    got = apply_variation(lib, _at("skill_form_bear", 2), POTENCY, bonus=40, rng=Rng(3))
    assert got is not None
    magnitude = got.form_magnitude
    form = lib.ruleset.scaled_form("bear", magnitude)
    card = "".join(skill_card(lib, got).effects)
    assert f"幅度強化 ×{magnitude / 10:g}%" in card
    assert f"最大 HP +{form.effects.max_hp_permille / 10:g}%" in card
    assert f"防禦 +{form.effects.defense_permille / 10:g}%" in card
