"""Phase 3J-4b：形態開局與「在形態中 +30%」的欄位規則（Phase3J計畫.md 4.13、06 6.30）。

- 起始技能規則只為 ``enter_form`` 開放姿態；
- 開局選「形態」時給的那 1 招一定是 1 階化身（用 run 的亂數，確定性）；
- ``form_bonus_permille`` 的驗證、關鍵字推導與預算（精確倍率見 ``test_forms_3j4.py``）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library as engine_library
from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID
from tests.engine.test_combo_resources import SINGLE5, _problems
from tests.roguelite.helpers import library
from trpg.roguelite import new_keyword_run
from trpg.roguelite.start import start_weapons, starter_pools, starting_skill
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import derive_keywords, is_starter_skill

MAKERS = ("skill_form_bear", "skill_form_cat", "skill_form_roc", "skill_form_werewolf")
EXPLOITERS = ("skill_form_pounce", "skill_form_renewal", "skill_wild_roar")


def test_starter_rule_opens_stances_only_for_enter_form() -> None:
    lib = library()
    for skill_id in MAKERS:  # 1 階化身可當起始技能
        assert is_starter_skill(lib.skills[skill_id])
    for form in ("demon", "giant", "elemental", "shadow", "treant", "dragon"):  # 2 階不行
        assert not is_starter_skill(lib.skills[f"skill_form_{form}"])
    other_stances = [
        s for s in lib.skills.values() if s.kind == "stance" and s.tier == 1 and not s.form_id
    ]
    assert other_stances  # 其他姿態照舊不能當起始技能
    assert not any(is_starter_skill(s) for s in other_stances)


def test_the_form_start_pool_holds_only_the_tier_one_forms() -> None:
    lib = library()
    assert starter_pools(lib)["form"] == tuple(sorted(MAKERS))
    for other, ids in starter_pools(lib).items():  # 其他池不受影響
        assert len(ids) >= 3, other


@pytest.mark.parametrize("weapon", ["one_handed_sword", "fire_staff", "bow", "scepter"])
def test_the_form_keyword_always_gives_a_tier_one_form_for_many_seeds(weapon: str) -> None:
    lib = library()
    assert weapon in start_weapons(lib)
    seen: set[str] = set()
    for seed in range(40):
        skill = starting_skill(lib, weapon, "form", seed)
        assert skill is not None and skill.id in MAKERS and skill.tier == 1
        assert skill.form_id is not None
        assert skill == starting_skill(lib, weapon, "form", seed)  # 確定性
        seen.add(skill.id)
    assert len(seen) >= 3  # 四招隨機（用 run 的亂數），不是固定一招


def test_a_form_run_starts_with_a_form_and_another_keyword_skill() -> None:
    lib = library()
    for seed in range(25):
        run = new_keyword_run(lib, "fire_staff", ("form", "ignite"), seed)
        assert run == new_keyword_run(lib, "fire_staff", ("form", "ignite"), seed)
        first, second = run.hero.skills
        assert first in MAKERS and second != first
        assert "form" in derive_keywords(lib.skills[first], lib.keywords).makes
        swapped = new_keyword_run(lib, "fire_staff", ("ignite", "form"), seed)
        assert swapped.hero.skills[1] in MAKERS


def test_the_exploiters_stay_in_the_pool_but_are_not_starters() -> None:
    lib = library()
    for skill_id in EXPLOITERS:
        assert (
            "form" in derive_keywords(lib.skills[skill_id], lib.keywords, exclusive_only=True).uses
        )
        assert skill_id not in starter_pools(lib)["form"]


def test_form_bonus_is_valid_on_top_level_damage_and_heal_only() -> None:
    damage = {"type": "damage", "dice": "1d6", "element": "fire", "form_bonus_permille": 300}
    assert _problems(make_skill(SID, SINGLE5, [damage])) == []
    heal = {"type": "heal", "dice": "1d6", "form_bonus_permille": 300}
    assert _problems(make_skill(SID, SINGLE5, [heal], category="spell")) == []
    for bad in (0, 1001):
        with pytest.raises(ValueError, match="form_bonus_permille"):
            make_skill(SID, SINGLE5, [{**damage, "form_bonus_permille": bad}])
    with pytest.raises(ValueError, match="form_bonus_permille"):
        make_skill(
            SID,
            SINGLE5,
            [{"type": "apply_status", "status": "burning", "form_bonus_permille": 300}],
        )


def test_form_bonus_makes_a_skill_a_form_exploiter() -> None:
    lib = engine_library()
    for skill_id in EXPLOITERS:
        skill = lib.skills[skill_id]
        assert any(e.form_bonus_permille == 300 for e in skill.effects)
        assert all(e.condition is None for e in skill.effects)  # 不再多加一段條件效果
        assert "form" in derive_keywords(skill, lib.keywords).uses


def test_the_three_exploiters_stay_within_seventy_to_one_hundred_percent_of_the_budget() -> None:
    lib = engine_library()
    for skill_id in EXPLOITERS:
        report = skill_budget(lib.skills[skill_id], lib)
        assert report.ok, (skill_id, float(report.ratio))
        assert 0.7 <= float(report.ratio) <= 1.0, (skill_id, float(report.ratio))
