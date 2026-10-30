"""BAL-2b：姿態的費用、修正類模板適用所有（有強度旋鈕的）姿態，不只元素姿態階梯。

沒有階梯的單一狀態姿態（狂怒、堅壁…）：費用類＝維持費 ±1 搭配姿態幅度（``magnitude_permille``）
升降、修正類＝同維持費、幅度提高。行為一致：卡片數字＝實戰、預算比例在預算窗內、分數不低於變化前。
變身姿態沒有每招維持費與強度旋鈕，不出（見 BAL-2b 報告）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import caster_template, library, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1
from trpg.content.skills import SkillDef
from trpg.engine.rules.statuses import damage_taken_permille, scaled_status_def
from trpg.engine.state import StatusInstance
from trpg.narrative.status_info import status_rules
from trpg.shared.rng import Rng
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import apply_variation, at_role_tier
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.validate import validate_skill

LIGHT = Variation(source="minor", template="stance_cost_light", category="cost")
HEAVY = Variation(source="minor", template="stance_cost_heavy", category="cost")
POTENCY = Variation(source="minor", template="stance_potency", category="modifier")
PLAIN = ("skill_fury_stance", "skill_bulwark_stance")
"""沒有階梯的單一狀態姿態（內建）。"""


def _plain(skill_id: str, tier: int) -> SkillDef:
    return at_role_tier(library(), library().skills[skill_id], tier)


def _magnitude(skill: SkillDef) -> int:
    return skill.effects[0].magnitude_permille or 1000


@pytest.mark.parametrize("tier", [1, 2, 3])
@pytest.mark.parametrize("skill_id", PLAIN)
def test_cost_heavy_and_potency_are_legal_for_plain_stances_at_every_tier(
    skill_id: str, tier: int
) -> None:
    lib = library()
    stance = _plain(skill_id, tier)
    before = budget_power(stance, lib)
    heavy = apply_variation(lib, stance, HEAVY, bonus=40, rng=Rng(3))
    assert heavy is not None
    assert heavy.stance_upkeep == stance.stance_upkeep + 1
    assert _magnitude(heavy) > _magnitude(stance)  # 效果提高
    assert budget_power(heavy, lib) >= before
    potency = apply_variation(lib, stance, POTENCY, bonus=40, rng=Rng(3))
    assert potency is not None
    assert potency.stance_upkeep == stance.stance_upkeep
    assert _magnitude(potency) > _magnitude(stance)
    assert budget_power(potency, lib) > before  # 嚴格變強
    for got in (heavy, potency):
        assert validate_skill(got, lib) == []
        report = skill_budget(got, lib)
        assert report.min_ratio <= report.ratio <= report.max_ratio  # 預算比例在窗內


@pytest.mark.parametrize("skill_id", PLAIN)
def test_light_needs_upkeep_and_then_lowers_the_effect(skill_id: str) -> None:
    lib = library()
    stance = _plain(skill_id, 1)
    assert apply_variation(lib, stance, LIGHT, bonus=40, rng=Rng(3)) is None  # 沒有維持費可減
    heavy = apply_variation(lib, stance, HEAVY, bonus=80, rng=Rng(3))
    assert heavy is not None
    light = apply_variation(lib, heavy, LIGHT, bonus=80, rng=Rng(3))
    assert light is not None
    assert light.stance_upkeep == heavy.stance_upkeep - 1
    assert _magnitude(light) < _magnitude(heavy)
    assert budget_power(light, lib) >= budget_power(heavy, lib)
    assert validate_skill(light, lib) == []


@pytest.mark.parametrize("skill_id", PLAIN)
def test_card_numbers_match_the_engine_for_a_flashed_plain_stance(skill_id: str) -> None:
    """卡片（狀態規則句）寫的倍率＝引擎用的倍率（幅度提高之後）。"""
    lib = library()
    got = apply_variation(lib, _plain(skill_id, 2), POTENCY, bonus=40, rng=Rng(3))
    assert got is not None and got.effects[0].status is not None
    magnitude = _magnitude(got)
    assert magnitude > 1000
    status = lib.ruleset.status_def(got.effects[0].status)
    scaled = scaled_status_def(status, magnitude)
    text = "".join(status_rules(scaled, lib))
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([], max_hp=99)),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=99)),
        ],
    )
    unit = state.units[U1]
    unit.statuses = [StatusInstance(status_id=status.id, magnitude_permille=magnitude)]
    taken = damage_taken_permille(lib.ruleset, unit)
    assert taken == scaled.damage_taken_permille
    if taken != 1000:
        assert f"×{taken / 10:g}%" in text


def test_every_stance_with_a_knob_accepts_the_stance_templates() -> None:
    """階梯上的元素姿態、白板姿態與沒有階梯的單一狀態姿態，費用（蓄力）與修正類都有合法變化；
    只有變身姿態（沒有旋鈕）不出。"""
    lib = library()
    forms = 0
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        if skill.kind != "stance":
            continue
        if skill.form_id is not None:
            forms += 1
            for variation in (LIGHT, HEAVY, POTENCY):
                assert apply_variation(lib, skill, variation, bonus=40, rng=Rng(1)) is None
            continue
        assert apply_variation(lib, skill, HEAVY, bonus=40, rng=Rng(1)) is not None, skill.id
        assert apply_variation(lib, skill, POTENCY, bonus=40, rng=Rng(1)) is not None, skill.id
    assert forms >= 8
