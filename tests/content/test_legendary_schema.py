"""傳說技能的定位（Phase 3C-4a 6.2）：源力代價、改寫規則型原語、冷卻限制與手寫示範技能。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import SkillDef, skill_problems
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

DEMO = ("skill_time_surge", "skill_rallying_cry", "skill_undying_oath", "skill_mirror_cast")
LASTING = (  # 常駐類傳說（Phase 3D-6，tests/content/test_lasting_legendary_schema.py）
    "skill_war_avatar",
    "skill_kindred_flame",
    "skill_mountain_mover",
    "skill_bloodwake_stride",
    "skill_afterimage_vow",
)
GRANT = {"type": "grant_ap", "amount": 2, "affects": "self"}


def _data(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "skill_t_legend",
        "name_zh": "測試傳說",
        "tier": 1,
        "rarity": "legendary",
        "skeleton": "aura",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": 1,
        "scaling_attr": "wis",
        "shape": {"type": "self"},
        "effects": [GRANT],
        "cost": {"cooldown": 2, "source": 1},
    }
    data.update(over)
    return data


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


def test_a_valid_legendary_passes() -> None:
    skill = SkillDef.model_validate(_data())
    assert _problems(skill) == []
    assert validate_skill(skill, library()) == []


def test_a_legendary_without_source_cost_is_rejected() -> None:
    with pytest.raises(ValidationError, match=r"傳說技能必須有 cost\.source"):
        SkillDef.model_validate(_data(cost={"cooldown": 2}))


@pytest.mark.parametrize("rarity", ["common", "rare", "epic"])
def test_a_non_legendary_with_source_cost_is_rejected(rarity: str) -> None:
    with pytest.raises(ValidationError, match=r"只有傳說技能可以有 cost\.source"):
        SkillDef.model_validate(_data(rarity=rarity))


@pytest.mark.parametrize("source", [0, 3])
def test_source_cost_is_one_or_two(source: int) -> None:
    with pytest.raises(ValidationError):
        SkillDef.model_validate(_data(cost={"cooldown": 2, "source": source}))


def test_a_legendary_without_a_rule_rewrite_or_modifier_is_rejected() -> None:
    plain = SkillDef.model_validate(_data(effects=[{"type": "heal", "dice": "2d6"}]))
    assert _problems(plain) == [
        "rarity：傳說技能必須恰好有 1 個核心（改寫規則型原語、修正規則 modifiers、規則改變 "
        "rule_change 三擇一），收到 沒有"
    ]
    (violation,) = validate_skill(plain, library())
    assert violation.rule == "reference"


def test_only_active_skills_can_spend_source() -> None:
    with pytest.raises(ValidationError, match="只有主動技能與修正型傳說可以花源力"):
        SkillDef.model_validate(
            _data(
                kind="passive",
                ap_cost=None,
                skeleton="passive",
                trigger={"event": "on_turn_start"},
            )
        )


@pytest.mark.parametrize(
    ("cost", "rejected"),
    [
        ({"source": 1}, True),  # 沒有冷卻也沒有次數限制
        ({"source": 1, "cooldown": 1}, True),
        (
            {"source": 1, "cooldown": 2},
            False,
        ),  # 花源力時冷卻 ≥ 2 即可（rule_rewrite_min_cooldown_with_source）
        ({"source": 1, "uses_per_battle": 1}, False),
    ],
)
def test_source_relaxes_the_rule_rewrite_cooldown(cost: dict[str, int], rejected: bool) -> None:
    skill = SkillDef.model_validate(_data(cost=cost))
    rules = {v.rule for v in validate_skill(skill, library())}
    assert ("cap.rule_rewrite_cost" in rules) is rejected
    assert library().budget.rule_rewrite_min_cooldown_with_source == 2


def test_a_non_legendary_rule_rewrite_still_needs_cooldown_four() -> None:
    data = _data(rarity="epic", cost={"cooldown": 3})
    rules = {v.rule for v in validate_skill(SkillDef.model_validate(data), library())}
    assert "cap.rule_rewrite_cost" in rules
    data = _data(rarity="epic", cost={"cooldown": 4})
    rules = {v.rule for v in validate_skill(SkillDef.model_validate(data), library())}
    assert "cap.rule_rewrite_cost" not in rules


def test_at_most_one_rule_rewrite_per_skill() -> None:
    # 傳說「恰好 1 個核心」（Phase 3D-6）已在引用檢查擋下兩個改寫規則型原語，這裡用史詩檢查上限
    two = SkillDef.model_validate(
        _data(
            rarity="epic",
            cost={"cooldown": 4},
            effects=[GRANT, {"type": "cheat_death", "duration": 1, "affects": "self"}],
        )
    )
    assert "cap.rule_rewrite" in {v.rule for v in validate_skill(two, library())}


def test_the_source_allowance_is_part_of_the_budget() -> None:
    report = skill_budget(SkillDef.model_validate(_data()), library())
    assert ("源力 1", 250) in report.allowance_parts
    two = skill_budget(SkillDef.model_validate(_data(cost={"cooldown": 2, "source": 2})), library())
    assert ("源力 2", 500) in two.allowance_parts


def test_the_demo_legendaries_are_valid_equipped_and_cover_each_primitive() -> None:
    lib = library()
    equipped = {s for b in lib.builds.builds for s in b.hero.skills}
    primitives: set[str] = set()
    for skill_id in DEMO:
        skill = lib.skills[skill_id]
        assert skill.rarity == "legendary" and skill.cost.source in (1, 2)
        assert validate_skill(skill, lib) == [], skill_id
        assert skill_budget(skill, lib).ok, skill_id
        assert skill_id in equipped, skill_id
        primitives |= {e.type for e in skill.effects}
    assert {"grant_ap", "reset_cooldown", "cheat_death", "copy_skill"} <= primitives
    legendaries = sorted(s.id for s in lib.skills.values() if s.rarity == "legendary")
    assert legendaries == sorted(DEMO + LASTING)
